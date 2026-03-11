# 运行与产物

## 运行目录

- `runtime/runs/<run_id>/`：单次运行的中间文件与 run manifest
- `runtime/artifacts/`：稳定保留的产物
- `runtime/cache/`：可丢弃的缓存
- `runtime/logs/`：日志输出

## 一次典型运行会产出什么

- `runtime/runs/<run_id>/candidate_pool.jsonl`
- `runtime/runs/<run_id>/triage_result.json`
- `runtime/runs/<run_id>/run_manifest.json`
- `runtime/artifacts/reading_queue-<run_id>.md`
- `runtime/artifacts/dossier-<paper_id>-<slug>.md`
- `runtime/artifacts/figure_manifest-<paper_id>.json`
- `runtime/artifacts/synthesis_report-<paper_id>.md`
- `runtime/artifacts/paper_registry.jsonl`
- `runtime/artifacts/run_registry.jsonl`
- `runtime/artifacts/relations.json`
- `workspace.notes_root/<inbox_dir>/daily-recommendations/YYYY/YYYY-MM-DD-<profile_id>.md`

## 验证命令

脚本语法检查：

```bash
python -m compileall scripts
```

CLI 帮助检查：

```bash
python scripts/intake/flow_intake_fetch.py --help
python scripts/triage/flow_triage_rank.py --help
python scripts/dossier/flow_dossier_build.py --help
python scripts/synthesis/flow_synthesis_link.py --help
python scripts/registry/flow_registry_update.py --help
```

## 失败时应该有什么表现

- 缺配置：立即报错，不继续执行。
- 源数据为空：仍应保留 run 目录，并明确状态。
- registry 更新失败：不能静默丢掉 artifact 路径。
- 可选依赖缺失：应明确指出缺什么，而不是让无关阶段一起失效。

## 实际排查建议

先看 `runtime/runs/<run_id>/run_manifest.json`，确认：

- `run_id` 是否正确
- 当前阶段写入了哪些 artifact
- `status` 是否符合预期

再看 `runtime/artifacts/`，确认稳定产物是否真的落盘。
