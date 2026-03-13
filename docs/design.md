# 设计说明：离线回放与 Source Routing 回归基座

**目标**
- 提供可重复、可离线的 source-routing 回放样本。
- 固定输入，保证 triage 与 today flow 的关键输出结构可回放。
- 允许后续调权与策略变更时做对比回归。

**设计原则**
- 不访问网络，所有输入均来自 fixtures。
- 不修改推荐逻辑，仅补回放与验收基座。
- 断言优先关注来源角色、桶路由、解释字段与编排结构，不绑定脆弱排序。

**关键不变量**
- `semantic_scholar` 首版限制不得进入 `must_read`。
- `trend_watch` 允许 S2 进入，且满足 target mix 或最小数量。
- `gap_fill` 由 knowledge gap 驱动，S2 数量受限。
- `daily_context` 必须包含 source_pools / source_mix_summary / queue_decisions / deepread_picks 等结构字段。
 - fixtures 中 `published_at` 固定为远期/历史日期，避免 recency 随时间漂移。

**样本覆盖**
- A：arXiv-only 基线，验证 S2 关闭时不漂移。
- B：arXiv + S2 趋势补充，验证 S2 仅进入 trend_watch。
- C：knowledge gap 优先，验证 blind_spot / weak 驱动。
- D：跨来源去重，验证 arXiv 优先保留。
- E：today 编排与 explain 完整性。

**脚本入口**
- `scripts/tooling/run_source_routing_fixture.py`
- `scripts/tooling/validate_source_routing_fixture.py`
