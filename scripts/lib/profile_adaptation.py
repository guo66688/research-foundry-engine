from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any, Dict, Iterable, List

from scripts.shared.flow_common import utc_timestamp


EVENT_POLARITY = {
    "opened": 0.15,
    "skimmed": 0.25,
    "deepread": 1.0,
    "mark_useful": 1.0,
    "compared": 0.75,
    "backfill_started": 0.45,
    "revisit_completed": 0.65,
    "archived": -0.9,
    "ignored": -0.6,
    "mark_not_useful": -1.0,
}


def empty_adaptation_state(profile_id: str) -> Dict[str, Any]:
    return {
        "generated_at": utc_timestamp(),
        "profiles": {
            profile_id: {
                "topic_adjustments": {},
                "slot_adjustments": {},
                "action_adjustments": {},
                "bucket_adjustments": {},
                "tolerance_for_novelty": 0.0,
                "tolerance_for_redundancy": 0.0,
                "evidence_counts": {"positive": 0, "negative": 0, "neutral": 0},
            }
        },
    }


def compute_profile_adaptation(
    *,
    profile_id: str,
    feedback_events: Iterable[Dict[str, Any]],
    settings: Dict[str, Any],
    previous_state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    cap = float(settings.get("adaptation", {}).get("topic_weight_adjustment_cap", 0.15) or 0.15)
    decay = float(settings.get("adaptation", {}).get("decay_factor", 0.9) or 0.9)
    previous_state = deepcopy(previous_state or empty_adaptation_state(profile_id))
    profile_state = deepcopy(previous_state.get("profiles", {}).get(profile_id, {}))

    topic_scores: Dict[str, float] = defaultdict(float)
    slot_scores: Dict[str, float] = defaultdict(float)
    action_scores: Dict[str, float] = defaultdict(float)
    bucket_scores: Dict[str, float] = defaultdict(float)
    positive = negative = neutral = 0
    novelty_signal = 0.0
    redundancy_signal = 0.0

    for event in feedback_events:
        if str(event.get("profile_id", "")) != profile_id:
            continue
        event_type = str(event.get("event_type", ""))
        weight = EVENT_POLARITY.get(event_type, 0.0)
        if weight > 0:
            positive += 1
        elif weight < 0:
            negative += 1
        else:
            neutral += 1

        for topic in event.get("topics", []) or []:
            topic_scores[str(topic)] += weight
        for slot in event.get("knowledge_slots", []) or []:
            slot_scores[str(slot)] += weight
        action = str(event.get("suggested_action", "") or event.get("actual_action", ""))
        if action:
            action_scores[action] += weight
        bucket = str(event.get("bucket", ""))
        if bucket:
            bucket_scores[bucket] += weight

        if bucket == "gap_fill":
            novelty_signal += weight
        if event_type in {"ignored", "archived", "mark_not_useful"}:
            redundancy_signal -= abs(weight)
        elif event_type in {"compare", "deepread", "mark_useful"}:
            redundancy_signal += abs(weight) * 0.5

    adapted = {
        "topic_adjustments": _merge_adjustments(profile_state.get("topic_adjustments", {}), topic_scores, cap, decay),
        "slot_adjustments": _merge_adjustments(profile_state.get("slot_adjustments", {}), slot_scores, cap, decay),
        "action_adjustments": _merge_adjustments(profile_state.get("action_adjustments", {}), action_scores, cap, decay),
        "bucket_adjustments": _merge_adjustments(profile_state.get("bucket_adjustments", {}), bucket_scores, cap, decay),
        "tolerance_for_novelty": _blend_scalar(profile_state.get("tolerance_for_novelty", 0.0), novelty_signal, cap, decay),
        "tolerance_for_redundancy": _blend_scalar(profile_state.get("tolerance_for_redundancy", 0.0), redundancy_signal, cap, decay),
        "evidence_counts": {"positive": positive, "negative": negative, "neutral": neutral},
    }
    previous_state["generated_at"] = utc_timestamp()
    previous_state.setdefault("profiles", {})[profile_id] = adapted
    return previous_state


def _merge_adjustments(
    previous: Dict[str, float],
    new_scores: Dict[str, float],
    cap: float,
    decay: float,
) -> Dict[str, float]:
    merged: Dict[str, float] = {}
    keys = set(previous) | set(new_scores)
    for key in keys:
        prior = float(previous.get(key, 0.0) or 0.0) * decay
        current = _normalize_signal(float(new_scores.get(key, 0.0) or 0.0), cap)
        blended = max(min(prior + current, cap), -cap)
        if abs(blended) >= 0.005:
            merged[key] = round(blended, 4)
    return merged


def _blend_scalar(previous: float, raw_signal: float, cap: float, decay: float) -> float:
    prior = float(previous or 0.0) * decay
    current = _normalize_signal(float(raw_signal or 0.0), cap)
    return round(max(min(prior + current, cap), -cap), 4)


def _normalize_signal(value: float, cap: float) -> float:
    if value == 0:
        return 0.0
    normalized = value / max(abs(value) + 3.0, 1.0)
    return max(min(normalized * cap * 2.0, cap), -cap)


def adaptation_for_profile(adaptation_state: Dict[str, Any], profile_id: str) -> Dict[str, Any]:
    profiles = adaptation_state.get("profiles", {}) if isinstance(adaptation_state, dict) else {}
    payload = profiles.get(profile_id)
    if isinstance(payload, dict):
        return payload
    return empty_adaptation_state(profile_id)["profiles"][profile_id]

