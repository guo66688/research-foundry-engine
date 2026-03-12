from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple


BUCKET_ORDER = ["must_read", "trend_watch", "gap_fill"]


def _record_key(record: Dict[str, Any]) -> str:
    paper_id = str(record.get("paper_id", "")).strip()
    if paper_id:
        return paper_id
    title = str(record.get("title", "")).strip().lower()
    source_name = str(record.get("source", "")).strip().lower()
    return f"{source_name}:{title}"


def build_source_routing_policy(settings: Dict[str, Any]) -> Dict[str, Any]:
    strategy = settings.get("source_strategy", {}) if isinstance(settings.get("source_strategy", {}), dict) else {}
    source_block = strategy.get("sources", {}) if isinstance(strategy.get("sources", {}), dict) else {}
    bucket_block = strategy.get("bucket_strategy", {}) if isinstance(strategy.get("bucket_strategy", {}), dict) else {}
    source_rules: Dict[str, Dict[str, Any]] = {}
    for source_name, raw_rule in source_block.items():
        if not isinstance(raw_rule, dict):
            raw_rule = {}
        preferred_buckets = raw_rule.get("preferred_buckets", [])
        if not isinstance(preferred_buckets, list):
            preferred_buckets = []
        restricted_buckets = raw_rule.get("restricted_buckets", [])
        if not isinstance(restricted_buckets, list):
            restricted_buckets = []
        restricted_set = {str(item) for item in restricted_buckets if str(item).strip()}
        preferred_list = [str(item) for item in preferred_buckets if str(item).strip()]
        if preferred_list:
            allowed = [bucket for bucket in preferred_list if bucket not in restricted_set]
        else:
            allowed = [bucket for bucket in BUCKET_ORDER if bucket not in restricted_set]
        source_rules[str(source_name)] = {
            "allowed_buckets": allowed,
            "restricted_buckets": sorted(restricted_set),
        }
    return {
        "source_rules": source_rules,
        "bucket_strategy": bucket_block,
    }


def _allowed_buckets(record: Dict[str, Any], source_rules: Dict[str, Dict[str, Any]]) -> List[str]:
    source_name = str(record.get("source", "")).strip()
    rule = source_rules.get(source_name)
    if rule is None:
        return list(BUCKET_ORDER)
    allowed = rule.get("allowed_buckets", [])
    if not isinstance(allowed, list):
        return list(BUCKET_ORDER)
    return [str(item) for item in allowed if str(item).strip()]


def _score_tuple(record: Dict[str, Any], bucket_name: str) -> Tuple[float, float, float]:
    components = record.get("scores", {}).get("components", {}) if isinstance(record.get("scores", {}), dict) else {}
    total_score = float(record.get("scores", {}).get("total", record.get("score", 0.0)) or 0.0)
    knowledge_gain = float(components.get("knowledge_gain", 0.0) or 0.0)
    impact = float(components.get("impact", 0.0) or 0.0)
    recency = float(components.get("recency", components.get("freshness", 0.0)) or 0.0)
    bridge_value = float(components.get("bridge_value", 0.0) or 0.0)
    if bucket_name == "must_read":
        return knowledge_gain, total_score, impact
    if bucket_name == "trend_watch":
        return impact, recency, total_score
    if bucket_name == "gap_fill":
        return knowledge_gain, bridge_value, total_score
    return total_score, knowledge_gain, impact


def _source_preference(source_name: str, prefer_sources: Sequence[str]) -> int:
    if source_name not in prefer_sources:
        return 0
    return max(len(prefer_sources) - prefer_sources.index(source_name), 1)


def _source_caps(bucket_name: str, bucket_rule: Dict[str, Any]) -> Dict[str, int]:
    caps: Dict[str, int] = {}
    max_s2 = bucket_rule.get("max_semantic_scholar_items")
    if max_s2 is not None:
        caps["semantic_scholar"] = max(int(max_s2 or 0), 0)
    return caps


def _can_take_source(source_name: str, source_counts: Dict[str, int], source_caps: Dict[str, int]) -> bool:
    if source_name not in source_caps:
        return True
    return int(source_counts.get(source_name, 0)) < int(source_caps[source_name])


