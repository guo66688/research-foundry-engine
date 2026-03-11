# Research Foundry

Research Foundry 是一套面向 Codex + Obsidian 的论文发现与研究笔记工作流。

默认使用方式是 `standalone` 内置分发版，不再把 `external` 外置仓库版当作日常入口。

`standalone` 适合日常使用：
- 只分发 `standalone-skills/`
- 跑一次安装脚本
- 用 Codex 打开 Obsidian Vault
- 直接输入 `今日推荐 / 深读论文 / 提取配图 / 搜索论文`

`external` 只保留给开发和调试：
- 修改 `scripts/commands/`
- 调试 phase scripts
- 重新打包 standalone skills

## 现在推荐怎么用

如果你的目标是“在 Vault 里直接用”，看这三份文档即可：

1. [QUICKSTART.md](QUICKSTART.md)
2. [standalone-skills/README.md](standalone-skills/README.md)
3. [docs/index.md](docs/index.md)

## 高层命令

日常使用的入口由 Vault 里的 `AGENTS.md` 定义：

- `今日推荐 [profile_id]`
- `深读论文 <paper_id|title>`
- `提取配图 <paper_id|title>`
- `搜索论文 <query>`

这些命令不会创建新的高层 skill，而是编排现有 phase skills：

`source-intake -> candidate-triage -> evidence-dossier -> knowledge-synthesis -> run-registry`

默认执行偏好：

1. `standalone`
2. `external` 仅在你显式要求时使用

## 仓库结构

```text
.
├── README.md
├── QUICKSTART.md
├── configs/
├── docs/
├── .agents/skills/
├── scripts/
├── standalone-skills/
└── runtime/
```

关键目录：

- `scripts/commands/`：高层命令编排层
- `.agents/skills/`：phase skills 源码说明
- `standalone-skills/`：推荐分发包
- `runtime/`：运行时产物，必须放在 Vault 外

## 最短路径

### A. 默认路径：standalone

1. 复制 `standalone-skills/` 到目标机器
2. 运行安装脚本
3. 在 Vault 中准备 `AGENTS.md`、`configs/workflow.yaml`、`configs/profiles.yaml`
4. 用 Codex 打开 Vault，直接输入 `今日推荐`

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\standalone-skills\install-standalone-skills.ps1 -InstallDeps
```

macOS/Linux:

```bash
./standalone-skills/install-standalone-skills.sh --install-deps
```

固定虚拟环境路径：

- Windows: `%USERPROFILE%\.codex\venvs\research-foundry-standalone`
- macOS/Linux: `~/.codex/venvs/research-foundry-standalone`

### B. 开发路径：external

只有在你明确需要调试或改代码时，才直接运行仓库里的脚本：

```bash
python scripts/commands/flow_today_command.py --mode external --config configs/workflow.yaml --profiles configs/profiles.yaml
python scripts/commands/flow_deepread_command.py 2603.09821 --mode external --config configs/workflow.yaml --profiles configs/profiles.yaml
python scripts/commands/flow_figures_command.py 2603.09821 --mode external --config configs/workflow.yaml
python scripts/commands/flow_lookup_command.py "agent memory" --config configs/workflow.yaml
```

## 设计边界

- Vault 里只放 Markdown、图片和配置
- `candidate_pool.jsonl`、`triage_result.json`、manifest、cache、logs 不应写入 Vault
- 高层命令由 `AGENTS.md` 路由
- phase skills 只负责各自阶段
- standalone 与 external 共用同一套阶段契约，但默认入口是 standalone

## 开发校验

改动脚本后建议运行：

```bash
python -m compileall scripts
python scripts/tooling/build_standalone_skills.py
```
