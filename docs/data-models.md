# 数据契约

这份文档定义 phase 层和命令层共享的数据模型。新增字段、改状态或改命名时，应该先更新这里。

## 标识规则

- `run_id`：`run-<YYYYMMDDTHHMMSSZ>`
- `paper_id`：优先使用规范化 arXiv ID；没有时使用带源前缀的 slug
- `profile_id`：使用小写 snake case
- `relation_id`：`rel-<source_slug>-<target_slug>-<relation_type>`

## 状态流转

推荐状态顺序：

1. `discovered`
2. `triaged`
3. `dossier_ready`
4. `linked`
5. `registered`

## Phase 文件契约

### `candidate_pool.jsonl`

每行至少包含：

- `run_id`
- `profile_id`
- `paper_id`
- `source`
- `source_record_id`
- `title`
- `abstract`
- `authors`
- `published_at`
- `updated_at`
- `categories`
- `source_url`
- `pdf_url`
- `citation_count`
- `influential_citation_count`
- `profile_hits`
- `state`
- `fetched_at`

### `run_manifest.json`

顶层至少包含：

- `run_id`
- `profile_id`
- `started_at`
- `updated_at`
- `status`
- `stage`
- `artifacts`
- `candidate_count`
- `source_counts`
- `source_status`
- `warnings`

### `triage_result.json`

顶层字段：

- `run_id`
- `profile_id`
- `generated_at`
- `input_path`
- `dedupe_strategy`
- `weights`
- `stats`
- `selected`
- `rejected`

`selected` 和 `rejected` 中每项至少包含：

- `paper_id`
- `title`
- `state`
- `scores`
- `score_breakdown`
- `tier`
- `decision`
- `decision_reasons`
- `dedupe_group_id`
- `reason`

### `figure_manifest-<paper_id>.json`

顶层字段：

- `paper_id`
- `generated_at`
- `figure_count`
- `items`

`items` 中每项至少包含：

- `name`
- `source`
- `path`
- `format`
- `bytes`

### `paper_registry.jsonl`

每行至少包含：

- `run_id`
- `paper_id`
- `profile_id`
- `title`
- `slug`
- `state`
- `artifacts`
- `registered_at`
- `updated_at`

### `run_registry.jsonl`

每行至少包含：

- `run_id`
- `profile_id`
- `started_at`
- `updated_at`
- `status`
- `artifacts`

### `relations.json`

顶层字段：

- `updated_at`
- `nodes`
- `edges`

节点字段：

- `id`
- `kind`
- `label`
- `path`
- `paper_id`

边字段：

- `id`
- `source`
- `target`
- `type`
- `weight`

## Vault 文档契约

### 每日推荐文档 `YYYY-MM-DD-<profile_id>.md`

建议至少包含：

- `run_id`
- `profile_id`
- `candidate_count`
- `shortlist_count`
- `source_status`
- Top 5 推荐论文
- 完整 shortlist
- 前 3 篇深读笔记链接
- 运行产物路径

### 单篇深读文档 `<paper_id>.md`

建议至少包含：

- 论文标题
- `paper_id`
- 摘要翻译
- 要点提炼
- 背景与动机
- 方法概述
- 实验与结果
- 价值判断
- 优势与局限
- 相关笔记链接
- 图片索引或图片目录

### 图片索引文档 `<paper_id>-figures.md`

建议至少包含：

- `paper_id`
- 图片数量
- 每张图片的相对路径
- 图片来源说明

## 命名规则

- dossier 文件：`dossier-<paper_id>-<slug>.md`
- 图像清单：`figure_manifest-<paper_id>.json`
- 阅读队列：`reading_queue-<run_id>.md`
- 单次运行摘要：`run_manifest.json`
- 每日推荐文档：`YYYY-MM-DD-<profile_id>.md`
- 单篇深读文档：`<paper_id>.md`
- 图片索引文档：`<paper_id>-figures.md`

## 枚举值

### `tier`

- `priority`
- `watch`
- `discard`

### `status`

- `running`
- `completed`
- `failed`

### `relation_type`

- `extends`
- `references`
- `shares_topic`
- `same_method_family`

## 2026-03 来源角色化数据扩展

### intake 输出扩展

新增运行产物：

- `runtime/runs/<run_id>/fresh_pool.jsonl`
- `runtime/runs/<run_id>/hot_pool.jsonl`

`candidate_pool.jsonl` 继续保留，作为兼容总池。

### candidate 记录扩展字段

- `source_role`
- `source_pool`
- `recency_days`
- `publication_year`
- `fields_of_study`
- `venue`
- `paper_type`
- `recent_citation_velocity`

### triage 结果扩展字段

在 `selected/rejected` 项中新增：

- `source`
- `source_role`
- `bucket_routing_reason`
- `source_selection_reason`

在 `triage_result.json` 顶层新增：

- `source_routing_policy`
- `source_mix_summary`
