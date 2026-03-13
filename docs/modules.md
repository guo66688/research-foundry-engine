# 模块清单：Source Routing 与回放基座

**核心模块**
- `scripts/lib/source_pools.py`：来源分池与跨来源去重。
- `scripts/lib/source_routing.py`：来源感知路由与解释生成。
- `scripts/lib/triage_scoring.py`：评分与 knowledge gap 计算。
- `scripts/lib/research_queue.py`：today 队列编排与 queue_decisions。
- `scripts/lib/revisit_planner.py`：revisit/回访候选规划。
- `scripts/lib/canonical_backfill.py`：canonical backfill 生成。

**回放模块**
- `tests/fixtures/source_routing/*`：离线样本与期望断言。
- `scripts/tooling/run_source_routing_fixture.py`：回放执行器。
- `scripts/tooling/validate_source_routing_fixture.py`：断言与验收。
