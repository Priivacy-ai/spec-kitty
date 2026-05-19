# Tasks: Unblock Sync Identity-Boundary Canary

**Mission**: `unblock-sync-identity-boundary-canary-01KRZJ07`
**Spec**: [spec.md](spec.md) — **Plan**: [plan.md](plan.md)
**Branch contract**: planning base `main` → merge target `main` (`branch_matches_target=true`)
**Date**: 2026-05-19

## Overview

Three CLI bug fixes (WP01–WP03) plus one cross-repo canary verification (WP04). WP01/WP02/WP03 are independent and parallel-safe; WP04 depends on all three landing.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add `is_mission_lifecycle_row` predicate in `audit/shape_registry.py` | WP01 |  |
| T002 | Teach `FORBIDDEN_KEYS` detector in `audit/detectors.py` to consult the predicate | WP01 |  |
| T003 | Per-shape regression test matrix for the detector | WP01 |  |
| T004 | End-to-end integration test: fresh mission produces zero FORBIDDEN_KEY findings | WP01 |  |
| T005 | mypy --strict + ruff + audit suite green check | WP01 |  |
| T006 | Inventory path-bearing fields in `sync status --check` boundary state | WP02 | [P] |
| T007 | Refactor renderer in `cli/commands/sync.py` to print path rows outside the Rich Table | WP02 |  |
| T008 | Regression tests for non-TTY capture, long path, narrow column, JSON parity | WP02 |  |
| T009 | Smoke run of `sync status --check` confirming no `…` ellipsis | WP02 |  |
| T010 | mypy --strict + ruff green check on touched files | WP02 |  |
| T011 | Implement `restart_daemon` composition primitive reusing stop + launch | WP03 | [P] |
| T012 | Register `restart-daemon` typer subcommand under `spec-kitty doctor` | WP03 |  |
| T013 | Refresh all 4 `_REMEDIATION_HINTS` occurrences + comment in `sync/preflight.py` | WP03 |  |
| T014 | Regression tests for `doctor restart-daemon` (happy / no-owner / stop-fail / respawn-fail / foreground-binding) | WP03 |  |
| T015 | Hint-coverage test: every command in any hint resolves on the installed CLI | WP03 |  |
| T016 | Manual smoke: spawn fake daemon, restart, verify; trigger boundary mismatch | WP03 |  |
| T017 | Document sibling-repo canary checkout + invocation in `canary-evidence/RUNBOOK.md` | WP04 |  |
| T018 | Run `pytest tests/identity_boundary/` against rc bump in canary venv | WP04 |  |
| T019 | Capture `latest.json` + `run-1.json` (and optional `canary-run.log`) under `canary-evidence/` | WP04 |  |
| T020 | Verify scenarios 1, 2, 4 are GREEN in captured artifacts; scenario 3 may remain RED | WP04 |  |
| T021 | Record final canary outcome summary in WP04 PR description | WP04 |  |
| T022 | Audit performance gate (≤ 2× rc13 baseline on 100-mission tree) | WP01 |  |
| T023 | Full `pytest tests/` gate against rc bump (NFR-004 regression check) | WP04 |  |

**Parallelization**: WP01, WP02, WP03 run in three independent lanes. WP04 starts only after WP01+WP02+WP03 are approved and merged.

## Work Packages

### WP01 — Audit row-family classifier (#1122) — ~430 lines

**Goal**: Eliminate the `FORBIDDEN_KEY` false positive on mission-lifecycle rows so fresh missions don't auto-create TeamSpace blockers.

**Priority**: P0 (blocks canary scenarios 1, 2; affects every fresh project)

**Independent test**: `pytest tests/specify_cli/audit/` plus the integration test that runs `spec-kitty agent mission create` + `spec-kitty doctor mission-state --audit --json` in a tmp project and asserts zero `FORBIDDEN_KEY` findings.

**Included subtasks**:
- [x] T001 Add `is_mission_lifecycle_row` predicate in `audit/shape_registry.py` (WP01)
- [x] T002 Teach `FORBIDDEN_KEYS` detector to consult the predicate (WP01)
- [x] T003 Per-shape regression test matrix (WP01)
- [x] T004 End-to-end integration test on fresh mission (WP01)
- [x] T005 mypy --strict + ruff + audit suite green check (WP01)
- [x] T022 Audit performance gate (NFR-001; ≤ 2× rc13 baseline) (WP01)

**Implementation sketch**: predicate in `shape_registry.py` → detector consults it before applying `FORBIDDEN_KEYS` → test matrix per contract row → integration test confirms fresh mission yields zero findings.

**Dependencies**: none.

**Risks**: classifier accidentally accepts malformed status-transition rows. Mitigated by the explicit "AND" predicate (`aggregate_type==Mission` AND `event_type`) plus the regression test for the malformed-row case.

**Requirement refs**: FR-001, FR-002, FR-003, FR-009 (regression test), NFR-001 (audit perf ≤ 2× rc13 baseline). Constraints touched: C-003 (no file split), C-005 (additive against existing event logs).

---

### WP02 — `sync status --check` path rendering (#1123) — ~350 lines

**Goal**: Render canonical file paths in `sync status --check` text output verbatim on a single line, byte-identical to the `--json` form, in every terminal width and in non-TTY captures.

**Priority**: P0 (blocks canary scenario 4)

**Independent test**: `pytest tests/specify_cli/cli/commands/test_sync_status_check_paths.py` covering non-TTY capture, long path, narrow column, JSON parity.

