# Research Foundry

Research Foundry is a Codex-oriented workflow toolkit for paper intake, triage, evidence capture, knowledge linking, and run registration. It is organized as a research pipeline first and a skill collection second.

## What It Solves

- Turn raw paper feeds into a candidate pool tied to a research profile.
- Score and trim that pool into a deliberate reading queue.
- Build a structured evidence dossier for one paper at a time.
- Link new findings back into an existing note base.
- Register runs and artifacts so the workflow stays auditable.

## Workflow Shape

`source-intake` -> `candidate-triage` -> `evidence-dossier` -> `knowledge-synthesis` -> `run-registry`

Each phase has a narrow contract:

- `source-intake` fetches and normalizes source records.
- `candidate-triage` scores, deduplicates, and emits a shortlist.
- `evidence-dossier` builds a structured dossier plus figure manifest.
- `knowledge-synthesis` links the dossier to existing notes and relations.
- `run-registry` records the run and registers resulting artifacts.

## Repository Layout

```text
.
├── AGENTS.md
├── QUICKSTART.md
├── README.md
├── configs/
│   ├── profiles.example.yaml
│   └── workflow.example.yaml
├── docs/
│   ├── architecture.md
│   ├── conventions.md
│   ├── data-models.md
│   └── runtime.md
├── .agents/
│   └── skills/
├── scripts/
│   ├── shared/
│   ├── intake/
│   ├── triage/
│   ├── dossier/
│   ├── synthesis/
│   └── registry/
└── runtime/
    ├── artifacts/
    ├── cache/
    ├── logs/
    └── runs/
```

## Configuration

Workflow-wide settings live in `configs/workflow.example.yaml`.
Research strategies live in `configs/profiles.example.yaml`.

The split is intentional:

- Workflow config describes storage, source settings, runtime behavior, and output policy.
- Profile config describes research focus, candidate limits, source scope, and scoring overrides.

Field definitions and file contracts are documented in `docs/data-models.md`.

## Minimal Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Prepare local config copies:

```bash
cp configs/workflow.example.yaml configs/workflow.yaml
cp configs/profiles.example.yaml configs/profiles.yaml
```

Run the smallest end-to-end path:

```bash
python scripts/intake/flow_intake_fetch.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id llm_systems

python scripts/triage/flow_triage_rank.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id llm_systems \
  --input runtime/runs/<run_id>/candidate_pool.jsonl

python scripts/dossier/flow_dossier_build.py \
  --config configs/workflow.yaml \
  --profiles configs/profiles.yaml \
  --profile-id llm_systems \
  --triage-file runtime/runs/<run_id>/triage_result.json \
  --paper-id <paper_id>

python scripts/synthesis/flow_synthesis_link.py \
  --config configs/workflow.yaml \
  --dossier runtime/artifacts/dossier-<paper_id>-<slug>.md

python scripts/registry/flow_registry_update.py \
  --config configs/workflow.yaml \
  --run-id <run_id> \
  --paper-id <paper_id> \
  --state registered \
  --artifact dossier=runtime/artifacts/dossier-<paper_id>-<slug>.md
```

## Using Codex Skills

The skills in `.agents/skills/` are operator guides for these phases. Use them when you want Codex to decide the exact command invocation, validate inputs, or explain a failure. Do not treat the skills as the project itself; they are thin operational overlays on top of the workflow scripts and data contracts.

## Optional Integrations

- Local note library: set `workspace.notes_root` and related subdirectories.
- Semantic Scholar API key: set the env var referenced by `sources.semantic_scholar.api_key_env`.
- Figure extraction: enabled by `dossier_policy.figure_mode` and the dossier figure script.

## Verification

After editing scripts, run:

```bash
python -m compileall scripts
```

Validation and runtime checks are listed in `docs/runtime.md`.
