# Conventions

## Names

- Project name: `Research Foundry`
- Skill folders: phase names only
- Scripts: `flow_<phase>_<action>.py`
- Artifact files: lowercase, dash-delimited, documented in `docs/data-models.md`

## Slugs

- Convert titles to lowercase
- Transliterate to ASCII where possible
- Replace non-alphanumeric spans with a single dash
- Trim leading and trailing dashes
- Limit to 80 characters

## Timestamps

- Use UTC for machine timestamps
- Preferred format: `YYYY-MM-DDTHH:MM:SSZ`
- Run directory suffix: `YYYYMMDDTHHMMSSZ`

## Paths

- Stable outputs go to `runtime/artifacts/`
- Per-run working files go to `runtime/runs/<run_id>/`
- Cache and logs stay under `runtime/cache/` and `runtime/logs/`

## States

Valid paper lifecycle states:

- `discovered`
- `triaged`
- `dossier_ready`
- `linked`
- `registered`

Do not invent synonyms in scripts or documentation.
