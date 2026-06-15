---
work_package_id: WP04
title: Route remaining lanes/ worktree-dir sites through the seam
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-005
- FR-009
tracker_refs: []
planning_base_branch: mission/mission-identity-seam-and-1908-panel
merge_target_branch: mission/mission-identity-seam-and-1908-panel
branch_strategy: Planning artifacts for this mission were generated on mission/mission-identity-seam-and-1908-panel. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/mission-identity-seam-and-1908-panel unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
phase: Phase 2 - Route call sites
assignee: ''
agent: claude
shell_pid: '1073121'
history:
- at: '2026-06-15T17:53:20Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/
create_intent:
- tests/lanes/test_lanes_worktree_routing.py
execution_mode: code_change
owned_files:
- src/specify_cli/lanes/merge.py
- src/specify_cli/lanes/recovery.py
- src/specify_cli/lanes/lifecycle_sync.py
- src/specify_cli/lanes/implement_support.py
- tests/lanes/test_lanes_worktree_routing.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Route remaining lanes/ worktree-dir sites

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, claude).

---

## Objectives & Success Criteria
Route the worktree-dir name-guesses in the other `lanes/` modules through WP01's `worktree_path()`
so the seam is the only authority. Read [spec.md](../spec.md) FR-005/FR-001, paula F-1.

**Done when:** each site emits byte-identical names via the seam; targeted tests green; no other
`lanes/` module (besides WP03's allocator) re-guesses a worktree name.

## Context & Constraints
- **Depends on WP01.** TDD-first. Only the 4 named files + the new test. **Do NOT** touch
  `worktree_allocator.py` (WP03 owns it). Emit byte-identical names (no on-disk churn).
- **CRITICAL byte-identical rule (squad):** today's sites are `f"{mission_slug}-{lane_id}"` (no mid8).
  Route as `worktree_path(..., mission_id=None, lane_id=…)` so WP01's legacy-faithful grammar
  reproduces them EXACTLY. Do **NOT** introduce `mission_id` where the old f-string lacked it. Assert
  each routed site against WP01's shared golden-value table.

## Subtasks
### T016 [P] — `lanes/merge.py:83`
Replace the `.worktrees/...` worktree-dir f-string with `worktree_path(...)` (pass the same
`mission_slug`, `mission_id`, `lane_id` already in scope).

### T017 [P] — `lanes/recovery.py:392/593/608`
Route all three worktree-dir constructions through `worktree_path(...)`.

### T018 [P] — `lanes/lifecycle_sync.py:150/157`
Route both worktree-dir constructions through `worktree_path(...)`.

### T019 [P] — `lanes/implement_support.py:120`
Route the `context_name`/worktree-dir construction through the seam (`worktree_dir_name(...)` if a
bare name is needed, `worktree_path(...)` if a path).

### T020 — Tests + gates
Create `tests/lanes/test_lanes_worktree_routing.py` asserting each routed site yields the
byte-identical name for an embedded slug. `ruff`+`mypy`; `PWHEADLESS=1 pytest tests/lanes/ -q`.
- [ ] all 4 files routed; [ ] byte-identical names; [ ] `git grep -nE '\.worktrees/.*f"' src/specify_cli/lanes/{merge,recovery,lifecycle_sync,implement_support}.py` → 0; [ ] ruff/mypy clean.

## Branch Strategy
Planning base / merge target: `mission/mission-identity-seam-and-1908-panel`; lane-per-WP.

## Definition of Done
All 4 sites routed through the seam; byte-identical names verified; tests green.

## Reviewer Guidance
Confirm no remaining worktree name-guess f-strings in these 4 files, names unchanged, allocator
untouched.
