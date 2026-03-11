# 交接矩阵

| 当前 skill | 完成条件 | 交接目标 | 不允许越过的下游阶段 | 必需产物 |
| --- | --- | --- | --- | --- |
| `source-intake` | `candidate_pool.jsonl` 写出且记录数大于 0 | `candidate-triage` | `evidence-dossier`、`knowledge-synthesis`、`run-registry` | `candidate_pool.jsonl` |
| `candidate-triage` | `triage_result.json` 与 `reading_queue-<run_id>.md` 写出 | `evidence-dossier` 或等待用户选择论文 | `knowledge-synthesis`、`run-registry` | `triage_result.json`、`reading_queue-<run_id>.md` |
| `evidence-dossier` | `dossier-<paper_id>-<slug>.md` 写出；若启用图像模式，则 `figure_manifest-<paper_id>.json` 也写出 | `knowledge-synthesis` | `run-registry` | `dossier-<paper_id>-<slug>.md` |
| `knowledge-synthesis` | `synthesis_report-<paper_id>.md` 写出且 `relations.json` 已更新 | `run-registry` 或人工审阅 | 不应直接回跳到 `source-intake` 或 `candidate-triage` | `synthesis_report-<paper_id>.md`、`relations.json` |
| `run-registry` | `run_manifest.json`、`paper_registry.jsonl`、`run_registry.jsonl` 更新成功 | 无，等待下一次显式调度 | 不应自动触发任何上游阶段 | `run_manifest.json`、`paper_registry.jsonl`、`run_registry.jsonl` |
