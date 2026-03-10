# Skills 使用说明

Research Foundry 的 skills 是流程调度控制面，不是百科，也不是脚本目录的另一份复制品。它们的职责只有一个：告诉 Codex 什么时候进入某个阶段，进入后只干什么，干到什么程度必须停手。

## 控制面结构

每个 `SKILL.md` 采用固定布局：

### 核心 8 段

1. `目标`
2. `何时触发`
3. `何时不触发`
4. `必需输入`
5. `输出文件`
6. `前置检查`
7. `失败处理`
8. `交接条件`

### 固定示例附录

9. `最小可执行示例`
10. `常见错误示例`

前 8 段负责定义边界，后 2 段负责把边界落成可执行样例。不要再额外长出新的大段落。

## references 分层

复杂说明不放进 `SKILL.md` 本体，而是放进各阶段的 `references/`。

每个 skill 至少包含：

- `references/io-contracts.md`
- `references/failure-cases.md`

按阶段再补：

- `candidate-triage/references/scoring.md`
- `evidence-dossier/references/modes.md`
- `knowledge-synthesis/references/thresholds.md`
- `run-registry/references/idempotency.md`
- `source-intake/references/source-behavior.md`

跨 skill 的统一交接视图见：

- [.agents/skills/references/handoff-matrix.md](/home/icoffee/Projects/codex-arxiv-tools/.agents/skills/references/handoff-matrix.md)

## 五个 skills 的定位

### `source-intake`

- 负责：抓取并标准化候选论文
- 停止点：`candidate_pool.jsonl` 成功写出后立即停止
- 下游：`candidate-triage`

### `candidate-triage`

- 负责：评分、去重、分层、生成阅读队列
- 停止点：`triage_result.json` 和 `reading_queue` 生成后立即停止
- 下游：`evidence-dossier` 或等待用户选择论文

### `evidence-dossier`

- 负责：围绕单篇论文生成 dossier 和可选图像清单
- 停止点：`dossier-<paper_id>-<slug>.md` 生成后立即停止
- 下游：`knowledge-synthesis`

### `knowledge-synthesis`

- 负责：将 dossier 连接到本地笔记与 relation 图
- 停止点：`synthesis_report` 与 `relations.json` 更新后立即停止
- 下游：`run-registry` 或人工审阅

### `run-registry`

- 负责：登记 run 元数据、paper 索引与 artifact 索引
- 停止点：registry 文件更新后立即停止
- 下游：无，等待下一次显式调度

## 使用方式

- 先看 `.agents/skills/<phase>/SKILL.md`，判断是否该进入该阶段。
- 再按需要查看同目录下的 `references/`，只加载当前问题相关的文件。
- 如果是跨阶段调度问题，先看共享交接矩阵。
- 如果已经知道具体脚本与参数，直接运行 `scripts/` 下的 CLI。
