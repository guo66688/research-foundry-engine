# Data Models

This document defines the shared contract used by all five phases.

## Identifier Rules

- `run_id`: `run-<YYYYMMDDTHHMMSSZ>`
- `paper_id`: canonical arXiv identifier when available, otherwise a normalized slug prefixed by source name
- `profile_id`: lowercase snake case from profile config
- `relation_id`: `rel-<source_slug>-<target_slug>-<relation_type>`

## State Flow

The expected state progression is:

1. `discovered`
2. `triaged`
3. `dossier_ready`
4. `linked`
5. `registered`

Scripts may skip ahead only when they can prove prior artifacts already exist.

## File Contracts

### `candidate_pool.jsonl`

One JSON object per line with these fields:

- `run_id`
- `profile_id`
- `paper_id`
- `source`
- `source_record_id`
- `title`
- `abstract`
- `authors`
- `published_at`
- `updated_at`
- `categories`
- `source_url`
- `pdf_url`
- `citation_count`
- `influential_citation_count`
- `profile_hits`
- `state`
- `fetched_at`

### `triage_result.json`

Top-level fields:

- `run_id`
- `profile_id`
- `generated_at`
- `input_path`
- `dedupe_strategy`
- `weights`
- `stats`
- `selected`
- `rejected`

Each selected or rejected item must include:

- `paper_id`
- `title`
- `state`
- `scores`
- `tier`
- `reason`

### `figure_manifest-<paper_id>.json`

Top-level fields:

- `paper_id`
- `generated_at`
- `figure_count`
- `items`

Each item:

- `name`
- `source`
- `path`
- `format`
- `bytes`

### `paper_registry.jsonl`

One entry per registered paper artifact group:

- `run_id`
- `paper_id`
- `profile_id`
- `title`
- `slug`
- `state`
- `artifacts`
- `registered_at`

### `run_registry.jsonl`

One entry per run:

- `run_id`
- `profile_id`
- `started_at`
- `updated_at`
- `status`
- `artifacts`

### `relations.json`

Top-level fields:

- `updated_at`
- `nodes`
- `edges`

Node fields:

- `id`
- `kind`
- `label`
- `path`
- `paper_id`

Edge fields:

- `id`
- `source`
- `target`
- `type`
- `weight`

## Naming Rules

- Dossier markdown: `dossier-<paper_id>-<slug>.md`
- Figure manifest: `figure_manifest-<paper_id>.json`
- Reading queue: `reading_queue-<run_id>.md`
- Run manifest: `run_manifest.json`

## Enum Values

### `tier`

- `priority`
- `watch`
- `discard`

### `status`

- `running`
- `completed`
- `failed`

### `relation type`

- `extends`
- `references`
- `shares_topic`
- `same_method_family`
