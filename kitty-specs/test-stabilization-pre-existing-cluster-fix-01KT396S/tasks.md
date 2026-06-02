# Tasks: Test Stabilization — Pre-Existing Failure Cluster Fix

**Mission**: test-stabilization-pre-existing-cluster-fix-01KT396S
**Branch**: `kitty/mission-test-stabilization-pre-existing-cluster-fix-01KT396S`
**Target**: `main`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Locate the two broken glossary context files with bad link fragments | WP01 | — |
| T002 | Fix `#doctrine-pack` anchor (add heading or correct fragment) | WP01 | [P] |
| T003 | Fix `#platform-darwin--platform-linux` anchor | WP01 | [P] |
| T004 | Locate and fix `five-paradigm-parallel-debugging` tactic schema | WP01 | [P] |
| T005 | Run `pytest tests/doctrine/` to confirm green | WP01 | — |
| T006 | Grep `src/charter/synthesizer/` for direct write primitives (not PathGuard) | WP02 | — |
| T007 | Route all found direct writes through PathGuard methods | WP02 | — |
| T008 | Verify/add sort-by-(kind,slug) before manifest hash in promote pipeline | WP02 | — |
| T009 | Regenerate stale test fixtures if manifest hash format changed | WP02 | — |
| T010 | Run `pytest tests/charter/synthesizer/` to confirm all four target tests green | WP02 | — |
| T011 | Audit `src/specify_cli/next/__init__.py` for DecisionKind→exit-code mapping | WP03 | — |
| T012 | Fix exit-code mapping (terminal→0, blocked→non-zero, step→0) | WP03 | — |
| T013 | Trace engine/runtime_bridge for success→query vs success→decide routing bug | WP03 | — |
| T014 | Fix result-success routing to call `decide_next` not `query_next` | WP03 | — |
| T015 | Run the four failing next tests to confirm green | WP03 | — |
| T016 | Diagnose auth test fixture: find missing config causing Typer exit code 2 | WP04 | — |
| T017 | Fix auth test fixture to provide required config for `sync status --check` | WP04 | — |
| T018 | Add autouse conftest fixture to reset `logged_out_on_connected_teamspace` after each invocation test | WP04 | — |
| T019 | Audit schema-version message change: update test assertion or restore message | WP04 | — |
| T020 | Run `test_all_kitty_specs_wp_files_validate` to enumerate the 6 failing WP files | WP04 | — |
| T021 | Update the 6 WP JSON files to conform to the current Pydantic model | WP04 | — |
| T022 | Verify all WP04 target tests green | WP04 | — |
| T023 | Run `mypy --strict` on `executor.py`, document all type errors | WP05 | — |
| T024 | Add type annotations to `executor.py` until mypy --strict passes | WP05 | — |
| T025 | Read mission switching guard logic; identify the blocking condition | WP05 | — |
| T026 | Fix mission switching guard to allow valid mission-type transitions | WP05 | — |
| T027 | Trace `--base` flag from CLI through to bulk-edit gate; fix the broken layer | WP05 | — |
| T028 | Run architectural tests; identify and fix the package-boundary violation | WP05 | — |
| T029 | Attempt init skill test; skip with reason if externally blocked | WP05 | — |
| T030 | Verify all WP05 target tests green | WP05 | — |
| T031 | Run `pytest tests/charter/ -x`; capture first failure and its import path | WP06 | — |
| T032 | Trace the failing import through `charter_runtime/` shim layer | WP06 | — |
| T033 | Repair missing shim re-exports for all failing symbols | WP06 | — |
| T034 | Run `pytest tests/charter/` iteratively; fix remaining shim gaps | WP06 | — |
| T035 | Confirm all five charter integration sub-suites pass | WP06 | — |

---

## Work Packages

### WP01 — Doctrine/Glossary Content Fixes

