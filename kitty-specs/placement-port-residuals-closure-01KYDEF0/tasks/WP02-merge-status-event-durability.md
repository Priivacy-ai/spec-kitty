---
work_package_id: WP02
title: Merge status-event durability
dependencies:
- WP01
requirement_refs:
- FR-011
planning_base_branch: placement-port-residuals
merge_target_branch: placement-port-residuals
branch_strategy: Planning artifacts for this mission were generated on placement-port-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into placement-port-residuals unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
history:
- at: '2026-07-25T21:12:34Z'
  actor: tasks
  note: WP created from IC-04 (FR-011)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/merge/executor.py
- tests/cli/commands/test_merge_status_commit.py
- tests/integration/test_merge_lane_planning_data_loss.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before reading anything else**, load `python-pedro` (role `implementer`) via `/ad-hoc-profile-load`;
adopt its directives/tactics and state which you applied. Then proceed.

## Objective

Make merges durably commit `status.events.jsonl` alongside `meta.json`/`status.json` (FR-011).
Two tests are RED on `upstream/main` because the merge committed-file set drops the status event log.
Judge per the failing-test remediation framework: these tests encode the **real FR-019/FR-020 durability
invariant** ("done events durably committed; `git show HEAD:` finds them") → **fix the PRODUCT**, not the test.

Read first: `spec.md` (FR-011), `contracts/gate-reconciliation.md` (C-GATE-3), `quickstart.md`.

## Context

- RED: `tests/cli/commands/test_merge_status_commit.py::TestSafeCommitCalledAfterMarkDoneLoop::test_safe_commit_is_called_with_correct_files` — `assert 'status.events.jsonl' in ['status.json','meta.json']` fails.
- RED: `tests/integration/test_merge_lane_planning_data_loss.py::TestPlanningArtifactReachesTarget::test_planning_artifact_only_merge_does_not_require_mission_branch` — `status.events.jsonl` absent from the committed `{meta.json, status.json}` set.
- Both live in the merge executor's mark-done / planning-artifact commit path (`merge/executor.py`).
- NOTE: `merge/executor.py` is owned by this WP. The `executor.py:1053-1060` coord-seed **arch-gate** reds are handled by WP03 (test-allowlist edits only — no product change there). Do not edit the coord-seed commit here.

## Subtasks

### T007 — Confirm red-first
Run both tests (`PWHEADLESS=1 pytest … -q`); capture the exact assertion (status.events.jsonl absent).

### T008 — Fix the committed-file set
In `merge/executor.py`, add `status.events.jsonl` to the file set committed by the mark-done loop and the
planning-artifact merge path (wherever `meta.json`/`status.json` are staged for the status-bookkeeping commit).
Ensure it is committed on the correct partition (the status event log is a STATUS_STATE artifact). Preserve
resume-safety and best-effort semantics of the surrounding commit helpers.

### T009 — Verify
Both tests green. Run the merge suites (`tests/cli/commands/test_merge_status_commit.py`,
`tests/integration/test_merge_lane_planning_data_loss.py`, plus `fast-tests-merge`-scoped tests) — no regression.

### T010 — Gate clean
`ruff` + `mypy --strict` clean; complexity ≤15.

## Branch Strategy
Planning base `placement-port-residuals`; merge target `placement-port-residuals`. Worktree per `lanes.json`
via `spec-kitty agent action implement WP02 --agent claude`. **The `dependencies: [WP01]` edge is a deliberate
*sequencing* choice** (a coherent fast-green-main Lane A stack landing after the MVP), NOT a file-collision or
code dependency — WP01 (`migration/*`) and WP02 (`merge/executor.py`) own disjoint files and WP02's merge tests
are orthogonal to WP01's cutover path. It may be parallelized later if the operator prefers.

## Definition of Done
- [ ] Both merge tests RED→GREEN; product (committed-set) fixed, tests unchanged in intent.
- [ ] `status.events.jsonl` committed on its correct partition in mark-done + planning-artifact paths.
- [ ] Merge suites green; ruff/mypy clean.

## Risks / reviewer guidance
- Do NOT re-pin the tests to accept the missing file — the invariant is real (FR-019/FR-020).
- Reviewer: confirm the event log is committed on the STATUS_STATE partition, resume-safety preserved, and the coord-seed commit (WP03 territory) was not touched.
