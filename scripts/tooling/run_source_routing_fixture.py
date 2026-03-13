from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from scripts.commands.command_common import (  # noqa: E402
        load_yaml,
        plan_today_queue,
        prepare_today_materials,
        resolve_backend,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - 仅用于依赖缺失提示
    if "yaml" in str(exc):
        raise SystemExit("缺少 PyYAML 依赖，请先安装 requirements.txt") from exc
    raise


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def list_samples(fixtures_root: Path, selected: Iterable[str]) -> List[Path]:
    if selected:
        return [fixtures_root / name for name in selected]
    return sorted([path for path in fixtures_root.iterdir() if path.is_dir()])


def run_triage(config_path: Path, profiles_path: Path, candidate_pool: Path) -> Path:
    workflow = load_yaml(config_path)
    records = read_jsonl(candidate_pool)
    if not records:
        raise RuntimeError(f"candidate_pool is empty: {candidate_pool}")
    run_id = str(records[0].get("run_id", "")).strip()
    if not run_id:
        raise RuntimeError(f"candidate_pool missing run_id: {candidate_pool}")
    run_dir = Path(workflow.get("runtime", {}).get("run_dir", "runtime/runs")) / run_id
    artifact_dir = Path(workflow.get("runtime", {}).get("artifact_dir", "runtime/artifacts"))
    triage_output = run_dir / "triage_result.json"
    queue_output = artifact_dir / f"reading_queue-{run_id}.md"

    # 中文注释：这里直接调用 triage CLI，确保走完整评分与分桶逻辑。
    script_path = ROOT / "scripts" / "triage" / "flow_triage_rank.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--config",
            str(config_path),
            "--profiles",
            str(profiles_path),
            "--profile-id",
            "llm_systems",
            "--input",
            str(candidate_pool),
            "--output",
            str(triage_output),
            "--queue-output",
            str(queue_output),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stdout or "") + (completed.stderr or ""))
    return triage_output


def bucket_source_mix(triage_payload: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    buckets = triage_payload.get("buckets", {}) or {}
    summary: Dict[str, Dict[str, int]] = {}
    for bucket_name in ["must_read", "trend_watch", "gap_fill"]:
        counts: Dict[str, int] = {"arxiv": 0, "semantic_scholar": 0}
        for item in buckets.get(bucket_name, []) or []:
            source = str(item.get("source", "")).strip()
            counts[source] = counts.get(source, 0) + 1
        summary[bucket_name] = counts
    return summary


def run_today(
    config_path: Path,
    profiles_path: Path,
    intake: Dict[str, Any],
    triage: Dict[str, Any],
    triage_payload: Dict[str, Any],
    manifest_payload: Dict[str, Any],
) -> Path:
    workflow = load_yaml(config_path)
    backend = resolve_backend("external")
    queue_plan = plan_today_queue(workflow, config_path, "llm_systems", triage_payload)
    prepared = prepare_today_materials(
        backend,
        workflow,
        config_path,
        profiles_path,
        "llm_systems",
        Path(workflow.get("workspace", {}).get("notes_root", ".")),
        intake,
        triage,
        triage_payload,
        manifest_payload,
        queue_plan,
        top_deepreads=0,
    )
    return Path(prepared["context_path"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Run offline source-routing fixtures.")
    parser.add_argument("--fixtures-root", default="tests/fixtures/source_routing", help="Fixture root directory")
    parser.add_argument("--sample", action="append", default=[], help="Sample folder name (repeatable)")
    parser.add_argument("--today", action="store_true", help="Also generate daily_context (top_deepreads=0)")
    args = parser.parse_args()

    fixtures_root = (ROOT / args.fixtures_root).resolve()
    samples = list_samples(fixtures_root, args.sample)
    if not samples:
        raise SystemExit("no fixtures found")

    for sample in samples:
        config_path = sample / "workflow.yaml"
        profiles_path = sample / "profile.json"
        candidate_pool = sample / "candidate_pool.jsonl"
        fresh_pool = sample / "fresh_pool.jsonl"
        hot_pool = sample / "hot_pool.jsonl"
        manifest_path = sample / "run_manifest.json"

        triage_result = run_triage(config_path, profiles_path, candidate_pool)
        triage_payload = read_json(triage_result, default={}) or {}
        mix = bucket_source_mix(triage_payload)

        print(f"[{sample.name}] triage_result={triage_result}")
        print(json.dumps(mix, ensure_ascii=False, indent=2))

        if args.today:
            workflow = load_yaml(config_path)
            reading_queue_path = (
                Path(workflow.get("runtime", {}).get("artifact_dir", "runtime/artifacts"))
                / f"reading_queue-{triage_payload.get('run_id', '')}.md"
            )
            if not reading_queue_path.exists():
                reading_queue_path = None
            intake = {
                "run_id": triage_payload.get("run_id", ""),
                "candidate_pool": candidate_pool,
                "fresh_pool": fresh_pool,
                "hot_pool": hot_pool,
                "raw_output": "",
            }
            triage = {
                "triage_result": triage_result,
                "reading_queue": reading_queue_path,
                "raw_output": "",
            }
            manifest_payload = read_json(manifest_path, default={}) or {}
            context_path = run_today(config_path, profiles_path, intake, triage, triage_payload, manifest_payload)
            print(f"[{sample.name}] daily_context={context_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
