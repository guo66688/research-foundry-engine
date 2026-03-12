from __future__ import annotations

import argparse
from pathlib import Path

from runtime_bootstrap import maybe_reexec_for_runtime

maybe_reexec_for_runtime(__file__)

from command_common import (
    build_deepread_note,
    console_summary,
    daily_note_path,
    load_yaml,
    plan_today_queue,
    prepare_today_materials,
    read_json,
    render_daily_note,
    resolve_backend,
    resolve_notes_root,
    run_candidate_triage,
    run_source_intake,
    write_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare daily recommendation materials; final Markdown is normally written by Codex.")
    parser.add_argument("--config", default="configs/workflow.yaml", help="Path to workflow config")
    parser.add_argument("--profiles", default="configs/profiles.yaml", help="Path to profiles config")
    parser.add_argument("--profile-id", default="llm_systems", help="Profile identifier")
    parser.add_argument("--mode", choices=["auto", "external", "standalone"], default="standalone", help="Execution backend")
    parser.add_argument("--notes-root", default="", help="Optional notes root override")
    parser.add_argument("--top-deepreads", type=int, default=3, help="How many shortlisted papers to deep-read")
    parser.add_argument("--reuse-run-id", default="", help="Reuse an existing run directory instead of fetching again")
    parser.add_argument("--write-final-markdown", action="store_true", help="Also write the final daily note and deepread markdown files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve()
    profiles_path = Path(args.profiles).resolve()
    backend = resolve_backend(args.mode)
    workflow = load_yaml(config_path)
    notes_root = resolve_notes_root(workflow, args.notes_root)
    if args.reuse_run_id:
        run_dir = Path(workflow.get("runtime", {}).get("run_dir", "runtime/runs")) / args.reuse_run_id
        intake = {
            "run_id": args.reuse_run_id,
            "candidate_pool": run_dir / "candidate_pool.jsonl",
            "fresh_pool": run_dir / "fresh_pool.jsonl",
            "hot_pool": run_dir / "hot_pool.jsonl",
            "raw_output": "",
        }
        triage_result_path = run_dir / "triage_result.json"
        if triage_result_path.exists():
            triage = {"triage_result": triage_result_path, "reading_queue": None, "raw_output": ""}
        else:
            triage = run_candidate_triage(backend, config_path, profiles_path, args.profile_id, intake["candidate_pool"])
    else:
        intake = run_source_intake(backend, config_path, profiles_path, args.profile_id)
        triage = run_candidate_triage(backend, config_path, profiles_path, args.profile_id, intake["candidate_pool"])
    triage_payload = read_json(triage["triage_result"], default={}) or {}
    manifest_payload = read_json(intake["candidate_pool"].parent / "run_manifest.json", default={}) or {}
    queue_plan = plan_today_queue(workflow, config_path, args.profile_id, triage_payload)
    prepared = prepare_today_materials(
        backend,
        workflow,
        config_path,
        profiles_path,
        args.profile_id,
        notes_root,
        intake,
        triage,
        triage_payload,
        manifest_payload,
        queue_plan,
        top_deepreads=args.top_deepreads,
    )

    if args.write_final_markdown:
        selected = list(triage_payload.get("selected", []))
        deepread_picks = {
            "must_read_top2": [item.get("paper_id", "") for item in queue_plan.get("final_buckets", {}).get("must_read", [])[:2]],
            "gap_fill_top1": [item.get("paper_id", "") for item in queue_plan.get("final_buckets", {}).get("gap_fill", [])[:1]],
        }
        selected_map = {str(item.get("paper_id", "")): item for item in selected}
        deepread_ids = []
        for key in ["must_read_top2", "gap_fill_top1"]:
            for paper_id in deepread_picks.get(key, []) or []:
                if paper_id and paper_id not in deepread_ids:
                    deepread_ids.append(str(paper_id))
        if not deepread_ids:
            deepread_ids = [str(item.get("paper_id", "")) for item in selected[: max(args.top_deepreads, 0)]]
        top3_notes = []
        for paper_id in deepread_ids[: max(args.top_deepreads, 0)]:
            record = selected_map.get(str(paper_id))
            if record is None:
                continue
            bundle = dict(record)
            bundle["_triage_file"] = str(triage["triage_result"])
            bundle["_candidate_file"] = str(intake["candidate_pool"])
            bundle["_run_id"] = str(triage_payload.get("run_id", ""))
            deepread = build_deepread_note(
                backend,
                workflow,
                config_path,
                profiles_path,
                args.profile_id,
                notes_root,
                bundle,
                enable_links=True,
            )
            top3_notes.append({"title": str(record.get("title", "")), "note_path": deepread["note_path"]})
        daily_path = daily_note_path(notes_root, args.profile_id, str(triage_payload.get("generated_at", "")))
        write_text(daily_path, render_daily_note(manifest_payload, triage_payload, top3_notes, notes_root))

    print(
        console_summary(
            "today",
            [
                f"backend={backend.mode}",
                f"run_id={triage_payload.get('run_id', '')}",
                f"candidate_pool={intake['candidate_pool']}",
                f"fresh_pool={intake.get('fresh_pool', '')}",
                f"hot_pool={intake.get('hot_pool', '')}",
                f"triage_result={triage['triage_result']}",
                f"daily_context={prepared['context_path']}",
                f"daily_template={prepared['template_path']}",
                f"target_daily_note={prepared['target_note_path']}",
                f"top_deepread_count={len(prepared['prepared_deepreads'])}",
                f"review_or_backfill_count={len(queue_plan.get('review_or_backfill', []))}",
                f"candidate_count={triage_payload.get('stats', {}).get('input_count', 0)}",
                f"shortlist_count={triage_payload.get('stats', {}).get('selected_count', 0)}",
                f"final_markdown_written={'yes' if args.write_final_markdown else 'no'}",
            ],
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
