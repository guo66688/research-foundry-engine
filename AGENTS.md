# AGENTS

## Project Goal

Research Foundry is a research workflow system for paper discovery, triage, evidence capture, synthesis, and registry maintenance. Treat the repository as a pipeline product, not a loose bag of actions.

## Naming Principles

- Prefer neutral, professional names.
- Keep phase names aligned with the pipeline: intake, triage, dossier, synthesis, registry.
- Use `flow_<phase>_<action>.py` for scripts.
- Use stable artifact names documented in `docs/data-models.md`.

## Reference Hygiene

- Do not preserve expression-layer content from any reference repository.
- Do not reintroduce legacy names, path conventions, prompt phrasing, or config field names.
- All new copy must be written from scratch, not lightly paraphrased.

## Change Discipline

- When scripts change, provide at least one verification command.
- Do not run `git commit` unless explicitly asked.
- Do not run `git push` unless explicitly asked.
- Keep documentation and code changes aligned in the same turn.

## Skill Discipline

- Before adding a new skill, check whether the work fits an existing phase.
- Prefer instruction-heavy skills first; add scripts only when deterministic behavior or reuse justifies them.
- Each skill must state when it should trigger and when it should not trigger.
- Each skill must define its inputs, outputs, limits, and failure path.

## Data Contracts

- Treat `docs/data-models.md` as the source of truth for IDs, states, and JSON shape.
- Do not invent new artifact names or state values without updating that document.
- Keep status transitions consistent across scripts and skills.

## Validation

- Use `python -m compileall scripts` after script edits.
- When a script has a dedicated CLI path, include a concrete example command in the final report.
