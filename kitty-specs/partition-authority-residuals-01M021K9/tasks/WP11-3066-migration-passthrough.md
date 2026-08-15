---
work_package_id: WP11
title: '#3066 mission-state repair preserves legacy WPStatusChanged transitions'
dependencies: []
requirement_refs:
- FR-015
planning_base_branch: fix/partition-authority-residuals
merge_target_branch: fix/partition-authority-residuals
branch_strategy: Planning artifacts for this mission were generated on fix/partition-authority-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/partition-authority-residuals unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
phase: Phase 2 - Scope B (fidelity)
history:
- timestamp: '2026-08-15T00:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/migration/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/migration/mission_state.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP11 – #3066 mission-state repair preserves legacy WPStatusChanged transitions

**Concern**: IC-09 · **Requirements**: FR-015 · **Priority**: P1

## Purpose
`doctor mission-state --fix` quarantines legacy `WPStatusChanged` lane transitions and regenerates a zero-WP status.json — a data-destroying repair. An existing PR #3067 carries the fix but is stale (462 behind, CI-red).

## Files / changes
- `migration/mission_state.py:1583-1667` (`_rule_reject_non_status_event` / `_is_preserved_non_lane_row`) — adopt PR #3067's diff (rerolled): add `_is_legacy_typed_lane_transition(row)` (true when `event_type=="WPStatusChanged"` AND `wp_id`/`from_lane`/`to_lane` present) and route it via passthrough at the head of the rule, before the quarantine branches.
- TeamSpace envelopes (lane fields under `payload`) and `DecisionPointOpened` mirrors MUST stay quarantined.

## Coordination & guardrails
Scope B (C-007). Reroll PR #3067 rather than re-implementing; keep its red-first migration test. The repair is mutating — assert status.json retains the WPs after --fix.

## Definition of Done
- **Red-first**: author the failing test first (see `tasks.md` T001 for this WP) and show it red before the fix.
- **Scope B**: a regression/migration test (NFR-004) that goes red on the defect and green after; topology-agnostic.
- Non-coord control asserts identical behavior where applicable.
- No predicate fork / no new legacy resolver path (C-001); STATUS reads stay COORD (C-002).
- `ruff` + `mypy` clean; complexity ≤15; new helpers/branches have focused tests.
- See `tasks.md` for the full subtask breakdown and the universal DoD.
