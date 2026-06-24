---
work_package_id: WP08
title: Relocate planning-commit residue to commit_router + repoint tasks.py
dependencies:
- WP07
requirement_refs:
- FR-007
- C-002
- NFR-005
tracker_refs: []
planning_base_branch: prog/2056-mission
merge_target_branch: prog/2056-mission
branch_strategy: Planning artifacts for this mission were generated on prog/2056-mission. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2056-mission unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-decompose-mission-god-module-01KVXHF8
base_commit: cc74304cd7f3ac2d26cc05c3904ff69feb19f276
created_at: '2026-06-24T19:52:40.998893+00:00'
subtasks:
- T032
- T033
- T034
- T035
- T036
phase: Phase 4 - Commit-pipeline consolidation
assignee: ''
agent: "claude:opus:randy-reducer:implementer"
shell_pid: "3596104"
history:
- timestamp: '2026-06-24T19:52:40Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/coordination/commit_router.py
create_intent:
- tests/specify_cli/coordination/test_commit_router_planning_residue.py
execution_mode: code_change
owned_files:
- src/specify_cli/coordination/commit_router.py
- tests/specify_cli/coordination/test_commit_router_planning_residue.py
tags: []
---

# Work Package Prompt: WP08 – Relocate planning-commit residue to commit_router + repoint tasks.py

## Do This First

1. Confirm WP07 merged; golden test green.
2. ⚠️ CRITICAL — read research.md §0/§3/§6 (O-1, O-2) and spec.md "Critical base-version constraint".
   On THIS base (`origin/main` `c3814ec5a`, which does NOT include #2058):
   - `tasks.py` STILL imports + calls `_planning_commit_worktree` (`tasks.py:3928`/`:3936`) and imports
     `_resolve_planning_placement` (`tasks.py:3704`). These symbols are **LIVE**.
   - Therefore: **RELOCATE them — DO NOT DELETE as dead code.**
3. `commit_router.py` already has a near-duplicate `_stage_artifacts_in_coord_worktree`
   (`commit_router.py:366`, whose docstring names the mission.py `_stage_finalize_artifacts_in_coord_worktree`
   as its mirror). Reconcile — do not fork a second copy (O-2).

## Objective

Complete the commit-pipeline consolidation that mission 01KVMBD6 started: relocate the LIVE planning-commit
residue into the canonical `coordination/commit_router.py` and repoint `tasks.py`'s import.

## Implementation

### T032 — Relocate the residue
Move `_planning_commit_worktree`, `_resolve_planning_placement`, and their helper
`_stage_finalize_artifacts_in_coord_worktree` from `mission.py` into `coordination/commit_router.py`.
(`_safe_load_meta` already lives in the resolution seam from WP02 — import it, do not duplicate.)

### T033 — Reconcile the staging helper
Reconcile `_stage_finalize_artifacts_in_coord_worktree` against the existing
`_stage_artifacts_in_coord_worktree` in commit_router: collapse the near-duplicate into a single helper
(preserve the "skip coord-owned status files" behavior that the finalize variant adds). Do NOT fork.

### T034 — Repoint tasks.py
Update `tasks.py`'s function-local import (currently `from specify_cli.cli.commands.agent.mission import
_planning_commit_worktree` at line ~3928, and `_resolve_planning_placement` at ~3704) to import from
`specify_cli.coordination.commit_router`. Single out-of-map line edit per import — documented below.

### T035 — One-way imports
Confirm `commit_router` does NOT import from `mission`/seams (INV-8); keep `commit_for_mission` /
`CoordinationWorkspace` imports lazy (NFR-005).

### T036 — Tests + gates
Author `test_commit_router_planning_residue.py` covering the relocated functions + the reconciled staging
helper; run `tests/tasks/`, `tests/specify_cli/coordination/test_commit_router*.py`,
`test_write_surface_coherence.py`; ruff + mypy --strict clean. `grep` confirms the symbols are defined in
commit_router and tasks.py imports them from there.

## Acceptance

- `_planning_commit_worktree` / `_resolve_planning_placement` /
  `_stage_finalize_artifacts_in_coord_worktree` live in `commit_router.py`; the staging duplication is
  collapsed; `tasks.py` imports them from commit_router; tasks suite + write-surface coherence green.
- These symbols were RELOCATED, never deleted (they are LIVE on this base).

## Out-of-map edits

- `src/specify_cli/cli/commands/agent/tasks.py`: the two function-local import lines for
  `_planning_commit_worktree` / `_resolve_planning_placement`, repointed to `coordination.commit_router`.
- `src/specify_cli/cli/commands/agent/mission.py`: removal of the now-relocated defs (final shim reduction
  is WP09, which solely owns `mission.py`; this WP removes only these relocated symbols' definitions).

## Activity Log

- 2026-06-24T23:24:00Z – claude:opus:randy-reducer:implementer – shell_pid=3596104 – Assigned agent via action command
- 2026-06-24T23:46:11Z – claude:opus:randy-reducer:implementer – shell_pid=3596104 – Moved to for_review
- 2026-06-24T23:46:14Z – user – shell_pid=3596104 – Moved to approved
