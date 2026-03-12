# 评分与路由说明

## 基础评分维度

`final_base_score` 由以下组件与权重计算：

- `topical_fit`
- `impact`
- `recency`
- `method_signal`
- `knowledge_gain`
- `bridge_value`
- `actionability`
- `redundancy_penalty`（惩罚项）

## 处理流程

1. 基础评分
2. 去重（硬去重 + 近似去重）
3. 主题多样性筛选
4. 来源感知路由（source-aware routing）
5. 分桶输出（must_read / trend_watch / gap_fill）

## 来源感知路由规则（首版默认）

- `arxiv` 可进入 `must_read/trend_watch/gap_fill`
- `semantic_scholar` 默认仅可进入 `trend_watch/gap_fill`
- `semantic_scholar` 默认禁止直接进入 `must_read`

## 可解释输出

每条推荐都应可解释：

- 为什么进入当前桶（`bucket_routing_reason`）
- 为什么该来源被选中（`source_selection_reason`）
- 为什么未进入 must_read（如受来源限制）
