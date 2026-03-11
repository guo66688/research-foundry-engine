# 架构说明

Research Foundry 现在分成四层，而不是只有 phase scripts。

## 四层结构

### 1. Vault 路由层

由 Obsidian Vault 中的 `AGENTS.md` 定义用户入口：

- `今日推荐`
- `深读论文`
- `提取配图`
- `搜索论文`

这一层只描述“用户想做什么”，不实现抓源、排序或 dossier 逻辑。

### 2. 命令编排层

对应 `scripts/commands/`：

- `flow_today_command.py`
- `flow_deepread_command.py`
- `flow_figures_command.py`
- `flow_lookup_command.py`

职责：

- 解析高层命令意图
- 选择 `external` 或 `standalone` backend
- 组合 phase skills
- 把运行结果转写成 Obsidian 友好的 Markdown

这层是高层入口的真实执行器，但它不是新的 skill 层。

### 3. Phase 层

固定为五个阶段：

1. `source-intake`
2. `candidate-triage`
3. `evidence-dossier`
4. `knowledge-synthesis`
5. `run-registry`

每个阶段只负责自己的输入输出契约，不直接感知 Vault 的高层产品命令。

### 4. 运行后端层

同一套命令编排可落到两种后端：

- `external`：调用仓库中的 `scripts/...`
- `standalone`：调用 `~/.codex/skills/*/scripts/...`

这两种模式应共享同一套行为语义和数据契约。

## 默认组合关系

### `今日推荐`

默认编排：

1. `source-intake`
2. `candidate-triage`
3. 渲染日报
4. 对前 3 篇运行 `evidence-dossier`
5. 为前 3 篇提取图片
6. 为前 3 篇运行 `knowledge-synthesis`

### `深读论文`

默认编排：

1. 解析 `paper_id` 或标题
2. `evidence-dossier`
3. 图片提取
4. `knowledge-synthesis`
5. 渲染中文深读笔记

### `提取配图`

默认编排：

1. 解析 `paper_id` 或标题
2. 运行 dossier figure flow
3. 写图片索引 Markdown

### `搜索论文`

默认编排：

1. 只搜索本地 Vault Markdown
2. 按标题、关键词和主题命中排序
3. 默认直接返回结果，不写文件

## 为什么不新增高层 skill

因为高层入口已经由 `AGENTS.md` 提供。再新增一套 `research-radar` 之类的 skill 会重复描述同一件事，增加维护面。当前设计把职责稳定划成：

- `AGENTS.md`：定义用户命令
- `scripts/commands/`：做编排
- phase skills：定义阶段边界
- scripts：执行实现

## standalone 打包的意义

`standalone-skills/` 不是另一套功能，而是把 phase skills 与内部命令支持层打包成可分发形式。它的目标是：

- 新机器只复制 skill 即可
- 用固定虚拟环境安装依赖
- 不要求额外 clone `research-foundry-engine`

## 设计原则

- 高层入口用中文命令表达用户意图
- 中层编排负责组合已有 phase
- phase 契约稳定，不为单个产品用法临时扩边界
- Vault 中只保留 Markdown 和图片
- runtime 目录必须与 Vault 解耦
