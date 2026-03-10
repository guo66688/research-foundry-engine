---
name: evidence-dossier
description: 用于 dossier 阶段，在已有 profile_id、paper_id 与 candidate/triage 元数据时生成单篇 evidence dossier，可按模式附带图像清单。不要用于 candidate intake、global ranking、knowledge synthesis 或 registry updates。
---

# evidence-dossier

## 目标

围绕单个 `paper_id` 生成结构化证据档案，并根据模式决定是否产出图像清单。模式枚举见 `references/modes.md`。

## 何时触发

- 已明确选定一个 `paper_id`。
- 已有 candidate 或 triage 元数据。
- 需要产出单篇论文的可读 dossier。

## 何时不触发

- 还没有 shortlist 或 `paper_id`。
- 只需要对候选池做排序。
- dossier 已生成，现在只需要做知识关联或 registry 更新。

## 必需输入

- `configs/workflow.yaml`
- `configs/profiles.yaml`
- `profile_id`
- `paper_id`
- `triage_result.json` 或 `candidate_pool.jsonl`

## 输出文件

- `runtime/artifacts/dossier-<paper_id>-<slug>.md`
- 可选 `runtime/artifacts/figure_manifest-<paper_id>.json`

## 前置检查

- 确认 `paper_id` 能在 triage 或 candidate 输入中找到。
- 确认 `runtime/artifacts/` 可写。
- 确认当前模式是 `dossier_only`、`dossier_with_figures` 或 `offline_no_figures` 之一。
- 如启用图像模式，确认相关依赖可用。

## 失败处理

- `paper_id` 不存在于输入文件：立即停止。
- 图像提取失败：保留 dossier 主文件，并明确说明 figures 被跳过。
- 上游元数据不足：只输出可证实内容，不补写虚构章节。
- 详细失败场景见 `references/failure-cases.md`

## 交接条件

- 当 `dossier-<paper_id>-<slug>.md` 已成功生成时停止。
- 若模式为 `dossier_with_figures`，则以 `figure_manifest-<paper_id>.json` 生成完毕为附加完成条件。
- 不继续执行 `knowledge-synthesis`。
- 将结果交给 `knowledge-synthesis`。
- 共享交接视图见 `../references/handoff-matrix.md`

## 最小可执行示例

### 示例 1：仅生成 dossier

- 执行：

```bash
python scripts/dossier/flow_dossier_build.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id llm_systems \
  --triage-file runtime/runs/<run_id>/triage_result.json \
  --paper-id <paper_id> \
  --mode dossier_only
```

- 结果：只生成 `dossier-<paper_id>-<slug>.md`

### 示例 2：dossier + figures

- 输入：允许联网，图像依赖可用
- 结果：生成 dossier，并附带 `figure_manifest-<paper_id>.json`

### 示例 3：离线模式

- 输入：当前环境不适合联网或缺少图像依赖
- 结果：使用 `offline_no_figures`，只生成主文档

## 常见错误示例

### 错误 1：`paper_id` 不在 triage 结果里

- 处理：立即中止，不猜测相近标题

### 错误 2：图像依赖缺失

- 处理：切到 `offline_no_figures` 或显式使用 `--skip-figures`

### 错误 3：dossier 生成后继续顺手做 synthesis

- 处理：停止，交给 `knowledge-synthesis`
