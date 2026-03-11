from __future__ import annotations

import argparse
from pathlib import Path

from runtime_bootstrap import maybe_reexec_for_runtime

maybe_reexec_for_runtime(__file__)

from command_common import (
    build_deepread_note,
    console_summary,
    load_yaml,
    prepare_deepread_materials,
    resolve_backend,
    resolve_notes_root,
    resolve_paper_record,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare deep-read materials for one paper; final Markdown is normally written by Codex.")
    parser.add_argument("paper", help="paper_id or title")
    parser.add_argument("--config", default="configs/workflow.yaml", help="Path to workflow config")
    parser.add_argument("--profiles", default="configs/profiles.yaml", help="Path to profiles config")
    parser.add_argument("--profile-id", default="llm_systems", help="Profile identifier")
    parser.add_argument("--mode", choices=["auto", "external", "standalone"], default="standalone", help="Execution backend")
    parser.add_argument("--notes-root", default="", help="Optional notes root override")
    parser.add_argument("--disable-links", action="store_true", help="Skip knowledge synthesis and local linking")
    parser.add_argument("--write-final-markdown", action="store_true", help="Also write the final paper note markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve()
    profiles_path = Path(args.profiles).resolve()
    workflow = load_yaml(config_path)
    notes_root = resolve_notes_root(workflow, args.notes_root)
    backend = resolve_backend(args.mode)
    record = resolve_paper_record(args.paper, workflow)
    if args.write_final_markdown:
        result = build_deepread_note(
            backend,
            workflow,
            config_path,
            profiles_path,
            args.profile_id,
            notes_root,
            record,
            enable_links=not args.disable_links,
        )
    else:
        result = prepare_deepread_materials(
            backend,
            workflow,
            config_path,
            profiles_path,
            args.profile_id,
            notes_root,
            record,
            enable_links=not args.disable_links,
        )

    print(
        console_summary(
            "deepread",
            [
                f"backend={backend.mode}",
                f"paper_id={record.get('paper_id', '')}",
                f"target_note={result['note_path']}",
                f"context={result['context_path']}",
                f"template={result['template_path']}",
                f"dossier={result['dossier_path']}",
                f"synthesis_report={result.get('synthesis_report_path') or ''}",
                f"full_text={result.get('full_text_path') or ''}",
                f"figure_count={len(result.get('copied_figures', []))}",
                f"related_note_count={len(result.get('related_notes', []))}",
                f"final_markdown_written={'yes' if args.write_final_markdown else 'no'}",
            ],
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
