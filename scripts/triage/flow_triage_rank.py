from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List

import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.feedback_registry import (
    append_runtime_events,
    build_paper_state_registry,
    infer_feedback_events_from_inventory,
    load_feedback_events,
    load_registry_state,
    mark_last_feedback,
    merge_feedback_events,
    registry_paths,
)
from scripts.lib.knowledge_inventory import compact_topic_stats, scan_knowledge_inventory
from scripts.lib.paper_similarity import normalize_text, text_similarity
from scripts.lib.profile_adaptation import adaptation_for_profile, compute_profile_adaptation, empty_adaptation_state
from scripts.lib.source_routing import build_source_routing_policy, route_records_to_buckets
from scripts.lib.triage_diversity import apply_diversity_constraints
from scripts.lib.triage_scoring import score_record
from scripts.shared.flow_common import (  # noqa: E402
    ensure_dir,
    load_yaml,
    merged_weights,
    read_jsonl,
    resolve_runtime_path,
    select_profile,
    slugify,
    triage_settings,
    utc_timestamp,
    write_json,
)

LOGGER = logging.getLogger("flow_triage_rank")


def dedupe_group_id(record: Dict[str, Any], strategy: str) -> str:
    paper_id = str(record.get("paper_id", "")).strip()
    title = str(record.get("title", "")).strip()
    if strategy == "paper_id_then_title":
        if paper_id:
            return f"paper:{paper_id}"
        return f"title:{slugify(title)}"
    return f"raw:{slugify(paper_id or title)}"


