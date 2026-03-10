# 架构说明

Research Foundry 按五个明确的执行阶段组织，每个阶段只读写自己的输入输出，不跨界承担别人的职责。

## 阶段职责

### `source-intake`

- 输入：workflow 配置、profiles 配置、`profile_id`
- 输出：`candidate_pool.jsonl`
- 负责：从外部源抓取论文记录并标准化为统一 schema
- 不负责：排序打分、dossier 生成、笔记关联、registry 更新

### `candidate-triage`

- 输入：`candidate_pool.jsonl`、workflow 配置、profiles 配置
- 输出：`triage_result.json`、`reading_queue-<run_id>.md`
- 负责：打分、去重、分层、shortlist 生成
- 不负责：原始数据抓取、单篇档案生成、relation 更新

### `evidence-dossier`

- 输入：`paper_id`、candidate 或 triage 元数据、dossier 策略
- 输出：`dossier-<paper_id>-<slug>.md`，可选 `figure_manifest-<paper_id>.json`
- 负责：围绕单篇论文生成结构化 evidence package
- 不负责：全局优先级排序、知识图维护、registry 写入

### `knowledge-synthesis`

- 输入：dossier Markdown、notes root、relation 策略
- 输出：`synthesis_report-<paper_id>.md`、`relations.json`
- 负责：把新 dossier 连接到已有笔记和关系边
- 不负责：重排候选池、全文深度解析、运行登记

### `run-registry`

- 输入：run 元数据、paper 标识、artifact 路径
- 输出：`run_manifest.json`、`paper_registry.jsonl`、`run_registry.jsonl`
- 负责：登记发生了什么、产物在哪、状态是什么
- 不负责：内容生成、源数据访问、关系推理

## 默认依赖顺序

1. `source-intake`
2. `candidate-triage`
3. `evidence-dossier`
4. `knowledge-synthesis`
5. `run-registry`

## 哪些阶段可单独运行

- `source-intake`：可以单独刷新候选池。
- `candidate-triage`：可以对已有候选池反复重跑，不必重新抓源。
- `evidence-dossier`：可以基于 triage 文件或 candidate 文件独立运行。
- `knowledge-synthesis`：可以直接对已有 dossier 做关联。
- `run-registry`：只要 artifact 路径已知，就能补登记。

## 设计原则

- 先定义契约，再写脚本。
- 共享逻辑放在 `scripts/shared/`，阶段脚本保持薄。
- 所有阶段都必须遵守 [data-models.md](/home/icoffee/Projects/codex-arxiv-tools/docs/data-models.md) 中的数据契约。
