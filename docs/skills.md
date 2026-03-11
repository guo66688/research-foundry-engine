# Skills 与 AGENTS 说明

Research Foundry 当前有两层“说明”：

- `AGENTS.md`：定义 Vault 中的高层命令
- phase `SKILL.md`：定义每个阶段的边界和执行要求

这两层不是同一种东西。

## 高层入口在哪里

高层入口在 Obsidian Vault 的 `AGENTS.md` 中，面向用户的主命令是：

- `今日推荐 [profile_id]`
- `深读论文 <paper_id|title>`
- `提取配图 <paper_id|title>`
- `搜索论文 <query>`

这些命令会触发命令编排层，而不是新增一套高层 skill。

## phase skills 是什么

Research Foundry 的 phase skills 固定为：

- `source-intake`
- `candidate-triage`
- `evidence-dossier`
- `knowledge-synthesis`
- `run-registry`

每个 phase skill 只定义：

- 什么时候该进入该阶段
- 需要什么输入
- 产出什么输出
- 什么时候必须停止

## 为什么不新增高层 skill

因为高层命令已经由 `AGENTS.md` 统一路由。如果再增加 `research-radar` 一类的 skill，会出现两套高层描述同时存在的问题：

- 用户入口在 `AGENTS.md`
- 编排语义又在高层 skill

这会让维护和排错都变复杂。当前推荐设计是：

- `AGENTS.md`：定义用户命令
- `scripts/commands/`：实现编排
- phase skills：定义阶段边界

## standalone 与 external 的关系

### external

开发模式，直接使用仓库中的：

- `scripts/commands/*`
- `scripts/intake/*`
- `scripts/triage/*`
- `scripts/dossier/*`
- `scripts/synthesis/*`
- `scripts/registry/*`

### standalone

分发模式，使用安装后的：

- `~/.codex/skills/<phase>/`
- `~/.codex/skills/.internal/research-foundry/commands/`

standalone 的目标是：

- 不要求 clone 仓库
- 只分发 skill 即可
- 用一键安装脚本创建固定虚拟环境并安装依赖

## standalone 打包内容

`standalone-skills/` 中包含：

- 5 个 phase skills
- `.internal/research-foundry/commands/` 内部命令支持层
- 安装脚本
- `requirements.txt`

安装后默认路径：

- `~/.codex/skills/`
- `~/.codex/venvs/research-foundry-standalone`

## 什么时候直接读 SKILL.md

下面情况优先看 phase skill：

- 只想跑某一个 phase
- 想确认某个阶段的输入输出边界
- 想知道失败时应该停在哪里

下面情况优先看 `AGENTS.md`：

- 想知道 `今日推荐 / 深读论文 / 提取配图 / 搜索论文` 应该怎么走
- 想确认 Vault 中应该生成哪些 Markdown

## 维护建议

- 改高层用户入口：先改 `AGENTS.md`
- 改编排逻辑：改 `scripts/commands/`
- 改阶段职责：改对应 phase 的 `SKILL.md` 和 `scripts/<phase>/`
- 改 standalone 分发：改 `build_standalone_skills.py` 后重新生成 `standalone-skills/`
