# 评分说明

当前 triage 阶段由四类分数组成：

- `topical_fit`
- `freshness`
- `impact`
- `method_signal`

## 作用

- `topical_fit`：判断与研究画像的匹配度
- `freshness`：判断发布时间是否足够新
- `impact`：判断引用或高影响力指标
- `method_signal`：判断摘要里是否出现方法、实验和结果信号

## 来源

- 默认权重来自 `workflow.yaml -> triage_policy.score_weights`
- profile 覆盖来自 `profiles.yaml -> scoring_overrides`

## 非黑箱输出字段

- `score_breakdown`：记录四类分项分数
- `decision`：`selected` 或 `rejected`
- `decision_reasons`：拒绝或入选原因代码
- `dedupe_group_id`：去重分组键

## 去重优先级

- 优先按 `paper_id`
- 缺少 `paper_id` 时按标题 slug
- 同组只保留最高分项，其余记录以拒绝项形式保留

更细的字段定义以项目主文档 [docs/data-models.md](/home/icoffee/Projects/codex-arxiv-tools/docs/data-models.md) 为准。
