# Quickstart

This file is intentionally short. It covers the minimum path from install to first outputs.

## 1. Install

```bash
pip install -r requirements.txt
```

## 2. Prepare Config

```bash
cp configs/workflow.example.yaml configs/workflow.yaml
cp configs/profiles.example.yaml configs/profiles.yaml
```

Edit these two files:

- `configs/workflow.yaml`
- `configs/profiles.yaml`

Set at least:

- `workspace.notes_root`
- `profiles[].profile_id`
- `profiles[].include_terms`

## 3. Fetch Candidates

```bash
python scripts/intake/flow_intake_fetch.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id llm_systems
```

Output:

- `runtime/runs/<run_id>/candidate_pool.jsonl`

## 4. Score the Pool

```bash
python scripts/triage/flow_triage_rank.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id llm_systems \
  --input runtime/runs/<run_id>/candidate_pool.jsonl
```

Outputs:

- `runtime/runs/<run_id>/triage_result.json`
- `runtime/artifacts/reading_queue-<run_id>.md`

## 5. Build One Dossier

```bash
python scripts/dossier/flow_dossier_build.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id llm_systems \
  --triage-file runtime/runs/<run_id>/triage_result.json \
  --paper-id <paper_id>
```

Outputs:

- `runtime/artifacts/dossier-<paper_id>-<slug>.md`
- `runtime/artifacts/figure_manifest-<paper_id>.json` when figures are extracted

## 6. Inspect Artifacts

Look in:

- `runtime/runs/`
- `runtime/artifacts/`

For deeper contracts and directory rules, read `docs/data-models.md` and `docs/runtime.md`.
