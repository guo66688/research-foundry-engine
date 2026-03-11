---
name: knowledge-synthesis
description: 用于 synthesis 阶段，在已有 dossier 文件和可选 notes_root 的前提下生成 synthesis report 并更新 relations。不要用于重新分析论文、重排候选池、source fetching 或 registry updates。
---

# knowledge-synthesis

## 目标

把单篇 dossier 与已有笔记和 relation 图连接起来，生成可审阅的 synthesis report，并按阈值写入关系边。阈值与裁剪规则见 `references/thresholds.md`。

## 何时触发

- 已有有效的 dossier 文件。
- 需要生成 backlinks、relations 或 synthesis report。
- 需要把新论文接入现有知识库。

## 何时不触发

- dossier 还未生成。
- 需要重新分析论文全文。
- 需要对候选池重新打分。
- 只需要登记 registry。

## 必需输入

- `configs/workflow.yaml`
- `runtime/artifacts/dossier-<paper_id>-<slug>.md`
- 可选 `notes_root`

## 输出文件

- `runtime/artifacts/synthesis_report-<paper_id>.md`
- `runtime/artifacts/relations.json`

## 前置检查

- 确认 dossier 文件存在且可读。
- 如启用 backlinking，确认 `notes_root` 已配置。
- 确认 relation store 可写。
- 确认 relation 阈值和 `max_backlinks` 可解析。

## 失败处理

- `notes_root` 未配置：输出空的 synthesis report，不扫描随机目录。
- 未找到匹配笔记：仍写出合法 report，并保持 relation 文件结构稳定。
- relation 更新失败：不要覆盖无关节点或边。
- 详细失败场景见 `references/failure-cases.md`

## 交接条件

- 当 `synthesis_report-<paper_id>.md` 已生成，且 `relations.json` 已更新时停止。
- 不继续登记 run。
- 将结果交给 `run-registry`，或等待用户人工审阅后再登记。
- 共享交接视图见 `references/handoff-matrix.md`

## 最小可执行示例

### 示例 1：标准关联

- 执行：

```bash
python scripts/flow_synthesis_link.py \
  --config configs/workflow.yaml \
  --dossier runtime/artifacts/dossier-<paper_id>-<slug>.md
```

- 结果：生成 `synthesis_report-<paper_id>.md` 并更新 `relations.json`
- 完成条件：命中的 relation 分数达到阈值

### 示例 2：无命中笔记

- 输入：本地笔记库中没有明显相关笔记
- 结果：允许生成空命中 report，但 relations 结构仍然合法

## 常见错误示例

### 错误 1：未配置 `notes_root`

- 处理：输出空报告，不做目录乱扫

### 错误 2：relation 分数低于阈值

- 处理：不写边，不硬做弱关联

### 错误 3：生成 relations 后继续顺手更新 registry

- 处理：停止，交给 `run-registry`

## standalone execution

- This skill bundles its own `scripts/` and can be executed directly inside the skill directory.
- It does not depend on external `research-foundry-engine` Python import paths.
