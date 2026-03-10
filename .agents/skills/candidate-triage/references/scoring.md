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

更细的字段定义以项目主文档 [docs/data-models.md](/home/icoffee/Projects/codex-arxiv-tools/docs/data-models.md) 为准。
