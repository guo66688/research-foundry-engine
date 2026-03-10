# 输入输出契约

## 输入

- `configs/workflow.yaml`
- `run_id`
- `paper_id`
- `state`
- `kind=path` 形式的 artifact 列表

## 输出

- `runtime/runs/<run_id>/run_manifest.json`
- `runtime/artifacts/paper_registry.jsonl`
- `runtime/artifacts/run_registry.jsonl`

## `paper_registry.jsonl` 每项至少包含

- `run_id`
- `paper_id`
- `profile_id`
- `title`
- `slug`
- `state`
- `artifacts`
- `registered_at`
- `updated_at`

## `run_registry.jsonl` 每项至少包含

- `run_id`
- `profile_id`
- `started_at`
- `updated_at`
- `status`
- `artifacts`
