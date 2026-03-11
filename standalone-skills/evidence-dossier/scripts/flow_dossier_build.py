from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rf_standalone.flow_dossier_figures import build_figure_manifest  # noqa: E402
from rf_standalone.flow_common import (  # noqa: E402
    canonical_paper_id,
    load_yaml,
    read_json,
    read_jsonl,
    resolve_runtime_path,
    select_profile,
    slugify,
    utc_timestamp,
)

LOGGER = logging.getLogger("flow_dossier_build")


def load_paper_record(paper_id: str, triage_file: Optional[Path], candidate_file: Optional[Path]) -> Dict[str, Any]:
    normalized_paper_id = canonical_paper_id(paper_id)
    if triage_file and triage_file.exists():
        triage_payload = read_json(triage_file, default={}) or {}
        for item in list(triage_payload.get("selected", [])) + list(triage_payload.get("rejected", [])):
            if canonical_paper_id(item.get("paper_id", "")) == normalized_paper_id:
                return item
    if candidate_file and candidate_file.exists():
        for item in read_jsonl(candidate_file):
            if canonical_paper_id(item.get("paper_id", "")) == normalized_paper_id:
                return item
    raise KeyError(f"paper_id not found in provided inputs: {normalized_paper_id}")


def abstract_snapshot(text: str, summary_length: str) -> str:
    cleaned = " ".join(text.split())
    limits = {"short": 280, "medium": 560, "long": 960}
    limit = limits.get(summary_length, 560)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def claim_lines(record: Dict[str, Any]) -> List[str]:
    abstract = record.get("abstract", "")
    statements: List[str] = []
    keywords = [
        ("benchmark", "Benchmark or evaluation emphasis is present."),
        ("ablation", "Ablation evidence is mentioned."),
        ("framework", "The paper presents a named framework or pipeline."),
        ("analysis", "The abstract signals analysis beyond raw reporting."),
        ("outperform", "The abstract claims measurable gains over a baseline."),
    ]
    for needle, line in keywords:
        if needle in abstract.lower():
            statements.append(line)
    if not statements:
        statements.append("Read the full paper to confirm the main evidence path; the abstract is light on explicit proof signals.")
    return statements


