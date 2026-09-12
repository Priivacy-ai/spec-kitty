---
work_package_id: WP07
title: '#2692 check-prerequisites reports a truthful planning-artifact inventory'
dependencies: []
requirement_refs:
- FR-010
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
authoritative_surface: src/specify_cli/core/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/core/worktree.py
- tests/git_ops/test_worktree.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP07 – #2692 check-prerequisites reports a truthful planning-artifact inventory

**Concern**: IC-07 · **Requirements**: FR-010 · **Priority**: P2

## Purpose
check-prerequisites inventories only spec/plan/tasks (hardcoded), omitting research.md/data-model.md/quickstart.md/contracts/traces; `research_dir` has wrong file-vs-dir semantics.

## Files / changes
- `core/worktree.py:661-706` — derive `available_docs`/`artifact_files` from canonical mission `artifacts` metadata (not hardcoded).
- `core/worktree.py:718-721` — fix `research_dir` semantics.
- `tests/git_ops/test_worktree.py:465,487` — update the two behavior-locking assertions to the truthful inventory.

## Coordination & guardrails
Scope B (C-007): must not share a WP with any Scope-A concern. Partition anchoring here is already correct — this is inventory schema-drift only.

## Definition of Done
- **Red-first**: author the failing test first (see `tasks.md` T001 for this WP) and show it red before the fix.
- **Scope B**: a regression/migration test (NFR-004) that goes red on the defect and green after; topology-agnostic.
- Non-coord control asserts identical behavior where applicable.
- No predicate fork / no new legacy resolver path (C-001); STATUS reads stay COORD (C-002).
- `ruff` + `mypy` clean; complexity ≤15; new helpers/branches have focused tests.
- See `tasks.md` for the full subtask breakdown and the universal DoD.
