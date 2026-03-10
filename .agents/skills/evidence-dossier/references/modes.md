# 模式说明

`evidence-dossier` 目前建议按三种模式理解：

## 仅 dossier

- 适用：只需要结构化阅读档案
- 结果：只生成 `dossier-<paper_id>-<slug>.md`

## dossier + figures

- 适用：需要补充图像资产
- 结果：除 dossier 外，再生成 `figure_manifest-<paper_id>.json`

## 离线模式

- 适用：当前环境不具备网络或图像依赖
- 结果：显式使用 `--skip-figures`，只输出 dossier
