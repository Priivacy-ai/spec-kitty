---
work_package_id: WP02
title: '#3439 merge gates read real PRIMARY data on coord missions'
dependencies: []
requirement_refs:
- FR-003
- FR-004
- FR-005
planning_base_branch: fix/partition-authority-residuals
merge_target_branch: fix/partition-authority-residuals
branch_strategy: Planning artifacts for this mission were generated on fix/partition-authority-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/partition-authority-residuals unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Scope A (partition)
history:
- timestamp: '2026-08-15T00:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/policy/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/policy/merge_gates.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/cli/commands/agent/tasks_dependency_graph.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 – #3439 merge gates read real PRIMARY data on coord missions

**Concern**: IC-02 · **Requirements**: FR-003, FR-004, FR-005 · **Priority**: P1

## Purpose
On coord missions the risk gate silently SKIPs and the dependency gate sees an empty graph because they read `lanes.json`/`tasks/` off the coord husk. Fix per-leg and lift the C-009 pin.

## Files / changes
- `policy/merge_gates.py:86/194/242` — thread `repo_root`+`mission_slug` into `_evaluate_risk_gate`/`_evaluate_dependency_gate`; resolve LANE_STATE / WORK_PACKAGE_TASK via the seam; keep the STATUS_STATE event read on coord (C-002).
- `cli/commands/agent/workflow.py:202` — bulk-edit diff base resolves `lanes.json` via the seam (no silent `target_branch` fallback).
- `cli/commands/agent/tasks_dependency_graph.py:132` — remove the C-009 deferral note.

## Coordination & guardrails
Same merge-preflight seam as WP01 (different files). One shared coord-merge e2e can assert a fired risk gate AND an honored override. Do NOT over-correct STATUS_STATE reads to PRIMARY.

## Definition of Done
- **Red-first**: author the failing test first (see `tasks.md` T001 for this WP) and show it red before the fix.
- **Scope A**: a live coord-topology e2e (NFR-001) that is red-before/green-after, with the coord worktree registered.
- Non-coord control asserts identical behavior where applicable.
- No predicate fork / no new legacy resolver path (C-001); STATUS reads stay COORD (C-002).
- `ruff` + `mypy` clean; complexity ≤15; new helpers/branches have focused tests.
- See `tasks.md` for the full subtask breakdown and the universal DoD.
