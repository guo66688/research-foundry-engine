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
    source_strategy_settings,
    utc_timestamp,
    write_json,
    write_jsonl,
)
from rf_standalone.source_pools import build_source_pools, dedupe_records, merge_for_candidate_pool  # noqa: E402
from rf_standalone.flow_sources import (  # noqa: E402
    fetch_arxiv_candidates,
    fetch_semantic_scholar_candidates,
)

LOGGER = logging.getLogger("flow_intake_fetch")


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
    fresh_pool_path = run_dir / "fresh_pool.jsonl"
    hot_pool_path = run_dir / "hot_pool.jsonl"
    manifest_path = run_dir / "run_manifest.json"

    source_strategy = source_strategy_settings(workflow)
    source_config = source_strategy.get("sources", {})
    enabled_sources = [name for name, payload in source_config.items() if isinstance(payload, dict) and payload.get("enabled", False)]
    source_scope = list(profile.get("source_scope") or enabled_sources or ["arxiv"])
    records, source_status, warnings = collect_source_records(workflow, profile, source_scope)

    for record in records:
        record["run_id"] = run_id

    source_pools = build_source_pools(records)
    fresh_pool = dedupe_records(source_pools.get("fresh_pool", []))
    hot_pool = dedupe_records(source_pools.get("hot_pool", []))
    unique_records = merge_for_candidate_pool({"fresh_pool": fresh_pool, "hot_pool": hot_pool})
    source_counts = {
        source_name: int(payload.get("candidate_count", 0))
        for source_name, payload in source_status.items()
    }
    pool_counts = {
        "fresh_pool_count": len(fresh_pool),
        "hot_pool_count": len(hot_pool),
        "candidate_pool_count": len(unique_records),
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
        "source_pools": pool_counts,
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

    write_jsonl(fresh_pool_path, fresh_pool)
    write_jsonl(hot_pool_path, hot_pool)
    write_jsonl(output_path, unique_records)
    write_json(
        manifest_path,
        {
            **manifest_payload,
            "status": "completed",
            "artifacts": [
                {"kind": "fresh_pool", "path": str(fresh_pool_path)},
                {"kind": "hot_pool", "path": str(hot_pool_path)},
                {"kind": "candidate_pool", "path": str(output_path)},
            ],
        },
    )

    LOGGER.info("run_id=%s", run_id)
    LOGGER.info("fresh_pool=%s", fresh_pool_path)
    LOGGER.info("hot_pool=%s", hot_pool_path)
    LOGGER.info("candidate_pool=%s", output_path)
    LOGGER.info("fresh_pool_count=%d", len(fresh_pool))
    LOGGER.info("hot_pool_count=%d", len(hot_pool))
    LOGGER.info("candidate_count=%d", len(unique_records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
