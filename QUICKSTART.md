# 快速开始

这份文档只保留最短路径。默认推荐使用 `standalone` 内置分发版；`external` 外置仓库版放在文末作为开发模式。

## 路径 A：推荐的 standalone 内置分发

### 1. 安装 skills 和固定虚拟环境

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\standalone-skills\install-standalone-skills.ps1 -InstallDeps
```

macOS/Linux:

```bash
./standalone-skills/install-standalone-skills.sh --install-deps
```

默认会：

- 复制 phase skills 到 `~/.codex/skills/`
- 复制内部命令支持层到 `~/.codex/skills/.internal/research-foundry/commands/`
- 创建或复用固定虚拟环境 `research-foundry-standalone`
- 在该虚拟环境中安装依赖

如果你是在分发包目录中查看说明，继续看 [standalone-skills/README.md](standalone-skills/README.md)。

### 2. 准备 Vault 配置

在你的 Obsidian Vault 中准备：

- `configs/workflow.yaml`
- `configs/profiles.yaml`

至少确认这几个字段：

- `workspace.notes_root`
- `runtime.run_dir`
- `runtime.artifact_dir`
- `profiles[].profile_id`
- `profiles[].include_terms`

推荐做法：

- `notes_root` 指向 Vault 根目录
- `run_dir / artifact_dir / cache_dir / log_dir` 放在 Vault 外

### 3. 在 Codex 中打开 Vault

确保 Vault 根目录有 `AGENTS.md`，其中定义了这些高层命令：

- `今日推荐 [profile_id]`
- `深读论文 <paper_id|title>`
- `提取配图 <paper_id|title>`
- `搜索论文 <query>`

### 4. 直接使用中文命令

```text
今日推荐
深读论文 2603.09821
提取配图 2603.09821
搜索论文 "agent memory"
```

默认行为：

- `今日推荐`：抓候选、做 triage、生成日报，并自动深读前 3 篇
- `深读论文`：生成中文深读笔记、提图，并默认做知识链接
- `提取配图`：只提图，生成图片索引
- `搜索论文`：只搜本地 Markdown 笔记

## 路径 B：external 外置仓库开发模式

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 准备配置

```bash
cp configs/workflow.example.yaml configs/workflow.yaml
cp configs/profiles.example.yaml configs/profiles.yaml
```

### 3. 运行命令层脚本

```bash
python scripts/commands/flow_today_command.py --config configs/workflow.yaml --profiles configs/profiles.yaml
python scripts/commands/flow_deepread_command.py 2603.09821 --config configs/workflow.yaml --profiles configs/profiles.yaml
python scripts/commands/flow_figures_command.py 2603.09821 --config configs/workflow.yaml
python scripts/commands/flow_lookup_command.py "agent memory" --config configs/workflow.yaml
```

### 4. 常见调试入口

如果你需要只跑某个 phase，继续用这些底层脚本：

```bash
python scripts/intake/flow_intake_fetch.py --help
python scripts/triage/flow_triage_rank.py --help
python scripts/dossier/flow_dossier_build.py --help
python scripts/synthesis/flow_synthesis_link.py --help
python scripts/registry/flow_registry_update.py --help
```

## 你需要知道的边界

- `AGENTS.md` 是高层命令路由，不是新的高层 skill
- 真正执行的是命令层脚本和 phase skills
- standalone 与 external 的功能语义应保持一致
- Vault 中只保存最终文档和图片，不保存运行时 JSON 与日志
