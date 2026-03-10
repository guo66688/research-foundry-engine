# 配置说明

项目有两类配置文件：

- `configs/workflow.yaml`：描述工作区、数据源、运行策略和输出策略
- `configs/profiles.yaml`：描述研究画像、候选范围和打分偏好

## `workflow.yaml`

### `workspace`

- `notes_root`：本地笔记库根目录
- `inbox_dir`：原始输入或待整理目录
- `dossier_dir`：研究档案目录
- `assets_dir`：图像等资产目录

### `sources`

#### `sources.arxiv`

- `enabled`：是否启用 arXiv
- `categories`：要抓取的 arXiv 分类
- `lookback_days`：回看天数
- `max_results`：最大拉取量

#### `sources.semantic_scholar`

- `enabled`：是否启用 Semantic Scholar
- `api_key_env`：API key 的环境变量名
- `history_window_days`：历史窗口大小
- `max_results`：最大拉取量

### `triage_policy`

- `shortlist_size`：最终 shortlist 数量
- `score_weights`
- `topical_fit`：主题匹配权重
- `freshness`：新近性权重
- `impact`：影响力权重
- `method_signal`：方法信号权重

### `dossier_policy`

- `figure_mode`：图像提取策略
- `include_sections`：dossier 要包含的章节
- `citation_style`：引用风格
- `summary_length`：摘要长度档位
- `max_figures`：最多保留多少张图

### `synthesis_policy`

- `backlinking`：是否生成 backlinks
- `max_backlinks`：最多链接多少条已有笔记
- `relation_types`：允许写入的 relation 类型
- `link_strategy`：关联策略
- `relation_store`：relation 文件路径

### `runtime`

- `cache_dir`：缓存目录
- `run_dir`：单次运行目录
- `artifact_dir`：稳定产物目录
- `log_dir`：日志目录
- `log_level`：日志级别
- `retry_limit`：请求重试次数
- `request_timeout_seconds`：请求超时
- `dedupe_strategy`：去重策略

## `profiles.yaml`

`profiles` 是一个列表，每项代表一个研究策略单元，而不只是关键词集合。

每个 profile 至少应包含：

- `profile_id`：唯一标识
- `include_terms`：感兴趣的关键词
- `exclude_terms`：要排除的关键词
- `priority`：优先级
- `max_candidates`：候选上限
- `source_scope`：允许从哪些源拉取
- `scoring_overrides`：对默认打分权重的局部覆盖

## 推荐修改顺序

第一次配置时，优先改：

1. `workspace.notes_root`
2. `sources.*.enabled`
3. `profiles[].include_terms`
4. `profiles[].source_scope`
5. `triage_policy.shortlist_size`

## 常见组合

偏发现导向：

- 提高 `sources.*.max_results`
- 提高 `profiles[].max_candidates`
- 适当提高 `freshness`

偏高价值筛选：

- 降低 `shortlist_size`
- 提高 `impact`
- 提高 `method_signal`

偏本地知识沉淀：

- 明确 `workspace.notes_root`
- 开启 `backlinking`
- 配好 `relation_types` 和 `max_backlinks`
