from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple


POOL_BY_ROLE = {
    "fresh_discovery": "fresh_pool",
    "trend_support": "hot_pool",
    "hot_backfill": "hot_pool",
}

DEFAULT_ROLE_BY_SOURCE = {
    "arxiv": "fresh_discovery",
    "semantic_scholar": "trend_support",
}

SOURCE_PRIORITY = {
    "arxiv": 3,
    "semantic_scholar": 2,
    "local_inventory": 1,
    "canonical_map": 1,
}

POOL_PRIORITY = {
    "fresh_pool": 2,
    "hot_pool": 1,
}


def normalized_source_role(record: Dict[str, Any]) -> str:
    role = str(record.get("source_role") or "").strip()
    if role:
        return role
    source = str(record.get("source") or "").strip()
    return DEFAULT_ROLE_BY_SOURCE.get(source, "supplemental")


def resolve_pool_name(record: Dict[str, Any]) -> str:
    role = normalized_source_role(record)
    return POOL_BY_ROLE.get(role, "hot_pool")


def annotate_pool(record: Dict[str, Any]) -> Dict[str, Any]:
    bundle = dict(record)
    bundle["source_role"] = normalized_source_role(bundle)
    bundle["source_pool"] = resolve_pool_name(bundle)
    return bundle


def build_source_pools(records: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    pools = {
        "fresh_pool": [],
        "hot_pool": [],
    }
    for record in records:
        bundle = annotate_pool(record)
        pool_name = str(bundle.get("source_pool", "hot_pool"))
        if pool_name not in pools:
            pools[pool_name] = []
        pools[pool_name].append(bundle)
    return pools


def dedupe_key(record: Dict[str, Any]) -> str:
    paper_id = str(record.get("paper_id") or "").strip()
    if paper_id:
        return f"paper:{paper_id}"
    title = str(record.get("title") or "").strip().lower()
    return f"title:{title}"


def _dedupe_rank(record: Dict[str, Any]) -> Tuple[float, float, float, float]:
    source_name = str(record.get("source") or "").strip()
    source_priority = float(SOURCE_PRIORITY.get(source_name, 0))
    pool_priority = float(POOL_PRIORITY.get(str(record.get("source_pool") or ""), 0))
    citation_count = float(record.get("citation_count", 0) or 0)
    influential_count = float(record.get("influential_citation_count", 0) or 0)
    hotness = float(record.get("hotness_score", 0) or 0)
    return (source_priority, pool_priority, influential_count + citation_count * 0.2 + hotness * 0.1, citation_count)


def dedupe_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # 中文注释：跨来源去重时优先保留 arXiv/fresh 记录，避免 S2 覆盖新论文语义。
    winner_by_key: Dict[str, Dict[str, Any]] = {}
    for record in records:
        bundle = annotate_pool(record)
        key = dedupe_key(bundle)
        current = winner_by_key.get(key)
        if current is None:
            winner_by_key[key] = bundle
            continue
        if _dedupe_rank(bundle) > _dedupe_rank(current):
            winner_by_key[key] = bundle
    return list(winner_by_key.values())


def merge_for_candidate_pool(pools: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    merged = list(pools.get("fresh_pool", [])) + list(pools.get("hot_pool", []))
    return dedupe_records(merged)


def source_mix_summary(buckets: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, int]]:
    summary: Dict[str, Dict[str, int]] = {}
    for bucket_name, items in buckets.items():
        bucket_summary: Dict[str, int] = {"arxiv": 0, "semantic_scholar": 0}
        for item in items:
            source_name = str(item.get("source", "")).strip()
            if source_name not in bucket_summary:
                bucket_summary[source_name] = 0
            bucket_summary[source_name] += 1
        summary[bucket_name] = bucket_summary
    return summary
