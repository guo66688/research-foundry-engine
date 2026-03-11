from __future__ import annotations

from typing import Any, Dict, Iterable, List


def plan_revisit_candidates(
    *,
    inventory: Dict[str, Any],
    paper_state_registry: Dict[str, Any],
    selected_items: Iterable[Dict[str, Any]],
    max_items: int,
) -> List[Dict[str, Any]]:
    selected_slots = set()
    for item in selected_items:
        for slot in item.get("gap_matches", []) or []:
            selected_slots.add(str(slot))
        for slot_hit in item.get("slot_hits", []) or []:
            slot = str(slot_hit.get("slot", ""))
            if slot:
                selected_slots.add(slot)

    candidates: List[Dict[str, Any]] = []
    paper_states = paper_state_registry.get("papers", {}) if isinstance(paper_state_registry, dict) else {}
    for record in inventory.get("records", []):
        if record.get("evidence_strength") != "strong_knowledge":
            continue
        paper_id = str(record.get("paper_id", ""))
        state = paper_states.get(paper_id, {})
        status = str(state.get("status", record.get("status", ""))).lower()
        reasons: List[str] = []
        score = 0.0

        if status in {"skimmed", "queued"}:
            reasons.append("已有笔记但仍停留在浅读阶段")
            score += 1.0
        if state.get("importance") in {"high", "core"} or str(record.get("importance", "")).lower() in {"high", "core"}:
            reasons.append("曾被标记为重要，但后续跟进不足")
            score += 0.7
        if selected_slots and any(slot in selected_slots for slot in record.get("knowledge_slots", [])):
            reasons.append("今天的新推荐再次触发了同一知识槽位")
            score += 0.9
        if state.get("follow_up") in {False, "false", "pending"} or str(record.get("follow_up", "")).lower() in {"false", "pending", "todo"}:
            reasons.append("笔记里明确标记了待跟进")
            score += 0.5
        if status == "deepread":
            continue
        if not reasons:
            continue
        candidates.append(
            {
                "kind": "revisit",
                "paper_id": paper_id,
                "title": record.get("title", ""),
                "note_path": record.get("path", ""),
                "topics": list(record.get("bucket_topics", []) or record.get("topics", [])),
                "knowledge_slots": list(record.get("knowledge_slots", [])),
                "revisit_reason": "；".join(reasons[:3]),
                "backfill_reason": "",
                "why_recommended": reasons[0],
                "score": round(score, 4),
            }
        )

    candidates.sort(key=lambda item: (float(item.get("score", 0.0)), str(item.get("paper_id", ""))), reverse=True)
    seen = set()
    output: List[Dict[str, Any]] = []
    for item in candidates:
        paper_id = str(item.get("paper_id", ""))
        if paper_id in seen:
            continue
        seen.add(paper_id)
        output.append(item)
        if len(output) >= max_items:
            break
    return output

