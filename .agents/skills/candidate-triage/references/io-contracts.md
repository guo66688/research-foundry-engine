# 输入输出契约

## 输入

- `configs/workflow.yaml`
- `configs/profiles.yaml`
- `profile_id`
- `runtime/runs/<run_id>/candidate_pool.jsonl`

## 输出

- `runtime/runs/<run_id>/triage_result.json`
- `runtime/artifacts/reading_queue-<run_id>.md`

## `triage_result.json` 顶层字段

- `run_id`
- `profile_id`
- `generated_at`
- `input_path`
- `dedupe_strategy`
- `weights`
- `stats`
- `selected`
- `rejected`

## `selected` 与 `rejected` 每项至少包含

- `paper_id`
- `title`
- `state`
- `scores`
- `tier`
- `reason`
