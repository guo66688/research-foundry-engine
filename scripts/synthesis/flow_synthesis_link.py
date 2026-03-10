from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, List

import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.shared.flow_common import load_yaml, resolve_runtime_path, slugify, utc_timestamp  # noqa: E402
from scripts.shared.flow_notes import dossier_snapshot, scan_notes, score_note_matches  # noqa: E402
from scripts.shared.flow_relations import (  # noqa: E402
    load_relations,
    make_relation_id,
    save_relations,
    upsert_edge,
    upsert_node,
)

LOGGER = logging.getLogger("flow_synthesis_link")


def dedupe_matches(matches: List[Dict[str, object]]) -> List[Dict[str, object]]:
    output: List[Dict[str, object]] = []
    seen_note_ids = set()
    for match in matches:
        note_id = match["note_id"]
        if note_id in seen_note_ids:
            continue
        seen_note_ids.add(note_id)
        output.append(match)
    return output


def build_report(dossier: Dict[str, object], matches: List[Dict[str, object]]) -> str:
    lines = [
        f"# Synthesis Report: {dossier['title']}",
        "",
        f"- paper_id: `{dossier['paper_id']}`",
        f"- generated_at: `{utc_timestamp()}`",
        "",
    ]
    if not matches:
        lines.extend(
            [
                "No note matches were found.",
                "",
                "Check `workspace.notes_root` or adjust the synthesis policy.",
            ]
        )
        return "\n".join(lines).strip() + "\n"

    lines.append("## Suggested Links")
    lines.append("")
    for match in matches:
        lines.append(f"### {match['title']}")
        lines.append(f"- path: `{match['path']}`")
        lines.append(f"- overlap_score: `{match['score']}`")
        lines.append(f"- relation_score: `{match['relation_score']}`")
        lines.append(f"- overlap_terms: `{', '.join(match['overlaps'])}`")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Link one dossier to an existing note base.")
    parser.add_argument("--config", required=True, help="Path to workflow config")
    parser.add_argument("--dossier", required=True, help="Path to dossier markdown")
    parser.add_argument("--notes-root", default="", help="Optional notes root override")
    parser.add_argument("--output", default="", help="Optional synthesis report path")
    parser.add_argument("--relations-output", default="", help="Optional relations.json path")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    workflow = load_yaml(Path(args.config))
    dossier = dossier_snapshot(Path(args.dossier))
    notes_root_value = args.notes_root or workflow.get("workspace", {}).get("notes_root", "")
    notes_root = Path(notes_root_value) if notes_root_value else Path("__missing_notes_root__")
    matches = dedupe_matches(score_note_matches(dossier, scan_notes(notes_root)))
    max_backlinks = int(workflow.get("synthesis_policy", {}).get("max_backlinks", 8))
    relation_score_threshold = float(workflow.get("synthesis_policy", {}).get("relation_score_threshold", 0.2))
    allowed_relation_types = set(workflow.get("synthesis_policy", {}).get("relation_types", ["shares_topic"]))
    filtered_matches: List[Dict[str, object]] = []
    for match in matches:
        relation_score = min(float(match["score"]) / 10.0, 1.0)
        if relation_score < relation_score_threshold:
            continue
        bundle = dict(match)
        bundle["relation_score"] = round(relation_score, 3)
        filtered_matches.append(bundle)
    selected_matches = filtered_matches[:max_backlinks]

    artifact_dir = resolve_runtime_path(workflow, "artifact")
    paper_id = dossier["paper_id"] or slugify(str(dossier["title"]))
    report_path = (
        Path(args.output)
        if args.output
        else artifact_dir / f"synthesis_report-{paper_id}.md"
    )
    relations_path = (
        Path(args.relations_output)
        if args.relations_output
        else Path(workflow.get("synthesis_policy", {}).get("relation_store", artifact_dir / "relations.json"))
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_report(dossier, selected_matches), encoding="utf-8")

    relations = load_relations(relations_path)
    paper_node_id = f"paper:{paper_id}"
    upsert_node(
        relations,
        {
            "id": paper_node_id,
            "kind": "paper",
            "label": dossier["title"],
            "path": str(Path(args.dossier)),
            "paper_id": paper_id,
        },
    )
    for match in selected_matches:
        upsert_node(
            relations,
            {
                "id": match["note_id"],
                "kind": "note",
                "label": match["title"],
                "path": match["path"],
                "paper_id": "",
            },
        )
        if "shares_topic" in allowed_relation_types:
            upsert_edge(
                relations,
                {
                    "id": make_relation_id(paper_node_id, str(match["note_id"]), "shares_topic"),
                    "source": paper_node_id,
                    "target": match["note_id"],
                    "type": "shares_topic",
                    "weight": float(match["relation_score"]),
                },
            )
    save_relations(relations_path, relations)

    LOGGER.info("synthesis_report=%s", report_path)
    LOGGER.info("relations=%s", relations_path)
    LOGGER.info("backlinks=%d", len(selected_matches))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
