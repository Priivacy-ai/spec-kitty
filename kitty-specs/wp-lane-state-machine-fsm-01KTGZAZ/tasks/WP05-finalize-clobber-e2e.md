---
work_package_id: WP05
title: Finalize clobber hardening + end-to-end regression
dependencies: []
requirement_refs:
- FR-006
- FR-019
tracker_refs:
- '1589'
planning_base_branch: mission/wp-lane-state-machine-fsm
merge_target_branch: mission/wp-lane-state-machine-fsm
branch_strategy: Planning artifacts for this mission were generated on mission/wp-lane-state-machine-fsm. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/wp-lane-state-machine-fsm unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
phase: Phase 2 - Regression
assignee: ''
agent: claude
history:
- at: '2026-06-07T13:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/cli/commands/agent/test_finalize_clobber_e2e.py
execution_mode: code_change
model: ''
owned_files:
- tests/specify_cli/cli/commands/agent/test_finalize_clobber_e2e.py
role: implementer
tags:
- finalize
- regression
- '1589'
task_type: implement
---

# Work Package Prompt: WP05 — Finalize clobber end-to-end regression

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for profile **`python-pedro`** (role: `implementer`).

## Objective & Success Criteria

Lock in the finalize clobber fix (already merged: `_stage_finalize_artifacts_in_coord_worktree`)
with an **end-to-end** test that a coord-topology `finalize-tasks` preserves the seeded
coordination event log.

- FR-006, FR-019; US3 (the #1589 data-loss). SC-007.

## Context & Constraints

- Baseline fix lives in `cli/commands/agent/mission.py` (`_stage_finalize_artifacts_in_coord_worktree` skips `_COORD_OWNED_STATUS_FILES`); `test_finalize_coord_staging.py` already unit-tests the helper. This WP adds the **end-to-end** net (renata finding 3 / FR-019): run the real `finalize-tasks` and assert lane events survive.
- Create a NEW test file (`test_finalize_clobber_e2e.py`) — do not modify `mission.py` (the fix is done) or the existing staging unit test (owned by baseline).

## Branch Strategy
- Base/merge: `mission/wp-lane-state-machine-fsm`; lane worktree per `lanes.json`. `spec-kitty agent action implement WP05 --agent <name>`.

## Subtasks & Detailed Guidance

### T024 — E2E: coord finalize preserves bootstrap lane events
- Set up a real git repo with a coordination-topology mission (meta with `coordination_branch`, WP files), seed lane events into the coord worktree (bootstrap), run the real `finalize-tasks` command (CliRunner/subprocess), then assert the committed coordination event log STILL contains the bootstrap lane events (read via `read_events_transactional`). Model the coord setup on `tests/status/test_bootstrap.py::TestBootstrapCoordinationBranchPersistence`.

### T025 [P] — Negative: non-coord mission still commits status files
- A non-coordination mission's `finalize-tasks` still commits its primary-checkout `status.events.jsonl`/`status.json` (no regression from the skip).

### T026 — Edge: redundant coord re-finalize empty-changeset
- A coord re-finalize where only status files changed does not error with an empty-changeset commit (debbie Attack 3b).

## Test Strategy
- Targeted: `python -m pytest tests/specify_cli/cli/commands/agent/test_finalize_clobber_e2e.py -q`. Keep it hermetic (tmp git repo). Mark slow/integration if needed.

## Definition of Done
- E2E test proves the coord event log survives finalize; non-coord + empty-changeset cases covered; green.

## Risks & Mitigations
- E2E realism — use a real coord worktree, not a mock. Keep the fixture fast.

## Review Guidance — **Reviewer: reviewer-renata**
- Renata: the test is non-vacuous (fails if the clobber fix is reverted); covers coord + non-coord + empty-changeset.

## Activity Log
- 2026-06-07 — system — Prompt created.
