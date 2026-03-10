---
name: evidence-dossier
description: 当需要围绕单篇论文生成结构化 evidence dossier 时触发，可按配置附带图像清单。不要用于构建候选池、做全局排序、建立知识关联或登记运行结果。
---

# evidence-dossier

## 目标

围绕单个 `paper_id` 生成结构化证据档案，并在需要时生成图像清单。模式差异见 `references/modes.md`。

## 何时触发

- 已明确选定一个 `paper_id`。
- 已经有 candidate 或 triage 元数据。
- 需要产出单篇论文的可读 dossier。

## 何时不触发

- 还没有 shortlist 或 `paper_id`。
- 只需要对候选池做排序。
- dossier 已生成，现在只需要做知识关联。
- 需要登记 registry。

## 必需输入

- `configs/workflow.yaml`
- `configs/profiles.yaml`
- `profile_id`
- `paper_id`
- `triage_result.json` 或 `candidate_pool.jsonl`

## 输出文件

- `runtime/artifacts/dossier-<paper_id>-<slug>.md`
- 可选 `runtime/artifacts/figure_manifest-<paper_id>.json`
- 详细输入输出契约见 `references/io-contracts.md`

## 前置检查

- 确认 `paper_id` 能在 triage 或 candidate 输入中找到。
- 确认 `runtime/artifacts/` 可写。
- 如启用图像模式，确认相关依赖可用；否则显式使用 `--skip-figures`。
- 最小调用：

```bash
python scripts/dossier/flow_dossier_build.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id <profile_id> \
  --triage-file runtime/runs/<run_id>/triage_result.json \
  --paper-id <paper_id>
```

## 失败处理

- `paper_id` 不存在于输入文件：立即停止。
- 图像提取失败：保留 dossier 主文件，并明确说明 figures 被跳过。
- 上游元数据不足：只输出可证实内容，不补写虚构章节。
- 详细失败场景见 `references/failure-cases.md`

## 交接条件

- 当 `dossier-<paper_id>-<slug>.md` 已成功生成时停止。
- 若启用 figures 模式，则以 `figure_manifest-<paper_id>.json` 生成完毕为附加完成条件。
- 不继续执行 `knowledge-synthesis`。
- 将结果交给 `knowledge-synthesis`。
