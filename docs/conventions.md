# 约定与命名

## 命名

- 项目名固定为 `Research Foundry`
- skill 目录名使用阶段名
- 脚本名统一使用 `flow_<phase>_<action>.py`
- artifact 文件统一使用小写、短横线分隔

## slug 规则

- 标题先转小写
- 尽可能转为 ASCII
- 连续非字母数字字符折叠成一个 `-`
- 去掉首尾的 `-`
- 最长 80 个字符

## 时间戳

- 机器时间统一使用 UTC
- 推荐格式：`YYYY-MM-DDTHH:MM:SSZ`
- `run_id` 后缀格式：`YYYYMMDDTHHMMSSZ`

## 路径分层

- 稳定产物放到 `runtime/artifacts/`
- 单次运行文件放到 `runtime/runs/<run_id>/`
- 临时缓存放到 `runtime/cache/`
- 日志放到 `runtime/logs/`

## 状态词汇

论文生命周期状态只有这五个：

- `discovered`
- `triaged`
- `dossier_ready`
- `linked`
- `registered`

不要在脚本或文档里发明近义词。

## 文档写法

- README 负责总览，不承载全部细节
- QUICKSTART 只保留最短路径
- 具体契约落到 `docs/`
- skill 的边界定义以各自 `SKILL.md` 为准
