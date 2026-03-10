---
name: source-intake
description: Use when Codex needs to fetch or normalize candidate papers from configured sources for one research profile. Do not use for ranking, full-paper dossier building, note linking, or registry updates.
---

# Source Intake

## Inputs

- `configs/workflow.yaml`
- `configs/profiles.yaml`
- one `profile_id`

## Outputs

- `runtime/runs/<run_id>/candidate_pool.jsonl`
- `runtime/runs/<run_id>/run_manifest.json`

## Responsible For

- Pulling candidate papers from configured sources
- Normalizing source metadata into the shared candidate schema
- Emitting a candidate pool tied to one run and one profile

## Not Responsible For

- Sorting or scoring candidates
- Building a dossier for one paper
- Linking papers to notes
- Registering stable artifacts

## Invocation

```bash
python scripts/intake/flow_intake_fetch.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id <profile_id>
```

## Failure Handling

- If config files are missing or malformed, stop immediately.
- If a source returns no records, still create the run directory and manifest.
- If network access fails, report the source that failed and do not invent records.
