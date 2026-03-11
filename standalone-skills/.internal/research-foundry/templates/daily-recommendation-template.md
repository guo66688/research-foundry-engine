# 每日论文推荐模板

用途：
- 这是给 Codex 使用的日报写作模板。
- 目标是把 `daily_context-<run_id>.json` 改写成更像研究助理整理的每日摘要，而不是机械分数榜。

写作要求：
- 先总结今天的主题结构，再分别写：
  - `must_read`
  - `trend_watch`
  - `gap_fill`
  - `review_or_backfill`
- 每篇推荐至少回答五件事：
  - 这篇在做什么
  - 为什么今天推荐给我
  - 它补的是哪块知识空白，或为什么值得回炉 / 补链
  - 建议怎么处理：`deepread / skim / backfill / compare / archive`
  - 是否进入今天的深读准备
- 如果判断主要来自摘要、inventory、feedback 和 queue 信号，而不是正文证据，要明确写成“从当前摘要和本地知识覆盖看”。

建议结构：

```md
# 每日论文推荐｜<日期>

## 今日概览
- 研究画像
- run_id
- 候选总数
- shortlist 数
- active queue / revisit due / backfill required

## 今天该怎么分配注意力
- 用 2 到 4 条总结今天的阅读重心
- 明确哪些是立即投入、哪些只需追踪、哪些应该先补经典或回炉

## 必读（must_read）
### 1. <标题>
- paper_id：
- 这篇在做什么：
- 为什么推荐给我：
- 补的是哪块知识空白：
- 主要方法 / 系统信号：
- 建议动作：
- 反馈或历史状态是否影响了本次排序：
- 是否进入深读：是 / 否

## 追踪（trend_watch）
### 1. <标题>
- paper_id：
- 最近值得追踪的点：
- 为什么先看趋势而不是立刻深读：
- 建议动作：

## 补洞（gap_fill）
### 1. <标题>
- paper_id：
- 它补的是哪块知识空白：
- 为什么现在补：
- 建议动作：

## 回炉 / 补链（review_or_backfill）
### 1. <标题或经典论文名>
- 类型：revisit / backfill
- 为什么现在安排：
- 与今天的新论文有什么关系：
- 建议动作：

## 今日深读安排
- must_read_top2
- gap_fill_top1

## 备注
- 明确指出哪些条目受 feedback adjustment、revisit、backfill 或 queue demotion 影响。
```
