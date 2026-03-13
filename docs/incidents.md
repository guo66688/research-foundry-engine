# 事故与回放

**适用场景**
- 新增来源或调权后，出现来源分桶漂移。
- must_read 混入 S2 或 gap_fill 超出配额。
- daily_context 缺字段或 explain 不完整。

**回放流程**
1. 运行 `scripts/tooling/validate_source_routing_fixture.py`。
2. 根据失败样本定位：来源限制、gap_fill、dedupe 或 explain 字段。
3. 对应修改后复跑样本，确保回归通过。

**定位要点**
- 优先看 bucket/source mix 摘要。
- 再看 `triage_explanations` 与 `queue_decisions`。
- 必要时对照 fixtures 的 `expected.json`。
