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

## 2026-03 Semantic Scholar 来源角色化接入

本次架构调整不新增高层命令，也不新增高层 skill，而是在既有命令编排下新增“来源角色化 + 分池 + 分桶路由”能力：

- `source-intake` 负责把候选拆分为 `fresh_pool`（arXiv）与 `hot_pool`（Semantic Scholar）。
- `candidate-triage` 保留基础评分层，再通过 `source-aware routing` 决定候选可进入的桶。
- `flow_today_command` 仍走原有主流程，但会读取并透传来源池信息与来源混合统计。

### 模块分层

- `scripts/lib/semantic_scholar_adapter.py`
  - 负责 Semantic Scholar 原始响应到统一候选 schema 的字段映射。
  - 输出 `source_role`, `publication_year`, `fields_of_study`, `recent_citation_velocity` 等扩展字段。

- `scripts/lib/source_pools.py`
  - 负责来源角色到池的映射、池内组织与跨来源去重优先级。
  - 统一输出 `fresh_pool` / `hot_pool` / 兼容 `candidate_pool`。

- `scripts/lib/source_routing.py`
  - 负责来源感知桶准入、来源配额、来源混合策略与路由解释。
  - 明确首版限制：`semantic_scholar` 默认不进入 `must_read`。

### 关键设计原则

- 不把 arXiv 与 Semantic Scholar 直接混成单一候选池做统一排序。
- 不通过一个 `source_weight` 粗暴修正；而是先评分、后路由。
- `review_or_backfill` 继续由本地知识库存与 canonical/revisit 规划主导。
