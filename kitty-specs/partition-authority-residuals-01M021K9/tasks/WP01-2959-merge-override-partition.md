---
work_package_id: WP01
title: '#2959 merge-deadlock: partition-correct override write + merge escape hatch'
dependencies: []
requirement_refs:
- FR-001
- FR-002
planning_base_branch: fix/partition-authority-residuals
merge_target_branch: fix/partition-authority-residuals
branch_strategy: Planning artifacts for this mission were generated on fix/partition-authority-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/partition-authority-residuals unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-partition-authority-residuals-01M021K9
base_commit: ae488c6259eb69c372e57d321c28ac818f99479a
created_at: '2026-08-15T07:47:46.548663+00:00'
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
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_materialization.py
- src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py
- src/specify_cli/cli/commands/merge.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 – #2959 merge-deadlock: partition-correct override write + merge escape hatch

**Concern**: IC-01 · **Requirements**: FR-001, FR-002 · **Priority**: P1

## Purpose
Kill the coord merge deadlock: the ReviewOverride annotation is written to a PRIMARY-derived dir while the merge gate reads COORD, so any coord mission that took a review rejection is unmergeable, with no override escape hatch.

## Files / changes
- `tasks_materialization.py:78-90` (`_persist_review_artifact_override`) — reroute at the CALLER: resolve `placement_seam(...).read_dir(STATUS_STATE)` and pass that dir into `emit_inner_state_changed` (leave the shared function unchanged; ref pattern `tasks_dependency_graph.py:120-135`).
- `tasks_verdict_persistence.py:547-571` — caller that passes the artifact path today.
- `cli/commands/merge.py:420-446` — add `--skip-review-artifact-check` + `--note` (parity with `tasks_transition_core.py:414-418`); record the skip as evidence.
- Gate consumers (read-only verify they read COORD): `post_merge/review_artifact_consistency.py:243`, `merge/preflight.py:361`, `merge/forecast.py:203`.

## Coordination & guardrails
Shares the merge-preflight coord-merge e2e with WP02; shares `emit_inner_state_changed` (no edit) with WP03. Register the coord worktree in the fixture so STATUS_STATE resolves to coord, not the canonicalized primary.

## Definition of Done
- **Red-first**: author the failing test first (see `tasks.md` T001 for this WP) and show it red before the fix.
- **Scope A**: a live coord-topology e2e (NFR-001) that is red-before/green-after, with the coord worktree registered.
- Non-coord control asserts identical behavior where applicable.
- No predicate fork / no new legacy resolver path (C-001); STATUS reads stay COORD (C-002).
- `ruff` + `mypy` clean; complexity ≤15; new helpers/branches have focused tests.
- See `tasks.md` for the full subtask breakdown and the universal DoD.
