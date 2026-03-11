from __future__ import annotations

from typing import Any, Dict, Iterable, List

from rf_standalone.paper_similarity import normalize_text, text_similarity, token_set
from rf_standalone.flow_common import days_since


SLOT_STATUS_BONUS = {
    "blind_spot": 1.0,
    "weak": 0.8,
    "learning": 0.55,
    "known": 0.2,
}

ACTION_BY_SCORE = [
    ("deepread", 0.68),
    ("compare", 0.52),
    ("backfill", 0.4),
    ("skim", 0.24),
]

TOPIC_BUCKET_RULES = {
    "inference": ["inference", "serving", "decoding", "kv cache", "batching", "scheduling", "speculative decoding"],
    "agent": ["agent", "tool use", "planning", "memory", "verification", "multi-agent"],
    "alignment": ["alignment", "preference", "safety", "reward modeling", "constitutional"],
    "evaluation": ["evaluation", "benchmark", "robustness", "failure analysis", "hallucination"],
    "systems": ["systems", "efficiency", "infra", "throughput", "latency"],
}


def recency(record: Dict[str, Any]) -> float:
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


def topical_fit(record: Dict[str, Any], profile: Dict[str, Any]) -> tuple[float, List[str]]:
    title = record.get("title", "").lower()
    abstract = record.get("abstract", "").lower()
    include_terms = profile.get("include_terms", [])
    exclude_terms = profile.get("exclude_terms", [])
    content = f"{title}\n{abstract}"
    if any(term.lower() in content for term in exclude_terms):
        return 0.0, []
    if not include_terms:
        return 0.0, []
    hits: List[str] = []
    score = 0.0
    for term in include_terms:
        needle = term.lower()
        if needle in title:
            score += 1.0
            hits.append(term)
        elif needle in abstract:
            score += 0.6
            hits.append(term)
    return min(score / max(len(include_terms), 1), 1.0), hits


def impact(record: Dict[str, Any]) -> float:
    influential = float(record.get("influential_citation_count", 0) or 0)
    citations = float(record.get("citation_count", 0) or 0)
    raw = max(influential * 1.5, citations)
    return min(raw / 100.0, 1.0)


def method_signal(record: Dict[str, Any]) -> float:
    abstract = normalize_text(record.get("abstract", ""))
    strong_terms = [
        "outperform",
        "state-of-the-art",
        "benchmark",
        "ablation",
        "framework",
        "architecture",
        "analysis",
        "evaluation",
        "robustness",
    ]
    hits = sum(1 for term in strong_terms if term in abstract)
    return min(hits / 5.0, 1.0)


def infer_topic_buckets(record: Dict[str, Any], profile: Dict[str, Any]) -> tuple[List[str], List[str]]:
    text = normalize_text(
        f"{record.get('title', '')}\n{record.get('abstract', '')}\n{' '.join(record.get('categories', []) or [])}"
    )
    buckets: List[str] = []
    matched_terms: List[str] = []
    for bucket, keywords in TOPIC_BUCKET_RULES.items():
        for keyword in keywords:
            if keyword in text:
                if bucket not in buckets:
                    buckets.append(bucket)
                matched_terms.append(keyword)
                break
    if not buckets:
        for slot_name, slot in (profile.get("knowledge_map") or {}).items():
            topics = slot.get("topics") or []
            for topic in topics:
                normalized = normalize_text(str(topic))
                if normalized and normalized in text:
                    buckets.append(slot_name)
                    matched_terms.append(str(topic))
                    break
    return buckets or ["general_llm"], matched_terms


