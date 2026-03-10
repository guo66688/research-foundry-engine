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
    days_since,
    ensure_dir,
    load_yaml,
    merged_weights,
    read_jsonl,
    resolve_runtime_path,
    select_profile,
    slugify,
    utc_timestamp,
    write_json,
)

LOGGER = logging.getLogger("flow_triage_rank")


def topical_fit(record: Dict[str, Any], profile: Dict[str, Any]) -> float:
    title = record.get("title", "").lower()
    abstract = record.get("abstract", "").lower()
    include_terms = profile.get("include_terms", [])
    exclude_terms = profile.get("exclude_terms", [])
    if any(term.lower() in f"{title}\n{abstract}" for term in exclude_terms):
        return 0.0
    if not include_terms:
        return 0.0
    hits = 0.0
    for term in include_terms:
        term_lower = term.lower()
        if term_lower in title:
            hits += 1.0
        elif term_lower in abstract:
            hits += 0.6
    return min(hits / max(len(include_terms), 1), 1.0)


def freshness(record: Dict[str, Any]) -> float:
    age_days = days_since(record.get("published_at", ""))
    if age_days is None:
        return 0.0
    if age_days <= 30:
        return 1.0
    if age_days <= 90:
        return 0.7
    if age_days <= 180:
        return 0.4
    if age_days <= 365:
        return 0.2
    return 0.0


def impact(record: Dict[str, Any]) -> float:
    influential = float(record.get("influential_citation_count", 0) or 0)
    citations = float(record.get("citation_count", 0) or 0)
    raw = max(influential * 1.5, citations)
    return min(raw / 100.0, 1.0)


def method_signal(record: Dict[str, Any]) -> float:
    abstract = record.get("abstract", "").lower()
    strong_terms = [
        "outperform",
        "state-of-the-art",
        "benchmark",
        "ablation",
        "framework",
        "architecture",
        "analysis",
    ]
    hits = sum(1 for term in strong_terms if term in abstract)
    return min(hits / 4.0, 1.0)


def score_record(record: Dict[str, Any], weights: Dict[str, float], profile: Dict[str, Any]) -> Dict[str, Any]:
    components = {
        "topical_fit": topical_fit(record, profile),
        "freshness": freshness(record),
        "impact": impact(record),
        "method_signal": method_signal(record),
    }
    total = sum(components[name] * weights[name] for name in weights)
    return {
        "components": {name: round(value, 4) for name, value in components.items()},
        "total": round(total * 10.0, 2),
    }


def dedupe_group_id(record: Dict[str, Any], strategy: str) -> str:
    paper_id = str(record.get("paper_id", "")).strip()
    title = str(record.get("title", "")).strip()
    if strategy == "paper_id_then_title":
        if paper_id:
            return f"paper:{paper_id}"
        return f"title:{slugify(title)}"
    return f"raw:{slugify(paper_id or title)}"


