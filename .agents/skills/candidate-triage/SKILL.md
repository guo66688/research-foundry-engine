---
name: candidate-triage
description: Use when Codex needs to score, deduplicate, and shortlist a candidate pool into a reading queue. Do not use for fetching raw source data, building single-paper dossiers, note linking, or registry updates.
---

# Candidate Triage

## Inputs

- `configs/workflow.yaml`
- `configs/profiles.yaml`
- `runtime/runs/<run_id>/candidate_pool.jsonl`

## Outputs

- `runtime/runs/<run_id>/triage_result.json`
- `runtime/artifacts/reading_queue-<run_id>.md`

## Responsible For

- Scoring candidate records
- Deduplicating near-identical entries
- Assigning tiers and shortlist status
- Producing a reading queue

## Not Responsible For

- Pulling source records
- Reading the full paper
- Creating a dossier
- Updating relations or registry indexes

## Invocation

```bash
python scripts/triage/flow_triage_rank.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id <profile_id> \
  --input runtime/runs/<run_id>/candidate_pool.jsonl
```

## Failure Handling

- If the candidate pool is empty, stop with an explicit error.
- If weights are invalid, stop instead of guessing.
- If the output path is unwritable, do not partially emit queue files.
