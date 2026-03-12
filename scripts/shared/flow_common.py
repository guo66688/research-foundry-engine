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
            return normalize_profile(profile)
    raise KeyError(f"profile_id not found: {profile_id}")


def normalize_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(profile)
    include_keywords = normalized.get("include_keywords")
    exclude_keywords = normalized.get("exclude_keywords")
    if include_keywords is not None and "include_terms" not in normalized:
        normalized["include_terms"] = include_keywords
    if exclude_keywords is not None and "exclude_terms" not in normalized:
        normalized["exclude_terms"] = exclude_keywords

    source_scope = normalized.get("source_scope")
    sources = normalized.get("sources")
    if isinstance(sources, dict):
        allow_sources = sources.get("allow")
        if isinstance(allow_sources, list) and not source_scope:
            normalized["source_scope"] = [str(item) for item in allow_sources]

    knowledge_map = normalized.get("knowledge_map") or {}
    if not isinstance(knowledge_map, dict):
        knowledge_map = {}
    normalized["knowledge_map"] = knowledge_map
    reading_preferences = normalized.get("reading_preferences") or {}
    if not isinstance(reading_preferences, dict):
        reading_preferences = {}
    normalized["reading_preferences"] = reading_preferences
    return normalized


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


def source_strategy_settings(workflow: Dict[str, Any]) -> Dict[str, Any]:
    sources_block = workflow.get("sources", {})
    if not isinstance(sources_block, dict):
        sources_block = {}
    bucket_strategy_block = workflow.get("bucket_strategy", {})
    if not isinstance(bucket_strategy_block, dict):
        bucket_strategy_block = {}

    source_defaults: Dict[str, Dict[str, Any]] = {
        "arxiv": {
            "enabled": True,
            "role": ["fresh_discovery"],
            "default_window_days": 30,
            "preferred_buckets": ["must_read", "trend_watch", "gap_fill"],
            "restricted_buckets": [],
        },
        "semantic_scholar": {
            "enabled": False,
            "role": ["trend_support", "hot_backfill"],
            "default_window_days": 365,
            "preferred_buckets": ["trend_watch", "gap_fill"],
            "restricted_buckets": ["must_read"],
        },
    }

    resolved_sources: Dict[str, Dict[str, Any]] = {}
    known_sources = sorted(set(list(source_defaults.keys()) + list(sources_block.keys())))
    for source_name in known_sources:
        raw_block = sources_block.get(source_name, {})
        if not isinstance(raw_block, dict):
            raw_block = {}
        defaults = source_defaults.get(source_name, {})
        role_value = raw_block.get("role", defaults.get("role", []))
        if isinstance(role_value, str):
            role_value = [role_value]
        if not isinstance(role_value, list):
            role_value = list(defaults.get("role", []))
        roles = [str(item) for item in role_value if str(item).strip()]

        if source_name == "arxiv":
            window_days = int(raw_block.get("default_window_days", raw_block.get("lookback_days", defaults.get("default_window_days", 30))) or 30)
        elif source_name == "semantic_scholar":
            window_days = int(
                raw_block.get(
                    "default_window_days",
                    raw_block.get("history_window_days", defaults.get("default_window_days", 365)),
                )
                or 365
            )
        else:
            window_days = int(raw_block.get("default_window_days", defaults.get("default_window_days", 30)) or 30)

        preferred = raw_block.get("preferred_buckets", defaults.get("preferred_buckets", []))
        if isinstance(preferred, str):
            preferred = [preferred]
        if not isinstance(preferred, list):
            preferred = list(defaults.get("preferred_buckets", []))

        restricted = raw_block.get("restricted_buckets", defaults.get("restricted_buckets", []))
        if isinstance(restricted, str):
            restricted = [restricted]
        if not isinstance(restricted, list):
            restricted = list(defaults.get("restricted_buckets", []))

        resolved_block = dict(raw_block)
        resolved_block["enabled"] = bool(raw_block.get("enabled", defaults.get("enabled", False)))
        resolved_block["role"] = roles
        resolved_block["default_window_days"] = window_days
        resolved_block["preferred_buckets"] = [str(item) for item in preferred if str(item).strip()]
        resolved_block["restricted_buckets"] = [str(item) for item in restricted if str(item).strip()]
        if source_name == "arxiv":
            resolved_block.setdefault("lookback_days", window_days)
        if source_name == "semantic_scholar":
            resolved_block.setdefault("history_window_days", window_days)
        resolved_sources[source_name] = resolved_block

    bucket_defaults: Dict[str, Dict[str, Any]] = {
        "must_read": {
            "prefer_sources": ["arxiv"],
            "max_semantic_scholar_items": 0,
        },
        "trend_watch": {
            "prefer_sources": ["arxiv", "semantic_scholar"],
            "target_mix": {
                "arxiv": 0.5,
                "semantic_scholar": 0.5,
            },
        },
        "gap_fill": {
            "prefer_sources": ["arxiv", "semantic_scholar"],
            "max_semantic_scholar_items": 2,
        },
        "review_or_backfill": {
            "prefer_sources": ["local_inventory", "canonical_map"],
        },
    }
    resolved_bucket_strategy: Dict[str, Dict[str, Any]] = {}
    known_buckets = sorted(set(list(bucket_defaults.keys()) + list(bucket_strategy_block.keys())))
    for bucket_name in known_buckets:
        raw_bucket = bucket_strategy_block.get(bucket_name, {})
        if not isinstance(raw_bucket, dict):
            raw_bucket = {}
        defaults = bucket_defaults.get(bucket_name, {})
        prefer_sources = raw_bucket.get("prefer_sources", defaults.get("prefer_sources", []))
        if isinstance(prefer_sources, str):
            prefer_sources = [prefer_sources]
        if not isinstance(prefer_sources, list):
            prefer_sources = list(defaults.get("prefer_sources", []))
        target_mix = raw_bucket.get("target_mix", defaults.get("target_mix", {}))
        if not isinstance(target_mix, dict):
            target_mix = dict(defaults.get("target_mix", {}))
        resolved_bucket = dict(raw_bucket)
        resolved_bucket["prefer_sources"] = [str(item) for item in prefer_sources if str(item).strip()]
        resolved_bucket["target_mix"] = {
            str(source_name): float(value)
            for source_name, value in target_mix.items()
            if str(source_name).strip()
        }
        if "max_semantic_scholar_items" in raw_bucket:
            resolved_bucket["max_semantic_scholar_items"] = int(raw_bucket.get("max_semantic_scholar_items", 0) or 0)
        elif "max_semantic_scholar_items" in defaults:
            resolved_bucket["max_semantic_scholar_items"] = int(defaults.get("max_semantic_scholar_items", 0) or 0)
        resolved_bucket_strategy[bucket_name] = resolved_bucket

    return {
        "sources": resolved_sources,
        "bucket_strategy": resolved_bucket_strategy,
    }


