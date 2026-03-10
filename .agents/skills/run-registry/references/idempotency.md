# 幂等覆盖规则

## `paper_registry.jsonl`

- 以 `run_id + paper_id` 作为更新键
- 命中时执行 upsert，并保留旧的 artifact 引用
- 未命中时追加新记录

## `run_registry.jsonl`

- 以 `run_id` 作为更新键
- 命中时执行 upsert，并保留旧的 artifact 引用
- 未命中时追加新记录

## `run_manifest.json`

- 视为当前 `run_id` 的单一事实文件
- 后写入的有效结果更新状态与时间，但不应静默丢掉旧 artifact
