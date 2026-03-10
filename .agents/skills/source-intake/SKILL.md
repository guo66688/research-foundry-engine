---
name: source-intake
description: 当需要按研究画像抓取并标准化候选论文时触发。不要用于评分排序、生成单篇 dossier、建立知识关联或登记运行结果。
---

# source-intake

## 目标

为单个 `profile_id` 生成一份标准化候选池，作为后续 triage 的唯一上游输入。详细字段见 `references/io-contracts.md`。

## 何时触发

- 需要从已配置的数据源抓取候选论文。
- 需要把不同来源的记录统一为同一数据结构。
- 当前还没有可用的 `candidate_pool.jsonl`，或明确要求重新刷新候选池。

## 何时不触发

- 已经有 `candidate_pool.jsonl`，现在只需要评分或去重。
- 已经选定单篇论文，需要生成 dossier。
- 需要把 dossier 与本地笔记建立关联。
- 需要登记 run 或稳定产物。

## 必需输入

- `configs/workflow.yaml`
- `configs/profiles.yaml`
- `profile_id`

## 输出文件

- `runtime/runs/<run_id>/candidate_pool.jsonl`
- `runtime/runs/<run_id>/run_manifest.json`
- 详细输入输出契约见 `references/io-contracts.md`

## 前置检查

- 确认 `workflow.yaml` 和 `profiles.yaml` 可读。
- 确认目标 `profile_id` 已定义。
- 确认至少一个 source 已启用。
- 确认 `runtime/runs/` 可写。
- 最小调用：

```bash
python scripts/intake/flow_intake_fetch.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id <profile_id>
```

## 失败处理

- 配置缺失或格式错误：立即停止，不猜测默认值。
- 部分 source 失败：写出 `run_manifest.json`，明确报出失败源，不伪造记录。
- 所有 source 都返回空结果：停止并保留运行痕迹，等待用户调整画像或数据源。
- 详细失败场景见 `references/failure-cases.md`

## 交接条件

- 当 `candidate_pool.jsonl` 已成功写出，且记录数大于 `0` 时停止。
- 不继续执行 `candidate-triage`。
- 将结果交给 `candidate-triage`。
