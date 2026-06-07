---
work_package_id: WP02
title: Read/write parity for genesis + actionable unseeded-implement rejection
dependencies:
- WP01
requirement_refs:
- FR-008
- FR-009
tracker_refs:
- '1666'
planning_base_branch: mission/wp-lane-state-machine-fsm
merge_target_branch: mission/wp-lane-state-machine-fsm
branch_strategy: Planning artifacts for this mission were generated on mission/wp-lane-state-machine-fsm. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/wp-lane-state-machine-fsm unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
phase: Phase 2 - Parity
assignee: ''
agent: claude
history:
- at: '2026-06-07T13:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/status_service.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/coordination/status_service.py
- src/specify_cli/coordination/status_transition.py
- src/runtime/next/discovery.py
- src/runtime/next/decision.py
- src/specify_cli/agent_utils/status.py
- src/specify_cli/status/work_package_lifecycle.py
- src/specify_cli/cli/commands/agent/implement.py
role: implementer
tags:
- genesis
- read-write-parity
task_type: implement
---

# Work Package Prompt: WP02 — Read/write parity for genesis + actionable rejection

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for profile **`python-pedro`** (role: `implementer`).

## Objective & Success Criteria

Every lane reader reports an unseeded WP as `GENESIS` (matching the writer
`_derive_from_lane`); implementing an unfinalized WP fails fast with an actionable
"run finalize-tasks" message **before** any workspace is allocated.

- FR-008, FR-009; US4 (review finding F2). SC-003.

## Context & Constraints

- Review finding F2 (`research/review-reviewer-renata.md`, `review-debugger-debbie.md`): the write side derives `GENESIS` but readers still default to `PLANNED`, so `start_implementation_status` enters the PLANNED branch and the batch emit raises a cryptic `Illegal transition: genesis -> claimed` AFTER the worktree is allocated.
- Depends on WP01 (genesis is a first-class FSM state with `genesis→planned`/`canceled` edges only).

## Branch Strategy
- Base/merge: `mission/wp-lane-state-machine-fsm`; lane worktree per `lanes.json`. `spec-kitty agent action implement WP02 --agent <name>`.

## Subtasks & Detailed Guidance

### T008 — `wp_lane_actor_from_events` → GENESIS default
- `coordination/status_service.py`: when a WP has no lane events, return `Lane.GENESIS` (not `PLANNED`).

### T009 — Transactional read fallback → GENESIS
- `coordination/status_transition.py::read_current_wp_state_transactional`: the no-events fallback returns `Lane.GENESIS`.

### T010 [P] — Runtime discovery defaults → GENESIS
- `runtime/next/discovery.py`, `runtime/next/decision.py`, `agent_utils/status.py`: change `wp_lanes.get(wp_id, Lane.PLANNED)` defaults to `Lane.GENESIS` so unseeded WPs are filtered OUT of the claimable candidate list (genesis is not an active/claimable lane).

### T011 — Actionable rejection in `start_implementation_status`
- `status/work_package_lifecycle.py`: add an explicit `current_lane == Lane.GENESIS` branch raising `WorkPackageStartRejected("WP {wp_id} is not finalized; run `spec-kitty agent mission finalize-tasks`")`.

### T012 — Reject BEFORE workspace allocation
- `cli/commands/agent/implement.py`: ensure the genesis rejection happens before `result.workspace_path`/worktree allocation (currently allocation precedes the status call) — no dangling worktree on rejection.

### T013 — Tests
- Each reader returns `GENESIS` for an unseeded WP; `implement` on an unseeded WP exits with the actionable message and leaves NO `.worktrees/` entry; happy path (finalized WP) unaffected.

## Test Strategy
- Targeted: `python -m pytest tests/specify_cli/coordination/ tests/status/test_work_package_lifecycle.py tests/lanes/ -q`. `ruff`+`mypy` clean.

## Definition of Done
- All readers genesis-consistent; unseeded implement fails fast + actionable + no worktree; happy path green.

## Risks & Mitigations
- Ordering (reject before allocation). Do not regress the seeded happy path.

## Review Guidance — **Persona ICs: Paula-Patterns; reviewer: reviewer-renata**
- Paula: read and write layers now genuinely agree (the ADR claim becomes true). Renata: the dangling-worktree case is gone; the error is actionable.

## Activity Log
- 2026-06-07 — system — Prompt created.
