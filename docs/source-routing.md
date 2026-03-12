# 来源角色化路由设计

## 目标

将 `semantic_scholar` 作为 `trend_watch / hot_backfill` 的补充来源，而不是替代 `arXiv` 的 fresh discovery 主源。

## 核心流程

1. Intake 阶段分池  
- `fresh_pool`：arXiv，默认 30 天。  
- `hot_pool`：Semantic Scholar，默认 365 天。

2. Triage 阶段分层  
- 先算基础分（topical/impact/recency/method/knowledge/bridge/actionability/redundancy）。  
- 再做来源感知路由（source-aware routing）。  

3. Bucket 阶段分桶  
- `must_read`：优先 arXiv，首版默认禁用 S2。  
- `trend_watch`：arXiv + S2 混合，支持 target mix。  
- `gap_fill`：以知识缺口为核心，S2 受配额限制。  
- `review_or_backfill`：由本地 inventory/canonical/revisit 主导。  

## 关键模块

- `scripts/lib/source_pools.py`
  - 来源角色到 pool 的映射、池组织、兼容总池去重。
- `scripts/lib/semantic_scholar_adapter.py`
  - S2 字段标准化与 hotness 估计。
- `scripts/lib/source_routing.py`
  - 来源准入、来源配额、混合策略、路由解释生成。

## 可解释性

每条推荐会携带：

- `source`
- `source_role`
- `bucket_routing_reason`
- `source_selection_reason`

这样可以审计：

- 为什么某篇 S2 进入 `trend_watch`；
- 为什么它不能进入 `must_read`。
