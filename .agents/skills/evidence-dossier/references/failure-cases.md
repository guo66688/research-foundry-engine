# 失败场景

## `paper_id` 不在输入中

- 现象：triage 或 candidate 文件中找不到目标论文
- 处理：立即停止

## dossier 输出目录不可写

- 现象：无法写出 markdown
- 处理：立即停止，不生成半成品

## 图像依赖缺失

- 现象：启用图像模式但缺少 `PyMuPDF`
- 处理：明确提示依赖缺失，必要时改用 `--skip-figures`

## 图像提取失败

- 现象：下载、渲染或提取图像失败
- 处理：保留 dossier 主文件，并说明 figures 被跳过
