from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from scripts.lib.paper_similarity import normalize_text, token_set
from scripts.shared.flow_common import canonical_paper_id


TOPIC_BUCKET_RULES = {
    "inference": ["inference", "serving", "decoding", "kv cache", "batching", "scheduling", "speculative decoding"],
    "agent": ["agent", "tool use", "planning", "memory", "verification", "multi-agent"],
    "alignment": ["alignment", "preference", "safety", "reward modeling", "constitutional"],
    "evaluation": ["evaluation", "benchmark", "robustness", "failure analysis", "hallucination"],
    "systems": ["systems", "efficiency", "infra", "infrastructure", "throughput", "latency"],
}


def parse_frontmatter_and_body(text: str) -> tuple[Dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    marker = "\n---\n"
    end = text.find(marker, 4)
    if end < 0:
        return {}, text
    frontmatter_text = text[4:end]
    body = text[end + len(marker) :]
    try:
        import yaml

        payload = yaml.safe_load(frontmatter_text) or {}
    except Exception:
        payload = {}
    return payload if isinstance(payload, dict) else {}, body


def parse_timestamp(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    for candidate in [raw, raw.replace("Z", "+00:00")]:
        try:
            return datetime.fromisoformat(candidate).astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def recent_first_paragraphs(body: str, limit: int = 2) -> str:
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", body) if item.strip()]
    return "\n\n".join(paragraphs[:limit])


def infer_topics(title: str, frontmatter: Dict[str, Any], body: str) -> List[str]:
    explicit = frontmatter.get("topics") or []
    if isinstance(explicit, str):
        explicit = [explicit]
    inferred = [str(item).strip() for item in explicit if str(item).strip()]
    if inferred:
        return inferred
    text = normalize_text(f"{title}\n{recent_first_paragraphs(body, limit=3)}")
    topics: List[str] = []
    for bucket, keywords in TOPIC_BUCKET_RULES.items():
        if any(keyword in text for keyword in keywords):
            topics.append(bucket)
    if not topics:
        keywords = sorted(token_set(f"{title} {recent_first_paragraphs(body)}"))[:6]
        topics.extend(keywords[:3])
    return topics


def infer_bucket_topics(topics: Iterable[str]) -> List[str]:
    normalized = [normalize_text(str(item)) for item in topics]
    buckets: List[str] = []
    for bucket, keywords in TOPIC_BUCKET_RULES.items():
        if any(any(keyword in topic for keyword in keywords) for topic in normalized):
            buckets.append(bucket)
    return buckets or ["general_llm"]


def infer_paper_id(path: Path, frontmatter: Dict[str, Any], title: str) -> str:
    paper_id = str(frontmatter.get("paper_id") or "").strip()
    if paper_id:
        return canonical_paper_id(paper_id)
    match = re.search(r"(\d{4}\.\d{4,5})", path.stem)
    if match:
        return match.group(1)
    return canonical_paper_id(title or path.stem)


def scan_knowledge_inventory(
    notes_root: Path,
    *,
    include_daily_recommendations: bool = True,
    recent_window_days: int = 90,
) -> Dict[str, Any]:
    # 只扫描强知识证据和弱接触证据两类目录，避免把整个 Vault 的噪声引入推荐器。
    candidate_roots = [
        ("strong_knowledge", "papers", notes_root / "research" / "papers"),
    ]
    if include_daily_recommendations:
        candidate_roots.append(
            ("weak_signal", "daily_recommendations", notes_root / "research" / "inbox" / "daily-recommendations")
        )

    now = datetime.now(timezone.utc)
    records: List[Dict[str, Any]] = []
    topic_counter: Counter[str] = Counter()
    bucket_counter: Counter[str] = Counter()
    slot_counter: Counter[str] = Counter()
    recent_topic_counter: Counter[str] = Counter()
    strong_topic_counter: Counter[str] = Counter()
    strong_bucket_counter: Counter[str] = Counter()
    strong_slot_counter: Counter[str] = Counter()
    weak_topic_counter: Counter[str] = Counter()
    paper_ids: set[str] = set()

    for evidence_strength, source_type, root in candidate_roots:
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            try:
                raw_text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            frontmatter, body = parse_frontmatter_and_body(raw_text)
            title = str(frontmatter.get("title") or path.stem)
            paper_id = infer_paper_id(path, frontmatter, title)
            topics = infer_topics(title, frontmatter, body)
            buckets = infer_bucket_topics(topics)
            slot_names = [normalize_text(str(item)) for item in (frontmatter.get("knowledge_slots") or []) if str(item).strip()]
            if not slot_names:
                slot_names = buckets
            modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            published_at = parse_timestamp(str(frontmatter.get("date") or frontmatter.get("published_at") or ""))
            summary = recent_first_paragraphs(body)
            record = {
                "paper_id": paper_id,
                "path": str(path),
                "title": title,
                "topics": topics,
                "bucket_topics": buckets,
                "knowledge_slots": slot_names,
                "status": str(frontmatter.get("status") or ""),
                "importance": frontmatter.get("importance", ""),
                "novelty": frontmatter.get("novelty", ""),
                "quality": frontmatter.get("quality", ""),
                "follow_up": frontmatter.get("follow_up", ""),
                "year": frontmatter.get("year", ""),
                "source": frontmatter.get("source", ""),
                "authors": frontmatter.get("authors") or [],
                "source_type": source_type,
                "evidence_strength": evidence_strength,
                "summary": summary[:1200],
                "modified_at": modified_at.isoformat(),
                "published_at": published_at.isoformat() if published_at else "",
            }
            records.append(record)
            paper_ids.add(paper_id)
            for topic in topics:
                topic_counter[normalize_text(topic)] += 1
                if evidence_strength == "strong_knowledge":
                    strong_topic_counter[normalize_text(topic)] += 1
                else:
                    weak_topic_counter[normalize_text(topic)] += 1
            for bucket in buckets:
                bucket_counter[bucket] += 1
                if evidence_strength == "strong_knowledge":
                    strong_bucket_counter[bucket] += 1
            for slot in slot_names:
                slot_counter[slot] += 1
                if evidence_strength == "strong_knowledge":
                    strong_slot_counter[slot] += 1
            if modified_at >= now - timedelta(days=recent_window_days):
                for topic in topics:
                    recent_topic_counter[normalize_text(topic)] += 1

    recent_records = sorted(records, key=lambda item: item.get("modified_at", ""), reverse=True)
    return {
        "generated_at": now.isoformat(),
        "stats": {
            "note_count": len(records),
            "paper_count": len(paper_ids),
            "strong_note_count": sum(1 for item in records if item["evidence_strength"] == "strong_knowledge"),
            "weak_note_count": sum(1 for item in records if item["evidence_strength"] == "weak_signal"),
        },
        "paper_ids": sorted(paper_ids),
        "records": records,
        "topic_frequency": dict(topic_counter.most_common()),
        "bucket_frequency": dict(bucket_counter.most_common()),
        "slot_frequency": dict(slot_counter.most_common()),
        "strong_topic_frequency": dict(strong_topic_counter.most_common()),
        "strong_bucket_frequency": dict(strong_bucket_counter.most_common()),
        "strong_slot_frequency": dict(strong_slot_counter.most_common()),
        "weak_topic_frequency": dict(weak_topic_counter.most_common()),
        "recent_topic_frequency": dict(recent_topic_counter.most_common()),
        "recent_records": recent_records[:50],
    }


def compact_topic_stats(inventory: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "generated_at": inventory.get("generated_at", ""),
        "topic_frequency": inventory.get("topic_frequency", {}),
        "bucket_frequency": inventory.get("bucket_frequency", {}),
        "slot_frequency": inventory.get("slot_frequency", {}),
        "strong_topic_frequency": inventory.get("strong_topic_frequency", {}),
        "strong_bucket_frequency": inventory.get("strong_bucket_frequency", {}),
        "strong_slot_frequency": inventory.get("strong_slot_frequency", {}),
        "weak_topic_frequency": inventory.get("weak_topic_frequency", {}),
        "recent_topic_frequency": inventory.get("recent_topic_frequency", {}),
    }


def grouped_records_by_slot(inventory: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in inventory.get("records", []):
        for slot in record.get("knowledge_slots", []):
            grouped[slot].append(record)
    return grouped
