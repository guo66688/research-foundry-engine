# 快速开始

这份文档只保留日常使用最短路径。

默认方案是 `standalone` 内置分发版。  
如果你不是在改仓库代码，就不要先走 `external`。

## 路径 A：默认使用的 standalone

### 1. 安装 skills 和固定虚拟环境

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\standalone-skills\install-standalone-skills.ps1 -InstallDeps
```

macOS/Linux:

```bash
./standalone-skills/install-standalone-skills.sh --install-deps
```

这一步会：

- 复制 phase skills 到 `~/.codex/skills/`
- 复制内部命令支持层到 `~/.codex/skills/.internal/research-foundry/`
- 创建或复用固定虚拟环境 `research-foundry-standalone`
- 在这个虚拟环境中安装依赖

### 2. 准备 Vault 配置

在你的 Obsidian Vault 中准备：

- `AGENTS.md`
- `configs/workflow.yaml`
- `configs/profiles.yaml`

至少确认这些字段：

- `workspace.notes_root`
- `runtime.run_dir`
- `runtime.artifact_dir`
- `runtime.cache_dir`
- `runtime.log_dir`
- `profiles[].profile_id`
- `profiles[].include_terms`

推荐做法：

- `notes_root` 指向 Vault 根目录
- `run_dir / artifact_dir / cache_dir / log_dir` 全部放在 Vault 外

### 3. 用 Codex 打开 Vault

确保 `AGENTS.md` 中的默认执行偏好是：

1. `standalone`
2. `external` 仅显式要求时使用

### 4. 直接输入中文命令

```text
今日推荐
深读论文 2603.09821
提取配图 2603.09821
搜索论文 "agent memory"
```

默认行为：

- `今日推荐`：抓候选、做 triage、生成日报，并自动深读前 3 篇
- `深读论文`：生成中文深读笔记、提图，并默认做知识链接
- `提取配图`：只提图，并生成图片索引
- `搜索论文`：只搜本地 Markdown 笔记

## 路径 B：仅开发时使用的 external

只有在你明确要调试或修改仓库代码时，才直接运行 external：

```bash
python scripts/commands/flow_today_command.py --mode external --config configs/workflow.yaml --profiles configs/profiles.yaml
python scripts/commands/flow_deepread_command.py 2603.09821 --mode external --config configs/workflow.yaml --profiles configs/profiles.yaml
python scripts/commands/flow_figures_command.py 2603.09821 --mode external --config configs/workflow.yaml
python scripts/commands/flow_lookup_command.py "agent memory" --config configs/workflow.yaml
```

如果 external 报 `PyYAML`、`yaml` 或解释器缺包问题，优先检查：

- 你是否真的需要 external
- 你是否用了仓库自己的虚拟环境 Python

不是 daily use 场景时，不建议再回到 external。

## 你需要记住的边界

- `AGENTS.md` 是高层命令路由，不是新的高层 skill
- 真正执行的是命令层脚本和 phase skills
- Vault 中只保存最终 Markdown 和图片
- 运行时 JSON、日志、缓存都应留在 Vault 外
