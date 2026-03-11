# standalone-skills

这是 Research Foundry 的推荐分发形式。

如果你只是想在新机器上使用 `今日推荐 / 深读论文 / 提取配图 / 搜索论文`，通常只需要这一个目录，不需要完整 clone `research-foundry-engine` 仓库。

## 包含内容

- 5 个 phase skills
  - `source-intake`
  - `candidate-triage`
  - `evidence-dossier`
  - `knowledge-synthesis`
  - `run-registry`
- 内部命令支持层
  - `.internal/research-foundry/commands/`
- 安装脚本
  - `install-standalone-skills.ps1`
  - `install-standalone-skills.sh`
- 依赖清单
  - `requirements.txt`

## 安装

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\install-standalone-skills.ps1 -InstallDeps
```

### macOS/Linux

```bash
./install-standalone-skills.sh --install-deps
```

默认会：

- 安装到 `~/.codex/skills/`
- 创建或复用固定虚拟环境 `research-foundry-standalone`
- 复制内部命令支持层到 `~/.codex/skills/.internal/research-foundry/commands/`

## 安装后需要什么

你还需要一个 Obsidian Vault，并在 Vault 中准备：

- `AGENTS.md`
- `configs/workflow.yaml`
- `configs/profiles.yaml`

其中 `AGENTS.md` 负责把这些中文命令路由到命令层：

- `今日推荐`
- `深读论文`
- `提取配图`
- `搜索论文`

## 设计边界

- Vault 里只放 Markdown 和图片
- runtime 目录应放在 Vault 外
- phase skills 仍然是底层执行边界
- 这份分发包不是另一套功能，只是 standalone 安装形态
