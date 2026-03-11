from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Tuple

try:
    from scripts.shared.flow_common import utc_timestamp
except ModuleNotFoundError:
    from datetime import datetime, timezone

    def utc_timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


ACTIVE_STATES = {"recommended", "queued", "skimmed", "backfill_required", "revisit_due", "compared"}


def build_daily_queue(
    *,
    run_id: str,
    selected_buckets: Dict[str, List[Dict[str, Any]]],
    review_or_backfill: List[Dict[str, Any]],
    paper_state_registry: Dict[str, Any],
    queue_settings: Dict[str, Any],
) -> Dict[str, Any]:
    states = deepcopy(paper_state_registry)
    papers = states.setdefault("papers", {})
    decisions: List[Dict[str, Any]] = []
    max_daily_review = int(queue_settings.get("max_daily_review_or_backfill", 2) or 2)
    ignored_threshold = int(queue_settings.get("demote_after_ignored_runs", 3) or 3)

    _advance_ignored_runs(papers, run_id, ignored_threshold, decisions)

    final_buckets = {
        "must_read": [],
        "trend_watch": [],
        "gap_fill": [],
    }
    for bucket_name in ["must_read", "trend_watch", "gap_fill"]:
        for item in selected_buckets.get(bucket_name, []) or []:
            paper_id = str(item.get("paper_id", ""))
            state = papers.get(paper_id, {})
            status = str(state.get("status", "")).lower()
            target_bucket = bucket_name
            decision_reasons: List[str] = []

            if status in {"deepread", "archived"}:
                decisions.append(
                    {
                        "paper_id": paper_id,
                        "title": item.get("title", ""),
                        "from_bucket": bucket_name,
                        "to_bucket": "",
                        "decision": "dropped_from_daily_queue",
                        "reasons": [f"existing_state={status}"],
                    }
                )
                continue

            ignored_runs = int(state.get("ignored_runs", 0) or 0)
            if ignored_runs >= ignored_threshold and bucket_name == "must_read":
                target_bucket = "trend_watch"
                decision_reasons.append(f"demoted_after_{ignored_runs}_ignored_runs")
            elif ignored_runs >= ignored_threshold and bucket_name == "trend_watch":
                target_bucket = "gap_fill"
                decision_reasons.append(f"demoted_after_{ignored_runs}_ignored_runs")

            queue_item = deepcopy(item)
            queue_item["recommendation_bucket"] = target_bucket
            queue_item.setdefault("explain", {})
            queue_item["explain"]["feedback_adjustment"] = "；".join(decision_reasons) if decision_reasons else ""
            queue_item["score"] = item.get("scores", {}).get("total", item.get("score", 0.0))
            final_buckets[target_bucket].append(queue_item)
            _register_recommendation(papers, queue_item, run_id, target_bucket)
            decisions.append(
                {
                    "paper_id": paper_id,
                    "title": item.get("title", ""),
                    "from_bucket": bucket_name,
                    "to_bucket": target_bucket,
                    "decision": "kept" if target_bucket == bucket_name else "demoted",
                    "reasons": decision_reasons or ["selected_by_triage"],
                }
            )

    review_items = review_or_backfill[:max_daily_review]
    for item in review_items:
        paper_id = str(item.get("paper_id", ""))
        if paper_id:
            state = papers.setdefault(
                paper_id,
                {
                    "paper_id": paper_id,
                    "title": item.get("title", ""),
                    "status": "discovered",
                    "topics": list(item.get("topics", [])),
                    "knowledge_slots": list(item.get("knowledge_slots", [])),
                    "times_recommended": 0,
                    "ignored_runs": 0,
                    "recommendation_history": [],
                },
            )
            state["status"] = "revisit_due" if item.get("kind") == "revisit" else "backfill_required"
            state["last_recommended_run_id"] = run_id
            state["updated_at"] = utc_timestamp()

    queue_summary = {
        "new_candidates": sum(len(items) for items in selected_buckets.values()),
        "active_queue": sum(1 for item in papers.values() if str(item.get("status", "")) in ACTIVE_STATES),
        "revisit_due": sum(1 for item in papers.values() if str(item.get("status", "")) == "revisit_due"),
        "backfill_required": sum(1 for item in papers.values() if str(item.get("status", "")) == "backfill_required"),
    }
    states["generated_at"] = utc_timestamp()
    return {
        "final_buckets": final_buckets,
        "review_or_backfill": review_items,
        "queue_summary": queue_summary,
        "queue_decisions": {
            "run_id": run_id,
            "generated_at": utc_timestamp(),
            "decisions": decisions,
            "summary": queue_summary,
        },
        "paper_state_registry": states,
    }


def _advance_ignored_runs(
    papers: Dict[str, Any],
    run_id: str,
    ignored_threshold: int,
    decisions: List[Dict[str, Any]],
) -> None:
    for paper_id, state in papers.items():
        status = str(state.get("status", "")).lower()
        last_run = str(state.get("last_recommended_run_id", ""))
        if status not in {"recommended", "queued"} or not last_run or last_run == run_id:
            continue
        state["ignored_runs"] = int(state.get("ignored_runs", 0) or 0) + 1
        if int(state.get("ignored_runs", 0) or 0) >= ignored_threshold:
            state["status"] = "queued"
            decisions.append(
                {
                    "paper_id": paper_id,
                    "title": state.get("title", ""),
                    "from_bucket": "",
                    "to_bucket": "",
                    "decision": "marked_ignored",
                    "reasons": [f"ignored_runs={state['ignored_runs']}"],
                }
            )


def _register_recommendation(papers: Dict[str, Any], item: Dict[str, Any], run_id: str, bucket_name: str) -> None:
    paper_id = str(item.get("paper_id", ""))
    state = papers.setdefault(
        paper_id,
        {
            "paper_id": paper_id,
            "title": item.get("title", ""),
            "topics": list(item.get("topic_buckets", []) or item.get("categories", [])),
            "knowledge_slots": list(item.get("gap_matches", [])),
            "times_recommended": 0,
            "ignored_runs": 0,
            "recommendation_history": [],
        },
    )
    state["title"] = item.get("title", state.get("title", ""))
    state["status"] = "queued" if item.get("suggested_action") in {"deepread", "backfill", "compare"} else "recommended"
    state["times_recommended"] = int(state.get("times_recommended", 0) or 0) + 1
    state["last_recommended_run_id"] = run_id
    state["ignored_runs"] = 0
    history = list(state.get("recommendation_history", []))
    history.append(
        {
            "run_id": run_id,
            "bucket": bucket_name,
            "suggested_action": item.get("suggested_action", ""),
            "score": item.get("scores", {}).get("total", item.get("score", 0.0)),
        }
    )
    state["recommendation_history"] = history[-10:]
    state["updated_at"] = utc_timestamp()
