# Skills 使用说明

Research Foundry 的 skills 是流程调度控制面，不是百科，也不是脚本目录的另一份复制品。它们的职责只有一个：告诉 Codex 什么时候该进入某个阶段，进入后只做什么，做到什么程度必须停手。

## skill 的控制面结构

每个 `SKILL.md` 正文统一为 8 段，顺序固定：

1. `目标`
2. `何时触发`
3. `何时不触发`
4. `必需输入`
5. `输出文件`
6. `前置检查`
7. `失败处理`
8. `交接条件`

这个结构的目的不是写得好看，而是给 workflow 装上刹车片，防止某个阶段顺手越界去做下游工作。

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
- 如果已经知道具体脚本与参数，直接运行 `scripts/` 下的 CLI。
