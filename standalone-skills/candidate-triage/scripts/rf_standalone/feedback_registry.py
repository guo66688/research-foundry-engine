from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

try:
    from rf_standalone.flow_common import ensure_dir, read_json, read_jsonl, utc_timestamp, write_json, write_jsonl
except ModuleNotFoundError:
    import json

    def ensure_dir(path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        return path

    def read_json(path: Path, default: Any = None) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def read_jsonl(path: Path) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        if not path.exists():
            return rows
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    def utc_timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def write_json(path: Path, payload: Any) -> None:
        ensure_dir(path.parent)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
        ensure_dir(path.parent)
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")


RUNTIME_STATE_FILES = {
    "feedback_registry": "feedback_registry.jsonl",
    "paper_state_registry": "paper_state_registry.json",
    "profile_adaptation_state": "profile_adaptation_state.json",
    "canonical_backfill_state": "canonical_backfill_state.json",
}

INFERRED_STATUS_EVENT_MAP = {
    "queued": "opened",
    "skimmed": "skimmed",
    "deepread": "deepread",
    "archived": "archived",
    "backfill_required": "backfill_started",
    "compared": "compared",
    "revisit_due": "revisit_completed",
}


def runtime_state_root(workflow: Dict[str, Any]) -> Path:
    artifact_dir = Path(workflow.get("runtime", {}).get("artifact_dir", "runtime/artifacts"))
    return ensure_dir(artifact_dir.parent)


def registry_paths(workflow: Dict[str, Any]) -> Dict[str, Path]:
    root = runtime_state_root(workflow)
    return {name: root / filename for name, filename in RUNTIME_STATE_FILES.items()}


def load_feedback_events(path: Path) -> List[Dict[str, Any]]:
    return list(read_jsonl(path))


def load_registry_state(path: Path, *, default: Any) -> Any:
    payload = read_json(path, default=default)
    return deepcopy(payload if payload is not None else default)


def save_feedback_events(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    write_jsonl(path, rows)


def save_registry_state(path: Path, payload: Any) -> None:
    write_json(path, payload)


def _event_key(event: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        str(event.get("paper_id", "")),
        str(event.get("event_type", "")),
        str(event.get("note_path", "")),
    )


def infer_feedback_events_from_inventory(
    *,
    profile_id: str,
    inventory: Dict[str, Any],
    existing_events: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    # 仅从强知识证据里推断事件，避免日报类弱信号把反馈放大。
    existing_keys = {_event_key(item) for item in existing_events}
    inferred: List[Dict[str, Any]] = []
    for record in inventory.get("records", []):
        if record.get("evidence_strength") != "strong_knowledge":
            continue
        note_path = str(record.get("path", ""))
        paper_id = str(record.get("paper_id", ""))
        if not paper_id or not note_path:
            continue

        base_event = {
            "timestamp": str(record.get("modified_at") or utc_timestamp()),
            "profile_id": profile_id,
            "paper_id": paper_id,
            "source": "inventory_scan",
            "bucket": "",
            "suggested_action": "",
            "actual_action": "",
            "note_path": note_path,
            "topics": list(record.get("bucket_topics", []) or record.get("topics", [])),
            "knowledge_slots": list(record.get("knowledge_slots", [])),
            "metadata": {
                "inferred": True,
                "source_type": record.get("source_type", ""),
                "evidence_strength": record.get("evidence_strength", ""),
            },
        }

        opened_event = dict(base_event)
        opened_event["event_type"] = "opened"
        event_key = _event_key(opened_event)
        if event_key not in existing_keys:
            inferred.append(opened_event)
            existing_keys.add(event_key)

        status = str(record.get("status", "")).strip().lower()
        if not status:
            continue
        mapped_event = INFERRED_STATUS_EVENT_MAP.get(status)
        if not mapped_event:
            continue
        status_event = dict(base_event)
        status_event["event_type"] = mapped_event
        status_event["actual_action"] = status
        event_key = _event_key(status_event)
        if event_key not in existing_keys:
            inferred.append(status_event)
            existing_keys.add(event_key)
    return inferred


def build_paper_state_registry(
    *,
    inventory: Dict[str, Any],
    previous_state: Dict[str, Any],
) -> Dict[str, Any]:
    now = utc_timestamp()
    states = deepcopy(previous_state.get("papers", {})) if isinstance(previous_state, dict) else {}
    records_by_paper: Dict[str, List[Dict[str, Any]]] = {}
    for record in inventory.get("records", []):
        records_by_paper.setdefault(str(record.get("paper_id", "")), []).append(record)

    for paper_id, records in records_by_paper.items():
        if not paper_id:
            continue
        strong_records = [item for item in records if item.get("evidence_strength") == "strong_knowledge"]
        strongest = sorted(
            strong_records or records,
            key=lambda item: (
                str(item.get("status", "")) == "deepread",
                str(item.get("modified_at", "")),
            ),
            reverse=True,
        )[0]
        previous = deepcopy(states.get(paper_id, {}))
        status = infer_state_from_record(strongest, previous)
        states[paper_id] = {
            "paper_id": paper_id,
            "title": strongest.get("title", previous.get("title", "")),
            "status": status,
            "note_path": strongest.get("path", previous.get("note_path", "")),
            "topics": list(strongest.get("bucket_topics", []) or strongest.get("topics", [])),
            "knowledge_slots": list(strongest.get("knowledge_slots", [])),
            "last_note_modified_at": strongest.get("modified_at", ""),
            "source_type": strongest.get("source_type", ""),
            "evidence_strength": strongest.get("evidence_strength", ""),
            "importance": strongest.get("importance", previous.get("importance", "")),
            "follow_up": strongest.get("follow_up", previous.get("follow_up", "")),
            "times_recommended": int(previous.get("times_recommended", 0) or 0),
            "ignored_runs": int(previous.get("ignored_runs", 0) or 0),
            "last_recommended_run_id": previous.get("last_recommended_run_id", ""),
            "recommendation_history": list(previous.get("recommendation_history", [])),
            "last_feedback_event": previous.get("last_feedback_event", ""),
            "updated_at": now,
        }

    return {
        "generated_at": now,
        "papers": states,
    }


def infer_state_from_record(record: Dict[str, Any], previous: Dict[str, Any]) -> str:
    status = str(record.get("status", "")).strip().lower()
    if status:
        return status
    previous_status = str(previous.get("status", "")).strip().lower()
    if previous_status in {"recommended", "queued"}:
        return previous_status
    if record.get("evidence_strength") == "strong_knowledge":
        return "skimmed"
    return previous_status or "discovered"


def merge_feedback_events(existing_events: Iterable[Dict[str, Any]], new_events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = list(existing_events)
    known = {_event_key(item) for item in merged}
    for event in new_events:
        key = _event_key(event)
        if key in known:
            continue
        merged.append(event)
        known.add(key)
    merged.sort(key=lambda item: str(item.get("timestamp", "")))
    return merged


def mark_last_feedback(paper_states: Dict[str, Any], feedback_events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    states = deepcopy(paper_states)
    papers = states.get("papers", {})
    for event in feedback_events:
        paper_id = str(event.get("paper_id", ""))
        if not paper_id or paper_id not in papers:
            continue
        papers[paper_id]["last_feedback_event"] = str(event.get("event_type", ""))
    return states


def append_runtime_events(
    *,
    workflow: Dict[str, Any],
    feedback_events: List[Dict[str, Any]],
    paper_state_registry: Dict[str, Any],
    adaptation_state: Dict[str, Any],
    canonical_backfill_state: Dict[str, Any] | None = None,
) -> Dict[str, Path]:
    paths = registry_paths(workflow)
    save_feedback_events(paths["feedback_registry"], feedback_events)
    save_registry_state(paths["paper_state_registry"], paper_state_registry)
    save_registry_state(paths["profile_adaptation_state"], adaptation_state)
    if canonical_backfill_state is not None:
        save_registry_state(paths["canonical_backfill_state"], canonical_backfill_state)
    return paths
