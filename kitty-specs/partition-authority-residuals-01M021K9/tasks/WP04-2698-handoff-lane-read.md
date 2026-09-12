---
work_package_id: WP04
title: '#2698 review handoff shows real per-WP lane on coord missions'
dependencies: []
requirement_refs:
- FR-006
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
authoritative_surface: src/specify_cli/core/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/core/worktree_topology.py
- src/specify_cli/status/lane_reader.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP04 – #2698 review handoff shows real per-WP lane on coord missions

**Concern**: IC-04 · **Requirements**: FR-006 · **Priority**: P2

## Purpose
The review handoff reads the per-WP lane (a STATUS_STATE/COORD kind) off the PRIMARY LANE_STATE dir, so every WP on a coord mission renders stale `planned`. (Cited fix PR #2766 was closed, never merged.)

## Files / changes
- `core/worktree_topology.py:147-149/207` — resolve the per-WP lane via the coord-aware STATUS_STATE surface; keep the PRIMARY dir for identity/lanes/tasks.
- `status/lane_reader.py:51-76` — the lane read consumed here.

## Coordination & guardrails
Manifests only on multi-WP coord missions with stacking — build one in the e2e. Ref pattern `tasks_dependency_graph.py:120-135`.

## Definition of Done
- **Red-first**: author the failing test first (see `tasks.md` T001 for this WP) and show it red before the fix.
- **Scope A**: a live coord-topology e2e (NFR-001) that is red-before/green-after, with the coord worktree registered.
- Non-coord control asserts identical behavior where applicable.
- No predicate fork / no new legacy resolver path (C-001); STATUS reads stay COORD (C-002).
- `ruff` + `mypy` clean; complexity ≤15; new helpers/branches have focused tests.
- See `tasks.md` for the full subtask breakdown and the universal DoD.