def _initial_mix_quota(
    target: int,
    target_mix: Dict[str, float],
    candidates: Sequence[Dict[str, Any]],
    source_caps: Dict[str, int],
) -> Dict[str, int]:
    available_by_source: Dict[str, int] = {}
    for record in candidates:
        source_name = str(record.get("source", "")).strip()
        available_by_source[source_name] = available_by_source.get(source_name, 0) + 1

    quotas: Dict[str, int] = {}
    for source_name, ratio in target_mix.items():
        planned = int(max(target * float(ratio), 0))
        available = available_by_source.get(source_name, 0)
        if source_name in source_caps:
            available = min(available, int(source_caps[source_name]))
        if available <= 0:
            continue
        quotas[source_name] = min(planned, available)
    return quotas


def _ranking_key(record: Dict[str, Any], bucket_name: str, prefer_sources: Sequence[str]) -> Tuple[float, float, float, float]:
    source_name = str(record.get("source", "")).strip()
    preference = float(_source_preference(source_name, prefer_sources))
    score_tuple = _score_tuple(record, bucket_name)
    return (preference, score_tuple[0], score_tuple[1], score_tuple[2])


def _bucket_routing_reason(record: Dict[str, Any], bucket_name: str, blocked_buckets: Sequence[str]) -> str:
    source_name = str(record.get("source", "unknown")).strip()
    source_role = str(record.get("source_role", "")).strip() or "unspecified_role"
    if source_name == "semantic_scholar" and bucket_name == "trend_watch":
        if "must_read" in blocked_buckets:
            return "semantic_scholar 首版限制进入 must_read，因此按 trend_support/hot_backfill 路由到 trend_watch。"
        return "semantic_scholar 作为 trend_support/hot_backfill 来源，进入 trend_watch 补充趋势高热论文。"
    if source_name == "semantic_scholar" and bucket_name == "gap_fill":
        return "semantic_scholar 在 gap_fill 中以受限配额补齐知识缺口。"
    if source_name == "arxiv" and bucket_name == "must_read":
        return "arXiv 作为 fresh discovery 主源，优先进入 must_read。"
    if blocked_buckets:
        return f"{source_name} 受来源路由约束（blocked: {', '.join(blocked_buckets)}），最终进入 {bucket_name}。"
    return f"{source_name}({source_role}) 通过来源感知路由进入 {bucket_name}。"


def _source_selection_reason(record: Dict[str, Any], bucket_name: str) -> str:
    components = record.get("scores", {}).get("components", {}) if isinstance(record.get("scores", {}), dict) else {}
    impact = float(components.get("impact", 0.0) or 0.0)
    knowledge = float(components.get("knowledge_gain", 0.0) or 0.0)
    recency = float(components.get("recency", components.get("freshness", 0.0)) or 0.0)
    source_name = str(record.get("source", "unknown")).strip()
    source_role = str(record.get("source_role", "")).strip() or "unspecified_role"
    if bucket_name == "trend_watch":
        return f"{source_name}/{source_role} 在 impact={impact:.2f}, recency={recency:.2f} 上表现较强。"
    if bucket_name == "gap_fill":
        return f"{source_name}/{source_role} 命中 knowledge_gain={knowledge:.2f}，适合作为 gap_fill。"
    return f"{source_name}/{source_role} 综合分较高，满足 {bucket_name} 入口。"