def triage_settings(workflow: Dict[str, Any]) -> Dict[str, Any]:
    triage_block = workflow.get("triage")
    legacy_block = workflow.get("triage_policy", {})
    if not isinstance(triage_block, dict):
        triage_block = {}
    if not isinstance(legacy_block, dict):
        legacy_block = {}

    scoring_block = triage_block.get("scoring", {})
    shortlist_block = triage_block.get("shortlist", {})
    deepread_block = triage_block.get("deepread", {})
    diversity_block = triage_block.get("diversity", {})
    inventory_block = triage_block.get("inventory", {})
    feedback_block = triage_block.get("feedback", {})
    queue_block = triage_block.get("queue", {})
    revisit_block = triage_block.get("revisit", {})
    backfill_block = triage_block.get("backfill", {})
    adaptation_block = triage_block.get("adaptation", {})

    if not isinstance(scoring_block, dict):
        scoring_block = {}
    if not isinstance(shortlist_block, dict):
        shortlist_block = {}
    if not isinstance(deepread_block, dict):
        deepread_block = {}
    if not isinstance(diversity_block, dict):
        diversity_block = {}
    if not isinstance(inventory_block, dict):
        inventory_block = {}
    if not isinstance(feedback_block, dict):
        feedback_block = {}
    if not isinstance(queue_block, dict):
        queue_block = {}
    if not isinstance(revisit_block, dict):
        revisit_block = {}
    if not isinstance(backfill_block, dict):
        backfill_block = {}
    if not isinstance(adaptation_block, dict):
        adaptation_block = {}

    weights = scoring_block.get("weights", legacy_block.get("score_weights", {}))
    if not isinstance(weights, dict):
        weights = {}
    weights = dict(weights)
    if "recency" not in weights and "freshness" in weights:
        weights["recency"] = weights["freshness"]
    weights.pop("freshness", None)

    shortlist_total = int(shortlist_block.get("total", legacy_block.get("shortlist_size", 10)) or 10)
    shortlist = {
        "total": shortlist_total,
        "must_read": int(shortlist_block.get("must_read", 2) or 2),
        "trend_watch": int(shortlist_block.get("trend_watch", 3) or 3),
        "gap_fill": int(shortlist_block.get("gap_fill", max(shortlist_total - 5, 0)) or 0),
    }
    deepread = {
        "must_read_top2": int(deepread_block.get("must_read_top2", 2) or 2),
        "gap_fill_top1": int(deepread_block.get("gap_fill_top1", 1) or 1),
    }
    diversity = {
        "max_per_bucket": dict(diversity_block.get("max_per_bucket", {}) or {}),
        "min_per_bucket": dict(diversity_block.get("min_per_bucket", {}) or {}),
    }
    inventory = {
        "enable_daily_recommendations": bool(inventory_block.get("enable_daily_recommendations", True)),
        "recent_window_days": int(inventory_block.get("recent_window_days", 90) or 90),
    }
    feedback = {
        "enabled": bool(feedback_block.get("enabled", True)),
        "positive_events": list(feedback_block.get("positive_events", ["deepread", "mark_useful"]) or []),
        "negative_events": list(feedback_block.get("negative_events", ["mark_not_useful", "ignored", "archived"]) or []),
    }
    queue = {
        "enabled": bool(queue_block.get("enabled", True)),
        "max_active_items": int(queue_block.get("max_active_items", 30) or 30),
        "max_daily_review_or_backfill": int(queue_block.get("max_daily_review_or_backfill", 2) or 2),
        "demote_after_ignored_runs": int(queue_block.get("demote_after_ignored_runs", 3) or 3),
    }
    revisit = {
        "enabled": bool(revisit_block.get("enabled", True)),
        "max_daily_items": int(revisit_block.get("max_daily_items", 2) or 2),
        "prefer_recently_referenced": bool(revisit_block.get("prefer_recently_referenced", True)),
    }
    backfill = {
        "enabled": bool(backfill_block.get("enabled", True)),
        "canonical_map": str(backfill_block.get("canonical_map", "configs/canonical_map.yaml") or "configs/canonical_map.yaml"),
        "max_daily_items": int(backfill_block.get("max_daily_items", 2) or 2),
    }
    adaptation = {
        "enabled": bool(adaptation_block.get("enabled", True)),
        "topic_weight_adjustment_cap": float(adaptation_block.get("topic_weight_adjustment_cap", 0.15) or 0.15),
        "decay_factor": float(adaptation_block.get("decay_factor", 0.9) or 0.9),
    }
    source_strategy = source_strategy_settings(workflow)
    return {
        "weights": weights,
        "shortlist": shortlist,
        "deepread": deepread,
        "diversity": diversity,
        "inventory": inventory,
        "feedback": feedback,
        "queue": queue,
        "revisit": revisit,
        "backfill": backfill,
        "adaptation": adaptation,
        "source_strategy": source_strategy,
    }


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
