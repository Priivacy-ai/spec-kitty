# Tasks: Retire Standalone Tasks CLI

**Mission**: retire-standalone-tasks-cli-01KWAMQ3
**Branch**: planning/base/merge-target = `mission/retire-standalone-tasks-cli`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Strictly-linear chain (WP01 → WP02 → WP03 → WP04). The ordering is load-bearing: the `tests/utils.py` sys.path injection must survive until the DELETE-class files are removed (WP04), and the surgical test reconciliations (WP03) must land before the surface is deleted so nothing imports a missing module.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Repoint `tests/utils.py::write_wp` import to canonical `task_utils.support` | WP01 | |
| T002 | Run full suite (40 `write_wp` dependents) — confirm green | WP01 | |
| T003 | Confirm canonical helpers behaviorally equivalent; leave sys.path/run_tasks_cli intact | WP01 | |
| T004 | Add `--normalize-encoding/--no-normalize-encoding` option to `spec-kitty accept` | WP02 | |
| T005 | Wire the flag: on `ArtifactEncodingError`, delegate to `acceptance.normalize_feature_encoding`, re-collect | WP02 | |
| T006 | Test: repair-with-flag repairs a mojibake artifact | WP02 | [P] |
| T007 | Test: default-off performs no rewrite | WP02 | [P] |
| T008 | Test: error-without-flag surfaces clean exit 1 referencing the flag | WP02 | [P] |
| T009 | Reconcile `test_acceptance_support.py` → canonical imports; keep real-CLI tests; drop standalone encoding asserts | WP03 | |
| T010 | `test_feature_metadata.py` — delete `TestMergeToleranceMalformedMeta` (dead-only) | WP03 | [P] |
| T011 | `test_accept_pre30_hard_reject.py` — drop standalone-command tests; add real-CLI pre-3.0 reject regression | WP03 | |
| T012 | `test_acceptance_regressions.py` — delete T014 (standalone help) + T016 (acceptance_support alignment) | WP03 | [P] |
| T013 | `test_pre30_guard_wiring.py` — delete the `tasks_cli.*_command` arms | WP03 | [P] |
| T014 | `test_lane_regression_guard.py` — delete `_standalone_task_scripts` + its parametrized test | WP03 | [P] |
| T015 | `test_codebase_sweep.py` — delete the vacuous standalone-scripts sweep test | WP03 | [P] |
| T016 | Delete the 3 standalone copies (FR-001/002/003) | WP04 | |
| T017 | Delete the 5 DELETE-class test files + empty `tests/specify_cli/scripts/` package tree | WP04 | |
| T018 | Remove `tests/utils.py` sys.path injection + `run_tasks_cli`; delete `conftest.py::ensure_imports` | WP04 | |
| T019 | Update `pyproject.toml` — drop the `scripts/tasks` ruff ignores + `specify_cli.scripts.tasks.*` mypy/module entries | WP04 | |
| T020 | FR-007 ratchet shed: remove dead allowlist/audit entries across all gate files | WP04 | |
| T021 | Recompute `_baselines.yaml` `category_b` + `category_3` to live frozenset sizes (C-002) | WP04 | |
| T022 | Verify: `grep specify_cli.scripts.tasks` repo-wide → none; full suite + architectural + ruff + mypy green | WP04 | |

---

## WP01 — Repoint shared `write_wp` helper to canonical

**Goal**: Isolate and de-risk the 40-file `write_wp` blast radius before any deletion. Repoint `tests/utils.py::write_wp` from the standalone `task_helpers` to the canonical `specify_cli.task_utils.support` (behaviorally equivalent helpers). Leave the sys.path injection + `run_tasks_cli` in place (their removal is WP04, atomic with the deletion).
**Priority**: P1 (critical path — everything else builds on a green suite here)
**Independent test**: full suite green after the repoint; the 40 `write_wp` dependents pass unchanged.
**Requirements**: FR-004 (partial)
**Dependencies**: none

- [x] T001 Repoint `tests/utils.py::write_wp` import to canonical `task_utils.support` (WP01)
- [x] T002 Run full suite (40 `write_wp` dependents) — confirm green (WP01)
- [x] T003 Confirm canonical helpers behaviorally equivalent; leave sys.path/run_tasks_cli intact (WP01)

Prompt: [tasks/WP01-repoint-write-wp.md](./tasks/WP01-repoint-write-wp.md) (~200 lines)

## WP02 — Preserve encoding normalization on `spec-kitty accept` (FR-005)

