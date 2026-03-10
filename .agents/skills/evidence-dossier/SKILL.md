---
name: evidence-dossier
description: Use when Codex needs to build a structured evidence package for one paper, optionally including figure extraction. Do not use for candidate pool creation, global ranking, note graph maintenance, or registry updates.
---

# Evidence Dossier

## Inputs

- `configs/workflow.yaml`
- `configs/profiles.yaml`
- one `paper_id`
- either `triage_result.json` or `candidate_pool.jsonl`

## Outputs

- `runtime/artifacts/dossier-<paper_id>-<slug>.md`
- optional `runtime/artifacts/figure_manifest-<paper_id>.json`

## Responsible For

- Building a single-paper structured dossier
- Pulling figure assets when configured
- Producing a readable artifact for later synthesis

## Not Responsible For

- Building the candidate pool
- Global priority ranking
- Cross-note linking
- Run registration

## Invocation

```bash
python scripts/dossier/flow_dossier_build.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id <profile_id> \
  --triage-file runtime/runs/<run_id>/triage_result.json \
  --paper-id <paper_id>
```

## Failure Handling

- If the `paper_id` is not present in the provided input files, stop.
- If figure extraction fails, keep the dossier path valid and report that figures were skipped.
- Do not fabricate evidence sections that are not supported by the source record.
