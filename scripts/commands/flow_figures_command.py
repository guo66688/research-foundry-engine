from __future__ import annotations

import argparse
from pathlib import Path

from runtime_bootstrap import maybe_reexec_for_runtime

maybe_reexec_for_runtime(__file__)

from command_common import (
    console_summary,
    image_index_path,
    load_yaml,
    paper_image_dir,
    render_image_index,
    resolve_backend,
    resolve_notes_root,
    resolve_paper_record,
    run_figure_extraction,
    write_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract figures for one paper and optionally write an index note.")
    parser.add_argument("paper", help="paper_id or title")
    parser.add_argument("--config", default="configs/workflow.yaml", help="Path to workflow config")
    parser.add_argument("--mode", choices=["auto", "external", "standalone"], default="standalone", help="Execution backend")
    parser.add_argument("--notes-root", default="", help="Optional notes root override")
    parser.add_argument("--no-index", action="store_true", help="Do not create a figure index markdown note")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve()
    workflow = load_yaml(config_path)
    notes_root = resolve_notes_root(workflow, args.notes_root)
    backend = resolve_backend(args.mode)
    record = resolve_paper_record(args.paper, workflow)
    output_dir = paper_image_dir(notes_root, str(record.get("paper_id", "")))
    try:
        result = run_figure_extraction(backend, workflow, record, output_dir)
    except RuntimeError:
        result = {"manifest_path": "", "manifest": {"figure_count": 0, "items": []}}
    copied = result["manifest"].get("items", [])

    index_path = None
    if not args.no_index:
        index_path = image_index_path(notes_root, str(record.get("paper_id", "")))
        write_text(index_path, render_image_index(record, copied))

    print(
        console_summary(
            "figures",
            [
                f"backend={backend.mode}",
                f"paper_id={record.get('paper_id', '')}",
                f"output_dir={output_dir}",
                f"manifest={result['manifest_path']}",
                f"figure_count={result['manifest'].get('figure_count', 0)}",
                f"index_note={index_path or ''}",
            ],
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
