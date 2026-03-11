# Research Foundry

Research Foundry 是一套面向 Codex 的论文发现与沉淀工作流。它把论文抓取、候选筛选、单篇深读、笔记关联和运行登记拆成稳定阶段，同时支持两种运行方式：

- `standalone` 内置分发版：推荐给日常使用者。只分发 `standalone-skills/`，运行一键安装脚本后即可在新机器使用。
- `external` 外置仓库版：推荐给开发者。直接在 `research-foundry-engine` 仓库中调试脚本、修改命令层和 phase skills。

## 推荐使用方式

默认推荐 `standalone` 内置分发版。

典型场景：

- 你主要在 Obsidian Vault 里使用 `今日推荐 / 深读论文 / 提取配图 / 搜索论文`
- 你希望新机器只需要复制 skill 并安装一次环境
- 你不想把运行时 JSON、缓存和日志放进 Obsidian Vault

只有在下面情况才建议使用 `external` 外置仓库版：

- 需要修改 `scripts/commands/` 或某个 phase script
- 需要调试 source intake、triage 或 dossier 的实现
- 需要重新打包 standalone skills

## 功能概览

高层入口由 Obsidian Vault 中的 `AGENTS.md` 定义：

- `今日推荐 [profile_id]`
- `深读论文 <paper_id|title>`
- `提取配图 <paper_id|title>`
- `搜索论文 <query>`

这些入口不会创建新的高层 skill，而是编排现有 phase skills：

`source-intake -> candidate-triage -> evidence-dossier -> knowledge-synthesis -> run-registry`

其中：

- `今日推荐` 会运行 intake、triage、日报渲染，并默认深读前 3 篇
- `深读论文` 会生成单篇中文笔记、提取图片并默认做知识链接
- `提取配图` 只提图，不生成完整 dossier
- `搜索论文` 只搜本地 Vault Markdown，不做远程抓取

## 目录结构

```text
.
├── README.md
├── QUICKSTART.md
├── configs/
├── docs/
├── .agents/skills/
├── scripts/
│   ├── commands/
│   ├── shared/
│   ├── intake/
│   ├── triage/
│   ├── dossier/
│   ├── synthesis/
│   └── registry/
├── standalone-skills/
└── runtime/
```

关键目录说明：

- `scripts/commands/`：高层命令编排层，对应 `今日推荐 / 深读论文 / 提取配图 / 搜索论文`
- `.agents/skills/`：phase skills 的源码说明
- `standalone-skills/`：可分发的内置版 skill 打包结果
- `runtime/`：运行时产物，应该放在 Vault 外

## 快速入口

如果你是第一次使用，按这个顺序看：

1. [QUICKSTART.md](QUICKSTART.md)
2. [docs/index.md](docs/index.md)
3. [docs/skills.md](docs/skills.md)
4. [standalone-skills/README.md](standalone-skills/README.md)

如果你要改代码或排查问题，继续看：

1. [docs/architecture.md](docs/architecture.md)
2. [docs/configuration.md](docs/configuration.md)
3. [docs/runtime.md](docs/runtime.md)
4. [docs/data-models.md](docs/data-models.md)

## 最短路径

### A. 推荐路径：standalone 内置分发

1. 复制 `standalone-skills/` 到目标机器
2. 运行安装脚本
3. 在 Obsidian Vault 中准备 `configs/workflow.yaml` 和 `configs/profiles.yaml`
4. 用 Codex 打开 Vault，直接输入 `今日推荐`

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\standalone-skills\install-standalone-skills.ps1 -InstallDeps
```

macOS/Linux:

```bash
./standalone-skills/install-standalone-skills.sh --install-deps
```

默认虚拟环境路径：

- Windows: `%USERPROFILE%\.codex\venvs\research-foundry-standalone`
- macOS/Linux: `~/.codex/venvs/research-foundry-standalone`

### B. 开发路径：external 外置仓库

直接运行命令层脚本：

```bash
python scripts/commands/flow_today_command.py --config configs/workflow.yaml --profiles configs/profiles.yaml
python scripts/commands/flow_deepread_command.py 2603.09821 --config configs/workflow.yaml --profiles configs/profiles.yaml
python scripts/commands/flow_figures_command.py 2603.09821 --config configs/workflow.yaml
python scripts/commands/flow_lookup_command.py "agent memory" --config configs/workflow.yaml
```

## 设计边界

- Obsidian Vault 里只放 Markdown 文档、配置和图片
- `candidate_pool.jsonl`、`triage_result.json`、manifest、logs、cache 不应写入 Vault
- 高层命令由 `AGENTS.md` 路由
- phase skills 只负责各自阶段，不承担新的高层产品编排
- standalone 与 external 共用同一套阶段契约和命令语义

## 验证

改动脚本后先运行：

```bash
python -m compileall scripts
python scripts/tooling/build_standalone_skills.py
```

如果只改文档或配置，可以跳过构建。
