# 数据契约

这份文档定义五个阶段共享的数据模型。任何脚本新增字段、改状态、改命名，都应该先更新这里。

## 标识规则

- `run_id`：`run-<YYYYMMDDTHHMMSSZ>`
- `paper_id`：优先使用规范化 arXiv ID；没有时使用带源前缀的 slug
- `profile_id`：来自 profile 配置，使用小写 snake case
- `relation_id`：`rel-<source_slug>-<target_slug>-<relation_type>`

## 状态流转

推荐状态顺序：

1. `discovered`
2. `triaged`
3. `dossier_ready`
4. `linked`
5. `registered`

只有在已知前置产物存在时，脚本才能跳过中间状态。

## 文件契约

### `candidate_pool.jsonl`

每行一个 JSON 对象，至少包含：

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

顶层字段至少应包含：

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

`selected` 和 `rejected` 里的每项至少包含：

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

### `YYYY-MM-DD-<profile_id>.md`

这是 triage 阶段衍生出的 Obsidian 日报文档，默认写入：

- `workspace.notes_root/<inbox_dir>/daily-recommendations/YYYY/`

文档建议包含：

- `run_id`
- `profile_id`
- `candidate_count`
- `shortlist_count`
- Top 5 推荐论文
- 完整 shortlist
- 运行产物路径

### `figure_manifest-<paper_id>.json`

顶层字段：

- `paper_id`
- `generated_at`
- `figure_count`
- `items`

`items` 里的每项至少包含：

- `name`
- `source`
- `path`
- `format`
- `bytes`

### `paper_registry.jsonl`

每行代表一个已登记的论文产物组：

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

每行代表一次运行：

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

## 命名规则

- dossier 文件：`dossier-<paper_id>-<slug>.md`
- 图像清单：`figure_manifest-<paper_id>.json`
- 阅读队列：`reading_queue-<run_id>.md`
- 单次运行摘要：`run_manifest.json`
- 每日推荐文档：`YYYY-MM-DD-<profile_id>.md`

## 枚举值

### `tier`

- `priority`
- `watch`
- `discard`

### `status`

- `running`
- `completed`
- `failed`

### `relation type`

- `extends`
- `references`
- `shares_topic`
- `same_method_family`
