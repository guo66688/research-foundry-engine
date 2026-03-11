# standalone-skills

这是 Research Foundry 的默认分发形式。

如果你的目标是：

- 在新机器上快速装好
- 用 Codex 打开 Obsidian Vault 直接输入 `今日推荐 / 深读论文 / 提取配图 / 搜索论文`
- 不想额外 clone 整个 `research-foundry-engine`

那通常只需要这个目录。

## 包含内容

- 5 个 phase skills
  - `source-intake`
  - `candidate-triage`
  - `evidence-dossier`
  - `knowledge-synthesis`
  - `run-registry`
- 内部命令支持层
  - `.internal/research-foundry/commands/`
  - `.internal/research-foundry/templates/`
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
- 复制内部命令支持层到 `~/.codex/skills/.internal/research-foundry/`
- 创建或复用固定虚拟环境 `research-foundry-standalone`
- 在该虚拟环境中安装依赖
- 给每个 skill 写入 `.runtime/python.txt`

固定虚拟环境路径：

- Windows: `%USERPROFILE%\.codex\venvs\research-foundry-standalone`
- macOS/Linux: `~/.codex/venvs/research-foundry-standalone`

## 安装后还需要什么

你还需要一个 Obsidian Vault，并在 Vault 中准备：

- `AGENTS.md`
- `configs/workflow.yaml`
- `configs/profiles.yaml`

其中 `AGENTS.md` 负责把这些命令路由到命令层：

- `今日推荐`
- `深读论文`
- `提取配图`
- `搜索论文`

## 默认执行方式

安装完成后，默认应该走 `standalone`，不是 `external`。

只有在你明确要调试仓库代码时，才需要切到 `external`。

## 设计边界

- Vault 里只放 Markdown、图片和配置
- runtime 目录应放在 Vault 外
- phase skills 仍然是底层执行边界
- 这份分发包不是另一套功能，而是推荐的安装形态
