from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

try:
    from scripts.lib.paper_similarity import normalize_text
except ModuleNotFoundError:
    from lib.paper_similarity import normalize_text

try:
    from scripts.shared.flow_common import load_yaml, utc_timestamp
except ModuleNotFoundError:
    import yaml

    def load_yaml(path: Path) -> Dict[str, Any]:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"expected mapping in {path}")
        return payload

    def utc_timestamp() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_canonical_map(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"topics": {}}
    payload = load_yaml(path)
    topics = payload.get("topics", {})
    return {"topics": topics if isinstance(topics, dict) else {}}


def find_missing_canonicals(
    *,
    items: Iterable[Dict[str, Any]],
    inventory: Dict[str, Any],
    canonical_map: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    inventory_titles = {
        normalize_text(str(record.get("title", ""))): record
        for record in inventory.get("records", [])
        if record.get("evidence_strength") == "strong_knowledge"
    }
    suggestions: List[Dict[str, Any]] = []
    state = {"generated_at": utc_timestamp(), "missing_by_slot": {}}
    seen: set[tuple[str, str]] = set()

    for item in items:
        slots = _relevant_slots(item)
        for slot in slots:
            topic_entry = (canonical_map.get("topics", {}) or {}).get(slot, {})
            canonical_papers = topic_entry.get("canonical_papers", []) if isinstance(topic_entry, dict) else []
            if not canonical_papers:
                continue
            missing_titles: List[str] = []
            for canonical in canonical_papers:
                title, aliases = _canonical_title_and_aliases(canonical)
                if _covered_by_inventory(title, aliases, inventory_titles):
                    continue
                missing_titles.append(title)
                key = (slot, title)
                if key in seen:
                    continue
                seen.add(key)
                suggestions.append(
                    {
                        "kind": "backfill",
                        "slot": slot,
                        "title": title,
                        "aliases": aliases,
                        "trigger_paper_id": item.get("paper_id", ""),
                        "trigger_title": item.get("title", ""),
                        "revisit_reason": "",
                        "backfill_reason": f"当前推荐命中 {slot}，但本地尚未覆盖经典论文 {title}",
                        "why_recommended": f"先补经典 {title}，再读 {item.get('title', '')} 会更顺畅",
                        "source_type": "canonical_map",
                    }
                )
            if missing_titles:
                state["missing_by_slot"][slot] = missing_titles
    return suggestions, state


def _relevant_slots(item: Dict[str, Any]) -> List[str]:
    slots = list(item.get("gap_matches", []))
    if not slots:
        slots = [str(entry.get("slot", "")) for entry in item.get("slot_hits", []) if str(entry.get("slot", ""))]
    return [slot for slot in slots if slot]


def _canonical_title_and_aliases(payload: Any) -> Tuple[str, List[str]]:
    if isinstance(payload, str):
        return payload, []
    if isinstance(payload, dict):
        title = str(payload.get("title", ""))
        aliases = [str(item) for item in (payload.get("aliases") or []) if str(item).strip()]
        return title, aliases
    return "", []


def _covered_by_inventory(title: str, aliases: List[str], inventory_titles: Dict[str, Dict[str, Any]]) -> bool:
    title_keys = [normalize_text(title)] + [normalize_text(alias) for alias in aliases]
    for candidate in title_keys:
        if not candidate:
            continue
        for inventory_title in inventory_titles:
            if candidate in inventory_title or inventory_title in candidate:
                return True
    return False
