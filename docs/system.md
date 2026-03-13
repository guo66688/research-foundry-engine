# 系统视角：离线回放链路

**系统流转**
- Intake：从 `fresh_pool`/`hot_pool` 合并生成 `candidate_pool`。
- Triage：评分、去重、source-aware routing，产出 `triage_result.json`。
- Today：队列编排，生成 `daily_context-<run_id>.json`。

**离线回放**
- fixtures 提供稳定的 pools、profile、workflow、notes 与 expected。
- 通过回放脚本触发 triage 与 today，不依赖在线 API。

**输出契约**
- Triage：`buckets`、`source_mix_summary`、`explain` 字段必须完整。
- Today：`source_pools`、`queue_decisions`、`review_or_backfill` 必须落盘。
