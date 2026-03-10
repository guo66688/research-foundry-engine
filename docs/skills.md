# Skills 使用说明

Research Foundry 的 skills 是流程操作说明层，用来帮助 Codex 在正确阶段调用正确脚本。它们不负责替代整个项目。

## 什么时候看这个文档

- 你想知道五个 skills 的边界是否重叠。
- 你要判断某个请求该落到哪个阶段。
- 你要核对某个 skill 的输入输出文件名。

## 五个 skills 的定位

### `source-intake`

- 触发时机：需要抓取或标准化候选论文时
- 输入：config + profile
- 输出：`candidate_pool.jsonl`
- 不该触发：排序、dossier、关联、登记

### `candidate-triage`

- 触发时机：已经有候选池，需要 shortlist 和阅读队列时
- 输入：`candidate_pool.jsonl`
- 输出：`triage_result.json`、`reading_queue`
- 不该触发：原始数据抓取、全文档案生成

### `evidence-dossier`

- 触发时机：需要围绕单篇论文生成结构化档案时
- 输入：`paper_id` + candidate/triage metadata
- 输出：`dossier-*.md`、可选 `figure_manifest`
- 不该触发：候选排序、全局登记

### `knowledge-synthesis`

- 触发时机：已有 dossier，需要和本地笔记建立关系时
- 输入：dossier + notes root
- 输出：`synthesis_report`、`relations.json`
- 不该触发：重新分析论文、更新 registry

### `run-registry`

- 触发时机：需要登记 run 信息和产物索引时
- 输入：run metadata + artifact list
- 输出：`run_manifest.json`、`paper_registry.jsonl`、`run_registry.jsonl`
- 不该触发：内容生成、关系推理

## 使用方式

- 直接看 `.agents/skills/<phase>/SKILL.md` 获取该阶段的精确边界。
- 如果你已经知道具体脚本和参数，直接运行 `scripts/` 下的 CLI。
- 如果你不确定阶段归属，让 Codex 先根据这份文档判断职责边界，再决定调用哪个 skill。