def slot_matches(record: Dict[str, Any], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    knowledge_map = profile.get("knowledge_map") or {}
    text = normalize_text(f"{record.get('title', '')}\n{record.get('abstract', '')}")
    matches: List[Dict[str, Any]] = []
    for slot_name, slot in knowledge_map.items():
        topics = [normalize_text(str(item)) for item in (slot.get("topics") or []) if str(item).strip()]
        hit_topics = [topic for topic in topics if topic and topic in text]
        if not hit_topics:
            continue
        matches.append(
            {
                "slot": slot_name,
                "status": str(slot.get("status") or "learning"),
                "topics": hit_topics[:6],
            }
        )
    return matches


def knowledge_gain(
    record: Dict[str, Any],
    *,
    profile: Dict[str, Any],
    inventory: Dict[str, Any],
    bucket_topics: Iterable[str],
    slot_hits: List[Dict[str, Any]],
) -> tuple[float, List[str], List[str]]:
    # 初版不用 embedding，直接用知识槽位状态、覆盖频次和新主题稀缺度做可解释估分。
    reasons: List[str] = []
    gap_matches: List[str] = []
    score = 0.1
    slot_frequency = inventory.get("strong_slot_frequency", inventory.get("slot_frequency", {}))
    topic_frequency = inventory.get("strong_topic_frequency", inventory.get("topic_frequency", {}))
    weak_topic_frequency = inventory.get("weak_topic_frequency", {})

    if slot_hits:
        slot_scores = []
        for slot_hit in slot_hits:
            status = str(slot_hit.get("status", "learning"))
            slot = str(slot_hit.get("slot", ""))
            status_bonus = SLOT_STATUS_BONUS.get(status, 0.35)
            covered_count = int(slot_frequency.get(slot, 0) or 0)
            coverage_modifier = max(0.2, 1.0 - min(covered_count / 6.0, 0.8))
            slot_scores.append(status_bonus * coverage_modifier)
            if status in {"blind_spot", "weak"}:
                gap_matches.append(slot)
                reasons.append(f"命中待补知识槽位 {slot}")
            elif status == "known":
                reasons.append(f"命中已较熟悉槽位 {slot}")
        score += max(slot_scores)
    else:
        reasons.append("未命中显式 knowledge_map 槽位，退回关键词画像评估")

    text_tokens = token_set(f"{record.get('title', '')} {record.get('abstract', '')}")
    novelty_hits = [token for token in list(text_tokens)[:20] if int(topic_frequency.get(token, 0) or 0) == 0]
    if novelty_hits:
        score += min(0.18 + len(novelty_hits) * 0.02, 0.28)
        reasons.append("包含近期笔记中较少出现的新主题线索")

    weak_exposure_hits = [token for token in list(text_tokens)[:20] if int(weak_topic_frequency.get(token, 0) or 0) > 0]
    if weak_exposure_hits:
        score -= min(0.06 + len(weak_exposure_hits) * 0.01, 0.1)
        reasons.append("近期日报已多次接触相关主题，知识增益略有折损")

    rare_bucket_bonus = 0.0
    bucket_frequency = inventory.get("strong_bucket_frequency", inventory.get("bucket_frequency", {}))
    for bucket in bucket_topics:
        count = int(bucket_frequency.get(bucket, 0) or 0)
        if count <= 1:
            rare_bucket_bonus = max(rare_bucket_bonus, 0.16)
        elif count <= 3:
            rare_bucket_bonus = max(rare_bucket_bonus, 0.08)
    score += rare_bucket_bonus
    return min(score, 1.0), reasons[:4], gap_matches


def strongest_overlap(record: Dict[str, Any], inventory_records: Iterable[Dict[str, Any]]) -> tuple[float, List[str], List[Dict[str, Any]]]:
    # 重复惩罚分两层来源：相同 paper_id 直接高惩罚；主题/摘要高重叠视作近似重复。
    paper_id = str(record.get("paper_id", "")).strip()
    strong_records = [item for item in inventory_records if item.get("evidence_strength") == "strong_knowledge"]
    overlaps: List[Dict[str, Any]] = []
    max_score = 0.0
    reasons: List[str] = []
    for item in strong_records:
        if paper_id and paper_id == str(item.get("paper_id", "")):
            max_score = 1.0
            overlaps.append({"path": item.get("path", ""), "paper_id": item.get("paper_id", ""), "score": 1.0})
            reasons.append("本地已存在同一 paper_id 笔记")
            continue
        similarity = text_similarity(
            str(record.get("title", "")),
            str(record.get("abstract", "")),
            str(item.get("title", "")),
            str(item.get("summary", "")),
        )
        score = float(similarity["overall"])
        if score >= 0.45:
            overlaps.append(
                {
                    "path": item.get("path", ""),
                    "paper_id": item.get("paper_id", ""),
                    "score": score,
                    "evidence_strength": item.get("evidence_strength", ""),
                }
            )
        max_score = max(max_score, score)
    if max_score >= 0.85 and "本地已存在同一 paper_id 笔记" not in reasons:
        reasons.append("与现有笔记主题高度重合")
    elif max_score >= 0.55:
        reasons.append("与已有笔记存在明显重复覆盖")
    return min(max_score, 1.0), reasons[:3], overlaps[:5]


def bridge_value(slot_hits: List[Dict[str, Any]], inventory: Dict[str, Any]) -> tuple[float, List[str]]:
    # 先用启发式判断“是否连接了两个较少同时出现的知识槽位”。
    bridge_reasons: List[str] = []
    slots = [str(item.get("slot", "")) for item in slot_hits if str(item.get("slot", ""))]
    if len(slots) < 2:
        return 0.0, bridge_reasons
    unique_slots: List[str] = []
    for slot in slots:
        if slot not in unique_slots:
            unique_slots.append(slot)
    if len(unique_slots) < 2:
        return 0.0, bridge_reasons

    grouped = inventory.get("strong_slot_frequency", inventory.get("slot_frequency", {}))
    rare_pair = False
    for left in unique_slots:
        for right in unique_slots:
            if left >= right:
                continue
            bridge_reasons.append(f"connects {left} and {right}")
            if int(grouped.get(left, 0) or 0) <= 3 or int(grouped.get(right, 0) or 0) <= 3:
                rare_pair = True
    if rare_pair:
        bridge_reasons.append("rare cross-slot combination in local vault")
        return 0.8, bridge_reasons[:4]
    return 0.55, bridge_reasons[:4]


def actionability(record: Dict[str, Any], bucket_topics: Iterable[str]) -> float:
    text = normalize_text(f"{record.get('title', '')}\n{record.get('abstract', '')}")
    score = 0.1
    if any(keyword in text for keyword in ["framework", "system", "architecture", "pipeline"]):
        score += 0.25
    if any(keyword in text for keyword in ["benchmark", "evaluation", "analysis", "ablation"]):
        score += 0.22
    if any(bucket in {"systems", "inference", "agent", "evaluation"} for bucket in bucket_topics):
        score += 0.14
    if any(keyword in text for keyword in ["implementation", "deploy", "serving", "tool use", "memory"]):
        score += 0.18
    return min(score, 1.0)


def suggested_action(
    *,
    total_score: float,
    knowledge_gain_score: float,
    redundancy_penalty_score: float,
    bridge_score: float,
) -> tuple[str, str]:
    if redundancy_penalty_score >= 0.85:
        return "archive", "与现有知识高度重复，优先归档以避免重复投入"
    if knowledge_gain_score >= 0.65 and total_score >= 0.58:
        return "deepread", "知识增益高，值得投入完整阅读时间"
    if bridge_score >= 0.55:
        return "compare", "适合作为连接两个主题槽位的对照阅读"
    if total_score >= 0.4:
        return "backfill", "适合作为补齐背景或前置知识的阅读材料"
    for action, threshold in ACTION_BY_SCORE:
        if total_score >= threshold:
            return action, "热度或相关性中等，适合快速浏览"
    return "skim", "建议先快速浏览，再决定是否继续投入"


def explain_block(
    *,
    profile_hits: List[str],
    knowledge_reasons: List[str],
    gap_matches: List[str],
    overlap_reasons: List[str],
    action_reason: str,
    bucket_hint: str,
    feedback_adjustment: str,
    revisit_reason: str = "",
    backfill_reason: str = "",
) -> Dict[str, Any]:
    why_parts = []
    if profile_hits:
        why_parts.append(f"命中画像关键词：{', '.join(profile_hits[:4])}")
    why_parts.extend(knowledge_reasons[:2])
    if bucket_hint and bucket_hint != "general_llm":
        why_parts.append(f"进入 {bucket_hint} 主题桶")
    return {
        "why_recommended": "；".join(why_parts[:3]) or "与当前研究画像存在一定相关性",
        "knowledge_gap_matched": gap_matches,
        "overlap_with_existing_notes": overlap_reasons,
        "suggested_action_reason": action_reason,
        "feedback_adjustment": feedback_adjustment,
        "revisit_reason": revisit_reason,
        "backfill_reason": backfill_reason,
    }


def apply_feedback_adjustment(
    *,
    topical_score: float,
    knowledge_score: float,
    overlap_score: float,
    bucket_topics: Iterable[str],
    slot_hits: List[Dict[str, Any]],
    suggested_bucket_hint: str,
    paper_state: Dict[str, Any],
    adaptation: Dict[str, Any],
) -> tuple[float, float, float, str]:
    reasons: List[str] = []
    topic_adjustments = adaptation.get("topic_adjustments", {}) if isinstance(adaptation, dict) else {}
    slot_adjustments = adaptation.get("slot_adjustments", {}) if isinstance(adaptation, dict) else {}
    bucket_adjustments = adaptation.get("bucket_adjustments", {}) if isinstance(adaptation, dict) else {}
    novelty_tolerance = float(adaptation.get("tolerance_for_novelty", 0.0) or 0.0) if isinstance(adaptation, dict) else 0.0
    redundancy_tolerance = float(adaptation.get("tolerance_for_redundancy", 0.0) or 0.0) if isinstance(adaptation, dict) else 0.0

    topic_bias = max((float(topic_adjustments.get(topic, 0.0) or 0.0) for topic in bucket_topics), default=0.0)
    slot_bias = max(
        (float(slot_adjustments.get(str(item.get("slot", "")), 0.0) or 0.0) for item in slot_hits if str(item.get("slot", ""))),
        default=0.0,
    )
    bucket_bias = float(bucket_adjustments.get(suggested_bucket_hint, 0.0) or 0.0)
    if abs(topic_bias) >= 0.01 or abs(slot_bias) >= 0.01 or abs(bucket_bias) >= 0.01:
        knowledge_score = min(max(knowledge_score + topic_bias * 0.6 + slot_bias * 0.8 + bucket_bias * 0.4, 0.0), 1.0)
        topical_score = min(max(topical_score + topic_bias * 0.5, 0.0), 1.0)
        reasons.append("历史反馈对该主题的偏好已轻度调权")

    if abs(novelty_tolerance) >= 0.01:
        knowledge_score = min(max(knowledge_score + novelty_tolerance * 0.35, 0.0), 1.0)
        reasons.append("根据近期使用行为，对新知识增益做了轻微校准")

    if abs(redundancy_tolerance) >= 0.01:
        overlap_score = min(max(overlap_score - redundancy_tolerance * 0.35, 0.0), 1.0)
        reasons.append("根据近期重复容忍度，调整了重复惩罚")

    status = str(paper_state.get("status", "")).lower()
    ignored_runs = int(paper_state.get("ignored_runs", 0) or 0)
    if status in {"deepread", "archived"}:
        overlap_score = max(overlap_score, 0.95)
        reasons.append(f"该论文已有 {status} 记录，默认强力降权")
    elif ignored_runs >= 3:
        overlap_score = min(overlap_score + 0.18, 1.0)
        reasons.append("该论文已连续多次推荐未处理，自动降温")
    return topical_score, knowledge_score, overlap_score, "；".join(reasons[:3])


def score_record(
    record: Dict[str, Any],
    *,
    weights: Dict[str, float],
    profile: Dict[str, Any],
    inventory: Dict[str, Any],
    paper_states: Dict[str, Any] | None = None,
    adaptation: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    topical_score, profile_hits = topical_fit(record, profile)
    bucket_topics, matched_bucket_terms = infer_topic_buckets(record, profile)
    slot_hits = slot_matches(record, profile)
    knowledge_score, knowledge_reasons, gap_matches = knowledge_gain(
        record,
        profile=profile,
        inventory=inventory,
        bucket_topics=bucket_topics,
        slot_hits=slot_hits,
    )
    overlap_score, overlap_reasons, overlap_records = strongest_overlap(record, inventory.get("records", []))
    bridge_score, bridge_reasons = bridge_value(slot_hits, inventory)
    actionability_score = actionability(record, bucket_topics)
    paper_state = dict((paper_states or {}).get(str(record.get("paper_id", "")), {}) or {})
    adaptation = adaptation or {}
    topical_score, knowledge_score, overlap_score, feedback_adjustment = apply_feedback_adjustment(
        topical_score=topical_score,
        knowledge_score=knowledge_score,
        overlap_score=overlap_score,
        bucket_topics=bucket_topics,
        slot_hits=slot_hits,
        suggested_bucket_hint=bucket_topics[0] if bucket_topics else "general_llm",
        paper_state=paper_state,
        adaptation=adaptation,
    )
    if paper_state:
        state_label = str(paper_state.get("status", "")).lower()
        if state_label in {"deepread", "archived"}:
            overlap_reasons = list(overlap_reasons) + [f"本地已有 {state_label} 状态记录"]
        elif state_label in {"skimmed", "queued", "recommended"}:
            overlap_reasons = list(overlap_reasons) + [f"本地已有 {state_label} 处理痕迹"]

    components = {
        "topical_fit": topical_score,
        "recency": recency(record),
        "freshness": recency(record),
        "impact": impact(record),
        "method_signal": method_signal(record),
        "knowledge_gain": knowledge_score,
        "bridge_value": bridge_score,
        "actionability": actionability_score,
        "redundancy_penalty": overlap_score,
    }
    weak_topic_frequency = inventory.get("weak_topic_frequency", {})
    weak_exposure = sum(
        1
        for token in token_set(f"{record.get('title', '')} {record.get('abstract', '')}")
        if int(weak_topic_frequency.get(token, 0) or 0) > 0
    )
    if weak_exposure:
        overlap_reasons = list(overlap_reasons) + ["近期日报中已有相关暴露"]

    total = 0.0
    for name, weight in weights.items():
        value = float(components.get(name, components.get("freshness" if name == "recency" else name, 0.0)))
        if name == "redundancy_penalty":
            total -= value * weight
        else:
            total += value * weight

    action, action_reason = suggested_action(
        total_score=total,
        knowledge_gain_score=knowledge_score,
        redundancy_penalty_score=overlap_score,
        bridge_score=bridge_score,
    )
    bucket_hint = bucket_topics[0] if bucket_topics else "general_llm"
    explain = explain_block(
        profile_hits=profile_hits,
        knowledge_reasons=knowledge_reasons,
        gap_matches=gap_matches,
        overlap_reasons=overlap_reasons,
        action_reason=action_reason,
        bucket_hint=bucket_hint,
        feedback_adjustment=feedback_adjustment,
    )
    total_score = round(total * 10.0, 2)
    return {
        "components": {name: round(value, 4) for name, value in components.items()},
        "total": total_score,
        "score": total_score,
        "profile_hits": profile_hits,
        "topic_buckets": bucket_topics,
        "topic_terms": matched_bucket_terms,
        "slot_hits": slot_hits,
        "knowledge_reasons": knowledge_reasons,
        "gap_matches": gap_matches,
        "bridge_reasons": bridge_reasons,
        "overlap_reasons": overlap_reasons,
        "overlap_records": overlap_records,
        "suggested_action": action,
        "suggested_action_reason": action_reason,
        "bucket_hint": bucket_hint,
        "explain": explain,
    }
