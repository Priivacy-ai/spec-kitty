# Mission Review Report: coordination-topology-stabilization-01KTZVQ2

**Reviewer**: claude:sonnet-4-6:mission-reviewer
**Date**: 2026-06-13
**Mission**: `coordination-topology-stabilization-01KTZVQ2` — Coordination Topology Stabilization
**Baseline commit**: `b81e9eae94514833adba9960ac3a33a04c18ab2c`
**HEAD at review**: `75fdeb785` (via `ccc884f61` done-transitions, `991162c0a` squash merge)
**WPs reviewed**: WP01–WP10

---

## Gate Results

### Gate 1 — Contract tests

**Result: FAIL with mission-introduced regressions (2 of 5 failures are new)**

Run: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/pytest tests/contract/ -q`
Outcome: **5 failed, 253 passed** (40.70 s)

| Test | Classification | Detail |
|------|---------------|--------|
| `test_charter_compact_includes_section_anchors[minimal.md]` | Pre-existing | Not introduced by this mission; no mission commits touch the charter compact code path. |
| `test_charter_compact_includes_section_anchors[multidirective.md]` | Pre-existing | Same as above. |
| `test_contract_example_round_trip[doctrine-glossary…MISSING_FRONTMATTER]` | Pre-existing | Contract file predates this mission's baseline; no mission commits touch it. |
| `test_orchestrator_api.py::test_safe_commit_failure_codes_are_contract_allowed` | **Mission-introduced** | `SAFE_COMMIT_PATH_POLICY` error code (introduced by WP02 in `commit_helpers.py`) is emitted by the runtime but is absent from `src/specify_cli/core/upstream_contract.json`'s `allowed_error_codes` array. The contract JSON must be extended; the test is correctly enforcing the boundary. |
| `test_next_no_unknown_state.py::test_query_decision_for_missing_feature_dir_is_structured` | **Mission-introduced** | WP03 changed `query_current_state` to raise `MissionNotFoundError` instead of returning a `Decision`. The contract test still calls the deprecated `specify_cli.next.runtime_bridge.query_current_state` shim and expects a `Decision` return value. The test itself needs to be updated to either (a) catch `MissionNotFoundError` and assert its structured fields, or (b) import from `runtime.next` directly. The underlying behaviour (structured error on miss) is correct per FR-004. |

**Required follow-up actions (blocking for CI):**
1. Add `"SAFE_COMMIT_PATH_POLICY"` to `allowed_error_codes` in `src/specify_cli/core/upstream_contract.json`.
2. Update `tests/contract/test_next_no_unknown_state.py::test_query_decision_for_missing_feature_dir_is_structured` to assert `MissionNotFoundError` is raised (structured exception) rather than expecting a `Decision` return.

### Gate 2 — Architectural tests

**Result: FAIL with mission-introduced regressions (3 of 4 failures are new)**

Run: `.venv/bin/pytest tests/architectural/ -q`
Outcome: **4 failed, 347 passed** (125.89 s)

| Test | Classification | Detail |
|------|---------------|--------|
| `test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported` | **Mission-introduced** | WP04 added `GlobValidationResult` and `is_glob_pattern` to `__all__` in `src/specify_cli/ownership/validation.py`, but no other `src/` file imports them. They are used internally (the function calls itself and the class is instantiated within the module) but neither is consumed by a production entry-point import. Fix: remove both names from `__all__`, or wire an import from a production caller. |
| `test_pytest_marker_convention.py::test_every_test_file_declares_a_pytestmark_marker` | **Mission-introduced** | Two new test files introduced by this mission (`tests/architectural/test_worktrees_index_clean.py` and `tests/post_merge/test_stale_assertions_message.py`) are missing a module-level `pytestmark` declaration. |
| `test_pytest_marker_correctness.py::test_subprocess_git_users_must_carry_git_repo_marker` | **Mission-introduced** | Three new test files that call `git` via `subprocess` are missing the `git_repo` marker: `tests/architectural/test_worktrees_index_clean.py`, `tests/specify_cli/missions/test_is_committed_coord_aware.py`, and `tests/specify_cli/test_worktrees_index.py`. This silently excludes them from CI's `-m git_repo` filter. |
| `test_status_module_boundary.py::test_ast_scan_no_direct_status_imports_repo_wide` | Pre-existing | `src/specify_cli/migration/mission_state.py:43` imports `specify_cli.status.store` directly. This file was not modified by this mission and the violation predates the baseline. |

**Required follow-up actions (blocking for CI):**
1. Add `pytestmark = [pytest.mark.architectural]` (or appropriate category) to `tests/architectural/test_worktrees_index_clean.py`.
2. Add `pytestmark = [pytest.mark.unit]` (or appropriate category) to `tests/post_merge/test_stale_assertions_message.py`.
3. Add `git_repo` marker to `tests/architectural/test_worktrees_index_clean.py`, `tests/specify_cli/missions/test_is_committed_coord_aware.py`, and `tests/specify_cli/test_worktrees_index.py` (alongside each file's existing category marker).
4. Either remove `GlobValidationResult` and `is_glob_pattern` from `__all__` in `src/specify_cli/ownership/validation.py`, or add a production import.

### Gate 3 — Cross-repo E2E

**Result: BLOCKED (environmental — not a code defect)**

The `spec-kitty-end-to-end-testing` repository is not present at the sibling path `/Users/robert/spec-kitty-dev/spec-kitty-20260612-090944-mmoj1h/`. This is an environment gap, not a failure of mission code. Operator exception applied per the cross-repo E2E environmental blocker path.

### Gate 4 — Issue Matrix

**Result: PASS**

All rows carry a valid verdict. No `unknown` or empty verdict cells.

| Issue | Verdict | Status |
|-------|---------|--------|
| #1164 | `in-mission` | Addressed by WP07 + WP08 |
| #1878 | `in-mission` | Addressed by WP09 |
| #1883 | `in-mission` | Addressed by WP06 |
| #1884 | `in-mission` | Addressed by WP01 |
| #1885 | `in-mission` | Addressed by WP03 |
| #1886 | `fixed` | 5480c58e8; WP05 |
| #1887 | `fixed` | WP02 root anchor + SafeCommitPathPolicyError + ratchet |
| #1888 | `in-mission` | Addressed by WP07 + WP08 |
| #1895 | `deferred-with-followup` | Tracked as T048 in WP01 |
| #1825 | `in-mission` | Addressed by WP10 |
| #1771 | `verified-already-fixed` | Landed before this mission |

Note: Six issues carry `in-mission` rather than `fixed`. Per WP reviewer notes, these represent bugs that were closed by mission code and merged to local main — `in-mission` is correct for issues resolved within the mission scope. The issue-matrix verdicts are consistent with the per-WP review evidence recorded in `status.events.jsonl`.

---

## FR Coverage Matrix

| FR ID | Description (brief) | WP Owner | Test File(s) | Test Adequacy | Finding |
|-------|---------------------|----------|-------------|--------------|---------|
| FR-001 | Accept gate not self-dirtying | WP06 | `tests/specify_cli/missions/test_accept_convergence.py`, `tests/integration/test_implement_review_flow.py` | Adequate — convergence scenario covered per WP06 review approval | No finding |
| FR-002 | `--no-commit` is read-only | WP06 | Covered within WP06 accept-gate tests | Adequate per WP06 review evidence | No finding |
| FR-003 | Setup-plan gate recognizes coord-branch spec | WP01 | `tests/specify_cli/missions/test_is_committed_coord_aware.py` | Adequate — direct test of the placement-aware `is_committed()` | **Marker gap**: missing `git_repo` marker (see Gate 2) |
| FR-004 | `next` emits structured error on mission-not-found | WP03 | `tests/specify_cli/cli/commands/test_next_fail_closed.py`, `tests/contract/test_next_no_unknown_state.py` | Partial — WP03 implementation is correct (13/13 tests per review), but `test_next_no_unknown_state.py` contract test now fails because it expects a `Decision` instead of `MissionNotFoundError` | **Contract gap**: test not updated after behavior change (see Gate 1) |
| FR-005 | No `.worktrees/` paths in git index | WP02 | `tests/architectural/test_worktrees_index_clean.py`, `tests/specify_cli/test_worktrees_index.py`, `tests/git_ops/test_worktree_exclusion_integration.py` | Adequate — ratchet test + write-side guard + exclusion integration | **Marker gap**: two files missing `pytestmark` / `git_repo` (see Gate 2) |
| FR-006 | Ownership warnings routed, zero-match is hard error | WP04 | `tests/specify_cli/status/test_wp_metadata.py`, `tests/tasks/test_finalize_tasks_wps_yaml_unit.py`, `tests/specify_cli/ownership/test_inference.py` | Adequate per WP04 review approval | **Dead symbol**: `GlobValidationResult`, `is_glob_pattern` exported in `__all__` but not consumed externally (see Gate 2) |
| FR-007 | Terminus retrospective fires on `merge` path | WP07 | `tests/next/test_retrospective_terminus_wiring.py`, `tests/integration/retrospective/test_default_flow_healthy.py` | Adequate — merge-completion postcondition covered; 10/10 tests per review | No finding |
| FR-008 | Retrospective ingestors read mission-local artifacts | WP08 | `tests/retrospective/test_generator.py`, `tests/integration/retrospective/test_wp04_coverage_branches.py` | Adequate — golden-test fixture added for mission-131; `ran_no_findings` guard removed per WP08 review | No finding |
| FR-009 | Stale-assertion analyzer suppresses message-capture FPs | WP05 | `tests/post_merge/test_stale_assertions_message.py`, `tests/post_merge/test_stale_assertions.py` | Adequate — classifier logic tested; `test_stale_assertions_message.py` is the direct regression test | **Marker gap**: `test_stale_assertions_message.py` missing `pytestmark` (see Gate 2) |
| FR-010 | Zero manual ff-merges through full lifecycle | WP09 | `tests/specify_cli/missions/test_ffmerge_treadmill.py`, subtasks T041–T044 | Adequate — end-to-end test of zero-manual-ff lifecycle per WP09 | No finding |

---

## Drift Findings

No spec/plan/implementation drift found. All 10 WPs address FRs and issues named in `spec.md`. WP tasks track directly to FRs: WP01→FR-003, WP02→FR-005, WP03→FR-004, WP04→FR-006, WP05→FR-009, WP06→FR-001/FR-002, WP07→FR-007, WP08→FR-008, WP09→FR-010, WP10→FR-005 (cleanup). No out-of-scope changes detected in git diff.

---

## Risk Findings

### RISK-01 (Medium): Contract JSON not updated for new error code

`src/specify_cli/core/upstream_contract.json` does not include `SAFE_COMMIT_PATH_POLICY` in `allowed_error_codes`. This error code is raised by the new `path_is_under_worktrees()` rejection gate (WP02, `commit_helpers.py:302`). Any orchestrator agent that validates the error code against the contract will silently reject the new error as out-of-contract. The `test_safe_commit_failure_codes_are_contract_allowed` contract test correctly catches this and is currently failing.

**Resolution**: Add `"SAFE_COMMIT_PATH_POLICY"` to `allowed_error_codes` in `upstream_contract.json`.

### RISK-02 (Medium): Three new git-subprocess test files excluded from CI's `git_repo` filter

`tests/architectural/test_worktrees_index_clean.py`, `tests/specify_cli/missions/test_is_committed_coord_aware.py`, and `tests/specify_cli/test_worktrees_index.py` all call `git` via `subprocess` but lack the `git_repo` marker. In CI environments that run only `-m git_repo` tests (e.g., git-aware sandboxes), these three regression tests will be silently skipped, defeating their purpose.

**Resolution**: Add `git_repo` to each file's `pytestmark` list.

### RISK-03 (Low): Contract test for FR-004 is mis-targeted

`test_next_no_unknown_state.py` calls the deprecated `specify_cli.next` shim and expects a `Decision` return. After WP03, `MissionNotFoundError` is raised instead. The test is now a false red: the correct behavior is implemented, but the test does not exercise it. Until fixed, CI will flag this as a failure, potentially causing developers to distrust the test suite.

**Resolution**: Update the test to import from `runtime.next` and assert `MissionNotFoundError` with the expected structured fields.

---

## Silent Failure Candidates

### SFC-01: Retrospective fail-open on `merge` path

`run_retrospective_postcondition()` in `src/specify_cli/lanes/merge.py` (wired at merge.py:2894–2898) wraps the retrospective call in `except Exception: # noqa: BLE001 — fail-open`. When the retrospective fails, the merge completes silently. FR-007 requires that a `RetrospectiveSkipped` or `CaptureFailed` event be recorded in the mission event log on failure. Per the WP07 review approval, this event emission is implemented. Confirmed in `src/specify_cli/post_merge/retrospective_terminus.py`. **Assessment**: acceptable; fail-open is the correct policy for a non-blocking post-merge hook, and the event emission satisfies FR-007's observability requirement.

