---
work_package_id: WP10
title: MissionStatus consumption rework
dependencies:
- WP09
requirement_refs:
- FR-017
- FR-018
- FR-019
- NFR-006
tracker_refs: []
planning_base_branch: feat/execution-state-strangler
merge_target_branch: feat/execution-state-strangler
branch_strategy: Planning artifacts for this mission were generated on 
  feat/execution-state-strangler. During /spec-kitty.implement this WP may 
  branch from a dependency-specific base, but completed changes must merge back 
  into feat/execution-state-strangler unless the human explicitly redirects the 
  landing branch.
subtasks:
- T036
- T037
- T038
phase: Phase 5 - Consumption
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2932149"
history:
- at: '2026-06-07T05:16:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/
execution_mode: code_change
model: ''
scope: codebase-wide
owned_files:
- src/specify_cli/**
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP10 – MissionStatus consumption rework

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `randy-reducer`
- **Role**: `implementer`

## ⚙️ Persona IC — Randy Reducer

One status entry point. Mission-level reads/writes go through `MissionStatus`; there is no second write surface. Distinguish genuine plumbing (exempt) from mission-level access (route) — do not over-route internal plumbing.

## Objectives & Success Criteria

Route mission-level status read/write consumers onto the `MissionStatus` aggregate; eliminate direct `BookkeepingTransaction` calls outside `status/` and documented plumbing.

> **Post-FSM-rebase note (2026-06-08):** the canonical-reader routing pattern is **already demonstrated** — `runtime/next/decision.py::_get_wp_lanes` now delegates to `lane_reader.get_all_wp_lanes` (with `CanonicalStatusNotFoundError` fallback). Use it as the **reference exemplar**; that consumer is **done** — drop it from the to-do set. Also: `orchestrator_api/commands.py::_is_run_affecting` was renamed `_transition_requires_policy` (distinct from `WPState.is_run_affecting`) — use the new name, don't conflate.

- FR-017/018/019. NFR-002, NFR-006 (no `transaction.py` internals change). SC-005.

## Context & Constraints

- Aggregate: `src/specify_cli/status/aggregate.py` (`MissionStatus.load/claim/transition`). Data model: [data-model.md](../data-model.md). Overlaps with WP08 ROUTE category — coordinate.
- `coordination/transaction.py` internals unchanged (NFR-006).

## Branch Strategy

- **Strategy**: coordination-branch planning; merge to target
- **Planning base branch**: feat/execution-state-strangler
- **Merge target branch**: feat/execution-state-strangler

## Subtasks & Detailed Guidance

### Subtask T036 – Rework mission-level callers
- **Steps**: Replace direct `emit`/`lane_reader`/`store` mission-level access with `MissionStatus.load()/.claim()/.transition()`.
- **Files**: status consumers across `cli/`, `orchestrator_api/`, `core/`.

### Subtask T037 – No direct BookkeepingTransaction
- **Steps**: Ensure no consumer outside `status/` and documented plumbing calls `BookkeepingTransaction` directly.

### Subtask T038 – Confirm SC-005
- **Steps**: `grep -rn "BookkeepingTransaction(" src/ | grep -v "status/" | grep -v "coordination/"` → zero.

## Test Strategy

- Affected command tests green; WP01 ratchet green; `coordination/transaction.py` diff empty.

## Risks & Mitigations

- Over-routing plumbing → only mission-level access goes to the aggregate; plumbing stays exempt.

## Review Guidance — **Persona IC: reviewer-renata** (with Randy-Reducer leanness check)

- Reviewer profile: `reviewer-renata`. Verify single write surface, no `transaction.py` change, and SC-005 grep zero. Confirm no parallel status path reintroduced.

## Activity Log

- 2026-06-07T05:16:24Z – system – Prompt created.
- 2026-06-08T09:58:21Z – claude:opus:randy-reducer:implementer – shell_pid=2903235 – Started implementation via action command
- 2026-06-08T10:21:42Z – claude:opus:randy-reducer:implementer – shell_pid=2903235 – Ready for review: 14 ROUTE-deferred files routed (lifecycle_events x11, work_package_lifecycle x4, materialize_snapshot x2, run_doctor x1, InvalidMissionSlug x1 promoted to facade; sync handler onto 2 new facade helpers) + SC-005=0 + allow-list shrunk to 1 (cycle-breaker only)
- 2026-06-08T10:23:14Z – claude:opus:reviewer-renata:reviewer – shell_pid=2932149 – Started review via action command
