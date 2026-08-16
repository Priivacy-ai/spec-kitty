---
work_package_id: WP09
title: '#2717 diagnostics discover missions under the canonical kitty-specs root'
dependencies: []
requirement_refs:
- FR-013
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
authoritative_surface: src/specify_cli/retrospective/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/retrospective/summary.py
- src/specify_cli/cli/commands/retrospect.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP09 – #2717 diagnostics discover missions under the canonical kitty-specs root

**Concern**: IC-07 · **Requirements**: FR-013 · **Priority**: P2

## Purpose
`retrospect summary` anchors discovery on `.kittify/missions/` instead of `kitty-specs/*`, scanning support modules as missions and omitting the real record.

## Files / changes
- Add ONE canonical `kitty-specs/*` mission-instance iterator (reads meta.json, excludes `.kittify`).
- Route BOTH `retrospective/summary.py:296-303` and `cli/commands/retrospect.py:1003-1005` through it (avoid the two-copy trap).

## Coordination & guardrails
Scope B (C-007). Test the shared iterator directly.

## Definition of Done
- **Red-first**: author the failing test first (see `tasks.md` T001 for this WP) and show it red before the fix.
- **Scope B**: a regression/migration test (NFR-004) that goes red on the defect and green after; topology-agnostic.
- Non-coord control asserts identical behavior where applicable.
- No predicate fork / no new legacy resolver path (C-001); STATUS reads stay COORD (C-002).
- `ruff` + `mypy` clean; complexity ≤15; new helpers/branches have focused tests.
- See `tasks.md` for the full subtask breakdown and the universal DoD.