### SFC-02: `_read_mission_id_from_meta()` in merge.py swallows all exceptions

The `_read_mission_id_from_meta()` helper (introduced for WP07 retrospective triggering) wraps its JSON read in `except Exception: # noqa: BLE001` and returns `""` on any failure. If `meta.json` is absent or malformed, the retrospective is silently skipped without a `RetrospectiveSkipped` event, because the mission_id required to emit the event is unavailable. **Assessment**: low-severity edge case (meta.json is written at mission creation and its absence would indicate a broader corruption), but worth noting as an observability gap. A follow-up to emit a `CaptureFailed` event even when mission_id is unavailable would close this.

---

## Security Notes

No `subprocess` calls were added in mission `src/` code. All new `subprocess` usage is confined to new test files (git operations in test fixtures). No `shell=True` or `Popen` additions found in `src/`. All `noqa: BLE001` suppressions in `src/` are narrowly scoped to fail-open patterns (retrospective, mission-id read) with inline rationale; none suppress security-sensitive exception classes. No hard-coded credentials or secrets detected.

---

## Final Verdict

**PASS WITH NOTES**

### Verdict rationale

The mission correctly implements all 10 FRs and fixes or addresses all 8 confirmed defects. All WPs were reviewed and approved by Robert Douglass with explicit per-WP test counts (ranging from 4 to 13 passing tests each). Core logic — coord-aware `is_committed()`, `.worktrees/` rejection gates, `MissionNotFoundError` structured errors, retrospective triggering at merge, stale-assertion message-content classifier, ff-merge treadmill elimination — is implemented and regression-tested.