def tier_record(rank: int, shortlist_size: int) -> str:
    if rank < shortlist_size:
        if rank < max(1, shortlist_size // 3):
            return "priority"
        return "watch"
    return "discard"


def finalize_record(
    record: Dict[str, Any],
    *,
    decision: str,
    decision_reasons: List[str],
    tier: str,
) -> Dict[str, Any]:
    bundle = dict(record)
    bundle["tier"] = tier
    bundle["state"] = "triaged"
    bundle["decision"] = decision
    bundle["decision_reasons"] = decision_reasons
    bundle["reason"] = ", ".join(decision_reasons)
    bundle["score_breakdown"] = dict(bundle.get("scores", {}).get("components", {}))
    return bundle


def write_reading_queue(path: Path, result: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    lines = [
        "# Reading Queue",
        "",
        f"- run_id: `{result['run_id']}`",
        f"- profile_id: `{result['profile_id']}`",
        f"- generated_at: `{result['generated_at']}`",
        "",
    ]
    for index, item in enumerate(result["selected"], start=1):
        lines.append(f"## {index}. {item['title']}")
        lines.append(f"- paper_id: `{item['paper_id']}`")
        lines.append(f"- score: `{item['scores']['total']}`")
        lines.append(f"- tier: `{item['tier']}`")
        lines.append(f"- source: `{item['source']}`")
        lines.append(f"- decision_reasons: `{', '.join(item['decision_reasons'])}`")
        lines.append("")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Score and shortlist candidate papers.")
    parser.add_argument("--config", required=True, help="Path to workflow config")
    parser.add_argument("--profiles", required=True, help="Path to profile config")
    parser.add_argument("--profile-id", required=True, help="Profile identifier")
    parser.add_argument("--input", required=True, help="Path to candidate_pool.jsonl")
    parser.add_argument("--output", default="", help="Optional output path for triage_result.json")
    parser.add_argument("--queue-output", default="", help="Optional output path for reading queue markdown")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    workflow = load_yaml(Path(args.config))
    profile = select_profile(Path(args.profiles), args.profile_id)
    records = read_jsonl(Path(args.input))
    if not records:
        raise SystemExit("candidate pool is empty")

    run_id = records[0].get("run_id", "")
    run_dir = ensure_dir(resolve_runtime_path(workflow, "run") / run_id)
    output_path = Path(args.output) if args.output else run_dir / "triage_result.json"
    queue_path = (
        Path(args.queue_output)
        if args.queue_output
        else resolve_runtime_path(workflow, "artifact") / f"reading_queue-{run_id}.md"
    )

    base_weights = workflow.get("triage_policy", {}).get("score_weights", {})
    weights = merged_weights(base_weights, profile.get("scoring_overrides", {}))
    strategy = workflow.get("runtime", {}).get("dedupe_strategy", "paper_id_then_title")

    scored: List[Dict[str, Any]] = []
    for record in records:
        bundle = dict(record)
        bundle["scores"] = score_record(bundle, weights, profile)
        bundle["dedupe_group_id"] = dedupe_group_id(bundle, strategy)
        scored.append(bundle)

    # 先按组挑出主记录，再把组内剩余项作为重复项显式拒绝，避免静默消失。
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in scored:
        grouped.setdefault(item["dedupe_group_id"], []).append(item)

    primary_records: List[Dict[str, Any]] = []
    rejected_duplicates: List[Dict[str, Any]] = []
    for group_records in grouped.values():
        group_records.sort(key=lambda item: item["scores"]["total"], reverse=True)
        primary_records.append(group_records[0])
        for duplicate in group_records[1:]:
            rejected_duplicates.append(
                finalize_record(
                    duplicate,
                    decision="rejected",
                    decision_reasons=["duplicate_record", "lower_than_group_best"],
                    tier="discard",
                )
            )

    primary_records.sort(key=lambda item: item["scores"]["total"], reverse=True)
    shortlist_size = min(
        int(workflow.get("triage_policy", {}).get("shortlist_size", 12)),
        int(profile.get("max_candidates", 50)),
        len(primary_records),
    )

    selected: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = list(rejected_duplicates)
    for index, record in enumerate(primary_records):
        tier = tier_record(index, shortlist_size)
        if tier == "discard":
            rejected.append(
                finalize_record(
                    record,
                    decision="rejected",
                    decision_reasons=["below_shortlist_threshold"],
                    tier=tier,
                )
            )
        else:
            selected.append(
                finalize_record(
                    record,
                    decision="selected",
                    decision_reasons=["rank_within_shortlist"],
                    tier=tier,
                )
            )

    result = {
        "run_id": run_id,
        "profile_id": profile["profile_id"],
        "generated_at": utc_timestamp(),
        "input_path": str(Path(args.input)),
        "dedupe_strategy": strategy,
        "weights": weights,
        "stats": {
            "input_count": len(records),
            "deduped_count": len(primary_records),
            "duplicate_rejected_count": len(rejected_duplicates),
            "selected_count": len(selected),
            "rejected_count": len(rejected),
        },
        "selected": selected,
        "rejected": rejected,
    }

    write_json(output_path, result)
    write_reading_queue(queue_path, result)

    LOGGER.info("triage_result=%s", output_path)
    LOGGER.info("reading_queue=%s", queue_path)
    LOGGER.info("selected_count=%d", len(selected))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
