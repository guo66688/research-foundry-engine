---
name: knowledge-synthesis
description: Use when Codex needs to connect a finished dossier to an existing note base and relation graph. Do not use for reanalyzing the paper, candidate ranking, source fetching, or registry updates.
---

# Knowledge Synthesis

## Inputs

- `configs/workflow.yaml`
- `runtime/artifacts/dossier-<paper_id>-<slug>.md`
- optional `workspace.notes_root`

## Outputs

- `runtime/artifacts/synthesis_report-<paper_id>.md`
- `runtime/artifacts/relations.json`

## Responsible For

- Matching dossier terms against existing notes
- Emitting suggested backlinks
- Updating relation nodes and edges

## Not Responsible For

- Rebuilding the dossier
- Fetching raw paper data
- Reranking candidates
- Registering runs or artifacts

## Invocation

```bash
python scripts/synthesis/flow_synthesis_link.py \
  --config configs/workflow.yaml \
  --dossier runtime/artifacts/dossier-<paper_id>-<slug>.md
```

## Failure Handling

- If no notes root is configured, emit an empty report instead of scanning random directories.
- If no matches are found, write a valid report and keep the relation store consistent.
- Do not overwrite unrelated relation edges.
