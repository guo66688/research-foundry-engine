from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml

UTC_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
RUN_SUFFIX_FORMAT = "%Y%m%dT%H%M%SZ"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def utc_timestamp(value: Optional[datetime] = None) -> str:
    current = value or now_utc()
    return current.astimezone(timezone.utc).strftime(UTC_TIMESTAMP_FORMAT)


def make_run_id(value: Optional[datetime] = None) -> str:
    current = value or now_utc()
    return "run-" + current.astimezone(timezone.utc).strftime(RUN_SUFFIX_FORMAT)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping in {path}")
    return data


def load_profiles(path: Path) -> List[Dict[str, Any]]:
    data = load_yaml(path)
    profiles = data.get("profiles", [])
    if not isinstance(profiles, list):
        raise ValueError(f"profiles must be a list in {path}")
    return profiles


def select_profile(path: Path, profile_id: str) -> Dict[str, Any]:
    for profile in load_profiles(path):
        if profile.get("profile_id") == profile_id:
            return profile
    raise KeyError(f"profile_id not found: {profile_id}")


def slugify(text: str, max_length: int = 80) -> str:
    ascii_text = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    compact = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    if not compact:
        compact = "item"
    return compact[:max_length].rstrip("-")


def canonical_paper_id(raw_value: str, source_name: str = "paper") -> str:
    match = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", raw_value)
    if match:
        return match.group(1)
    return f"{source_name}-{slugify(raw_value, max_length=48)}"


def parse_timestamp(raw_value: str) -> Optional[datetime]:
    if not raw_value:
        return None
    candidates = [
        raw_value,
        raw_value.replace("Z", "+00:00"),
    ]
    for candidate in candidates:
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    return None


def days_since(raw_value: str) -> Optional[int]:
    parsed = parse_timestamp(raw_value)
    if parsed is None:
        return None
    delta = now_utc() - parsed.astimezone(timezone.utc)
    return max(delta.days, 0)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def resolve_runtime_path(workflow: Dict[str, Any], key: str) -> Path:
    runtime = workflow.get("runtime", {})
    mapping = {
        "run": runtime.get("run_dir", "runtime/runs"),
        "artifact": runtime.get("artifact_dir", "runtime/artifacts"),
        "cache": runtime.get("cache_dir", "runtime/cache"),
        "log": runtime.get("log_dir", "runtime/logs"),
    }
    return Path(mapping[key])


def merged_weights(base: Dict[str, float], override: Dict[str, float]) -> Dict[str, float]:
    merged = dict(base)
    merged.update(override or {})
    total = sum(merged.values())
    if total <= 0:
        raise ValueError("score weights must sum to a positive value")
    return {name: value / total for name, value in merged.items()}


def term_hits(text: str, terms: Iterable[str]) -> List[str]:
    haystack = text.lower()
    hits: List[str] = []
    for term in terms:
        if term.lower() in haystack:
            hits.append(term)
    return hits


def replace_jsonl_entry(
    entries: List[Dict[str, Any]],
    record: Dict[str, Any],
    key_fields: Iterable[str],
) -> List[Dict[str, Any]]:
    key_names = list(key_fields)
    output: List[Dict[str, Any]] = []
    replaced = False
    for entry in entries:
        if all(entry.get(name) == record.get(name) for name in key_names):
            if not replaced:
                output.append(record)
                replaced = True
            continue
        output.append(entry)
    if not replaced:
        output.append(record)
    return output
