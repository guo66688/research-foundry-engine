from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, List

import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.shared.flow_common import (  # noqa: E402
    ensure_dir,
    load_yaml,
    read_json,
    read_jsonl,
    replace_jsonl_entry,
    resolve_runtime_path,
    slugify,
    utc_timestamp,
    write_json,
    write_jsonl,
)

LOGGER = logging.getLogger("flow_registry_update")


def parse_artifacts(raw_items: List[str]) -> List[Dict[str, str]]:
    artifacts: List[Dict[str, str]] = []
    for item in raw_items:
        if "=" not in item:
            raise ValueError(f"artifact must use kind=path format: {item}")
        kind, path = item.split("=", 1)
        artifacts.append({"kind": kind.strip(), "path": path.strip()})
    return artifacts


def merge_artifacts(existing: List[Dict[str, str]], incoming: List[Dict[str, str]]) -> List[Dict[str, str]]:
    # registry 使用 upsert 语义，但不能在重复执行时丢掉旧的产物引用。
    merged: List[Dict[str, str]] = []
    seen = set()
    for item in existing + incoming:
        key = (item.get("kind", ""), item.get("path", ""))
        if key in seen:
            continue
        seen.add(key)
        merged.append({"kind": key[0], "path": key[1]})
    return merged


def find_existing(entries: List[Dict[str, object]], key_fields: List[str], record: Dict[str, object]) -> Dict[str, object]:
    for entry in entries:
        if all(entry.get(name) == record.get(name) for name in key_fields):
            return entry
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Register run outputs and stable artifacts.")
    parser.add_argument("--config", required=True, help="Path to workflow config")
    parser.add_argument("--run-id", required=True, help="Run identifier")
    parser.add_argument("--profile-id", default="", help="Optional profile identifier")
    parser.add_argument("--paper-id", required=True, help="Paper identifier")
    parser.add_argument("--title", default="", help="Optional paper title")
    parser.add_argument("--state", required=True, help="Lifecycle state to register")
    parser.add_argument("--artifact", action="append", default=[], help="Artifact entry in kind=path format")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    workflow = load_yaml(Path(args.config))
    artifact_dir = ensure_dir(resolve_runtime_path(workflow, "artifact"))
    run_dir = ensure_dir(resolve_runtime_path(workflow, "run") / args.run_id)

    artifacts = parse_artifacts(args.artifact)
    title = args.title or args.paper_id
    slug = slugify(title)
    registered_at = utc_timestamp()

    run_manifest_path = run_dir / "run_manifest.json"
    run_manifest = read_json(run_manifest_path, default={}) or {}
    merged_manifest_artifacts = merge_artifacts(list(run_manifest.get("artifacts", [])), artifacts)
    run_manifest.update(
        {
            "run_id": args.run_id,
            "profile_id": args.profile_id or run_manifest.get("profile_id", ""),
            "started_at": run_manifest.get("started_at", registered_at),
            "updated_at": registered_at,
            "status": "completed" if args.state == "registered" else "running",
            "artifacts": merged_manifest_artifacts,
        }
    )
    write_json(run_manifest_path, run_manifest)

    paper_registry_path = artifact_dir / "paper_registry.jsonl"
    run_registry_path = artifact_dir / "run_registry.jsonl"

    paper_entries = read_jsonl(paper_registry_path)
    existing_paper_record = find_existing(
        paper_entries,
        ["run_id", "paper_id"],
        {"run_id": args.run_id, "paper_id": args.paper_id},
    )
    paper_record = {
        "run_id": args.run_id,
        "paper_id": args.paper_id,
        "profile_id": args.profile_id,
        "title": title,
        "slug": slug,
        "state": args.state,
        "artifacts": merge_artifacts(list(existing_paper_record.get("artifacts", [])), artifacts),
        "registered_at": existing_paper_record.get("registered_at", registered_at),
        "updated_at": registered_at,
    }
    write_jsonl(paper_registry_path, replace_jsonl_entry(paper_entries, paper_record, ["run_id", "paper_id"]))

    run_entries = read_jsonl(run_registry_path)
    existing_run_record = find_existing(run_entries, ["run_id"], {"run_id": args.run_id})
    run_record = {
        "run_id": args.run_id,
        "profile_id": args.profile_id,
        "started_at": run_manifest.get("started_at", registered_at),
        "updated_at": registered_at,
        "status": run_manifest["status"],
        "artifacts": merge_artifacts(list(existing_run_record.get("artifacts", [])), artifacts),
    }
    write_jsonl(run_registry_path, replace_jsonl_entry(run_entries, run_record, ["run_id"]))

    LOGGER.info("run_manifest=%s", run_manifest_path)
    LOGGER.info("paper_registry=%s", paper_registry_path)
    LOGGER.info("run_registry=%s", run_registry_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
