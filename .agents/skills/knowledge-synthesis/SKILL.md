---
name: knowledge-synthesis
description: 当需要把已生成的 dossier 连接到本地笔记库和 relations 图时触发。不要用于重做论文分析、重排候选池、抓取源数据或登记运行结果。
---

# knowledge-synthesis

## 目标

把单篇 dossier 与已有笔记和 relation 图连接起来，输出一份可审阅的 synthesis report。阈值与裁剪规则见 `references/thresholds.md`。

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
- 详细输入输出契约见 `references/io-contracts.md`

## 前置检查

- 确认 dossier 文件存在且可读。
- 如启用 backlinking，确认 `notes_root` 已配置。
- 确认 relation store 可写。
- 最小调用：

```bash
python scripts/synthesis/flow_synthesis_link.py \
  --config configs/workflow.yaml \
  --dossier runtime/artifacts/dossier-<paper_id>-<slug>.md
```

## 失败处理

- `notes_root` 未配置：输出空的 synthesis report，不扫描随机目录。
- 未找到匹配笔记：仍写出合法 report，并保持 relation 文件结构稳定。
- relation 更新失败：不要覆盖无关节点或边。
- 详细失败场景见 `references/failure-cases.md`

## 交接条件

- 当 `synthesis_report-<paper_id>.md` 已生成，且 `relations.json` 已更新时停止。
- 不继续登记 run。
- 将结果交给 `run-registry`，或等待用户人工审阅后再登记。
