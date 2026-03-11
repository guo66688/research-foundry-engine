---
name: candidate-triage
description: 用于 triage 阶段，在已有 candidate_pool.jsonl、workflow 配置、profiles 配置和 profile_id 时执行评分、去重、分层与阅读队列生成。不要用于 source fetching、dossier generation、note linking 或 registry updates。
---

# candidate-triage

## 目标

把候选池转成可执行的 shortlist 和阅读队列，并显式写出入选、拒绝、去重的原因。评分与决策规则见 `references/scoring.md`。

## 何时触发

- 已经有 `candidate_pool.jsonl`。
- 需要生成 `triage_result.json` 和阅读队列。
- 需要明确哪些论文进入 dossier 阶段。

## 何时不触发

- 还没有候选池。
- 已经选定 `paper_id`，现在只需生成 dossier。
- 需要做知识关联或 registry 更新。

## 必需输入

- `configs/workflow.yaml`
- `configs/profiles.yaml`
- `profile_id`
- `runtime/runs/<run_id>/candidate_pool.jsonl`

## 输出文件

- `runtime/runs/<run_id>/triage_result.json`
- `runtime/artifacts/reading_queue-<run_id>.md`

## 前置检查

- 确认 `candidate_pool.jsonl` 存在且非空。
- 确认 `profile_id` 与候选池归属一致。
- 确认 triage 权重可解析。
- 确认 `runtime/artifacts/` 可写。

## 失败处理

- 候选池为空：立即停止，不生成空 shortlist。
- 权重非法：立即停止，不自动修正。
- 输出路径不可写：停止并避免写出半成品队列。
- 详细失败场景见 `references/failure-cases.md`

## 交接条件

- 当 `triage_result.json` 和 `reading_queue-<run_id>.md` 已成功生成时停止。
- 不继续生成 dossier。
- 将结果交给 `evidence-dossier`，或等待用户选择 `paper_id`。
- 共享交接视图见 `references/handoff-matrix.md`

## 最小可执行示例

### 示例 1：标准 shortlist 生成

- 输入：`candidate_pool.jsonl`
- 执行：

```bash
python scripts/flow_triage_rank.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id llm_systems \
  --input runtime/runs/<run_id>/candidate_pool.jsonl
```

- 结果：生成 `triage_result.json` 与 `reading_queue-<run_id>.md`
- 完成条件：`selected` 非空，且每项都带有 `decision` 与 `decision_reasons`

### 示例 2：存在重复论文

- 输入：候选池中同一 `paper_id` 或同标题重复出现
- 结果：只保留组内最高分项，其余项以拒绝记录写回 `triage_result.json`

## 常见错误示例

### 错误 1：输入文件不存在

- 处理：立即中止，返回 `source-intake`

### 错误 2：候选池为空

- 处理：立即中止，不生成空阅读队列

### 错误 3：用户要求“顺手生成 dossier”

- 处理：停止在 triage 结束，不越权进入 `evidence-dossier`

## standalone execution

- This skill bundles its own `scripts/` and can be executed directly inside the skill directory.
- It does not depend on external `research-foundry-engine` Python import paths.
