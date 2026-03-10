from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

import yaml

from scripts.shared.flow_common import slugify


def parse_frontmatter(text: str) -> Dict[str, object]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    payload = yaml.safe_load(match.group(1)) or {}
    return payload if isinstance(payload, dict) else {}


def dossier_snapshot(path: Path) -> Dict[str, object]:
    content = path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(content)
    title = frontmatter.get("title") or path.stem
    paper_id = frontmatter.get("paper_id") or ""
    return {
        "title": str(title),
        "paper_id": str(paper_id),
        "content": content,
    }


def scan_notes(notes_root: Path) -> List[Dict[str, object]]:
    notes: List[Dict[str, object]] = []
    if not notes_root.exists():
        return notes
    for note_path in notes_root.rglob("*.md"):
        try:
            content = note_path.read_text(encoding="utf-8")
        except OSError:
            continue
        frontmatter = parse_frontmatter(content)
        title = frontmatter.get("title") or note_path.stem
        tags = frontmatter.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        notes.append(
            {
                "id": f"note:{slugify(str(note_path))}",
                "title": str(title),
                "tags": [str(tag) for tag in tags],
                "path": str(note_path),
                "content": content,
            }
        )
    return notes


def important_terms(text: str) -> List[str]:
    candidates = re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", text.lower())
    stop_words = {
        "with",
        "from",
        "that",
        "this",
        "into",
        "paper",
        "results",
        "using",
        "their",
        "there",
        "these",
        "which",
        "have",
        "been",
        "model",
        "models",
    }
    unique: List[str] = []
    seen = set()
    for item in candidates:
        if item in stop_words or item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def score_note_matches(dossier: Dict[str, object], notes: List[Dict[str, object]]) -> List[Dict[str, object]]:
    terms = set(important_terms(str(dossier["title"]) + "\n" + str(dossier["content"])))
    scored: List[Dict[str, object]] = []
    for note in notes:
        note_text = f"{note['title']}\n{' '.join(note['tags'])}\n{note['content']}".lower()
        overlaps = [term for term in terms if term in note_text]
        if not overlaps:
            continue
        scored.append(
            {
                "note_id": note["id"],
                "title": note["title"],
                "path": note["path"],
                "score": len(overlaps),
                "overlaps": overlaps[:8],
            }
        )
    scored.sort(key=lambda item: int(item["score"]), reverse=True)
    return scored
