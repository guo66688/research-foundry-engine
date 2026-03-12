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
- `source_routing_policy`
- `source_mix_summary`
- `buckets`
- `selected`
- `rejected`

## `selected` / `rejected` 关键字段

- `paper_id`
- `title`
- `state`
- `scores`
- `score_breakdown`
- `tier`
- `decision`
- `decision_reasons`
- `source`
- `source_role`
- `bucket_routing_reason`
- `source_selection_reason`
- `dedupe_group_id`
- `reason`
