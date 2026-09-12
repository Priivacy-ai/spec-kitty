# Tasks: CI Suite Stability & Test-Isolation

**Mission**: ci-suite-stability-test-isolation-01M22MM5 (#4017 + #4015, epic #1931)
**Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)
**Planning base / merge target**: `issue-4017-ci-suite-stability`

Two independent lanes. **Lane A (#4017)** = runtime concurrency fix (sequential A-chain, high rigour). **Lane B (#4015)** = mechanical timing-guard sweep (B1 enabler → parallel per-subsystem split WPs). Tests are in scope (ATDD red-first).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Author deterministic apply-interleave test (force loser to observe winner mid-materialize) — RED on current code | WP01 | |
| T002 | Capture + record the exact "Global asset input changed" repro via the installed-CLI concurrent harness (RED snapshot, before any code change) | WP01 | |
| T003 | Role-tag observe() entries source-read vs destination-probe in asset_preparation.py (do NOT strip observations) | WP02 | |
| T004 | Filter destination-probe nodes at the check_assets compare-site; keep source-drift detection | WP02 | |
| T005 | Document the intermediate "File exists" state after role-tag-alone (proves the P1 blocker) | WP02 | |
| T006 | Re-assess-under-lock in ensure_runtime cold/effects path (recompute effects vs warm home → effects==[] → warm return); gate to cold path only | WP03 | |
| T007 | Emit OPERATOR_SIGNAL_CONTRACT human+machine signal on the converged-no-op path; red-first asserts on the SIGNAL | WP03 | |
| T008 | Un-skip + DRIVE both quarantined e2e tests for real (test_installed_cli_keeps_two_owned_worktrees_isolated + the 90d9be8823 charter epic test) | WP03 | |
| T009 | Source-drift guard test: a genuine package-source change between assess and apply is still caught (FR-003) | WP03 | |
| T010 | FR-007 live-composition regression: drive managed_skills composition apply (global_assets recheck + _recheck_command_completion under one lock); #4082 YAML-receipt suppression holds | WP03 | |
| T011 | Warm-path test: exactly one assess, no lock (NFR-002) | WP03 | |
| T012 | Generic-scope acceptance: drive the real global_assets batch path through a NON-runtime owner + the merge.py recheck nesting | WP04 | |
| T013 | Verify-or-exclude _recheck_command_completion (managed_skills.py:165) — confirm it needs no equivalent re-assess or bring into scope with rationale | WP04 | |
| T014 | Create tests/_perf_helpers.py::assert_timing_budget(measured, budget) (guard-clean call-site) | WP05 | |
| T015 | Triage ALL delete candidates (flake-rate + AST zero-functional-assert) → ONE consolidated operator sign-off (HiC); record dispositions | WP05 | |
| T016 | Create + own the master per-split coverage-mapping table (original→functional-retained-per-PR / timing-relocated) | WP05 | |
| T017 | tests/specify_cli/** timing tests: split mixed (functional per-PR / timing @performance nightly) + remediate vocab-blocked; append mapping rows | WP06 | [P] |
| T018 | tests/charter + tests/doctrine + tests/glossary + tests/cli timing tests (incl. vocab-blocked resolution_overhead/observation/reconcile): split + remediate; append mapping | WP07 | [P] |
| T019 | tests/zeitgeist_client + tests/cross_cutting + tests/status + tests/review + tests/auth timing tests: split + remediate; append mapping | WP08 | [P] |
| T020 | tests/retrospective + tests/regressions + tests/integration + tests/docs + remaining singles timing tests (incl. vocab-blocked docs_structural_lint): split + remediate; append mapping; lane-cycle functional now per-PR | WP09 | [P] |

## Work Packages

### WP01 — #4017 red-first capture (Lane A)
- **Goal**: Before any code change, capture the exact `"Global asset input changed"` signal (installed-CLI concurrent harness) + author the deterministic apply-interleave RED test. (FR-006)
- **Priority**: P1 (must precede A1 — role-tag flips the signal to "File exists").
- **Independent test**: the deterministic interleave test is RED with the exact signal on current code; the repro is recorded.
- **Subtasks**: T001, T002 · **Dependencies**: none
- **Risk**: if A1 lands first, the exact signal is unreproducible — this WP exists to prevent that.
- **Prompt**: [tasks/WP01-4017-red-first-capture.md](./tasks/WP01-4017-red-first-capture.md)

### WP02 — #4017 role-tag enabler (Lane A)
- **Goal**: Role-tag observe() source/destination + filter at check_assets; do NOT strip observations; document the intermediate File-exists state. (FR-002)
- **Priority**: P1 enabler · **Subtasks**: T003, T004, T005 · **Dependencies**: WP01
- **Risk**: over-narrowing (dropping source-drift detection) — guarded by WP03 T009.
- **Prompt**: [tasks/WP02-4017-role-tag-enabler.md](./tasks/WP02-4017-role-tag-enabler.md)

### WP03 — #4017 re-assess-under-lock core fix (Lane A)
- **Goal**: The race fix — re-assess under the held lock + operator signal + un-skip/drive e2e + source-drift guard + FR-007 live-composition regression + warm-path. (FR-001, FR-003, FR-005, FR-006, FR-007)
- **Priority**: P1 · **Subtasks**: T006–T011 · **Dependencies**: WP02
- **Risk**: poisoning the warm fast-path; operator-signal dropped; composition interplay regressed.
- **Prompt**: [tasks/WP03-4017-reassess-under-lock.md](./tasks/WP03-4017-reassess-under-lock.md)

### WP04 — #4017 generic-scope verification (Lane A)
- **Goal**: Prove the HiC "Generic — all owners" ruling — drive a non-runtime owner + merge.py nesting; verify-or-exclude _recheck_command_completion. (FR-004)
- **Priority**: P2 · **Subtasks**: T012, T013 · **Dependencies**: WP03
- **Prompt**: [tasks/WP04-4017-generic-scope-verify.md](./tasks/WP04-4017-generic-scope-verify.md)

### WP05 — #4015 helper + delete-triage + coverage-mapping (Lane B enabler)
- **Goal**: assert_timing_budget helper; triage ALL delete candidates → ONE consolidated operator sign-off; own the master coverage-mapping table. (FR-008, FR-011, FR-013)
- **Priority**: P2 enabler · **Subtasks**: T014, T015, T016 · **Dependencies**: none
- **HiC**: T015 escalates the consolidated delete list for operator sign-off.
- **Prompt**: [tasks/WP05-4015-helper-triage-mapping.md](./tasks/WP05-4015-helper-triage-mapping.md)

### WP06 — #4015 split: tests/specify_cli/** (Lane B)
- **Goal**: Split/remediate the specify_cli timing tests (~18). (FR-009, FR-010, FR-012)
- **Subtasks**: T017 · **Dependencies**: WP05 · **[P]** with WP07–09
- **Prompt**: [tasks/WP06-4015-split-specify-cli.md](./tasks/WP06-4015-split-specify-cli.md)

### WP07 — #4015 split: charter/doctrine/glossary/cli (Lane B)
- **Goal**: Split/remediate timing tests incl. vocab-blocked (resolution_overhead, observation, reconcile). (FR-009, FR-010, FR-012)
- **Subtasks**: T018 · **Dependencies**: WP05 · **[P]**
- **Prompt**: [tasks/WP07-4015-split-charter-glossary-cli.md](./tasks/WP07-4015-split-charter-glossary-cli.md)

### WP08 — #4015 split: zeitgeist/cross_cutting/status/review/auth (Lane B)
- **Goal**: Split/remediate timing tests (incl. auth_doctor <3s mixed). (FR-009, FR-010, FR-012)
- **Subtasks**: T019 · **Dependencies**: WP05 · **[P]**
- **Prompt**: [tasks/WP08-4015-split-zeitgeist-status-auth.md](./tasks/WP08-4015-split-zeitgeist-status-auth.md)

### WP09 — #4015 split: retrospective/regressions/integration/docs + singles (Lane B)
- **Goal**: Split/remediate remaining timing tests (incl. vocab-blocked docs_structural_lint; lane-cycle functional now per-PR). (FR-009, FR-010, FR-012)
- **Subtasks**: T020 · **Dependencies**: WP05 · **[P]**
- **Prompt**: [tasks/WP09-4015-split-remaining.md](./tasks/WP09-4015-split-remaining.md)

## Cross-lane coordination
- `tests/_next_shard_map.py` is edited by BOTH lanes (new/relocated test files) — serialize or union-resolve at merge.
- MVP: WP01→WP03 delivers the #4017 fix (the P2 user-facing bug). Lane B is P3 chore, fully parallel.
