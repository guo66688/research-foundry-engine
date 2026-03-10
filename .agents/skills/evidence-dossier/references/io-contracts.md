# 输入输出契约

## 输入

- `configs/workflow.yaml`
- `configs/profiles.yaml`
- `profile_id`
- `paper_id`
- `runtime/runs/<run_id>/triage_result.json` 或 `candidate_pool.jsonl`

## 输出

- `runtime/artifacts/dossier-<paper_id>-<slug>.md`
- 可选 `runtime/artifacts/figure_manifest-<paper_id>.json`

## dossier Frontmatter 最少应包含

- `title`
- `paper_id`
- `profile_id`
- `state`
- `generated_at`

## `figure_manifest-<paper_id>.json` 最少应包含

- `paper_id`
- `generated_at`
- `figure_count`
- `items`
