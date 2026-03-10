# 模式说明

`evidence-dossier` 目前固定为三种模式：

如果 CLI 没有显式指定 `--mode`，当前实现会使用 `auto` 自动推导最终模式。

## `dossier_only`

- 适用：只需要结构化阅读档案
- 联网要求：否
- 结果：只生成 `dossier-<paper_id>-<slug>.md`

## `dossier_with_figures`

- 适用：需要补充图像资产
- 联网要求：是
- 结果：除 dossier 外，再生成 `figure_manifest-<paper_id>.json`

## `offline_no_figures`

- 适用：当前环境不具备网络或图像依赖
- 联网要求：否
- 结果：显式使用 `--skip-figures` 或同名 mode，只输出 dossier
