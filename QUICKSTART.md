# 快速开始

这份文档只保留最短路径：安装、配置、跑通一次最小流程、查看产物。

## 1. 安装依赖

```bash
pip install -r requirements.txt
```

## 2. 复制配置模板

```bash
cp configs/workflow.example.yaml configs/workflow.yaml
cp configs/profiles.example.yaml configs/profiles.yaml
```

至少修改这几个字段：

- `workspace.notes_root`
- `profiles[].profile_id`
- `profiles[].include_terms`

如果要用 Semantic Scholar，再准备 `SEMANTIC_SCHOLAR_API_KEY`。

## 3. 拉取候选论文

```bash
python scripts/intake/flow_intake_fetch.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id llm_systems
```

产物：

- `runtime/runs/<run_id>/candidate_pool.jsonl`

## 4. 生成 shortlist

```bash
python scripts/triage/flow_triage_rank.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id llm_systems \
  --input runtime/runs/<run_id>/candidate_pool.jsonl
```

产物：

- `runtime/runs/<run_id>/triage_result.json`
- `runtime/artifacts/reading_queue-<run_id>.md`

## 5. 生成单篇 dossier

```bash
python scripts/dossier/flow_dossier_build.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id llm_systems \
  --triage-file runtime/runs/<run_id>/triage_result.json \
  --paper-id <paper_id>
```

产物：

- `runtime/artifacts/dossier-<paper_id>-<slug>.md`
- `runtime/artifacts/figure_manifest-<paper_id>.json`，如果启用了图像提取

## 6. 查看输出位置

- 运行过程文件在 `runtime/runs/`
- 稳定产物在 `runtime/artifacts/`

如果你要继续接本地笔记库、关系数据和运行登记，下一步读：

- [docs/configuration.md](/home/icoffee/Projects/codex-arxiv-tools/docs/configuration.md)
- [docs/runtime.md](/home/icoffee/Projects/codex-arxiv-tools/docs/runtime.md)
