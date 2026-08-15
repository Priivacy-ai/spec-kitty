---
work_package_id: WP08
title: '#2696 mission doctors: canonical writer schema + per-mission scoping'
dependencies: []
requirement_refs:
- FR-011
- FR-012
planning_base_branch: fix/partition-authority-residuals
merge_target_branch: fix/partition-authority-residuals
branch_strategy: Planning artifacts for this mission were generated on fix/partition-authority-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/partition-authority-residuals unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 2 - Scope B (fidelity)
history:
- timestamp: '2026-08-15T00:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/audit/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/audit/shape_registry.py
- src/specify_cli/cli/commands/doctor.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP08 – #2696 mission doctors: canonical writer schema + per-mission scoping

**Concern**: IC-07 · **Requirements**: FR-011, FR-012 · **Priority**: P2

## Purpose
`doctor` flags writer-canonical meta.json keys (coordination_branch/topology/flattened/pr_bound) as UNKNOWN_SHAPE (hand-rolled registry drifted); `doctor coordination` can't scope to one mission.

## Files / changes
- `audit/shape_registry.py:31-47` — derive `meta.json` known-keys programmatically from `mission_metadata.py:47-87` TypedDicts + coordination keys; add a regression test asserting every writer key is a known audit key.
- `cli/commands/doctor.py:1258` (`coordination_health`) — add `--mission`, filtering through the same resolver as `mission-state` (`doctor.py:1022`).

## Coordination & guardrails
Scope B (C-007). Findings are INFO — tests must assert specific keys, not just exit codes.

## Definition of Done
- **Red-first**: author the failing test first (see `tasks.md` T001 for this WP) and show it red before the fix.
- **Scope B**: a regression/migration test (NFR-004) that goes red on the defect and green after; topology-agnostic.
- Non-coord control asserts identical behavior where applicable.
- No predicate fork / no new legacy resolver path (C-001); STATUS reads stay COORD (C-002).
- `ruff` + `mypy` clean; complexity ≤15; new helpers/branches have focused tests.
- See `tasks.md` for the full subtask breakdown and the universal DoD.
