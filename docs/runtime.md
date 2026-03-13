# 运行与产物

这份文档同时说明两件事：

- Vault 中应该出现什么
- runtime 区域应该出现什么

## Vault 与 runtime 的边界

### Vault 中允许出现

- 每日推荐 Markdown
- 单篇深读 Markdown
- 图片索引 Markdown
- 论文图片
- `configs/*.yaml`
- `AGENTS.md`

### Vault 中不应出现

- `candidate_pool.jsonl`
- `triage_result.json`
- `run_manifest.json`
- `relations.json`
- `paper_registry.jsonl`
- `run_registry.jsonl`
- `cache/`
- `logs/`

### runtime 中保存

- `runtime/runs/<run_id>/`
- `runtime/artifacts/`
- `runtime/cache/`
- `runtime/logs/`

## 命令层产物

### `今日推荐`

会产出：

- `runtime/runs/<run_id>/candidate_pool.jsonl`
- `runtime/runs/<run_id>/triage_result.json`
- `runtime/runs/<run_id>/run_manifest.json`
- `runtime/artifacts/reading_queue-<run_id>.md`
- `workspace.notes_root/<inbox_dir>/daily-recommendations/YYYY/YYYY-MM-DD-<profile_id>.md`
- `workspace.notes_root/research/papers/<paper_id>.md`
- `workspace.notes_root/research/papers/<paper_id>/images/`

### `深读论文`

会产出：

- `runtime/artifacts/dossier-<paper_id>-<slug>.md`
- 可选 `runtime/artifacts/figure_manifest-<paper_id>.json`
- 可选 `runtime/artifacts/synthesis_report-<paper_id>.md`
- `workspace.notes_root/research/papers/<paper_id>.md`
- `workspace.notes_root/research/papers/<paper_id>/images/`

### `提取配图`

会产出：

- 可选 `runtime/artifacts/figure_manifest-<paper_id>.json`
- `workspace.notes_root/research/papers/<paper_id>/images/`
- 可选 `workspace.notes_root/research/papers/<paper_id>-figures.md`

### `搜索论文`

默认不写文件，只在控制台返回结果。

## standalone 安装位置

推荐默认路径：

- skills：`~/.codex/skills/`
- 内部命令支持层：`~/.codex/skills/.internal/research-foundry/commands/`
- 虚拟环境：`~/.codex/venvs/research-foundry-standalone`

每个 standalone skill 会记录自己的运行 Python：

- `.runtime/python.txt`

这样安装和执行可以绑定到同一个解释器。

## external 调试入口

```bash
python scripts/commands/flow_today_command.py --help
python scripts/commands/flow_deepread_command.py --help
python scripts/commands/flow_figures_command.py --help
python scripts/commands/flow_lookup_command.py --help
```

底层 phase 调试入口：

```bash
python scripts/intake/flow_intake_fetch.py --help
python scripts/triage/flow_triage_rank.py --help
python scripts/dossier/flow_dossier_build.py --help
python scripts/synthesis/flow_synthesis_link.py --help
python scripts/registry/flow_registry_update.py --help
```

## 失败排查建议

先看 `run_manifest.json`，确认：

- `run_id`
- `stage`
- `status`
- `artifacts`
- `warnings`
- `source_status`

再看 Vault，确认：

- 日报是否写入正确目录
- 单篇深读是否写入 `research/papers/`
- 图片是否落在论文目录

对于 standalone 模式，再额外确认：

- `~/.codex/skills/.internal/research-foundry/commands/` 是否存在
- `.runtime/python.txt` 是否记录了有效 Python 路径
- 固定 venv 是否安装了依赖

## 2026-03 daily_context 扩展

`daily_context-<run_id>.json` 新增以下结构：

- `fresh_pool_path`
- `hot_pool_path`
- `source_pools.fresh_pool_count`
- `source_pools.hot_pool_count`
- `source_mix_summary`
- `queue_decisions`

并且推荐项中会保留来源路由解释：

- `source`
- `source_role`
- `bucket_routing_reason`
- `source_selection_reason`

## 离线回放运行目录

- fixtures 使用独立 runtime：`tests/fixtures/source_routing/<sample>/runtime/*`。
- triage 产物：`triage_result.json`、`triage_explanations-<run_id>.json`。
- today 产物：`daily_context-<run_id>.json`、`queue_decisions-<run_id>.json`。
