from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rf_standalone.flow_common import (  # noqa: E402
    ensure_dir,
    load_yaml,
    make_run_id,
    resolve_runtime_path,
    select_profile,
    utc_timestamp,
    write_json,
    write_jsonl,
)
from rf_standalone.flow_sources import (  # noqa: E402
    fetch_arxiv_candidates,
    fetch_semantic_scholar_candidates,
)

LOGGER = logging.getLogger("flow_intake_fetch")


def dedupe_candidates(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    seen_by_paper = {}
    seen_by_title = {}
    for record in records:
        paper_key = record.get("paper_id", "")
        title_key = record.get("title", "").strip().lower()
        if paper_key and paper_key not in seen_by_paper:
            seen_by_paper[paper_key] = True
            output.append(record)
            continue
        if not paper_key and title_key and title_key not in seen_by_title:
            seen_by_title[title_key] = True
            output.append(record)
    return output


def collect_source_records(
    workflow: Dict[str, Any],
    profile: Dict[str, Any],
    source_scope: List[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]], List[str]]:
    records: List[Dict[str, Any]] = []
    source_status: Dict[str, Dict[str, Any]] = {}
    warnings: List[str] = []

    for source_name in source_scope:
        try:
            if source_name == "arxiv":
                source_records = fetch_arxiv_candidates(workflow, profile)
            elif source_name == "semantic_scholar":
                source_records = fetch_semantic_scholar_candidates(workflow, profile)
            else:
                warnings.append(f"unknown source skipped: {source_name}")
                source_status[source_name] = {
                    "status": "skipped",
                    "candidate_count": 0,
                    "warning": "unknown source name",
                }
                continue
        except RuntimeError as error:
            # 多源抓取允许部分成功，但失败源必须被显式记录。
            warnings.append(f"{source_name} failed: {error}")
            source_status[source_name] = {
                "status": "failed",
                "candidate_count": 0,
                "error": str(error),
            }
            continue

        records.extend(source_records)
        status = "ok" if source_records else "empty"
        source_status[source_name] = {
            "status": status,
            "candidate_count": len(source_records),
        }
        if not source_records:
            warnings.append(f"{source_name} returned zero records")

    return records, source_status, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and normalize candidate papers for one research profile.")
    parser.add_argument("--config", required=True, help="Path to workflow config")
    parser.add_argument("--profiles", required=True, help="Path to profile config")
    parser.add_argument("--profile-id", required=True, help="Profile identifier")
    parser.add_argument("--run-id", default="", help="Optional run identifier")
    parser.add_argument("--output", default="", help="Optional output path for candidate_pool.jsonl")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    workflow = load_yaml(Path(args.config))
    profile = select_profile(Path(args.profiles), args.profile_id)

    run_id = args.run_id or make_run_id()
    run_dir = ensure_dir(resolve_runtime_path(workflow, "run") / run_id)
    output_path = Path(args.output) if args.output else run_dir / "candidate_pool.jsonl"
    manifest_path = run_dir / "run_manifest.json"

    source_scope = list(profile.get("source_scope") or ["arxiv", "semantic_scholar"])
    records, source_status, warnings = collect_source_records(workflow, profile, source_scope)

    for record in records:
        record["run_id"] = run_id

    unique_records = dedupe_candidates(records)
    source_counts = {
        source_name: int(payload.get("candidate_count", 0))
        for source_name, payload in source_status.items()
    }
    manifest_payload = {
        "run_id": run_id,
        "profile_id": profile["profile_id"],
        "started_at": utc_timestamp(),
        "updated_at": utc_timestamp(),
        "stage": "source-intake",
        "source_counts": source_counts,
        "source_status": source_status,
        "warnings": warnings,
        "candidate_count": len(unique_records),
    }

    if not unique_records:
        write_json(
            manifest_path,
            {
                **manifest_payload,
                "status": "failed",
                "artifacts": [],
            },
        )
        LOGGER.error("no candidate records were produced")
        LOGGER.error("source_status=%s", source_status)
        return 1

    write_jsonl(output_path, unique_records)
    write_json(
        manifest_path,
        {
            **manifest_payload,
            "status": "completed",
            "artifacts": [{"kind": "candidate_pool", "path": str(output_path)}],
        },
    )

    LOGGER.info("run_id=%s", run_id)
    LOGGER.info("candidate_pool=%s", output_path)
    LOGGER.info("candidate_count=%d", len(unique_records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
