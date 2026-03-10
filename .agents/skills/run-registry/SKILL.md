---
name: run-registry
description: 当需要登记 run 元数据、artifact 路径和全局索引时触发。不要用于内容生成、论文分析、源数据抓取或关系推理。
---

# run-registry

## 目标

把一次运行的元数据和稳定产物登记进全局索引，保证结果可追溯、可重放、可幂等更新。覆盖规则见 `references/idempotency.md`。

## 何时触发

- 上游阶段已经产出可登记的 artifact。
- 需要更新 `run_manifest.json`、`paper_registry.jsonl`、`run_registry.jsonl`。
- 需要记录当前 `paper_id` 的最终状态。

## 何时不触发

- 上游内容还没有生成完成。
- 还在做候选抓取、评分或 dossier 生成。
- 还在做知识关联和 relation 更新。
- 需要重新发起新的 intake 或 triage。

## 必需输入

- `configs/workflow.yaml`
- `run_id`
- `paper_id`
- `state`
- 一个或多个 `kind=path` artifact 对

## 输出文件

- `runtime/runs/<run_id>/run_manifest.json`
- `runtime/artifacts/paper_registry.jsonl`
- `runtime/artifacts/run_registry.jsonl`
- 详细输入输出契约见 `references/io-contracts.md`

## 前置检查

- 确认 `run_id`、`paper_id`、`state` 已明确。
- 确认每个 artifact 使用 `kind=path` 形式。
- 确认 registry 目标目录可写。
- 最小调用：

```bash
python scripts/registry/flow_registry_update.py \
  --config configs/workflow.yaml \
  --run-id <run_id> \
  --paper-id <paper_id> \
  --state registered \
  --artifact dossier=runtime/artifacts/dossier-<paper_id>-<slug>.md
```

## 失败处理

- artifact 参数格式错误：立即停止。
- 目标 registry 文件已存在同 key 记录：按幂等规则覆盖，不追加重复项。
- 任一关键字段缺失：停止，不写入不完整登记。
- 详细失败场景见 `references/failure-cases.md`

## 交接条件

- 当 `run_manifest.json`、`paper_registry.jsonl`、`run_registry.jsonl` 更新成功时停止。
- 不继续触发新的 `source-intake` 或 `candidate-triage`。
- 将当前 run 视为完成，等待下一次显式调度。
