# 约定与命名

## 命名

- 项目名固定为 `Research Foundry`
- phase skill 目录名使用阶段名
- phase 脚本名统一使用 `flow_<phase>_<action>.py`
- 命令层脚本统一使用 `flow_<intent>_command.py`
- artifact 文件统一使用小写、短横线分隔

## 高层命令命名

面向用户的高层命令固定为：

- `今日推荐`
- `深读论文`
- `提取配图`
- `搜索论文`

英文 alias 只作为兼容入口，不应替代中文主命令。

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

- Vault 中只放 Markdown、图片和配置
- 稳定产物放到 `runtime/artifacts/`
- 单次运行文件放到 `runtime/runs/<run_id>/`
- 临时缓存放到 `runtime/cache/`
- 日志放到 `runtime/logs/`
- standalone 支持层放在 `~/.codex/skills/.internal/research-foundry/commands/`

## 运行环境约定

- standalone 默认虚拟环境名：`research-foundry-standalone`
- standalone 默认虚拟环境路径：
  - Windows：`%USERPROFILE%\\.codex\\venvs\\research-foundry-standalone`
  - macOS/Linux：`~/.codex/venvs/research-foundry-standalone`
- 每个 standalone skill 的运行解释器记录在 `.runtime/python.txt`

## 状态词汇

论文生命周期状态只有这五个：

- `discovered`
- `triaged`
- `dossier_ready`
- `linked`
- `registered`

不要在脚本或文档里发明近义词。

## 文档写法

- README 负责项目定位和推荐入口
- QUICKSTART 只保留最短安装和运行路径
- `docs/` 负责结构、配置、契约和运行说明
- `AGENTS.md` 负责高层命令路由
- `SKILL.md` 负责 phase 边界
