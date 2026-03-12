# 多源行为规则

## 来源角色

- `arxiv`: `fresh_discovery`（主源）
- `semantic_scholar`: `trend_support` / `hot_backfill`（补充源）

## 分池规则

- `fresh_pool`: 默认承载 arXiv 近 30 天候选
- `hot_pool`: 默认承载 Semantic Scholar 近 365 天高热候选

## 允许部分产出的最低条件

- 至少一个启用 source 成功返回候选即可产出

## 必须记录的元数据

- `source_counts`
- `source_status`
- `source_pools`
- `warnings`

## 明确中止条件

- 全部启用 source 失败
- 全部启用 source 返回空记录

## 不允许行为

- 只输出空候选池并标记成功
- 隐藏失败来源状态
- 将 `fresh_pool/hot_pool` 混写成不可区分的大池而不保留来源角色字段
