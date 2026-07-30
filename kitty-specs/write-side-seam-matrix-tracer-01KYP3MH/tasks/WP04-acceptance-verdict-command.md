---
work_package_id: WP04
title: Acceptance verdict command + persist-on-accept
dependencies:
- WP03
requirement_refs:
- FR-001
- FR-002
- NFR-001
- NFR-003
planning_base_branch: feat/write-side-seam-matrix-tracer
merge_target_branch: feat/write-side-seam-matrix-tracer
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-seam-matrix-tracer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-seam-matrix-tracer unless the human explicitly redirects the landing branch.
created_at: '2026-07-29T09:24:15+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
history:
- at: '2026-07-29T09:24:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/acceptance/
create_intent:
- src/specify_cli/cli/commands/agent/acceptance_verdict.py
- tests/specify_cli/acceptance/test_acceptance_verdict_command.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/acceptance/matrix.py
- src/specify_cli/acceptance/gates_core.py
- src/specify_cli/acceptance/post_consolidation.py
- src/specify_cli/cli/commands/accept.py
- src/specify_cli/cli/commands/migrate/backfill_provenance.py
- src/specify_cli/cli/commands/agent/acceptance_verdict.py
- tests/specify_cli/acceptance/test_acceptance_verdict_command.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '2318'
- '2743'
---

# Work Package Prompt: WP04 – Acceptance verdict command + persist-on-accept

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objective

Ship a deterministic `acceptance-verdict` command that **fronts** `write_acceptance_matrix` through the write-seam helper (WP03) and keeps the **computed** `overall_verdict` authoritative; and fix the live bug where canonical acceptance leaves a stale `overall_verdict: pending` after an all-pass accept (#2318 + comment 5102989064). Home the **acceptance half** of the FR-002 structured schema here.

## Context

- `write_acceptance_matrix(feature_dir, matrix)` already exists (`acceptance/matrix.py:259`); `overall_verdict` is a **computed `@property`** and `from_dict` excludes it — it **cannot** drift and MUST NOT be hand-stored (#2743 negative-invariant integrity). The command *materializes + routes* — it does not re-author verdict semantics.
- **The bug (#2318 comment):** `_evaluate_acceptance_matrix()` only writes on negative invariants → after an all-pass/no-negative-invariant accept the persisted `overall_verdict` stays stale `pending`, misleading PR/readiness tooling.
- Acceptance-matrix is COORD-partitioned; caller-resolved-`feature_dir` writers strand it on the wrong surface unless routed through `write_target(ACCEPTANCE_MATRIX)`.

## Subtasks

### T014 — Acceptance schema half
In `acceptance/matrix.py`, formalize the structured acceptance schema (per-requirement/DoD verdicts + accepted statuses). Confirm `overall_verdict` remains a computed property; add a test that `from_dict` round-trips without a stored `overall_verdict`.

### T015 — `acceptance-verdict` command
Create `cli/commands/agent/acceptance_verdict.py`: `--mission <handle> --criterion FR-00X --result pass|fail|... --verification-method ... --actor ... --json`. It updates the row deterministically via the WP03 helper (`write_target(ACCEPTANCE_MATRIX)`), recomputes derived fields, preserves negative-invariant provenance, and never stores the verdict. Idempotent + structured `--json` output (FR-012).

### T016 — Persist-on-accept (bug fix)
Fix `_evaluate_acceptance_matrix` (and the accept path in `cli/commands/accept.py`) to persist the **recomputed** `overall_verdict` on canonical acceptance **even with no negative invariants** — so an all-pass mission persists `overall_verdict: pass`. Red-first regression before the fix.

### T017 — Route the acceptance-matrix callers
Route the caller-resolved-`feature_dir` `write_acceptance_matrix` callers through the WP03 helper: `acceptance/gates_core.py:492`, `acceptance/post_consolidation.py:275`, `cli/commands/accept.py`, `cli/commands/migrate/backfill_provenance.py:109`. No hand-derived destinations; no second resolver.

### T018 — Tests
`tests/specify_cli/acceptance/test_acceptance_verdict_command.py`: verdict determinism with zero product-source reads (NFR-001); all-pass accept persists `pass` (#2318 regression); re-run is a no-op; a caller writes to the COORD surface (not a stranded primary dir).

## Branch Strategy

Both planning and merge target are `feat/write-side-seam-matrix-tracer`. Allocate via `/spec-kitty.implement WP04` (depends on WP03).

## Definition of Done
- Command + persist-on-accept fix land; all four callers routed via the helper.
- `overall_verdict` never hand-stored; provenance preserved.
- `ruff`/`mypy` clean; complexity ≤ 15; tests green.

## Risks / Reviewer guidance
- **Never** store `overall_verdict` — assert it stays a computed property.
- Confirm the persist-on-accept fix triggers on the all-pass/no-negative-invariant branch specifically (the previously-uncovered path).
- **Commit each slice** (schema, command, bug-fix, caller routing) so worktree progress is durable.
