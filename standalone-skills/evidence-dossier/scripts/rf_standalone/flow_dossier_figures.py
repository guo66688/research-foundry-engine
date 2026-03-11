from __future__ import annotations

import argparse
import logging
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rf_standalone.flow_common import canonical_paper_id, ensure_dir, utc_timestamp, write_json  # noqa: E402
from rf_standalone.flow_sources import _request  # noqa: E402

LOGGER = logging.getLogger("flow_dossier_figures")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".eps", ".pdf"}
SEARCH_DIR_NAMES = {"figures", "figure", "fig", "images", "img", "assets"}


def _require_fitz():
    try:
        import fitz  # type: ignore
    except ModuleNotFoundError as error:  # pragma: no cover - environment dependent
        raise RuntimeError("PyMuPDF is required for figure extraction. Install dependencies from requirements.txt.") from error
    return fitz


def _safe_extract(archive_path: Path, target_dir: Path) -> None:
    with tarfile.open(archive_path, "r:*") as archive:
        members = []
        for member in archive.getmembers():
            member_path = Path(member.name)
            if member_path.is_absolute() or ".." in member_path.parts:
                continue
            members.append(member)
        archive.extractall(path=target_dir, members=members)


def _download_arxiv_source(paper_id: str, temp_dir: Path, timeout: int, retry_limit: int) -> Optional[Path]:
    try:
        payload = _request(
            f"https://arxiv.org/e-print/{paper_id}",
            timeout=timeout,
            retry_limit=retry_limit,
            expect_json=False,
            as_bytes=True,
        )
    except RuntimeError:  # pragma: no cover - network dependent
        return None
    archive_path = temp_dir / f"{paper_id}.tar"
    try:
        archive_path.write_bytes(payload)
    except OSError:  # pragma: no cover - filesystem dependent
        return None
    return archive_path


def _download_pdf(paper_id: str, temp_dir: Path, timeout: int, retry_limit: int) -> Optional[Path]:
    try:
        payload = _request(
            f"https://arxiv.org/pdf/{paper_id}.pdf",
            timeout=timeout,
            retry_limit=retry_limit,
            expect_json=False,
            as_bytes=True,
        )
    except RuntimeError:  # pragma: no cover - network dependent
        return None
    pdf_path = temp_dir / f"{paper_id}.pdf"
    try:
        pdf_path.write_bytes(payload)
    except OSError:  # pragma: no cover - filesystem dependent
        return None
    return pdf_path


def _collect_source_files(source_root: Path) -> List[Path]:
    matches: List[Path] = []
    for path in source_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if path.parent.name.lower() in SEARCH_DIR_NAMES or any(part.lower() in SEARCH_DIR_NAMES for part in path.parts):
            matches.append(path)
    if matches:
        return matches
    return [path for path in source_root.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS]


def _copy_or_render_pdf(source_path: Path, output_dir: Path) -> List[Dict[str, object]]:
    manifest_items: List[Dict[str, object]] = []
    if source_path.suffix.lower() != ".pdf":
        target = output_dir / source_path.name
        shutil.copy2(source_path, target)
        manifest_items.append(
            {
                "name": target.name,
                "source": "source-package",
                "path": str(target),
                "format": target.suffix.lstrip(".").lower(),
                "bytes": target.stat().st_size,
            }
        )
        return manifest_items

    fitz = _require_fitz()
    document = fitz.open(source_path)
    try:
        for page_index in range(len(document)):
            pixmap = document[page_index].get_pixmap(dpi=150)
            output_name = f"{source_path.stem}-page-{page_index + 1}.png"
            output_path = output_dir / output_name
            pixmap.save(output_path)
            manifest_items.append(
                {
                    "name": output_path.name,
                    "source": "source-package-pdf",
                    "path": str(output_path),
                    "format": "png",
                    "bytes": output_path.stat().st_size,
                }
            )
    finally:
        document.close()
    return manifest_items


