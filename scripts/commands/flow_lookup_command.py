from __future__ import annotations

import argparse
from pathlib import Path

from command_common import console_summary, load_yaml, resolve_notes_root, search_notes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search paper notes in the vault.")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--config", default="configs/workflow.yaml", help="Path to workflow config")
    parser.add_argument("--notes-root", default="", help="Optional notes root override")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of matches")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve()
    workflow = load_yaml(config_path)
    notes_root = resolve_notes_root(workflow, args.notes_root)
    matches = search_notes(notes_root, args.query, limit=args.limit)

    rows = [f"query={args.query}", f"count={len(matches)}"]
    for index, item in enumerate(matches, start=1):
        rows.append(
            f"{index}. title={item['title']} | score={item['score']} | path={item['path']} | overlaps={', '.join(item['overlaps'])}"
        )
    print(console_summary("lookup", rows), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
