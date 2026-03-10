# 失败场景

## artifact 不是 `kind=path`

- 现象：参数格式不符合要求
- 处理：立即停止

## 关键字段缺失

- 现象：`run_id`、`paper_id` 或 `state` 缺失
- 处理：立即停止，不写入残缺记录

## registry 文件已存在同 key 记录

- 现象：同一 `run_id` 或 `paper_id` 已被登记
- 处理：按幂等规则覆盖，不追加重复项

## 输出路径不可写

- 现象：无法更新 manifest 或 registry
- 处理：停止，避免产生部分更新