The verdict is **not PASS** due to 5 mission-introduced test failures (2 contract, 3 architectural) that are blocking CI and represent incomplete follow-through on implementation quality gates. None of these failures indicate a defect in the primary bug fixes; they are all hygiene and wiring gaps that must be resolved before this mission can be considered fully closed.

The verdict is **not FAIL** because:
- The bug-fix logic itself is correct and tested.
- All failures are isolated hygiene gaps with clear, mechanical fixes.
- No regressions were introduced in previously-passing tests beyond the 5 documented here.
- The contract test failure for FR-004 (`test_next_no_unknown_state`) is a test-update lag, not a code defect — the implementation is correct.

### Open items (blocking CI — must resolve before merge to origin/main)

| Item | Severity | File(s) | Fix |
|------|----------|---------|-----|
| OI-01 | High | `src/specify_cli/core/upstream_contract.json` | Add `"SAFE_COMMIT_PATH_POLICY"` to `allowed_error_codes` |
| OI-02 | High | `tests/contract/test_next_no_unknown_state.py` | Update to assert `MissionNotFoundError` instead of expecting `Decision` return |
| OI-03 | High | `tests/architectural/test_worktrees_index_clean.py` | Add `pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]` |
| OI-04 | High | `tests/post_merge/test_stale_assertions_message.py` | Add `pytestmark = [pytest.mark.unit]` (or appropriate category) |
| OI-05 | High | `tests/specify_cli/missions/test_is_committed_coord_aware.py` | Add `git_repo` to existing `pytestmark` |
| OI-06 | High | `tests/specify_cli/test_worktrees_index.py` | Add `git_repo` to existing `pytestmark` |
| OI-07 | Medium | `src/specify_cli/ownership/validation.py` | Remove `GlobValidationResult` and `is_glob_pattern` from `__all__`, or wire a production import |

### Open items (non-blocking, follow-up recommended)

| Item | Severity | Detail |
|------|----------|--------|
| ONB-01 | Low | `_read_mission_id_from_meta()` swallows exceptions and returns `""`, silently skipping the retrospective without a `CaptureFailed` event when `meta.json` is unreadable. |
| ONB-02 | Low | Pre-existing: `src/specify_cli/migration/mission_state.py:43` imports `specify_cli.status.store` directly (violates status module boundary). Not introduced by this mission. |
| ONB-03 | Info | `#1895` (name-vs-authority-remediation) remains deferred per C-004; tracked as T048. Confirm follow-up ticket is filed before next mission batch. |

---

## Retrospective Reminder

Per FR-007 and WP07, the terminus retrospective should fire automatically when this mission is merged via `spec-kitty merge`. Verify `retrospective.yaml` is written to the mission directory after merge, or confirm a `RetrospectiveSkipped` event is present in `status.events.jsonl` if the retrospective was unable to run. If neither is present, trigger manually via `spec-kitty agent retrospect`.