def tier_record(index: int, shortlist_total: int) -> str:
    if index < max(1, shortlist_total // 5):
        return "priority"
    if index < shortlist_total:
        return "watch"
    return "discard"


def record_identity(record: Dict[str, Any]) -> str:
    paper_id = str(record.get("paper_id", "")).strip()
    if paper_id:
        return paper_id
    source_name = str(record.get("source", "")).strip().lower()
    title = normalize_text(str(record.get("title", "")))
    return f"{source_name}:{title}"


def finalize_record(
    record: Dict[str, Any],
    *,
    decision: str,
    decision_reasons: List[str],
    tier: str,
    recommendation_bucket: str = "",
    bucket_routing_reason: str = "",
    source_selection_reason: str = "",
) -> Dict[str, Any]:
    bundle = dict(record)
    bundle["tier"] = tier
    bundle["state"] = "triaged"
    bundle["decision"] = decision
    bundle["decision_reasons"] = decision_reasons
    bundle["reason"] = " | ".join(decision_reasons)
    bundle["score_breakdown"] = dict(bundle.get("scores", {}).get("components", {}))
    if recommendation_bucket:
        bundle["recommendation_bucket"] = recommendation_bucket
    if bucket_routing_reason:
        bundle["bucket_routing_reason"] = bucket_routing_reason
    if source_selection_reason:
        bundle["source_selection_reason"] = source_selection_reason
    bundle.setdefault("source", str(bundle.get("source") or ""))
    bundle.setdefault("source_role", str(bundle.get("source_role") or ""))
    bundle.setdefault("bucket_routing_reason", "")
    bundle.setdefault("source_selection_reason", "")
    explain_payload = dict(bundle.get("explain", {}))
    explain_payload.setdefault("bucket_routing_reason", bundle["bucket_routing_reason"])
    explain_payload.setdefault("source_selection_reason", bundle["source_selection_reason"])
    bundle["explain"] = explain_payload
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
    for section_name in ["must_read", "trend_watch", "gap_fill"]:
        items = list(result.get("buckets", {}).get(section_name, []))
        if not items:
            continue
        lines.append(f"## {section_name}")
        lines.append("")
        for index, item in enumerate(items, start=1):
            lines.append(f"### {index}. {item['title']}")
            lines.append(f"- paper_id: `{item['paper_id']}`")
            lines.append(f"- source: `{item.get('source', '')}` / `{item.get('source_role', '')}`")
            lines.append(f"- score: `{item['scores']['total']}`")
            lines.append(f"- bucket_hint: `{item.get('bucket_hint', '')}`")
            lines.append(f"- suggested_action: `{item.get('suggested_action', '')}`")
            lines.append(f"- bucket_routing_reason: {item.get('bucket_routing_reason', '')}")
            lines.append(f"- why_recommended: {item.get('explain', {}).get('why_recommended', '')}")
            lines.append("")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def candidate_pool_dedupe(scored_records: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    # 中文注释：先做硬去重（paper_id/标题），再做候选池内部近似去重。
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in scored_records:
        grouped.setdefault(item["dedupe_group_id"], []).append(item)

    primary_records: List[Dict[str, Any]] = []
    rejected_duplicates: List[Dict[str, Any]] = []
    explanations: List[Dict[str, Any]] = []
    for group_records in grouped.values():
        group_records.sort(key=lambda item: item["scores"]["total"], reverse=True)
        best = group_records[0]
        primary_records.append(best)
        for duplicate in group_records[1:]:
            explanation = {
                "paper_id": duplicate.get("paper_id", ""),
                "duplicate_of": best.get("paper_id", ""),
                "reasons": ["duplicate_record", "lower_than_group_best"],
            }
            explanations.append(explanation)
            rejected_duplicates.append(
                finalize_record(
                    duplicate,
                    decision="rejected",
                    decision_reasons=explanation["reasons"],
                    tier="discard",
                )
            )

    survivors: List[Dict[str, Any]] = []
    secondary_duplicates: List[Dict[str, Any]] = []
    primary_records.sort(key=lambda item: item["scores"]["total"], reverse=True)
    while primary_records:
        current = primary_records.pop(0)
        survivors.append(current)
        keep: List[Dict[str, Any]] = []
        for candidate in primary_records:
            similarity = text_similarity(
                str(current.get("title", "")),
                str(current.get("abstract", "")),
                str(candidate.get("title", "")),
                str(candidate.get("abstract", "")),
            )
            if similarity["title_overlap"] >= 0.86 or similarity["overall"] >= 0.82:
                reasons = ["candidate_pool_near_duplicate", f"similarity={similarity['overall']}"]
                explanations.append(
                    {
                        "paper_id": candidate.get("paper_id", ""),
                        "duplicate_of": current.get("paper_id", ""),
                        "reasons": reasons,
                    }
                )
                secondary_duplicates.append(
                    finalize_record(
                        candidate,
                        decision="rejected",
                        decision_reasons=reasons,
                        tier="discard",
                    )
                )
            else:
                keep.append(candidate)
        primary_records = keep
    return survivors, rejected_duplicates + secondary_duplicates, explanations


def build_explanation_index(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        str(item.get("paper_id", "")): {
            "score": item.get("scores", {}).get("total", item.get("score", 0.0)),
            "bucket_hint": item.get("bucket_hint", ""),
            "source": item.get("source", ""),
            "source_role": item.get("source_role", ""),
            "bucket_routing_reason": item.get("bucket_routing_reason", ""),
            "source_selection_reason": item.get("source_selection_reason", ""),
            "scores": item.get("scores", {}),
            "explain": item.get("explain", {}),
            "bridge_reasons": item.get("bridge_reasons", []),
            "knowledge_reasons": item.get("knowledge_reasons", []),
            "overlap_reasons": item.get("overlap_reasons", []),
            "suggested_action": item.get("suggested_action", ""),
        }
        for item in records
    }


def bucket_source_mix(bucket_payload: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, int]]:
    output: Dict[str, Dict[str, int]] = {}
    for bucket_name in ["must_read", "trend_watch", "gap_fill"]:
        source_counts: Dict[str, int] = {"arxiv": 0, "semantic_scholar": 0}
        for item in bucket_payload.get(bucket_name, []):
            source_name = str(item.get("source", "")).strip()
            if source_name not in source_counts:
                source_counts[source_name] = 0
            source_counts[source_name] += 1
        output[bucket_name] = source_counts
    return output


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

    settings = triage_settings(workflow)
    base_weights = settings["weights"]
    weights = merged_weights(base_weights, profile.get("scoring_overrides", {}))
    strategy = workflow.get("runtime", {}).get("dedupe_strategy", "paper_id_then_title")

    run_id = records[0].get("run_id", "")
    run_dir = ensure_dir(resolve_runtime_path(workflow, "run") / run_id)
    artifact_root = ensure_dir(resolve_runtime_path(workflow, "artifact"))
    output_path = Path(args.output) if args.output else run_dir / "triage_result.json"
    queue_path = (
        Path(args.queue_output)
        if args.queue_output
        else artifact_root / f"reading_queue-{run_id}.md"
    )
    explanations_path = artifact_root / f"triage_explanations-{run_id}.json"
    knowledge_inventory_path = artifact_root / "knowledge_inventory.json"
    knowledge_topic_stats_path = artifact_root / "knowledge_topic_stats.json"
    runtime_paths = registry_paths(workflow)

    notes_root = Path(workflow.get("workspace", {}).get("notes_root", "."))
    inventory = scan_knowledge_inventory(
        notes_root,
        include_daily_recommendations=settings["inventory"]["enable_daily_recommendations"],
        recent_window_days=settings["inventory"]["recent_window_days"],
    )
    write_json(knowledge_inventory_path, inventory)
    write_json(knowledge_topic_stats_path, compact_topic_stats(inventory))
    existing_feedback = load_feedback_events(runtime_paths["feedback_registry"])
    inferred_feedback = infer_feedback_events_from_inventory(
        profile_id=profile["profile_id"],
        inventory=inventory,
        existing_events=existing_feedback,
    )
    merged_feedback = merge_feedback_events(existing_feedback, inferred_feedback)
    previous_paper_state = load_registry_state(runtime_paths["paper_state_registry"], default={"papers": {}})
    paper_state_registry = build_paper_state_registry(inventory=inventory, previous_state=previous_paper_state)
    previous_adaptation = load_registry_state(
        runtime_paths["profile_adaptation_state"],
        default=empty_adaptation_state(profile["profile_id"]),
    )
    adaptation_state = compute_profile_adaptation(
        profile_id=profile["profile_id"],
        feedback_events=merged_feedback,
        settings=settings,
        previous_state=previous_adaptation,
    )
    paper_state_registry = mark_last_feedback(paper_state_registry, merged_feedback)
    append_runtime_events(
        workflow=workflow,
        feedback_events=merged_feedback,
        paper_state_registry=paper_state_registry,
        adaptation_state=adaptation_state,
    )
    active_adaptation = adaptation_for_profile(adaptation_state, profile["profile_id"])
    paper_states = dict(paper_state_registry.get("papers", {}))

    scored: List[Dict[str, Any]] = []
    for record in records:
        bundle = dict(record)
        if not str(bundle.get("source_role", "")).strip():
            source_name = str(bundle.get("source", "")).strip()
            if source_name == "arxiv":
                bundle["source_role"] = "fresh_discovery"
            elif source_name == "semantic_scholar":
                bundle["source_role"] = "trend_support"
        score_payload = score_record(
            bundle,
            weights=weights,
            profile=profile,
            inventory=inventory,
            paper_states=paper_states,
            adaptation=active_adaptation,
        )
        bundle["scores"] = {
            "components": score_payload["components"],
            "total": score_payload["total"],
        }
        bundle["score"] = score_payload["score"]
        bundle["score_breakdown"] = dict(score_payload["components"])
        bundle["profile_hits"] = score_payload["profile_hits"]
        bundle["topic_buckets"] = score_payload["topic_buckets"]
        bundle["topic_terms"] = score_payload["topic_terms"]
        bundle["slot_hits"] = score_payload["slot_hits"]
        bundle["knowledge_reasons"] = score_payload["knowledge_reasons"]
        bundle["gap_matches"] = score_payload["gap_matches"]
        bundle["bridge_reasons"] = score_payload["bridge_reasons"]
        bundle["overlap_reasons"] = score_payload["overlap_reasons"]
        bundle["overlap_records"] = score_payload["overlap_records"]
        bundle["suggested_action"] = score_payload["suggested_action"]
        bundle["suggested_action_reason"] = score_payload["suggested_action_reason"]
        bundle["bucket_hint"] = score_payload["bucket_hint"]
        bundle["explain"] = score_payload["explain"]
        bundle["dedupe_group_id"] = dedupe_group_id(bundle, strategy)
        scored.append(bundle)

    primary_records, duplicate_rejected, dedupe_explanations = candidate_pool_dedupe(scored)
    primary_records.sort(key=lambda item: item["scores"]["total"], reverse=True)

    shortlist_total = min(
        int(settings["shortlist"]["total"]),
        int(profile.get("max_candidates", 50)),
        len(primary_records),
    )
    diversified = apply_diversity_constraints(
        primary_records,
        total=shortlist_total,
        min_per_bucket=settings["diversity"]["min_per_bucket"],
        max_per_bucket=settings["diversity"]["max_per_bucket"],
    )
    # 中文注释：先满足主题多样性，再执行来源感知路由（不是统一混排后硬切片）。
    shortlisted_records = diversified["selected"]
    routing_policy = build_source_routing_policy(settings)
    routed = route_records_to_buckets(
        shortlisted_records,
        shortlist_config=settings["shortlist"],
        routing_policy=routing_policy,
    )
    bucketed = routed["buckets"]
    routing_notes = routed["notes"]

    selected: List[Dict[str, Any]] = []
    selected_ids = set()
    for bucket_name in ["must_read", "trend_watch", "gap_fill"]:
        for record in bucketed[bucket_name]:
            record_key = record_identity(record)
            selected_ids.add(record_key)
            note = routing_notes.get(record_key, {})
            selected.append(
                finalize_record(
                    record,
                    decision="selected",
                    decision_reasons=["rank_within_shortlist", f"assigned_to_{bucket_name}", f"source_routed_{record.get('source', 'unknown')}"],
                    tier="priority" if bucket_name == "must_read" else "watch",
                    recommendation_bucket=bucket_name,
                    bucket_routing_reason=str(note.get("bucket_routing_reason", "")),
                    source_selection_reason=str(note.get("source_selection_reason", "")),
                )
            )

    rejected: List[Dict[str, Any]] = list(duplicate_rejected)
    for record in primary_records:
        record_key = record_identity(record)
        if record_key in selected_ids:
            continue
        reasons = ["below_shortlist_threshold"]
        note = routing_notes.get(record_key, {})
        blocked_buckets = note.get("blocked_buckets", []) if isinstance(note, dict) else []
        if blocked_buckets and "must_read" in blocked_buckets:
            reasons.append("blocked_from_must_read_by_source_routing")
        if record in diversified["skipped"]:
            reasons.append("diversity_constraint_applied")
        rejected.append(
            finalize_record(
                record,
                decision="rejected",
                decision_reasons=reasons,
                tier="discard",
                bucket_routing_reason=str(note.get("bucket_routing_reason", "")) if isinstance(note, dict) else "",
                source_selection_reason=str(note.get("source_selection_reason", "")) if isinstance(note, dict) else "",
            )
        )

    selected.sort(key=lambda item: item["scores"]["total"], reverse=True)
    bucket_payload = {
        name: [item for item in selected if item.get("recommendation_bucket") == name]
        for name in ["must_read", "trend_watch", "gap_fill"]
    }
    source_mix_summary = bucket_source_mix(bucket_payload)
    deepread_picks = {
        "must_read_top2": [item.get("paper_id", "") for item in bucket_payload["must_read"][: settings["deepread"]["must_read_top2"]]],
        "gap_fill_top1": [item.get("paper_id", "") for item in bucket_payload["gap_fill"][: settings["deepread"]["gap_fill_top1"]]],
    }

    explanation_payload = {
        "run_id": run_id,
        "generated_at": utc_timestamp(),
        "dedupe_explanations": dedupe_explanations,
        "feedback_registry_path": str(runtime_paths["feedback_registry"]),
        "paper_state_registry_path": str(runtime_paths["paper_state_registry"]),
        "profile_adaptation_state_path": str(runtime_paths["profile_adaptation_state"]),
        "active_adaptation": active_adaptation,
        "source_routing_policy": routing_policy,
        "selected": build_explanation_index(selected),
        "rejected": build_explanation_index(rejected),
    }
    write_json(explanations_path, explanation_payload)

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
            "duplicate_rejected_count": len(duplicate_rejected),
            "selected_count": len(selected),
            "rejected_count": len(rejected),
        },
        "knowledge_inventory_path": str(knowledge_inventory_path),
        "knowledge_topic_stats_path": str(knowledge_topic_stats_path),
        "triage_explanations_path": str(explanations_path),
        "feedback_registry_path": str(runtime_paths["feedback_registry"]),
        "paper_state_registry_path": str(runtime_paths["paper_state_registry"]),
        "profile_adaptation_state_path": str(runtime_paths["profile_adaptation_state"]),
        "bucket_counts": diversified["bucket_counts"],
        "source_routing_policy": routing_policy,
        "source_mix_summary": source_mix_summary,
        "buckets": bucket_payload,
        "deepread_picks": deepread_picks,
        "selected": selected,
        "rejected": rejected,
    }

    write_json(output_path, result)
    if selected:
        write_reading_queue(queue_path, result)

    LOGGER.info("triage_result=%s", output_path)
    if selected:
        LOGGER.info("reading_queue=%s", queue_path)
    LOGGER.info("knowledge_inventory=%s", knowledge_inventory_path)
    LOGGER.info("triage_explanations=%s", explanations_path)
    LOGGER.info("selected_count=%d", len(selected))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
