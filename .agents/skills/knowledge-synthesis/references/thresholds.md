# 阈值与裁剪

当前 knowledge-synthesis 的控制点主要来自：

- `max_backlinks`
- `relation_score_threshold`
- `relation_types`
- `link_strategy`

## 基本规则

- relation 生成前先按 `note_id` 去重
- relation score 低于阈值时不写边
- 只保留前 `max_backlinks` 条匹配
- 当匹配数量超限时，按分数和笔记新鲜度裁剪
- 只写入配置允许的 `relation_types`
- 已存在同类 relation 时做 merge，不盲目追加
- 当前实现以关键词和内容重叠为主，不做复杂语义推断

如果需要调整更细的筛选逻辑，应优先修改 workflow 配置，而不是在 skill 中临时变更规则。