**Priority**: High (standalone, fastest path to closing #1304)
**Lane**: A
**Estimated prompt size**: ~320 lines
**Dependencies**: none

**Goal**: Repair two broken markdown link fragments in `glossary/contexts/` and fix the invalid `five-paradigm-parallel-debugging` tactic schema. Makes `test_glossary_link_integrity` (× 2) and `test_tactic_compliance` (× 2) pass.

**Subtasks**:
- [x] T001 Locate the two broken glossary context files with bad link fragments (WP01)
- [x] T002 Fix `#doctrine-pack` anchor — add heading or correct fragment (WP01)
- [x] T003 Fix `#platform-darwin--platform-linux` anchor — add heading or correct fragment (WP01)
- [x] T004 Locate and fix `five-paradigm-parallel-debugging` tactic schema (WP01)
- [x] T005 Run `pytest tests/doctrine/` to confirm green (WP01)

**Parallel opportunities**: T002, T003, T004 can be fixed in parallel (different files).

**Risks**: Double-dash in `#platform-darwin--platform-linux` is unusual — may be an anchor in the target file or may require adding a heading with exactly that slug. Use the slugification algorithm from the test to verify.

**Closes**: GitHub issue #1304

**Prompt**: [tasks/WP01-doctrine-glossary-content-fixes.md](tasks/WP01-doctrine-glossary-content-fixes.md)

---

### WP02 — Charter Synthesizer Hash Determinism + PathGuard

**Priority**: High (blocks WP06; closes #1303)
**Lane**: B
**Estimated prompt size**: ~370 lines
**Dependencies**: none

**Goal**: Ensure all synthesizer writes route through PathGuard and that manifest hashes are computed deterministically (sort-before-hash). Makes `test_manifest`, `test_path_guard`, `test_chokepoint_coverage`, `test_bundle_validate_cli` pass.

**Subtasks**:
- [ ] T006 Grep `src/charter/synthesizer/` for direct write primitives outside PathGuard (WP02)
- [ ] T007 Route all found direct writes through PathGuard methods (WP02)
- [ ] T008 Verify/add sort-by-(kind,slug) before manifest hash in promote pipeline (WP02)
- [ ] T009 Regenerate stale test fixtures if manifest hash format changed (WP02)
- [ ] T010 Run `pytest tests/charter/synthesizer/` to confirm all target tests green (WP02)

**Risks**: If the sort was already present but hashes are still non-deterministic, the cause may be timestamp fields or OS-dependent dict ordering — audit carefully.

**Closes**: GitHub issue #1303

**Prompt**: [tasks/WP02-charter-synthesizer-hash-pathguard.md](tasks/WP02-charter-synthesizer-hash-pathguard.md)

---

### WP03 — `next` CLI Exit-Code Regressions

**Priority**: High (standalone, closes #1305)
**Lane**: A (after WP01)
**Estimated prompt size**: ~340 lines
**Dependencies**: none

**Goal**: Fix the `next` CLI so exit codes match the `DecisionKind` contract and the `decide` path is taken on result-success. Makes `test_blocked_result_exit_code`, `test_terminal_state_exit_code_zero`, `test_advancing_mode_with_result_*`, `test_result_success_calls_decide_not_query` pass.

**Subtasks**:
- [ ] T011 Audit `src/specify_cli/next/__init__.py` for DecisionKind→exit-code mapping (WP03)
- [ ] T012 Fix exit-code mapping (terminal→0, blocked→non-zero, step→0) (WP03)
- [ ] T013 Trace engine/runtime_bridge for success→query vs success→decide routing bug (WP03)
- [ ] T014 Fix result-success routing to call `decide_next` not `query_next` (WP03)
- [ ] T015 Run the four failing next tests to confirm green (WP03)

**Risks**: The exit-code mapping and the query/decide routing may be two independent bugs, or one may cause the other. Fix the routing first (T013–T014) then verify exit codes.

**Closes**: GitHub issue #1305

**Prompt**: [tasks/WP03-next-cli-exit-code-fix.md](tasks/WP03-next-cli-exit-code-fix.md)

---

### WP04 — #1310 Residual: Auth, Invocation, Schema Version, WP Files

**Priority**: High (closes half of #1310 residual)
**Lane**: C
**Estimated prompt size**: ~460 lines
**Dependencies**: none

**Goal**: Fix four independent sub-failures from the #1310 residual cluster: auth transport exit code 2, invocation JSON noise, schema-version wording drift, and 6 WP files failing Pydantic validation.

**Subtasks**:
- [ ] T016 Diagnose auth test fixture: find the missing config causing Typer exit code 2 (WP04)
- [ ] T017 Fix auth test fixture to provide required config for `sync status --check` (WP04)
- [ ] T018 Add autouse conftest fixture to reset `logged_out_on_connected_teamspace` after each invocation test (WP04)
- [ ] T019 Audit schema-version message: update test assertion or restore production message (WP04)
- [ ] T020 Run `test_all_kitty_specs_wp_files_validate` to enumerate the 6 failing WP files (WP04)
- [ ] T021 Update the 6 WP JSON files to conform to the current Pydantic model (WP04)
- [ ] T022 Verify all WP04 target tests green (WP04)

**Risks**: Auth exit code 2 may require tracing multiple config layers. The 6 WP files may have different errors each — enumerate before bulk-fixing.

**Prompt**: [tasks/WP04-1310-auth-invocation-schema-wp-files.md](tasks/WP04-1310-auth-invocation-schema-wp-files.md)

---

### WP05 — #1310 Residual: mypy, Mission Switching, Base-Flag, Architectural

**Priority**: High (closes remaining #1310 residual)
**Lane**: C (after WP04)
**Estimated prompt size**: ~500 lines
**Dependencies**: WP04 (isolation — run after WP04 to avoid conftest pollution)

**Goal**: Fix the remaining five #1310 sub-failures: mypy strict on executor.py, mission switching blocked, --base flag plumbing, architectural boundary violations, and the init skill (skip if externally blocked).

**Subtasks**:
- [ ] T023 Run `mypy --strict` on `executor.py`, document all type errors (WP05)
- [ ] T024 Add type annotations to `executor.py` until mypy --strict passes (WP05)
- [ ] T025 Read mission switching guard logic; identify the blocking condition (WP05)
- [ ] T026 Fix mission switching guard to allow valid mission-type transitions (WP05)
- [ ] T027 Trace `--base` flag from CLI through to bulk-edit gate; fix the broken layer (WP05)
- [ ] T028 Run architectural tests; identify and fix the package-boundary violation (WP05)
- [ ] T029 Attempt init skill test; skip with reason if externally blocked (WP05)
- [ ] T030 Verify all WP05 target tests green (WP05)

**Risks**: The init skill dependency on an external mission may not be resolvable. The skip is acceptable; document clearly.

**Closes**: GitHub issue #1310 (residual)

**Prompt**: [tasks/WP05-1310-mypy-switching-baseflag-arch.md](tasks/WP05-1310-mypy-switching-baseflag-arch.md)

---

### WP06 — Charter Integration Suite

**Priority**: High (closes #1307)
**Lane**: B (after WP02)
**Estimated prompt size**: ~360 lines
**Dependencies**: WP02

**Goal**: Repair the `charter_runtime/` shim re-exports broken by the WP06/WP08 charter.py split. Makes the full charter integration suite pass across all five sub-suites.

**Subtasks**:
- [ ] T031 Run `pytest tests/charter/ -x`; capture first failure and its import path (WP06)
- [ ] T032 Trace the failing import through `charter_runtime/` shim layer (WP06)
- [ ] T033 Repair missing shim re-exports for all failing symbols (WP06)
- [ ] T034 Run `pytest tests/charter/` iteratively; fix remaining shim gaps (WP06)
- [ ] T035 Confirm all five charter integration sub-suites pass (WP06)

**Risks**: Multiple shim gaps may exist — the iterative approach (T034) handles this. Do not assume one gap fix resolves all failures.

**Closes**: GitHub issue #1307

**Prompt**: [tasks/WP06-charter-integration-suite.md](tasks/WP06-charter-integration-suite.md)

---

## Execution Lanes Summary

| Lane | WPs | Parallelizable with |
|------|-----|---------------------|
| A | WP01 → WP03 | Lanes B and C |
| B | WP02 → WP06 | Lanes A and C |
| C | WP04 → WP05 | Lanes A and B |

All three lanes run concurrently. Within each lane, WPs run sequentially.
