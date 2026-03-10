# 输入输出契约

## 输入

- `configs/workflow.yaml`
- `runtime/artifacts/dossier-<paper_id>-<slug>.md`
- 可选 `notes_root`

## 输出

- `runtime/artifacts/synthesis_report-<paper_id>.md`
- `runtime/artifacts/relations.json`

## `synthesis_report` 至少应包含

- `paper_id`
- `generated_at`
- 匹配到的笔记列表或空结果说明

## `relations.json` 顶层字段

- `updated_at`
- `nodes`
- `edges`