def route_bucket_candidates(
    records: Sequence[Dict[str, Any]],
    *,
    bucket_name: str,
    target: int,
    bucket_rule: Dict[str, Any],
    source_rules: Dict[str, Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    selected: List[Dict[str, Any]] = []
    notes: Dict[str, Dict[str, Any]] = {}
    if target <= 0:
        return selected, notes

    allowed_candidates: List[Dict[str, Any]] = []
    blocked_notes: Dict[str, Dict[str, Any]] = {}
    for record in records:
        key = _record_key(record)
        allowed = _allowed_buckets(record, source_rules)
        blocked = [bucket for bucket in BUCKET_ORDER if bucket not in allowed]
        if bucket_name not in allowed:
            blocked_notes[key] = {
                "blocked_buckets": blocked,
                "blocked_from_bucket": bucket_name,
            }
            continue
        allowed_candidates.append(record)
        blocked_notes[key] = {
            "blocked_buckets": blocked,
        }

    prefer_sources = bucket_rule.get("prefer_sources", [])
    if not isinstance(prefer_sources, list):
        prefer_sources = []
    prefer_sources = [str(item) for item in prefer_sources if str(item).strip()]
    source_caps = _source_caps(bucket_name, bucket_rule)
    source_counts: Dict[str, int] = {}
    selected_keys = set()

    ranked = sorted(
        allowed_candidates,
        key=lambda item: _ranking_key(item, bucket_name, prefer_sources),
        reverse=True,
    )

    target_mix = bucket_rule.get("target_mix", {})
    if not isinstance(target_mix, dict):
        target_mix = {}
    mix_quota = _initial_mix_quota(target, target_mix, ranked, source_caps)

    # 中文注释：先满足配比下限，再按综合分补齐，避免 trend_watch 被单一来源吞没。
    for source_name in prefer_sources:
        quota = int(mix_quota.get(source_name, 0))
        if quota <= 0:
            continue
        for record in ranked:
            key = _record_key(record)
            if key in selected_keys:
                continue
            candidate_source = str(record.get("source", "")).strip()
            if candidate_source != source_name:
                continue
            if not _can_take_source(candidate_source, source_counts, source_caps):
                continue
            selected.append(record)
            selected_keys.add(key)
            source_counts[candidate_source] = source_counts.get(candidate_source, 0) + 1
            if source_counts[candidate_source] >= quota:
                break
            if len(selected) >= target:
                break
        if len(selected) >= target:
            break

    for record in ranked:
        if len(selected) >= target:
            break
        key = _record_key(record)
        if key in selected_keys:
            continue
        source_name = str(record.get("source", "")).strip()
        if not _can_take_source(source_name, source_counts, source_caps):
            continue
        selected.append(record)
        selected_keys.add(key)
        source_counts[source_name] = source_counts.get(source_name, 0) + 1

    for record in selected:
        key = _record_key(record)
        blocked = blocked_notes.get(key, {}).get("blocked_buckets", [])
        notes[key] = {
            "bucket_routing_reason": _bucket_routing_reason(record, bucket_name, blocked),
            "source_selection_reason": _source_selection_reason(record, bucket_name),
            "blocked_buckets": blocked,
        }
    for key, payload in blocked_notes.items():
        notes.setdefault(key, payload)
    return selected, notes


def route_records_to_buckets(
    records: Sequence[Dict[str, Any]],
    *,
    shortlist_config: Dict[str, Any],
    routing_policy: Dict[str, Any],
) -> Dict[str, Any]:
    source_rules = routing_policy.get("source_rules", {}) if isinstance(routing_policy.get("source_rules", {}), dict) else {}
    bucket_strategy = routing_policy.get("bucket_strategy", {}) if isinstance(routing_policy.get("bucket_strategy", {}), dict) else {}

    remaining = list(records)
    buckets = {name: [] for name in BUCKET_ORDER}
    routing_notes: Dict[str, Dict[str, Any]] = {}
    selected_keys = set()

    for bucket_name in BUCKET_ORDER:
        target = int(shortlist_config.get(bucket_name, 0) or 0)
        bucket_rule = bucket_strategy.get(bucket_name, {})
        if not isinstance(bucket_rule, dict):
            bucket_rule = {}
        selected, notes = route_bucket_candidates(
            remaining,
            bucket_name=bucket_name,
            target=target,
            bucket_rule=bucket_rule,
            source_rules=source_rules,
        )
        buckets[bucket_name] = selected
        for record in selected:
            selected_keys.add(_record_key(record))
        for key, payload in notes.items():
            routing_notes[key] = {**routing_notes.get(key, {}), **payload}
        remaining = [item for item in remaining if _record_key(item) not in selected_keys]

    for record in records:
        key = _record_key(record)
        routing_notes.setdefault(
            key,
            {
                "blocked_buckets": [bucket for bucket in BUCKET_ORDER if bucket not in _allowed_buckets(record, source_rules)],
            },
        )
    return {
        "buckets": buckets,
        "notes": routing_notes,
    }
