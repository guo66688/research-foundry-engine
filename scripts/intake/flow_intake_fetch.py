from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List

import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.shared.flow_common import (  # noqa: E402
    ensure_dir,
    load_yaml,
    make_run_id,
    replace_jsonl_entry,
    resolve_runtime_path,
    select_profile,
    utc_timestamp,
    write_json,
    write_jsonl,
)
from scripts.shared.flow_sources import (  # noqa: E402
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

    source_scope = profile.get("source_scope") or ["arxiv", "semantic_scholar"]
    records: List[Dict[str, Any]] = []
    source_counts: Dict[str, int] = {}

    if "arxiv" in source_scope:
        arxiv_records = fetch_arxiv_candidates(workflow, profile)
        source_counts["arxiv"] = len(arxiv_records)
        records.extend(arxiv_records)

    if "semantic_scholar" in source_scope:
        scholar_records = fetch_semantic_scholar_candidates(workflow, profile)
        source_counts["semantic_scholar"] = len(scholar_records)
        records.extend(scholar_records)

    for record in records:
        record["run_id"] = run_id

    unique_records = dedupe_candidates(records)
    write_jsonl(output_path, unique_records)
    write_json(
        manifest_path,
        {
            "run_id": run_id,
            "profile_id": profile["profile_id"],
            "started_at": utc_timestamp(),
            "updated_at": utc_timestamp(),
            "status": "running",
            "stage": "source-intake",
            "artifacts": [{"kind": "candidate_pool", "path": str(output_path)}],
            "source_counts": source_counts,
            "candidate_count": len(unique_records),
        },
    )

    LOGGER.info("run_id=%s", run_id)
    LOGGER.info("candidate_pool=%s", output_path)
    LOGGER.info("candidate_count=%d", len(unique_records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