def _extract_pdf_images(pdf_path: Path, output_dir: Path, source_name: str) -> List[Dict[str, object]]:
    manifest_items: List[Dict[str, object]] = []
    fitz = _require_fitz()
    document = fitz.open(pdf_path)
    try:
        for page_index in range(len(document)):
            page = document[page_index]
            for image_index, image in enumerate(page.get_images(full=True), start=1):
                xref = image[0]
                try:
                    payload = document.extract_image(xref)
                except RuntimeError:
                    continue
                extension = payload.get("ext", "png")
                output_name = f"page-{page_index + 1}-image-{image_index}.{extension}"
                output_path = output_dir / output_name
                output_path.write_bytes(payload["image"])
                manifest_items.append(
                    {
                        "name": output_path.name,
                        "source": source_name,
                        "path": str(output_path),
                        "format": extension,
                        "bytes": output_path.stat().st_size,
                    }
                )
    finally:
        document.close()
    return manifest_items


def build_figure_manifest(
    paper_id: str,
    output_dir: Path,
    manifest_path: Path,
    *,
    pdf_path: Optional[Path],
    timeout: int,
    retry_limit: int,
    max_figures: int,
) -> Dict[str, object]:
    ensure_dir(output_dir)
    manifest_items: List[Dict[str, object]] = []
    normalized_paper_id = canonical_paper_id(paper_id)

    temp_root = output_dir.parent if output_dir.parent.exists() else None
    with tempfile.TemporaryDirectory(
        prefix="research-foundry-figures-",
        dir=str(temp_root) if temp_root else None,
        ignore_cleanup_errors=True,
    ) as temp_name:
        temp_dir = Path(temp_name)
        archive_path = _download_arxiv_source(normalized_paper_id, temp_dir, timeout, retry_limit)
        if archive_path is not None:
            extracted_dir = temp_dir / "source"
            ensure_dir(extracted_dir)
            try:
                _safe_extract(archive_path, extracted_dir)
            except tarfile.TarError:
                extracted_dir = temp_dir
            for source_file in _collect_source_files(extracted_dir):
                manifest_items.extend(_copy_or_render_pdf(source_file, output_dir))
                if len(manifest_items) >= max_figures:
                    break

        local_pdf = pdf_path
        if local_pdf is None:
            local_pdf = _download_pdf(normalized_paper_id, temp_dir, timeout, retry_limit)
        if local_pdf is not None and len(manifest_items) < max_figures:
            manifest_items.extend(_extract_pdf_images(local_pdf, output_dir, "pdf-fallback"))

    manifest = {
        "paper_id": normalized_paper_id,
        "generated_at": utc_timestamp(),
        "figure_count": min(len(manifest_items), max_figures),
        "items": manifest_items[:max_figures],
    }
    write_json(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract or render figures for one paper.")
    parser.add_argument("--paper-id", required=True, help="Canonical paper identifier or arXiv id")
    parser.add_argument("--output-dir", required=True, help="Directory for extracted figure assets")
    parser.add_argument("--manifest-output", required=True, help="Manifest JSON path")
    parser.add_argument("--pdf-path", default="", help="Optional local PDF path")
    parser.add_argument("--timeout", type=int, default=20, help="Request timeout in seconds")
    parser.add_argument("--retry-limit", type=int, default=3, help="Retry limit")
    parser.add_argument("--max-figures", type=int, default=12, help="Maximum figures to keep")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    pdf_path = Path(args.pdf_path) if args.pdf_path else None
    manifest = build_figure_manifest(
        args.paper_id,
        Path(args.output_dir),
        Path(args.manifest_output),
        pdf_path=pdf_path,
        timeout=args.timeout,
        retry_limit=args.retry_limit,
        max_figures=args.max_figures,
    )
    LOGGER.info("figure_manifest=%s", args.manifest_output)
    LOGGER.info("figure_count=%d", manifest["figure_count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
