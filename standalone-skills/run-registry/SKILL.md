---
name: run-registry
description: 用于 registry 阶段，在已有 run_id、paper_id、state 和 artifact 列表时更新 run manifest 与全局索引。不要用于内容生成、论文分析、source fetching 或 relation inference。
---

# run-registry

## 目标

把一次运行的元数据和稳定产物登记进全局索引，保证结果可追溯、可重放、可幂等更新。覆盖策略见 `references/idempotency.md`。

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

## 前置检查

- 确认 `run_id`、`paper_id`、`state` 已明确。
- 确认每个 artifact 使用 `kind=path` 形式。
- 确认 registry 目标目录可写。
- 确认当前更新语义是 upsert，而不是盲目 append。

## 失败处理

- artifact 参数格式错误：立即停止。
- 关键字段缺失：立即停止，不写入不完整登记。
- 同 key 记录已存在：按幂等规则覆盖并保留历史 artifact 引用。
- 详细失败场景见 `references/failure-cases.md`

## 交接条件

- 当 `run_manifest.json`、`paper_registry.jsonl`、`run_registry.jsonl` 更新成功时停止。
- 不继续触发新的 `source-intake` 或 `candidate-triage`。
- 将当前 run 视为完成，等待下一次显式调度。
- 共享交接视图见 `references/handoff-matrix.md`

## 最小可执行示例

### 示例 1：登记单篇 dossier

- 执行：

```bash
python scripts/flow_registry_update.py \
  --config configs/workflow.yaml \
  --run-id <run_id> \
  --paper-id <paper_id> \
  --state registered \
  --artifact dossier=runtime/artifacts/dossier-<paper_id>-<slug>.md
```

- 结果：三个 registry 文件和 `run_manifest.json` 都被更新

### 示例 2：重复执行相同 `run_id`

- 输入：同一 `run_id` 再次登记新 artifact
- 结果：执行 upsert，合并 artifact 引用，而不是无限追加重复记录

## 常见错误示例

### 错误 1：artifact 不是 `kind=path`

- 处理：立即中止

### 错误 2：同一 `paper_id` 更新时覆盖了旧 artifact

- 处理：不允许静默丢失旧引用，必须按幂等规则合并

### 错误 3：登记完成后自动触发新的 intake

- 处理：禁止，registry 是终点，不是循环入口

## standalone execution

- This skill bundles its own `scripts/` and can be executed directly inside the skill directory.
- It does not depend on external `research-foundry-engine` Python import paths.
- If `.runtime/python.txt` exists, run bundled scripts with the Python executable recorded there.
