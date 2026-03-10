---
name: run-registry
description: Use when Codex needs to register run metadata, artifact paths, and global indexes after work has been completed. Do not use for content generation, paper analysis, source fetching, or relation inference.
---

# Run Registry

## Inputs

- `configs/workflow.yaml`
- one `run_id`
- one `paper_id`
- one lifecycle `state`
- one or more `kind=path` artifact pairs

## Outputs

- `runtime/runs/<run_id>/run_manifest.json`
- `runtime/artifacts/paper_registry.jsonl`
- `runtime/artifacts/run_registry.jsonl`

## Responsible For

- Recording run metadata
- Registering stable artifacts
- Maintaining global run and paper indexes

## Not Responsible For

- Generating dossier content
- Analyzing papers
- Inferring note relations
- Fetching candidates

## Invocation

```bash
python scripts/registry/flow_registry_update.py \
  --config configs/workflow.yaml \
  --run-id <run_id> \
  --paper-id <paper_id> \
  --state registered \
  --artifact dossier=runtime/artifacts/dossier-<paper_id>-<slug>.md
```

## Failure Handling

- If an artifact is missing the `kind=path` format, stop.
- If registry files already contain the same run or paper key, replace that entry deterministically.
- Do not silently discard artifact paths.
