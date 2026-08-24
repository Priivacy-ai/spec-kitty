# Tracer: Tooling Friction

No friction encountered during spec authoring. `gh issue view 3701 --repo Priivacy-ai/spec-kitty --json title,body,comments` returned cleanly once `GITHUB_TOKEN` was unset (as instructed by the mission brief); the mission scaffold (`meta.json`, stub `spec.md`, `checklists/`, `research/`, `tasks/`, `status.events.jsonl`) was already present and correctly pointed at `fix/mission-types-empty-action-sequence-3701`; `.venv/bin/spec-kitty spec-commit --help` resolved without needing a fallback lookup.

## R4 round-2 fixer (2026-08-24)

`spec-kitty safe-commit` failed on its first invocation with "Missing argument 'FILES...'" when
called with only `-m` — it requires explicit positional `FILES...` arguments plus (soon,
becoming mandatory in v3.3) `--to-branch`. Not a defect, just worth flagging: the command's
`--help` text should make the required-soon `--to-branch` more prominent given it is currently
optional-with-deprecation-warning. Retried with the file path and `--to-branch
fix/mission-types-empty-action-sequence-3701` explicit and it succeeded.
