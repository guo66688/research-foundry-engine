# Runtime

## Directories

- `runtime/runs/<run_id>/`: per-run working files
- `runtime/artifacts/`: stable outputs worth keeping
- `runtime/cache/`: disposable fetched payloads
- `runtime/logs/`: execution logs

## Expected Outputs

A typical run can produce:

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

## Validation Commands

Syntax validation:

```bash
python -m compileall scripts
```

Check CLI help:

```bash
python scripts/intake/flow_intake_fetch.py --help
python scripts/triage/flow_triage_rank.py --help
python scripts/dossier/flow_dossier_build.py --help
python scripts/synthesis/flow_synthesis_link.py --help
python scripts/registry/flow_registry_update.py --help
```

## Failure Expectations

- Missing config should stop immediately with a clear error.
- Empty source responses should still emit a run directory and a failure status when appropriate.
- Registry updates must never silently drop an artifact path.
