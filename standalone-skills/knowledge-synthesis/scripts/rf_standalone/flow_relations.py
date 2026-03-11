from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from rf_standalone.flow_common import read_json, slugify, utc_timestamp, write_json


def load_relations(path: Path) -> Dict[str, object]:
    payload = read_json(path, default=None)
    if isinstance(payload, dict):
        payload.setdefault("updated_at", utc_timestamp())
        payload.setdefault("nodes", [])
        payload.setdefault("edges", [])
        return payload
    return {"updated_at": utc_timestamp(), "nodes": [], "edges": []}


def upsert_node(relations: Dict[str, object], node: Dict[str, object]) -> None:
    nodes: List[Dict[str, object]] = relations["nodes"]  # type: ignore[assignment]
    for index, existing in enumerate(nodes):
        if existing.get("id") == node.get("id"):
            nodes[index] = node
            return
    nodes.append(node)


def make_relation_id(source: str, target: str, relation_type: str) -> str:
    return f"rel-{slugify(source)}-{slugify(target)}-{relation_type}"


def upsert_edge(relations: Dict[str, object], edge: Dict[str, object]) -> None:
    edges: List[Dict[str, object]] = relations["edges"]  # type: ignore[assignment]
    for index, existing in enumerate(edges):
        if existing.get("id") == edge.get("id"):
            edges[index] = edge
            return
    edges.append(edge)


def save_relations(path: Path, relations: Dict[str, object]) -> None:
    relations["updated_at"] = utc_timestamp()
    write_json(path, relations)
