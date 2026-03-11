---
name: source-intake
description: 用于 intake 阶段，在已有 workflow 配置、profiles 配置和 profile_id 的前提下抓取并标准化候选论文。不要用于 ranking、dossier generation、note linking 或 registry updates。
---

# source-intake

## 目标

为单个 `profile_id` 生成一份可供后续 triage 使用的标准化候选池。字段契约见 `references/io-contracts.md`，多源行为规则见 `references/source-behavior.md`。

## 何时触发

- 需要从已配置的数据源抓取候选论文。
- 需要把多源返回结果统一成同一 schema。
- 当前还没有可用的 `candidate_pool.jsonl`，或明确要求重新刷新候选池。

## 何时不触发

- 已有候选池，只需要评分、去重或分层。
- 已确定单篇论文，需要生成 dossier。
- 需要做笔记关联或 registry 更新。

## 必需输入

- `configs/workflow.yaml`
- `configs/profiles.yaml`
- `profile_id`

## 输出文件

- `runtime/runs/<run_id>/candidate_pool.jsonl`
- `runtime/runs/<run_id>/run_manifest.json`

## 前置检查

- 确认 `workflow.yaml` 和 `profiles.yaml` 可读。
- 确认 `profile_id` 已定义。
- 确认至少一个 source 已启用。
- 确认 `runtime/runs/` 可写。

## 失败处理

- 配置缺失或格式错误：立即停止。
- 部分 source 失败：允许部分产出，但必须记录失败源与 warning。
- 所有 source 失败或都未返回候选记录：中止，不生成空候选池伪装成功。
- 详细失败场景见 `references/failure-cases.md`

## 交接条件

- 当 `candidate_pool.jsonl` 已成功写出，且记录数大于 `0` 时停止。
- 不继续执行 `candidate-triage`。
- 将结果交给 `candidate-triage`。
- 共享交接视图见 `references/handoff-matrix.md`

## 最小可执行示例

### 示例 1：常规抓取

- 输入：`workflow.yaml`、`profiles.yaml`、`profile_id=llm_systems`
- 执行：

```bash
python scripts/flow_intake_fetch.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id llm_systems
```

- 结果：生成 `candidate_pool.jsonl` 和 `run_manifest.json`
- 完成条件：候选记录数大于 `0`

### 示例 2：多源部分成功

- 输入：一个 source 成功、一个 source 请求失败
- 结果：允许生成 `candidate_pool.jsonl`
- 附加要求：`run_manifest.json` 中必须记录 `source_status` 和 `warnings`

## 常见错误示例

### 错误 1：`profile_id` 不存在

- 处理：立即中止，不猜测相近 profile

### 错误 2：所有启用 source 都失败

- 处理：中止，并把失败情况写入 `run_manifest.json`

### 错误 3：所有 source 返回空记录

- 处理：中止，不生成空的 `candidate_pool.jsonl`

## standalone execution

- This skill bundles its own `scripts/` and can be executed directly inside the skill directory.
- It does not depend on external `research-foundry-engine` Python import paths.
