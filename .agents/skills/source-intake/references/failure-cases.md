# 失败场景

## 配置文件不存在

- 现象：`workflow.yaml` 或 `profiles.yaml` 无法读取
- 处理：立即停止

## `profile_id` 未定义

- 现象：输入的 `profile_id` 在配置中找不到
- 处理：立即停止，不猜测相近 profile

## 单个 source 请求失败

- 现象：某一数据源超时或返回错误
- 处理：记录失败源，保留 `run_manifest.json`

## 所有 source 均返回空结果

- 现象：没有任何候选记录
- 处理：停止，并提示调整画像、时间窗口或 source 配置
