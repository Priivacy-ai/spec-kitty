---
work_package_id: WP05
title: Migrate merge+lanes cluster to the read seam
dependencies:
- WP02
requirement_refs:
- FR-002
- NFR-002
planning_base_branch: fix/read-side-placement-seam-migration
merge_target_branch: fix/read-side-placement-seam-migration
branch_strategy: Planning artifacts for this mission were generated on fix/read-side-placement-seam-migration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/read-side-placement-seam-migration unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
phase: Phase 3 - Migrate
history:
- at: '2026-07-27T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/
create_intent:
- tests/specify_cli/merge/test_read_seam_migration_merge_lanes.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/merge/**
- src/specify_cli/lanes/**
- tests/specify_cli/merge/test_read_seam_migration_merge_lanes.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – Migrate merge+lanes cluster

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` to load `python-pedro` (implementer, claude).

## Objective
Apply the **shared migration procedure** ([tasks.md](../tasks.md)) per the WP02 ledger to `src/specify_cli/merge/**` (`done_bookkeeping.py`, `executor.py`, `forecast.py`, `ordering.py`, `resolve.py`) + `src/specify_cli/lanes/**` (`lifecycle_sync.py`, `merge.py`, `recovery.py`, `worktree_allocator.py`). `merge/executor.py` (~6 sites) is the hot spot — the birth-cutover seam (Mission E) also lives here, so read the current file carefully.

## Subtasks
### T011 — Migrate per ledger (as WP03 T007).
### T012 — Behavior-preservation tests: `tests/specify_cli/merge/test_read_seam_migration_merge_lanes.py`.

## Gates
`PWHEADLESS=1 uv run pytest tests/specify_cli/merge/ tests/specify_cli/lanes/ -q`; `ruff`; `mypy` project-mode.

## DoD / Review
Owned bypass sites resolved per ledger; healthy-case identical. Finish: commit, `mark-status T011 T012 --status done`, `move-task WP05 --to for_review`.