**Goal**: Add an opt-in `--normalize-encoding` flag to the supported `spec-kitty accept`, delegating to canonical `acceptance.normalize_feature_encoding`, so the one unique standalone capability survives the deletion. Includes the three NFR-004 tests.
**Priority**: P1
**Independent test**: `spec-kitty accept --normalize-encoding` repairs a mojibake artifact; default-off does not rewrite; without-flag malformed input → clean exit 1.
**Requirements**: FR-005, NFR-004
**Dependencies**: WP01

- [x] T004 Add `--normalize-encoding/--no-normalize-encoding` option to `spec-kitty accept` (WP02)
- [x] T005 Wire the flag: on `ArtifactEncodingError`, delegate to `acceptance.normalize_feature_encoding`, re-collect (WP02)
- [x] T006 Test: repair-with-flag repairs a mojibake artifact (WP02)
- [x] T007 Test: default-off performs no rewrite (WP02)
- [x] T008 Test: error-without-flag surfaces clean exit 1 referencing the flag (WP02)

Prompt: [tasks/WP02-accept-normalize-encoding.md](./tasks/WP02-accept-normalize-encoding.md) (~320 lines)

## WP03 — Surgical test reconciliation (FR-004 surgical / FR-009)

**Goal**: Edit the behavior-bearing test files so they no longer import the standalone surface — repoint to canonical, delete dead-only tests, and add the real-CLI pre-3.0 reject regression — while the standalone modules still exist (so the suite stays green). After this WP, only the DELETE-class scaffolding still references the surface.
**Priority**: P1
**Independent test**: the 7 reconciled files pass; `grep specify_cli.scripts.tasks` in them returns nothing; full suite green (modules still present).
**Requirements**: FR-004, FR-009, NFR-002
**Dependencies**: WP02 (so the standalone encoding asserts can be dropped against WP02's real-surface coverage)

- [x] T009 Reconcile `test_acceptance_support.py` → canonical imports; keep real-CLI tests; drop standalone encoding asserts (WP03)
- [x] T010 `test_feature_metadata.py` — delete `TestMergeToleranceMalformedMeta` (dead-only) (WP03)
- [x] T011 `test_accept_pre30_hard_reject.py` — drop standalone-command tests; add real-CLI pre-3.0 reject regression (WP03)
- [x] T012 `test_acceptance_regressions.py` — delete T014 + T016 (WP03)
- [x] T013 `test_pre30_guard_wiring.py` — delete the `tasks_cli.*_command` arms (WP03)
- [x] T014 `test_lane_regression_guard.py` — delete `_standalone_task_scripts` + its parametrized test (WP03)
- [x] T015 `test_codebase_sweep.py` — delete the vacuous standalone-scripts sweep test (WP03)

Prompt: [tasks/WP03-surgical-test-reconciliation.md](./tasks/WP03-surgical-test-reconciliation.md) (~420 lines)

## WP04 — Delete the surface + scaffolding + ratchet shed (FR-001/002/003/006/007)

**Goal**: Atomically remove the standalone surface and everything that referenced it: delete the 3 copies, the 5 DELETE-class test files, the `tests/utils.py` sys.path injection / `run_tasks_cli`, `conftest.py::ensure_imports`, the pyproject entries, and shed every dead architectural-ratchet/audit entry — recomputing baselines to live sizes. Suite collects + green at the end.
**Priority**: P1
**Independent test**: `grep specify_cli.scripts.tasks` repo-wide → none; full suite + architectural suite green; ruff + mypy clean; `_baselines.yaml` equals live frozenset sizes.
**Requirements**: FR-001, FR-002, FR-003, FR-006, FR-007, C-002
**Dependencies**: WP03

- [ ] T016 Delete the 3 standalone copies (FR-001/002/003) (WP04)
- [ ] T017 Delete the 5 DELETE-class test files + empty `tests/specify_cli/scripts/` package tree (WP04)
- [ ] T018 Remove `tests/utils.py` sys.path injection + `run_tasks_cli`; delete `conftest.py::ensure_imports` (WP04)
- [ ] T019 Update `pyproject.toml` — drop the `scripts/tasks` ruff ignores + `specify_cli.scripts.tasks.*` entries (WP04)
- [ ] T020 FR-007 ratchet shed: remove dead allowlist/audit entries across all gate files (WP04)
- [ ] T021 Recompute `_baselines.yaml` `category_b` + `category_3` to live frozenset sizes (WP04)
- [ ] T022 Verify: `grep specify_cli.scripts.tasks` repo-wide → none; full suite + architectural + ruff + mypy green (WP04)

Prompt: [tasks/WP04-delete-surface-and-ratchet.md](./tasks/WP04-delete-surface-and-ratchet.md) (~460 lines)

---

## MVP / sequencing
The mission has no partial-MVP — all four WPs are required for a coherent, green end state. WP01 is the safe de-risk-first step; WP04 is the irreversible deletion that must land last. Strictly sequential; no parallel lanes.
