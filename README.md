# Research Foundry

Research Foundry 是一个面向 Codex 的研究流程工具箱，用来把论文发现、筛选、证据整理、知识关联和运行登记串成一条清晰的工程化流水线。项目优先强调流程阶段和数据契约，而不是零散动作集合。

## 项目目标

- 从论文源中拉取候选记录，并归入明确的研究画像。
- 用统一规则做评分、去重和阅读队列生成。
- 围绕单篇论文生成结构化 evidence dossier。
- 把新结论回连到本地笔记库和关系图。
- 记录每次运行与产物，保证流程可追溯。

## 核心流程

`source-intake` -> `candidate-triage` -> `evidence-dossier` -> `knowledge-synthesis` -> `run-registry`

五个阶段各自只负责一段职责：

- `source-intake`：抓取并标准化候选论文。
- `candidate-triage`：打分、去重、分层并输出阅读队列。
- `evidence-dossier`：围绕单篇论文产出结构化证据档案。
- `knowledge-synthesis`：把 dossier 连接到已有笔记和关系数据。
- `run-registry`：登记运行元数据、产物路径和全局索引。

## 文档入口

- 文档总览：[docs/index.md](/home/icoffee/Projects/codex-arxiv-tools/docs/index.md)
- 快速开始：[QUICKSTART.md](/home/icoffee/Projects/codex-arxiv-tools/QUICKSTART.md)
- 架构说明：[docs/architecture.md](/home/icoffee/Projects/codex-arxiv-tools/docs/architecture.md)
- 配置说明：[docs/configuration.md](/home/icoffee/Projects/codex-arxiv-tools/docs/configuration.md)
- 数据契约：[docs/data-models.md](/home/icoffee/Projects/codex-arxiv-tools/docs/data-models.md)
- 运行与产物：[docs/runtime.md](/home/icoffee/Projects/codex-arxiv-tools/docs/runtime.md)
- 命名与约定：[docs/conventions.md](/home/icoffee/Projects/codex-arxiv-tools/docs/conventions.md)
- Skills 使用边界：[docs/skills.md](/home/icoffee/Projects/codex-arxiv-tools/docs/skills.md)

## 目录结构

```text
.
├── AGENTS.md
├── QUICKSTART.md
├── README.md
├── configs/
│   ├── profiles.example.yaml
│   └── workflow.example.yaml
├── docs/
│   ├── architecture.md
│   ├── configuration.md
│   ├── conventions.md
│   ├── data-models.md
│   ├── index.md
│   ├── runtime.md
│   └── skills.md
├── .agents/
│   └── skills/
├── scripts/
│   ├── shared/
│   ├── intake/
│   ├── triage/
│   ├── dossier/
│   ├── synthesis/
│   └── registry/
└── runtime/
    ├── artifacts/
    ├── cache/
    ├── logs/
    └── runs/
```

## 最小运行路径

先安装依赖：

```bash
pip install -r requirements.txt
```

再准备本地配置：

```bash
cp configs/workflow.example.yaml configs/workflow.yaml
cp configs/profiles.example.yaml configs/profiles.yaml
```

然后依次执行：

```bash
python scripts/intake/flow_intake_fetch.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id llm_systems

python scripts/triage/flow_triage_rank.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id llm_systems \
  --input runtime/runs/<run_id>/candidate_pool.jsonl

python scripts/dossier/flow_dossier_build.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id llm_systems \
  --triage-file runtime/runs/<run_id>/triage_result.json \
  --paper-id <paper_id>

python scripts/synthesis/flow_synthesis_link.py \
  --config configs/workflow.yaml \
  --dossier runtime/artifacts/dossier-<paper_id>-<slug>.md

python scripts/registry/flow_registry_update.py \
  --config configs/workflow.yaml \
  --run-id <run_id> \
  --paper-id <paper_id> \
  --state registered \
  --artifact dossier=runtime/artifacts/dossier-<paper_id>-<slug>.md
```

## 在 Codex 中如何使用

`.agents/skills/` 下的 skills 是这套流程的操作说明层，不是项目本体。适合在这几种情况下调用：

- 需要 Codex 帮你判断应该跑哪个阶段。
- 需要 Codex 根据输入输出契约拼出正确命令。
- 需要 Codex 在失败时解释边界、前置条件和回退方式。

如果你已经清楚脚本入口和参数，直接运行 `scripts/` 下的 CLI 即可。

## 可选集成

- 本地笔记库：通过 `workspace.notes_root` 及其子目录接入。
- Semantic Scholar API Key：由 `sources.semantic_scholar.api_key_env` 指定环境变量名。
- 图像提取：由 `dossier_policy.figure_mode` 控制，相关逻辑在 dossier 阶段。

## 验证

改动脚本后先运行：

```bash
python -m compileall scripts
```

如果只想验证 CLI 接口是否可用，可继续查看 [docs/runtime.md](/home/icoffee/Projects/codex-arxiv-tools/docs/runtime.md) 里的帮助命令。
