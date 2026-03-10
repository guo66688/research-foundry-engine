# 输入输出契约

## 输入

- `configs/workflow.yaml`
- `configs/profiles.yaml`
- `profile_id`

## 输出

- `runtime/runs/<run_id>/candidate_pool.jsonl`
- `runtime/runs/<run_id>/run_manifest.json`

## `candidate_pool.jsonl` 关键字段

- `run_id`
- `profile_id`
- `paper_id`
- `source`
- `source_record_id`
- `title`
- `abstract`
- `authors`
- `published_at`
- `updated_at`
- `categories`
- `source_url`
- `pdf_url`
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
- `warnings`
