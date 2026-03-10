---
name: candidate-triage
description: 当需要对候选池执行评分、去重、分层并输出阅读队列时触发。不要用于抓取源数据、生成单篇 dossier、建立知识关联或登记运行结果。
---

# candidate-triage

## 目标

把 `candidate_pool.jsonl` 收敛成可执行的 shortlist 和阅读队列，作为单篇 dossier 的直接输入。评分细节见 `references/scoring.md`。

## 何时触发

- 已经有候选池，需要做评分、去重和分层。
- 需要输出 `triage_result.json` 和阅读队列。
- 需要决定下一步哪些论文值得进入 dossier 阶段。

## 何时不触发

- 还没有生成 `candidate_pool.jsonl`。
- 已经选定 `paper_id`，现在只需要生成 dossier。
- 需要做笔记关联或关系更新。
- 需要登记 registry。

## 必需输入

- `configs/workflow.yaml`
- `configs/profiles.yaml`
- `profile_id`
- `runtime/runs/<run_id>/candidate_pool.jsonl`

## 输出文件

- `runtime/runs/<run_id>/triage_result.json`
- `runtime/artifacts/reading_queue-<run_id>.md`
- 详细输入输出契约见 `references/io-contracts.md`

## 前置检查

- 确认 `candidate_pool.jsonl` 存在且非空。
- 确认 `profile_id` 与候选池归属一致。
- 确认 triage 权重可解析。
- 确认 `runtime/artifacts/` 可写。
- 最小调用：

```bash
python scripts/triage/flow_triage_rank.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id <profile_id> \
  --input runtime/runs/<run_id>/candidate_pool.jsonl
```

## 失败处理

- 候选池为空：立即停止，不生成空 shortlist。
- 权重非法：立即停止，不自动修正。
- 输出路径不可写：停止并避免写出半成品队列。
- 详细失败场景见 `references/failure-cases.md`

## 交接条件

- 当 `triage_result.json` 与 `reading_queue-<run_id>.md` 已成功生成时停止。
- 不继续生成 `dossier`。
- 将结果交给 `evidence-dossier`，或等待用户从 shortlist 中选择 `paper_id`。
