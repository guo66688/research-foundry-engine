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
from scripts.lib.source_pools import build_source_pools, dedupe_records, merge_for_candidate_pool, dedupe_key  # noqa: E402


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


def bucket_source_mix(bucket_payload: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, int]]:
    summary: Dict[str, Dict[str, int]] = {}
    for bucket_name in ["must_read", "trend_watch", "gap_fill"]:
        counts: Dict[str, int] = {"arxiv": 0, "semantic_scholar": 0}
        for item in bucket_payload.get(bucket_name, []) or []:
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
    # 中文注释：today 回放只生成 daily_context，避免触发 deepread/dossier。
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


def ensure(condition: bool, message: str, errors: List[str]) -> None:
    if not condition:
        errors.append(message)


def validate_explain_fields(items: Iterable[Dict[str, Any]], required: List[str], errors: List[str], scope: str) -> None:
    for item in items:
        for field in required:
            value = item.get(field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"{scope}: missing field {field} for paper_id={item.get('paper_id', '')}")


def validate_dedupe(sample: Path, expected: Dict[str, Any], errors: List[str]) -> None:
    if not expected.get("validate_source_dedupe"):
        return
    fresh_pool = read_jsonl(sample / "fresh_pool.jsonl")
    hot_pool = read_jsonl(sample / "hot_pool.jsonl")
    candidate_pool = read_jsonl(sample / "candidate_pool.jsonl")

    # 中文注释：复用 source_pools 的去重逻辑，确保 cross-source dedupe 生效。
    pools = build_source_pools(fresh_pool + hot_pool)
    fresh_deduped = dedupe_records(pools.get("fresh_pool", []))
    hot_deduped = dedupe_records(pools.get("hot_pool", []))
    rebuilt = merge_for_candidate_pool({"fresh_pool": fresh_deduped, "hot_pool": hot_deduped})

    rebuilt_keys = {dedupe_key(item) for item in rebuilt}
    candidate_keys = {dedupe_key(item) for item in candidate_pool}
    ensure(rebuilt_keys == candidate_keys, f"{sample.name}: candidate_pool 与 dedupe 结果不一致", errors)

    for expectation in expected.get("dedupe_expectations", []):
        paper_id = expectation.get("paper_id", "")
        expected_source = expectation.get("expected_source", "")
        max_count = int(expectation.get("max_count", 1) or 1)
        matched = [item for item in candidate_pool if str(item.get("paper_id", "")) == paper_id]
        if len(matched) > max_count:
            errors.append(f"{sample.name}: paper_id={paper_id} 去重后数量超限 {len(matched)} > {max_count}")
        if matched and expected_source:
            actual_source = str(matched[0].get("source", ""))
            if actual_source != expected_source:
                errors.append(
                    f"{sample.name}: paper_id={paper_id} 去重来源不符 expected={expected_source} actual={actual_source}"
                )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate offline source-routing fixtures.")
    parser.add_argument("--fixtures-root", default="tests/fixtures/source_routing", help="Fixture root directory")
    parser.add_argument("--sample", action="append", default=[], help="Sample folder name (repeatable)")
    args = parser.parse_args()

    fixtures_root = (ROOT / args.fixtures_root).resolve()
    samples = list_samples(fixtures_root, args.sample)
    if not samples:
        raise SystemExit("no fixtures found")

    failed = 0
    for sample in samples:
        errors: List[str] = []
        expected = read_json(sample / "expected.json", default={}) or {}
        validate_dedupe(sample, expected, errors)

        config_path = sample / "workflow.yaml"
        profiles_path = sample / "profile.json"
        candidate_pool = sample / "candidate_pool.jsonl"
        fresh_pool = sample / "fresh_pool.jsonl"
        hot_pool = sample / "hot_pool.jsonl"
        manifest_path = sample / "run_manifest.json"

        triage_result = run_triage(config_path, profiles_path, candidate_pool)
        triage_payload = read_json(triage_result, default={}) or {}
        buckets = triage_payload.get("buckets", {}) or {}
        mix = bucket_source_mix(buckets)

        must_read = buckets.get("must_read", []) or []
        trend_watch = buckets.get("trend_watch", []) or []
        gap_fill = buckets.get("gap_fill", []) or []

        must_read_sources = set(expected.get("must_read_sources", []))
        forbidden_must_read_sources = set(expected.get("forbidden_must_read_sources", []))
        if must_read_sources:
            for item in must_read:
                ensure(
                    str(item.get("source", "")) in must_read_sources,
                    f"{sample.name}: must_read 来源超出允许范围",
                    errors,
                )
        if forbidden_must_read_sources:
            for item in must_read:
                ensure(
                    str(item.get("source", "")) not in forbidden_must_read_sources,
                    f"{sample.name}: must_read 出现禁止来源",
                    errors,
                )

        s2_trend_min = int(expected.get("trend_watch_min_semantic_scholar", 0) or 0)
        s2_trend_count = sum(1 for item in trend_watch if str(item.get("source", "")) == "semantic_scholar")
        ensure(
            s2_trend_count >= s2_trend_min,
            f"{sample.name}: trend_watch S2 数量不足 {s2_trend_count} < {s2_trend_min}",
            errors,
        )

        s2_gap_max = int(expected.get("gap_fill_max_semantic_scholar", 999) or 999)
        s2_gap_count = sum(1 for item in gap_fill if str(item.get("source", "")) == "semantic_scholar")
        ensure(
            s2_gap_count <= s2_gap_max,
            f"{sample.name}: gap_fill S2 超限 {s2_gap_count} > {s2_gap_max}",
            errors,
        )

        required_fields = list(expected.get("required_explain_fields", []))
        validate_explain_fields(must_read, required_fields, errors, f"{sample.name}:must_read")
        validate_explain_fields(trend_watch, required_fields, errors, f"{sample.name}:trend_watch")
        validate_explain_fields(gap_fill, required_fields, errors, f"{sample.name}:gap_fill")

        required_reason_tokens = expected.get("require_trend_watch_reason_contains", []) or []
        if required_reason_tokens:
            for item in trend_watch:
                if str(item.get("source", "")) != "semantic_scholar":
                    continue
                reason = str(item.get("bucket_routing_reason", ""))
                for token in required_reason_tokens:
                    if token not in reason:
                        errors.append(
                            f"{sample.name}: trend_watch 解释缺少关键字 '{token}' paper_id={item.get('paper_id', '')}"
                        )

        gap_slots = expected.get("required_gap_slots_any_of", []) or []
        if gap_slots:
            matched = False
            for item in gap_fill:
                explain = item.get("explain", {}) or {}
                hits = [str(slot) for slot in (explain.get("knowledge_gap_matched", []) or [])]
                if any(slot in gap_slots for slot in hits):
                    matched = True
                    break
            ensure(
                matched,
                f"{sample.name}: gap_fill 未命中期望的 knowledge_gap 槽位",
                errors,
            )

        if expected.get("validate_today"):
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
            context_payload = read_json(context_path, default={}) or {}
            required_daily_fields = expected.get("required_daily_context_fields", []) or []
            for field in required_daily_fields:
                ensure(field in context_payload, f"{sample.name}: daily_context 缺少字段 {field}", errors)

            review_min = int(expected.get("review_or_backfill_min", 0) or 0)
            review_items = context_payload.get("review_or_backfill", []) or []
            ensure(
                len(review_items) >= review_min,
                f"{sample.name}: review_or_backfill 数量不足 {len(review_items)} < {review_min}",
                errors,
            )

            validate_explain_fields(
                context_payload.get("must_read", []) or [],
                required_fields,
                errors,
                f"{sample.name}:daily_context.must_read",
            )
            validate_explain_fields(
                context_payload.get("trend_watch", []) or [],
                required_fields,
                errors,
                f"{sample.name}:daily_context.trend_watch",
            )
            validate_explain_fields(
                context_payload.get("gap_fill", []) or [],
                required_fields,
                errors,
                f"{sample.name}:daily_context.gap_fill",
            )

        status = "PASS" if not errors else "FAIL"
        print(f"[{sample.name}] {status}")
        print(json.dumps(mix, ensure_ascii=False, indent=2))
        if errors:
            failed += 1
            for error in errors:
                print(f"- {error}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