def build_dossier_markdown(
    record: Dict[str, Any],
    workflow: Dict[str, Any],
    profile: Dict[str, Any],
    figure_manifest: Optional[Dict[str, Any]],
    dossier_mode: str,
) -> str:
    policy = workflow.get("dossier_policy", {})
    sections = policy.get("include_sections", ["snapshot", "claims", "evidence", "questions"])
    summary_length = policy.get("summary_length", "medium")
    title = record.get("title", "Untitled Paper")
    paper_id = canonical_paper_id(record.get("paper_id", title))
    lines = [
        "---",
        f'title: "{title.replace(chr(34), chr(39))}"',
        f'paper_id: "{paper_id}"',
        f'profile_id: "{profile["profile_id"]}"',
        f'dossier_mode: "{dossier_mode}"',
        'state: "dossier_ready"',
        f'generated_at: "{utc_timestamp()}"',
        "---",
        "",
        f"# {title}",
        "",
    ]

    if "snapshot" in sections:
        lines.extend(
            [
                "## Snapshot",
                "",
                f"- source: `{record.get('source', 'unknown')}`",
                f"- published_at: `{record.get('published_at', 'unknown')}`",
                f"- authors: `{', '.join(record.get('authors', [])) or 'unknown'}`",
                f"- source_url: {record.get('source_url', '') or 'n/a'}",
                f"- pdf_url: {record.get('pdf_url', '') or 'n/a'}",
                f"- dossier_mode: `{dossier_mode}`",
                "",
                "## Abstract Snapshot",
                "",
                abstract_snapshot(record.get("abstract", ""), summary_length),
                "",
            ]
        )

    if "claims" in sections:
        lines.extend(["## Claim Map", ""])
        for statement in claim_lines(record):
            lines.append(f"- {statement}")
        lines.append("")

    if "evidence" in sections:
        lines.extend(["## Evidence Cues", ""])
        score_bundle = record.get("scores", {})
        if score_bundle:
            lines.append(f"- triage_total: `{score_bundle.get('total', 'n/a')}`")
            components = score_bundle.get("components", {})
            for name, value in components.items():
                lines.append(f"- {name}: `{value}`")
        else:
            lines.append("- This dossier was built without triage scores.")
        lines.append("")

        lines.extend(["## Figure Inventory", ""])
        if figure_manifest and figure_manifest.get("items"):
            for item in figure_manifest["items"]:
                lines.append(f"- `{item['name']}` from `{item['source']}`")
        else:
            lines.append("- No figure assets were captured for this dossier.")
        lines.append("")

    if "questions" in sections:
        lines.extend(
            [
                "## Reading Questions",
                "",
                "- Which result in the paper acts as the strongest evidence node?",
                "- What assumptions would fail first outside the reported setup?",
                "- Which existing notes should absorb this paper once validated?",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def resolve_dossier_mode(workflow: Dict[str, Any], requested_mode: str, skip_figures: bool) -> str:
    if requested_mode and requested_mode != "auto":
        return requested_mode
    if skip_figures:
        return "offline_no_figures"
    figure_mode = str(workflow.get("dossier_policy", {}).get("figure_mode", "disabled"))
    if figure_mode == "disabled":
        return "dossier_only"
    return "dossier_with_figures"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a structured evidence dossier for one paper.")
    parser.add_argument("--config", required=True, help="Path to workflow config")
    parser.add_argument("--profiles", required=True, help="Path to profile config")
    parser.add_argument("--profile-id", required=True, help="Profile identifier")
    parser.add_argument("--paper-id", required=True, help="Canonical paper identifier")
    parser.add_argument("--triage-file", default="", help="Optional triage_result.json path")
    parser.add_argument("--candidate-file", default="", help="Optional candidate_pool.jsonl path")
    parser.add_argument("--output", default="", help="Optional dossier output path")
    parser.add_argument(
        "--mode",
        default="auto",
        choices=["auto", "dossier_only", "dossier_with_figures", "offline_no_figures"],
        help="Explicit dossier generation mode",
    )
    parser.add_argument("--skip-figures", action="store_true", help="Disable figure extraction")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    workflow = load_yaml(Path(args.config))
    profile = select_profile(Path(args.profiles), args.profile_id)
    triage_file = Path(args.triage_file) if args.triage_file else None
    candidate_file = Path(args.candidate_file) if args.candidate_file else None
    record = load_paper_record(args.paper_id, triage_file, candidate_file)
    paper_id = canonical_paper_id(record.get("paper_id", args.paper_id))
    slug = slugify(record.get("title", paper_id))

    artifact_dir = resolve_runtime_path(workflow, "artifact")
    output_path = Path(args.output) if args.output else artifact_dir / f"dossier-{paper_id}-{slug}.md"
    figure_dir = artifact_dir / f"figures-{paper_id}"
    figure_manifest_path = artifact_dir / f"figure_manifest-{paper_id}.json"
    figure_manifest = None
    dossier_mode = resolve_dossier_mode(workflow, args.mode, args.skip_figures)

    if dossier_mode == "dossier_with_figures":
        try:
            figure_manifest = build_figure_manifest(
                paper_id,
                figure_dir,
                figure_manifest_path,
                pdf_path=None,
                timeout=int(workflow.get("runtime", {}).get("request_timeout_seconds", 20)),
                retry_limit=int(workflow.get("runtime", {}).get("retry_limit", 3)),
                max_figures=int(workflow.get("dossier_policy", {}).get("max_figures", 12)),
            )
        except RuntimeError as error:
            LOGGER.warning("figure extraction skipped: %s", error)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        build_dossier_markdown(record, workflow, profile, figure_manifest, dossier_mode),
        encoding="utf-8",
    )
    LOGGER.info("dossier=%s", output_path)
    LOGGER.info("dossier_mode=%s", dossier_mode)
    if figure_manifest:
        LOGGER.info("figure_manifest=%s", figure_manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
