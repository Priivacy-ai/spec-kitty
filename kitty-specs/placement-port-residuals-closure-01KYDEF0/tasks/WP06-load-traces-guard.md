---
work_package_id: WP06
title: _load_traces best-effort guard
dependencies: []
requirement_refs:
- FR-006
planning_base_branch: placement-port-residuals
merge_target_branch: placement-port-residuals
branch_strategy: Planning artifacts for this mission were generated on placement-port-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into placement-port-residuals unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-placement-port-residuals-closure-01KYDEF0
base_commit: 29d1ee7c91356d9dd6e038a3bb23d538850b09e6
created_at: '2026-07-26T20:47:29.959441+00:00'
subtasks:
- T024
- T025
- T026
history:
- at: '2026-07-25T21:12:34Z'
  actor: tasks
  note: WP created from IC-07 (FR-006)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/retrospective/
create_intent:
- tests/specify_cli/retrospective/test_load_traces_deleted_coord.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/retrospective/generator.py
- tests/specify_cli/retrospective/test_load_traces_deleted_coord.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before reading anything else**, load `python-pedro` (role `implementer`) via `/ad-hoc-profile-load`;
adopt its directives/tactics and state which you applied. Then proceed.

## Objective

Make a deleted-coord retrospective degrade to `[]` traces instead of crashing (FR-006), preserving
`_load_traces`' documented best-effort contract. Single call site (C-003) — do NOT expand into #2922's read-side set.

Read first: `spec.md` (FR-006, C-003, Edge Cases), `contracts/degrade-and-read-hygiene.md` (C-READ-1).

## Context

- `retrospective/generator.py::_load_traces` (`:224-273`) calls `placement_seam(...).read_dir(TRACER_FILE)`
  at `:251` **unwrapped**. Per-file reads are guarded (`except (OSError, UnicodeDecodeError)` at `:264`), but
  nothing catches an exception from `read_dir` itself.
- `read_dir` for a COORD kind (`TRACER_FILE`) can raise `CoordinationBranchDeleted`
  (`coordination/surface_resolver.py:181`, subclass of `StatusReadPathNotFound`) when the coord branch is deleted.
- `_load_traces` is best-effort (returns `[]` on missing/unreadable). It is the ONLY `read_dir`/`placement_seam`
  in the module (paula-confirmed) — greening it does not touch #2922.

## Subtasks

### T024 — Red-first
In `tests/specify_cli/retrospective/test_load_traces_deleted_coord.py`, drive `generate_retrospective(...)` on a
coord mission whose `meta.json` declares a `coordination_branch` that no longer exists in git; assert it raises
`CoordinationBranchDeleted` today (crash instead of degrade). Confirm RED.

### T025 — Guard the read
Wrap the `read_dir(TRACER_FILE)` call in `except (CoordinationBranchDeleted, StatusReadPathNotFound): return []`
(the deleted-coord family). Do NOT widen to bare `Exception` — genuinely unexpected errors stay loud (Edge Case).

### T026 — Verify
Red-first test green (returns without raising, `[]` traces, retrospective completes). Confirm the except set is
exactly the deleted-coord family and the call site count is unchanged (still one). `ruff` + `mypy --strict` clean;
`PWHEADLESS=1 pytest tests/specify_cli/retrospective/ -q`.

## Branch Strategy
Planning base / merge target `placement-port-residuals`. Worktree per `lanes.json` via
`spec-kitty agent action implement WP06 --agent claude`. Lane C (independent).

## Definition of Done
- [ ] Deleted-coord `generate_retrospective` degrades to `[]` (RED→GREEN).
- [ ] `except (CoordinationBranchDeleted, StatusReadPathNotFound)` only — no bare `Exception`.
- [ ] Single call site preserved (C-003); ruff/mypy clean.

## Risks / reviewer guidance
- Widening the except to bare `Exception` would swallow real errors — reject.
- Reviewer: confirm the guard is scoped to the one call site and does not touch other read surfaces (#2922).
