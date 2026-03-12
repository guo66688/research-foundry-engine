# 输入输出契约

## 输入

- `configs/workflow.yaml`
- `configs/profiles.yaml`
- `profile_id`

## 输出

- `runtime/runs/<run_id>/fresh_pool.jsonl`
- `runtime/runs/<run_id>/hot_pool.jsonl`
- `runtime/runs/<run_id>/candidate_pool.jsonl`（兼容总池）
- `runtime/runs/<run_id>/run_manifest.json`

## `candidate_pool.jsonl` 关键字段

- `run_id`
- `profile_id`
- `paper_id`
- `source`
- `source_role`
- `source_pool`
- `title`
- `abstract`
- `authors`
- `published_at`
- `categories`
- `citation_count`
- `influential_citation_count`
- `profile_hits`
- `state`
- `fetched_at`

## `run_manifest.json` 最少应包含

- `run_id`
- `profile_id`
- `started_at`
- `updated_at`
- `status`
- `stage`
- `artifacts`
- `candidate_count`
- `source_counts`
- `source_status`
- `source_pools`
- `warnings`
