# 多源行为规则

## 允许部分产出的最低条件

- 只要至少一个启用 source 成功返回候选记录，就允许生成 `candidate_pool.jsonl`

## 必须记录的元数据

- `source_counts`
- `source_status`
- `warnings`

## 明确中止条件

- 全部启用 source 都失败：中止
- 全部启用 source 都返回空记录：中止

## 不允许的行为

- 不允许生成空候选池并把运行标成成功
- 不允许吞掉失败源，只保留表面成功