**Included subtasks**:
- [x] T006 Inventory path-bearing fields in boundary state (WP02)
- [x] T007 Refactor `_render_boundary_table` (or equivalent) to print path rows outside the Table (WP02)
- [x] T008 Regression tests for non-TTY, long-path, narrow-column, JSON parity (WP02)
- [x] T009 Smoke run confirming no `…` ellipsis in piped capture (WP02)
- [x] T010 mypy --strict + ruff green on touched files (WP02)

**Implementation sketch**: separate path rows from identity scalars → render path rows via `Console.print(f"{label}: {path}")` outside Rich Table → keep Table for non-path identity rows → tests cover the documented edge cases.

**Dependencies**: none.

**Risks**: visual regression on wide-TTY operator view. Mitigated by keeping the Table for non-path rows and snapshot-testing both renderings.

**Requirement refs**: FR-004, FR-005, FR-006, FR-009 (regression test), C-004 (no rename of `_failure_lines_from_set` / identity field names).

---

### WP03 — `doctor restart-daemon` subcommand + hint refresh (#1124) — ~480 lines

**Goal**: Provide a working `spec-kitty doctor restart-daemon` subcommand AND refresh all 4 `_REMEDIATION_HINTS` occurrences in `sync/preflight.py` so every command mentioned in any hint actually resolves.

**Priority**: P1 (operator UX bug; closes #1124 — non-canary-blocking, but required by FR-007/FR-008)

**Independent test**: `pytest tests/specify_cli/cli/commands/test_doctor_restart_daemon.py tests/specify_cli/sync/test_preflight_remediation_hints.py`.

**Included subtasks**:
- [x] T011 Implement `restart_daemon` composition primitive (WP03)
- [x] T012 Register `restart-daemon` typer subcommand under `spec-kitty doctor` (WP03)
- [x] T013 Refresh 4 `_REMEDIATION_HINTS` occurrences + line-218 comment in `sync/preflight.py` (WP03)
- [x] T014 Regression tests for the subcommand (5 scenarios) (WP03)
- [x] T015 Hint-coverage test: every command in any hint resolves on installed CLI (WP03)
- [x] T016 Manual smoke: spawn fake daemon, restart, verify; trigger boundary mismatch (WP03)

**Implementation sketch**: `restart_daemon(repo_root, foreground)` composes existing `stop_registered_daemon` + `launch_daemon_for_foreground` → typer command in `doctor.py` is a thin wrapper → refresh 4 hint strings + comment to reference the new (now-working) subcommand uniformly.

**Dependencies**: none.

**Risks**: `restart-daemon` invoked with no owner record must produce an actionable error (exit 1) not a crash. Stop-hang case must leave owner record intact (exit 3). Mitigated by per-scenario regression test matrix.

**Requirement refs**: FR-007, FR-008, FR-009 (regression test), NFR-002 (≤10 s end-to-end), C-004 (no rename of identity field names — read-only consumer).

---

### WP04 — Canary local verification — ~360 lines

**Goal**: Prove scenarios 1, 2, and 4 of the deployed-dev sync identity-boundary canary turn green against the rc bump that bundles WP01–WP03 fixes. Capture evidence in this repo.

**Priority**: P0 (mission acceptance gate per spec done criterion)

**Independent test**: visual inspection of `canary-evidence/{latest,run-1}.json` shows scenarios 1, 2, 4 green; scenario 3 may remain red per C-002.

**Included subtasks**:
- [x] T017 Document sibling-repo canary checkout + invocation (WP04)
- [x] T018 Run `pytest tests/identity_boundary/` against rc bump (WP04)
- [x] T019 Capture canary artifacts under `canary-evidence/` (WP04)
- [x] T020 Verify scenarios 1, 2, 4 GREEN; scenario 3 may stay RED (WP04)
- [x] T023 Full `pytest tests/` gate (NFR-004 regression check) (WP04)
- [x] T021 Record canary outcome summary in WP04 PR description (WP04)

**Implementation sketch**: clone/checkout `Priivacy-ai/spec-kitty-end-to-end-testing` next to this repo → install rc bump → run `pytest tests/identity_boundary/` → copy `artifacts/sync_identity_boundary/<rc>/{latest,run-1}.json` into `canary-evidence/` → assert scenarios 1, 2, 4 pass.

**Dependencies**: **WP01, WP02, WP03** must all be merged first (the canary needs the bundled rc bump to validate).

**Risks**:
- Scenario 4 still fails post-fix for an unrelated reason. Mitigated by capturing full artifacts so the diagnostic is visible in the PR.
- Sibling-repo checkout drifts (recent commit on `main` of `spec-kitty-end-to-end-testing`). Mitigated by recording the exact `HEAD` commit of the sibling repo in the runbook.
- `#43` not yet landed → scenario 3 red. This is **expected** per C-002 and does not gate this mission.

**Requirement refs**: NFR-003 (canary scenarios 1, 2, 4 green), NFR-004 (no regression in existing test suites). Constraints touched: C-001 (no code in sibling repo), C-002 (scenario 3 may stay red).

## MVP Scope

WP01 alone unblocks canary scenarios 1 and 2 (the most user-impactful), since those are what every fresh project hits. **Recommended MVP if pressed: WP01 → WP02 → WP03 → WP04 in priority order.** All three CLI fixes are small enough that the full sequence is the realistic MVP.

## Parallelization plan

| Lane | WPs | Notes |
|------|-----|-------|
| Lane A | WP01 | Audit fix |
| Lane B | WP02 | Sync status rendering |
| Lane C | WP03 | doctor restart-daemon + hint refresh |
| Lane A (post-merge) | WP04 | Cross-repo canary verification — runs after A/B/C merge |

`finalize-tasks` will assign concrete lane letters from `lanes.json`. Three Python implementers can run in parallel for WP01–WP03; WP04 is sequenced last.
