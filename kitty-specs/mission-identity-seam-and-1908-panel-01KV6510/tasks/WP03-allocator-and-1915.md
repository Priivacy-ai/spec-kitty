---
work_package_id: WP03
title: 'Worktree allocator routing + #1915 lane-merge atomicity'
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-005
- FR-006
- FR-009
tracker_refs: []
planning_base_branch: mission/mission-identity-seam-and-1908-panel
merge_target_branch: mission/mission-identity-seam-and-1908-panel
branch_strategy: Planning artifacts for this mission were generated on mission/mission-identity-seam-and-1908-panel. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/mission-identity-seam-and-1908-panel unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
phase: Phase 2 - Route call sites
assignee: ''
agent: claude
shell_pid: '1073121'
history:
- at: '2026-06-15T17:53:20Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/worktree_allocator.py
create_intent:
- tests/lanes/test_worktree_allocator_atomicity.py
execution_mode: code_change
owned_files:
- src/specify_cli/lanes/worktree_allocator.py
- tests/lanes/test_worktree_allocator_atomicity.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Allocator routing + #1915 atomicity

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, claude).

---

## Objectives & Success Criteria
Route the allocator's worktree f-string through the WP01 seam, and make multi-dependency lane
merges atomic (#1915). Read [spec.md](../spec.md) FR-005/FR-006, [research.md](../research.md) R4,
[plan.md](../plan.md) IC-03/IC-04.

**Done when:** the allocator emits byte-identical worktree names via `worktree_path()`; a later-dep
conflict rolls the lane back fully (no orphaned earlier-dep merge commit); tests green.

## Context & Constraints
- **Depends on WP01** (`worktree_path()`/`worktree_dir_name()` + the shared golden-value table). TDD-first. Only this file + its new test.
- `worktree_allocator.py:127` currently does `repo_root/".worktrees"/f"{mission_slug}-{lane.lane_id}"`
  — a name-guess the seam's own L234 comment forbids. Must emit the identical name (no churn).
- **CRITICAL byte-identical rule (squad):** the old f-string has **no mid8** (`{slug}-{lane}`). Route
  as `worktree_path(repo_root, mission_slug, mission_id=None, lane_id=lane.lane_id)` so WP01's
  legacy-faithful grammar reproduces it EXACTLY. Do **NOT** newly pass `mission_id` (that appends
  `-{mid8}` and renames existing worktrees — the divergence the squad flagged). Assert against WP01's
  shared golden-value table, not a self-authored expectation.
- `_merge_dependency_lane_tips` (def L223, callers L136/L176) loops `git merge` over dep lanes;
  `git merge --abort` on a later conflict only undoes the conflicting merge — earlier clean dep
  merges survive (#1915).

## Subtasks
### T012 — Route the worktree f-string (#1899/FR-005)
Replace `worktree_allocator.py:127`'s f-string with
`worktree_path(repo_root, mission_slug, mission_id=mission_id, lane_id=lane.lane_id)`. Confirm the
emitted path is byte-identical to the previous f-string for an embedded slug (no churn).

### T013 — Failing regression (#1915)
Create `tests/lanes/test_worktree_allocator_atomicity.py`: set up a lane with ≥2 dependency lanes
where an earlier dep merges cleanly and a later dep conflicts; assert the lane worktree currently
RETAINS the earlier-dep merge commit after the abort (the bug), then (post-fix) is fully rolled back.

### T014 — Make the multi-dep merge atomic
In `_merge_dependency_lane_tips`, snapshot the lane ref (e.g. record `HEAD` / a pre-merge ref) before
the loop; on ANY dep-merge conflict, `git reset --hard <snapshot>` (and abort) so no partial dep
merge survives. Preserve the existing success path and error reporting.

### T015 — Gates
`ruff`+`mypy`; `PWHEADLESS=1 pytest tests/lanes/ -q` (+ new test).
- [ ] allocator emits identical names via seam (no churn); [ ] later-dep conflict → full rollback; [ ] ruff/mypy clean.

## Branch Strategy
Planning base / merge target: `mission/mission-identity-seam-and-1908-panel`; lane-per-WP.

## Definition of Done
f-string routed through the seam; `_merge_dependency_lane_tips` atomic; both regressions green.

## Reviewer Guidance
Confirm the worktree name is byte-identical (no orphaned worktrees), the rollback is to the exact
pre-loop ref, and the #1915 regression genuinely reproduced the surviving-merge-commit bug.
