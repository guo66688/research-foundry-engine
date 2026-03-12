# 配置说明

Research Foundry 的核心配置仍然是两份 YAML：

- `configs/workflow.yaml`
- `configs/profiles.yaml`

这两份配置同时适用于 `external` 与 `standalone` 两种模式。

## 推荐配置原则

- `notes_root` 指向 Obsidian Vault 根目录
- `run_dir / artifact_dir / cache_dir / log_dir` 放在 Vault 外
- `triage_policy.shortlist_size` 默认为 `10`
- 默认 `profile_id` 使用 `llm_systems`

## `workflow.yaml`

### `workspace`

- `notes_root`：Vault 根目录
- `inbox_dir`：每日推荐文档目录的相对根
- `dossier_dir`：论文深读笔记目录
- `assets_dir`：论文图片目录

推荐理解：

- `notes_root` 下面只放 Markdown 和图片
- `daily-recommendations`、`research/papers` 等最终文档由命令层写入这里

### `sources`

#### `sources.arxiv`

- `enabled`
- `categories`
- `lookback_days`
- `max_results`

推荐用途：最近 30 天的新论文发现。

#### `sources.semantic_scholar`

- `enabled`
- `api_key_env`
- `history_window_days`
- `max_results`

推荐用途：补充更长时间窗里的高信号论文。

### `triage_policy`

- `shortlist_size`
- `score_weights.topical_fit`
- `score_weights.freshness`
- `score_weights.impact`
- `score_weights.method_signal`

默认推荐：

- `shortlist_size: 10`
- 用四个维度做综合排序：相关性、新近性、热门度、质量/方法信号

### `dossier_policy`

- `figure_mode`
- `include_sections`
- `citation_style`
- `summary_length`
- `max_figures`

说明：

- `深读论文` 默认会调用 dossier 和 figure extraction
- `提取配图` 只走 figure 相关逻辑，不生成完整 dossier

### `synthesis_policy`

- `backlinking`
- `max_backlinks`
- `relation_score_threshold`
- `relation_types`
- `link_strategy`
- `relation_store`

说明：

- `深读论文` 默认会继续做知识链接
- `今日推荐` 默认会对前 3 篇做知识链接

### `runtime`

- `cache_dir`
- `run_dir`
- `artifact_dir`
- `log_dir`
- `log_level`
- `retry_limit`
- `request_timeout_seconds`
- `dedupe_strategy`

推荐放置策略：

- 不要把这些目录放进 Vault
- standalone 与 external 都应指向 Vault 外的统一 runtime 区域

## `profiles.yaml`

每个 profile 至少应包含：

- `profile_id`
- `include_terms`
- `exclude_terms`
- `priority`
- `max_candidates`
- `source_scope`
- `scoring_overrides`

默认推荐的日常 profile：

- `profile_id: llm_systems`

## 最常改的字段

第一次接入 Vault 时，优先改：

1. `workspace.notes_root`
2. `runtime.run_dir`
3. `runtime.artifact_dir`
4. `profiles[].include_terms`
5. `profiles[].source_scope`
6. `triage_policy.shortlist_size`

## 配置与命令层的关系

- `今日推荐` 会读取 `workflow.yaml` 与 `profiles.yaml`
- `深读论文` 会读取 `workflow.yaml`，并在需要时用 `profiles.yaml`
- `提取配图` 只依赖 `workflow.yaml`
- `搜索论文` 只依赖 `workflow.yaml` 中的 `notes_root`

## 2026-03 来源角色配置

新增 `sources.<source>.role/default_window_days/preferred_buckets/restricted_buckets` 与 `bucket_strategy`。

```yaml
sources:
  arxiv:
    enabled: true
    role: [fresh_discovery]
    default_window_days: 30
    preferred_buckets: [must_read, trend_watch, gap_fill]

  semantic_scholar:
    enabled: false
    role: [trend_support, hot_backfill]
    default_window_days: 365
    preferred_buckets: [trend_watch, gap_fill]
    restricted_buckets: [must_read]

bucket_strategy:
  must_read:
    prefer_sources: [arxiv]
    max_semantic_scholar_items: 0
  trend_watch:
    prefer_sources: [arxiv, semantic_scholar]
    target_mix:
      arxiv: 0.5
      semantic_scholar: 0.5
  gap_fill:
    prefer_sources: [arxiv, semantic_scholar]
    max_semantic_scholar_items: 2
```

### 向后兼容

- 旧字段 `lookback_days/history_window_days` 仍可继续使用。
- 未配置 `bucket_strategy` 时，会使用内置默认策略。
- `semantic_scholar.enabled` 默认 `false`，默认行为与原先 arXiv 主流程保持一致。
