---
work_package_id: WP07
title: Merge Engine v2 — Workspace and State
lane: planned
dependencies:
- WP02
requirement_refs:
- FR-012
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
- T036
- T037
- T038
phase: Phase C - Merge
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-27T17:23:39Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – Merge Engine v2 — Workspace and State

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`

---

## Objectives & Success Criteria

- Dedicated merge worktree created at `.kittify/runtime/merge/<mission_id>/workspace/`.
- MergeState persisted at `.kittify/runtime/merge/<mission_id>/state.json` with per-mission scoping.
- Old merge executor, forecast, and status_resolver are deleted.
- Preflight simplified to use MissionContext.
- Main repo's checked-out branch is never changed by merge operations.

## Context & Constraints

- **Spec**: FR-012 (dedicated merge workspace), FR-013 (resumable state)
- **Plan**: Move 4 — Merge Engine v2 section
- **Key files to delete**: `executor.py` (~450 lines), `forecast.py` (~200 lines), `status_resolver.py` (~150 lines)
- **Key file to rewrite**: `state.py` — new location, per-mission scoping
- **Depends on**: WP02 (context tokens), WP05 (canonical state)

## Subtasks & Detailed Guidance

### Subtask T034 – Create merge/workspace.py

- **Purpose**: Dedicated merge worktree lifecycle management.
- **Steps**:
  1. Create `src/specify_cli/merge/workspace.py`
  2. Implement `create_merge_workspace(mission_id: str, target_branch: str, repo_root: Path) -> Path`:
     - Workspace path: `.kittify/runtime/merge/<mission_id>/workspace/`
     - Create directories if not exist
     - Run `git worktree add <workspace_path> <target_branch>` from repo root
     - Return workspace path
  3. Implement `cleanup_merge_workspace(mission_id: str, repo_root: Path) -> None`:
     - Run `git worktree remove <workspace_path>` (force if needed)
     - Remove `.kittify/runtime/merge/<mission_id>/` directory
  4. Implement `get_merge_workspace(mission_id: str, repo_root: Path) -> Path | None`:
     - Check if workspace exists and is valid git worktree
     - Return path or None
- **Files**: `src/specify_cli/merge/workspace.py` (new, ~70 lines)

### Subtask T035 – Rewrite merge/state.py

- **Purpose**: Per-mission merge state at the new runtime location.
- **Steps**:
  1. Rewrite `src/specify_cli/merge/state.py`
  2. Update `MergeState` dataclass to include `mission_id` and `workspace_path`
  3. Update `save_state()`: write to `.kittify/runtime/merge/<mission_id>/state.json`
  4. Update `load_state()`: read from new location
  5. Update `clear_state()`: remove state file
  6. Update `has_active_merge()`: check for state at new location
  7. Add lock file support:
     - `acquire_merge_lock(mission_id, repo_root)` → creates `.kittify/runtime/merge/<mid>/lock`
     - `release_merge_lock(mission_id, repo_root)` → removes lock
     - `is_merge_locked(mission_id, repo_root)` → checks lock existence
  8. Remove all references to old `.kittify/merge-state.json` location
- **Files**: `src/specify_cli/merge/state.py` (rewrite, ~100 lines)
- **Parallel?**: Yes — can proceed alongside T034

### Subtask T036 – Simplify merge/preflight.py

- **Purpose**: Use MissionContext instead of heuristic feature detection.
- **Steps**:
  1. Read `src/specify_cli/merge/preflight.py` (~276 lines)
  2. Update `run_preflight()` to accept `MissionContext` instead of loose parameters
  3. Remove any `detect_feature()` calls
  4. Simplify WP discovery: get WP list from MissionContext or from event log snapshot
  5. Keep cleanliness checks and divergence checks — those are still needed
- **Files**: `src/specify_cli/merge/preflight.py` (modify, ~30 lines changed)

### Subtask T037 – Delete executor.py, forecast.py, status_resolver.py

- **Purpose**: Remove the old merge implementation.
- **Steps**:
  1. Delete `src/specify_cli/merge/executor.py` (~450 lines)
  2. Delete `src/specify_cli/merge/forecast.py` (~200 lines)
  3. Delete `src/specify_cli/merge/status_resolver.py` (~150 lines)
  4. Remove from `src/specify_cli/merge/__init__.py` exports
  5. Remove all imports of deleted modules across the codebase
  6. Keep `ordering.py` — dependency-based ordering is still needed
- **Files**: Delete 3 files, update exports
- **Parallel?**: Yes — independent of T034-T036

### Subtask T038 – Tests for merge workspace and state

- **Purpose**: Verify workspace creation, state persistence, lock management.
- **Steps**:
  1. Update tests in `tests/specify_cli/merge/`
  2. Test workspace creation: directory exists, is valid git worktree, target branch checked out
  3. Test workspace cleanup: directory removed, git worktree removed
  4. Test state save/load at new location: per-mission scoping works
  5. Test lock: acquire/release/check cycle
  6. Test: main repo checkout unchanged after workspace creation
  7. Delete tests for executor.py, forecast.py, status_resolver.py
- **Files**: `tests/specify_cli/merge/` (modify + delete, ~120 lines changed)
- **Parallel?**: Yes

## Risks & Mitigations

- **Git worktree under .kittify/**: Some git configurations may have issues with worktrees inside gitignored directories. Test across platforms.
- **Orphan worktrees**: If cleanup fails, stale worktrees accumulate. Add a `spec-kitty merge --cleanup` command for manual recovery.

## Review Guidance

- Verify merge workspace is at `.kittify/runtime/merge/<mid>/workspace/`, NOT under `.worktrees/`
- Verify old executor.py is fully deleted
- Verify preflight uses MissionContext, not detect_feature()
- Verify lock file prevents concurrent merges

## Activity Log

- 2026-03-27T17:23:39Z – system – lane=planned – Prompt created.
