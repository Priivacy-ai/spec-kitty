---
work_package_id: WP03
title: '#2939 move-task leaves a clean tree after a rejected review'
dependencies: []
requirement_refs:
- FR-007
planning_base_branch: fix/partition-authority-residuals
merge_target_branch: fix/partition-authority-residuals
branch_strategy: Planning artifacts for this mission were generated on fix/partition-authority-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/partition-authority-residuals unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Scope A (partition)
history:
- timestamp: '2026-08-15T00:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_move_task.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP03 – #2939 move-task leaves a clean tree after a rejected review

**Concern**: IC-03 · **Requirements**: FR-007 · **Priority**: P2

## Purpose
After a rejected-review transition the post-transition `InnerStateChanged` annotation is written+materialized but never committed, leaving the status tree dirty.

## Files / changes
- `tasks_move_task.py:2190-2318` — gather the annotation into the same bookkeeping transaction (or a second atomic status commit).
- `status/emit.py:971-1041` (`emit_inner_state_changed`) — DO NOT edit; it stays generic. The fix is caller-side.

## Coordination & guardrails
Shares `emit_inner_state_changed` as a dependency with WP01 (neither edits it). Cover the non-rejection `→for_review` path when a note/agent annotation rides along.

## Definition of Done
- **Red-first**: author the failing test first (see `tasks.md` T001 for this WP) and show it red before the fix.
- **Scope A**: a live coord-topology e2e (NFR-001) that is red-before/green-after, with the coord worktree registered.
- Non-coord control asserts identical behavior where applicable.
- No predicate fork / no new legacy resolver path (C-001); STATUS reads stay COORD (C-002).
- `ruff` + `mypy` clean; complexity ≤15; new helpers/branches have focused tests.
- See `tasks.md` for the full subtask breakdown and the universal DoD.
