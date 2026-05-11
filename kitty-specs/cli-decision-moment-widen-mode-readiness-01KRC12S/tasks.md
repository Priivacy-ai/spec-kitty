# Tasks: CLI Decision Moment Widen Mode Readiness

**Mission**: cli-decision-moment-widen-mode-readiness-01KRC12S
**Branch**: `main` (planning, base, and merge target — all `main`)
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)
**Generated**: 2026-05-11

---

## Branch Strategy

- **Current branch at workflow start**: `main`
- **Planning/base branch for this mission**: `main`
- **Final merge target for completed changes**: `main`
- **Branch matches target**: ✅ true

Execution worktrees are allocated per computed lane from `lanes.json` after `finalize-tasks` runs. Agents working a WP MUST enter the workspace path printed by `spec-kitty implement WP##`.

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Update `tests/specify_cli/cli/commands/test_plan_widen.py::_setup_repo` to write a minimal valid `.kittify/config.yaml` (with `version: 1` and `project: {uuid: <fixed-test-uuid>}`) and explicitly create the parent `kitty-specs/` directory so `assert_initialized(require_specs=True)` passes during the 4 plan-widen integration tests. | WP01 | [D] |
| T002 | Run the acceptance test set (SC-001) and the broader CLI slice (SC-003); confirm 4 previously-failing tests pass, zero regressions versus the 51-passing baseline. | WP01 | [D] |
| T003 | Audit other widen-related test helpers (`grep -l "_setup_repo" tests/specify_cli/`) to confirm they either already satisfy the gate or do not exercise commands that call `_enforce_initialized()`. Document findings inline in the WP01 prompt. | WP01 | [D] |

**Total**: 3 subtasks in 1 work package.

---

## Phase 1 — Setup

*(No setup WPs required. The dev environment is already configured.)*

---

## Phase 2 — Foundational

*(No foundational WPs required.)*

---

## Phase 3 — Story WPs

### WP01 — Plan-Widen Test Fixture Repair

**Goal**: Fix the 4 failing `test_plan_widen.py` tests by hardening their `_setup_repo` helper to satisfy the FR-032 `assert_initialized(require_specs=True)` gate. No production code changes.
**Priority**: P0 (release blocker per missions-list.md Mission 1)
**Estimated prompt size**: ~120 lines (3 subtasks × ~40 lines each)
**Independent test**: `uv run pytest tests/specify_cli/cli/commands/test_charter_widen.py tests/specify_cli/cli/commands/test_plan_widen.py tests/specify_cli/cli/commands/test_decision_widen_subcommand.py tests/specify_cli/cli/commands/test_charter_prereq_suppression.py tests/status/test_read_events_tolerates_decision_events.py -q` exits zero (was 4 failed / 51 passed; target 55 passed).
**Dependencies**: none.
**Owned files**: `tests/specify_cli/cli/commands/test_plan_widen.py` (test helper only).
