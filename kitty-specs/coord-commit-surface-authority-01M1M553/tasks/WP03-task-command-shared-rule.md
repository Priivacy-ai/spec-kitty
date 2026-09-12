---
work_package_id: WP03
title: Task-command shared-rule consultation (#2300)
dependencies:
- WP01
requirement_refs:
- FR-005
planning_base_branch: fix/coord-commit-surface-authority
merge_target_branch: fix/coord-commit-surface-authority
branch_strategy: Planning artifacts for this mission were generated on fix/coord-commit-surface-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/coord-commit-surface-authority unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
history:
- at: '2026-09-03T00:00:00+00:00'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/specify_cli/cli/commands/agent/test_tasks_surface_authority.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_shared.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- src/specify_cli/cli/commands/agent/tasks_map_requirements.py
- src/specify_cli/cli/commands/agent/tasks_mark_status.py
- tests/specify_cli/cli/commands/agent/test_tasks_surface_authority.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`); apply and state. Stay within `owned_files`.

## Objective

Make the commit-bearing task commands consult ONE shared kind-aware rule instead of hardcoding divergent verdicts. `move-task` (lifecycle-kind) keeps RouteToCoord/exit-0; `map-requirements` (planning-kind) keeps Refuse/exit-1 — both now DERIVED from `resolve_surface_authority`, not hardcoded. `mark-status` is frozen event-log-only (no commit).

**CRITICAL (squad-adjudicated from source)**: `mark-status`'s `_ms_commit` is DEAD (only reachable via the `tasks.py:814` compat re-export + two unit tests; `_do_mark_status` never calls it). Do **NOT** revive a commit path on mark-status — that would undo the #2816 event-sourcing cutover. And do **NOT** force move-task to refuse: its skip is CORRECT coord deferral (the coord status transition is authoritative). This WP changes *how the verdict is derived*, preserving observable behavior.

Read first: [contracts/authoritative-surface.md](../contracts/authoritative-surface.md) §2 + ledger, [research.md](../research.md) D-003, [plan.md](../plan.md) DD-1. **Depends on WP01.** Run WP01's golden harness BEFORE touching code.

## Subtasks

### T009 — Collapse the two shell helpers into the shared rule
`tasks_shared.py`: replace the bodies of `_skip_target_branch_commit` (`:353-373`) and `_protected_branch_status_commit_error` (`:317-330`) so they delegate to `resolve_surface_authority` (passing the correct `artifact_kind`). Keep their existing signatures/callsites stable (thin adapters over the shared verdict) to avoid churn in callers. The verdict → (skip / refuse / route) mapping lives in one place now.

### T010 — Wire move-task (lifecycle-kind)
`tasks_move_task.py:388-414`: the WP-file is a lifecycle/coordination-kind artifact under coord. The RouteToCoord verdict must yield the SAME observable result as today's skip (exit 0, coord commit authoritative). Confirm via the frozen golden — this subtask is a derivation refactor, NOT a behavior change.

### T011 — Wire map-requirements (planning-kind)
`tasks_map_requirements.py:199-206`: planning-kind on a protected primary → Refuse/exit-1 via the shared verdict; unify the remedy to the shared constant (was a per-command message). Behavior preserved (exit 1); message unified.

### T012 — Freeze mark-status no-commit `[P]`
`tasks_mark_status.py`: add an assertion-level test with a **non-fakeable mechanism** — asserting the *absence* of a commit via exit-code-only is fakeable, so the test MUST: (a) spy that `commit_for_mission` (the seam `_do_mark_status` routes through) is **never invoked**, AND (b) assert `git rev-parse HEAD` is **unchanged** across the call — while confirming the event log WAS written (event-log-only) and exit 0. Optionally correct the stale module docstring (`:19-24`) claiming a refuse-exit-1 commit contract — docstring-only (boy-scout), NO behavior change. Do not touch `_ms_commit` (dead) beyond a comment noting it is compat-shim/test-only.

### T013 — Characterization diff (JSON-mode) `[P]`
Re-run WP01's golden harness (**`tests/coordination/test_surface_authority_goldens.py`**) through the three commands AFTER wiring, asserting JSON-mode exit codes; add a mission-specific `tests/specify_cli/cli/commands/agent/test_tasks_surface_authority.py` for the CLI-level diffs. Add genuine-no-op→exit-0 rows for move-task and map-requirements (typed reason). Prove: same `{kind,topology,protection}` → same verdict via the shared rule; wrong-surface → Refuse (exit 1) not collapsed to exit 0.

## Branch Strategy
Base/merge: `fix/coord-commit-surface-authority`. One lane; worktree from `lanes.json`.

## Definition of Done
- move-task & map-requirements derive their verdict from `resolve_surface_authority`; observable behavior preserved (goldens green before AND after).
- mark-status proven event-log-only no-commit; `_ms_commit` NOT revived.
- New characterization tests assert JSON-mode exit codes incl. no-op→exit-0 and wrong-surface→exit-1.
- `ruff`/`mypy` clean, no suppressions.

## Reviewer Guidance
- Confirm NO new commit path on mark-status (grep `_ms_commit` callers unchanged; `_do_mark_status` flow unchanged).
- Confirm move-task still exits 0 (RouteToCoord) — a refuse here is a regression.
- Confirm the remedy string is a shared constant (not per-command drift).
