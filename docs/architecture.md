# Architecture

Research Foundry is split into five execution phases with explicit handoffs.

## Phase Responsibilities

### `source-intake`

- Inputs: workflow config, profile config, `profile_id`
- Outputs: `candidate_pool.jsonl`
- Responsibility: fetch source records and normalize them into a common schema
- Not responsible for: ranking, dossier generation, note linking, registry updates

### `candidate-triage`

- Inputs: `candidate_pool.jsonl`, workflow config, profile config
- Outputs: `triage_result.json`, `reading_queue-<run_id>.md`
- Responsibility: score, deduplicate, layer, and shortlist candidates
- Not responsible for: source fetching, dossier generation, relation updates

### `evidence-dossier`

- Inputs: `paper_id`, candidate or triage metadata, dossier policy
- Outputs: `dossier-<paper_id>-<slug>.md`, optional `figure_manifest-<paper_id>.json`
- Responsibility: build a structured evidence package for one paper
- Not responsible for: global ranking, note graph maintenance, registry writes

### `knowledge-synthesis`

- Inputs: dossier markdown, notes root, relation policy
- Outputs: `synthesis_report.md`, `relations.json`
- Responsibility: link new material to existing notes and relation graph
- Not responsible for: reranking, full-paper parsing, run registration

### `run-registry`

- Inputs: run metadata, paper identifiers, artifact paths
- Outputs: `run_manifest.json`, `paper_registry.jsonl`, `run_registry.jsonl`
- Responsibility: register what happened and where outputs landed
- Not responsible for: content generation, source access, relation inference

## Dependency Order

Default order:

1. `source-intake`
2. `candidate-triage`
3. `evidence-dossier`
4. `knowledge-synthesis`
5. `run-registry`

## Standalone Execution

- `source-intake` can run by itself to refresh candidate pools.
- `candidate-triage` can rerun against an existing pool without refetching sources.
- `evidence-dossier` can run from a triage file or a candidate file.
- `knowledge-synthesis` can run on any valid dossier file.
- `run-registry` can register artifacts after the fact if paths are known.

## Contracts First

Phase scripts are small by design. Shared logic belongs under `scripts/shared/`. Every phase must read and write the contracts defined in `docs/data-models.md`.
