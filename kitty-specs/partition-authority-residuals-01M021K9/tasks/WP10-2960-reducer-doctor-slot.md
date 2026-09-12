---
work_package_id: WP10
title: '#2960 status doctor must not report Healthy over blanked runtime slots'
dependencies: []
requirement_refs:
- FR-014
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
authoritative_surface: src/specify_cli/status/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/status/models.py
- src/specify_cli/status/reducer.py
- src/specify_cli/status/doctor.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP10 – #2960 status doctor must not report Healthy over blanked runtime slots

**Concern**: IC-08 · **Requirements**: FR-014 · **Priority**: P2

## Purpose
`agent: ""` silently blanks recorded attribution (reducer guards `is not None`, not truthiness); `status doctor` reports Healthy over the corrupt state.

## Files / changes
- `status/models.py:460+` (`WPInnerStateDelta`) — normalize `""`→`None` at the write boundary (durable net).
- `status/reducer.py:262-264` (replace-slot) and `:185` (claim arm) — treat empty strings as no-op.
- `status/doctor.py` — add a check for empty-string runtime slots on non-terminal WPs.

## Coordination & guardrails
Scope B (C-007). Regression test: fold `agent:""` over `agent:"claude"` and assert survival + a non-Healthy doctor verdict.

## Definition of Done
- **Red-first**: author the failing test first (see `tasks.md` T001 for this WP) and show it red before the fix.
- **Scope B**: a regression/migration test (NFR-004) that goes red on the defect and green after; topology-agnostic.
- Non-coord control asserts identical behavior where applicable.
- No predicate fork / no new legacy resolver path (C-001); STATUS reads stay COORD (C-002).
- `ruff` + `mypy` clean; complexity ≤15; new helpers/branches have focused tests.
- See `tasks.md` for the full subtask breakdown and the universal DoD.
