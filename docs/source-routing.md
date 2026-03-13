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

## 离线回放与回归样本

- fixtures 目录：`tests/fixtures/source_routing/`。
- 每个样本包含：`fresh_pool.jsonl`、`hot_pool.jsonl`、`candidate_pool.jsonl`、`profile.json`、`workflow.yaml`、`knowledge_inventory.json`、`expected.json`。
- 样本覆盖：A(arXiv-only)、B(arXiv+S2 trend)、C(gap_fill)、D(cross-source dedupe)、E(today 编排)。

**验收要点**
- must_read 不得出现 `semantic_scholar`。
- trend_watch 至少包含 1 篇 S2（样本 B/E）。
- gap_fill 需命中 blind_spot/weak（样本 C）。
- cross-source dedupe 保留 arXiv（样本 D）。
- daily_context 字段完整（样本 E）。

**运行方式**
- 回放：`python scripts/tooling/run_source_routing_fixture.py`。
- 验证：`python scripts/tooling/validate_source_routing_fixture.py`。
