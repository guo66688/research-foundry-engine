from __future__ import annotations

from typing import Any, Dict, List, Sequence


def bucket_for_record(record: Dict[str, Any]) -> str:
    buckets = list(record.get("topic_buckets") or [])
    if buckets:
        return str(buckets[0])
    return "general_llm"


def apply_diversity_constraints(
    ranked_records: Sequence[Dict[str, Any]],
    *,
    total: int,
    min_per_bucket: Dict[str, int],
    max_per_bucket: Dict[str, int],
) -> Dict[str, Any]:
    # 先满足保底桶，再按总分依次填充，同时尊重单桶上限，避免 shortlist 被单一主题刷屏。
    selected: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    remaining = list(ranked_records)

    for bucket, minimum in min_per_bucket.items():
        needed = max(int(minimum or 0), 0)
        if needed <= 0:
            continue
        for item in list(remaining):
            if len(selected) >= total or counts.get(bucket, 0) >= needed:
                break
            if bucket_for_record(item) != bucket:
                continue
            selected.append(item)
            counts[bucket] = counts.get(bucket, 0) + 1
            remaining.remove(item)

    for item in list(remaining):
        if len(selected) >= total:
            break
        bucket = bucket_for_record(item)
        bucket_max = int(max_per_bucket.get(bucket, total) or total)
        if counts.get(bucket, 0) >= bucket_max:
            skipped.append(item)
            continue
        selected.append(item)
        counts[bucket] = counts.get(bucket, 0) + 1
        remaining.remove(item)

    if len(selected) < total:
        for item in remaining:
            if len(selected) >= total:
                break
            selected.append(item)

    return {
        "selected": selected[:total],
        "skipped": skipped,
        "bucket_counts": counts,
    }


def assign_recommendation_buckets(selected: Sequence[Dict[str, Any]], shortlist_config: Dict[str, int]) -> Dict[str, List[Dict[str, Any]]]:
    # 推荐三桶和主题桶是两层逻辑：先做主题多样性，再按阅读动作拆成 must/trend/gap。
    must_read: List[Dict[str, Any]] = []
    trend_watch: List[Dict[str, Any]] = []
    gap_fill: List[Dict[str, Any]] = []

    must_target = int(shortlist_config.get("must_read", 2) or 2)
    trend_target = int(shortlist_config.get("trend_watch", 3) or 3)
    gap_target = int(shortlist_config.get("gap_fill", 5) or 5)

    remaining = list(selected)

    must_candidates = sorted(
        remaining,
        key=lambda item: (
            float(item.get("scores", {}).get("components", {}).get("knowledge_gain", 0.0)),
            float(item.get("scores", {}).get("total", 0.0)),
        ),
        reverse=True,
    )
    for item in must_candidates:
        if len(must_read) >= must_target:
            break
        must_read.append(item)
        remaining.remove(item)

    trend_candidates = sorted(
        remaining,
        key=lambda item: (
            float(item.get("scores", {}).get("components", {}).get("impact", 0.0)),
            float(item.get("scores", {}).get("components", {}).get("recency", item.get("scores", {}).get("components", {}).get("freshness", 0.0))),
            float(item.get("scores", {}).get("total", 0.0)),
        ),
        reverse=True,
    )
    for item in trend_candidates:
        if len(trend_watch) >= trend_target:
            break
        trend_watch.append(item)
        remaining.remove(item)

    gap_candidates = sorted(
        remaining,
        key=lambda item: (
            float(item.get("scores", {}).get("components", {}).get("knowledge_gain", 0.0)),
            float(item.get("scores", {}).get("components", {}).get("bridge_value", 0.0)),
            float(item.get("scores", {}).get("total", 0.0)),
        ),
        reverse=True,
    )
    for item in gap_candidates:
        if len(gap_fill) >= gap_target:
            break
        gap_fill.append(item)
        remaining.remove(item)

    for item in remaining:
        if len(trend_watch) < trend_target:
            trend_watch.append(item)
        elif len(gap_fill) < gap_target:
            gap_fill.append(item)
        elif len(must_read) < must_target:
            must_read.append(item)

    return {
        "must_read": must_read[:must_target],
        "trend_watch": trend_watch[:trend_target],
        "gap_fill": gap_fill[:gap_target],
    }
