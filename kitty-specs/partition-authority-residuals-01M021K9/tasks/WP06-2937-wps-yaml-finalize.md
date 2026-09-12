---
work_package_id: WP06
title: '#2937 finalize checkpoints wps.yaml (gated on D-001)'
dependencies: []
requirement_refs:
- FR-009
planning_base_branch: fix/partition-authority-residuals
merge_target_branch: fix/partition-authority-residuals
branch_strategy: Planning artifacts for this mission were generated on fix/partition-authority-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/partition-authority-residuals unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Scope A (partition)
history:
- timestamp: '2026-08-15T00:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission_finalize.py
- src/mission_runtime/artifacts.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP06 – #2937 finalize checkpoints wps.yaml (gated on D-001)

**Concern**: IC-06 · **Requirements**: FR-009 · **Priority**: P3

## Purpose
finalize reads `wps.yaml` (regenerating `tasks.md`) but never commits it, so the checkpoint cannot reproduce its own state. Blocked-by Decision D-001 (version vs document-as-non-versioned).

## Files / changes
- Decision D-001 first (default lean: version it; record in the mission decision log).
- If versioned: `cli/commands/agent/mission_finalize.py:187-216` add `feature_dir/"wps.yaml"` to `_collect_finalize_artifacts` + a `wps.yaml → TASKS_INDEX` classifier entry in `mission_runtime/artifacts.py`; tighten `files_committed`.
- If non-versioned: document + adjust reporting only.

## Coordination & guardrails
This is the one place a classifier membership ADD is in play (a currently-unclassified file) — still not a predicate fork.

## Definition of Done
- **Red-first**: author the failing test first (see `tasks.md` T001 for this WP) and show it red before the fix.
- **Scope A**: a live coord-topology e2e (NFR-001) that is red-before/green-after, with the coord worktree registered.
- Non-coord control asserts identical behavior where applicable.
- No predicate fork / no new legacy resolver path (C-001); STATUS reads stay COORD (C-002).
- `ruff` + `mypy` clean; complexity ≤15; new helpers/branches have focused tests.
- See `tasks.md` for the full subtask breakdown and the universal DoD.
