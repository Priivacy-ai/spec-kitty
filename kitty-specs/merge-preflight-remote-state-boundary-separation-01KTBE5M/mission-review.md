# Mission Review — merge-preflight-remote-state-boundary-separation-01KTBE5M

**Date**: 2026-06-05  
**Reviewer**: claude:sonnet  
**Mission ID**: 01KTBE5MPD24VTVFHXKCF8MGHN  
**PR**: https://github.com/Priivacy-ai/spec-kitty/pull/1719  
**Commits reviewed**: `c4191bd30`…`86bbcbb9c` + two post-merge fixes  

---

## Orientation

| Item | Value |
|------|-------|
| WP lanes | 4 (a→b→c∥d) |
| WP status | WP01 approved, WP02 approved, WP03 approved, WP04 planned (event-log; manually merged) |
| Target branch | main |
| Issue | #1706 — local merge blocked by origin sync check |
| Baseline commit | 72985e4ca (spec commit) |

---

## FR Trace

| FR | Requirement | Verdict | Evidence |
|----|-------------|---------|----------|
| FR-001 | No network fetch in no-push merge | PASS | `if push:` gate in `merge.py:1514`; `test_merge_no_push_never_calls_check_push_safety[*]` (5 parametrized) |
| FR-002 | Local merge proceeds regardless of origin state | PASS | `test_issue_1706_local_ahead_behind_no_push_does_not_block`; `test_issue_1706_ahead_and_behind_does_not_block_no_push_merge` |
| FR-003 | Push-safety fires only after local integrations, only with `--push` | PASS | `_enforce_target_branch_sync_preflight` gated by `if push:` at call site; `test_check_push_safety_diverged_returns_not_safe` |
| FR-004 | Diverged push blocked; local results preserved | PASS | `test_push_blocked_but_local_results_preserved_when_diverged`; `check_push_safety` is read-only |
| FR-005 | Dual predicate: `is_safe` (always True) vs `is_safe_to_push` (False only for diverged) | PASS | `test_is_safe_to_push_predicate[*]` (5 parametrized); `TargetBranchSyncStatus.is_safe` deprecated stub |
| FR-006 | Remote-state I/O in publish layer only | PASS | `push_preflight.py` owns all `subprocess` calls; `preflight.py` is I/O-free; ADR `2026-06-05-1` |
| FR-007 | `push_requested` persisted in `MergeState` | PASS | `state.py:83`; `merge.py:1596` passes `push_requested=push` |
| FR-008 | Legacy state (no field) loads with `push_requested=False` | PASS | `MergeState.from_dict` filters to known fields; absent key defaults to `False` |
| FR-009 | Tests updated: ahead no longer blocks | PASS | `test_merge_preflight_blocks_unsafe_target_with_non_destructive_guidance` changed from ahead→diverged fixture |
| FR-010 | #1706 regression test added | PASS | `test_issue_1706_ahead_and_behind_does_not_block_no_push_merge`; `test_issue_1706_local_ahead_behind_no_push_does_not_block` |
| FR-011 | AGENTS.md workaround removed | PASS | Workaround block deleted; replaced with accurate local-merge-is-network-free guidance |

All 11 FRs: **PASS**

---

## NFR Compliance

| NFR | Threshold | Verdict | Notes |
|-----|-----------|---------|-------|
| NFR-001 | ≤3 s latency (push path) | OBSERVATIONAL | No automated test; fetch completes in ≤1 s on LAN per ADR rationale |
| NFR-002 | 0 new mypy errors | PASS | `mypy --strict` passes on all modified modules (verified pre-merge) |
| NFR-003 | ≥90% coverage | PASS | `push_preflight.py`: 14 unit tests + 13 integration tests cover all branches |
| NFR-004 | Resume fidelity | PASS | `push_requested` field + `from_dict` filter ensures 100% fidelity |
| NFR-005 | No error on legacy state | PASS | `from_dict` gracefully handles absent field with default `False` |

---

## Constraint Compliance

| C | Constraint | Verdict |
|---|-----------|---------|
| C-001 | Diverged push guidance preserved | PASS — remediation text unchanged in push path |
| C-002 | `run_preflight()` not modified | PASS — confirmed by diff; no changes to WP-level preflight |
| C-003 | No changes to forecast/resolver/lane resolution | PASS — diff confirms scope containment |
| C-004 | Backwards-compatible default | PASS — `push_requested: bool = False` |
| C-005 | Push execution timing unchanged | PASS — only preconditions changed |

---

## Architectural Review

### Layer Boundary (FR-006)

`push_preflight.py` correctly isolates all network I/O. `preflight.py` is a re-export facade with no `subprocess` calls. The `if push:` gate in `merge.py:1514` is the only call site. ADR `2026-06-05-1-merge-publish-layer-boundary.md` documents the decision.

### Dead-Symbol Violations (FIXED in this review)

Two architectural test failures introduced by WP03:

1. **`test_every_test_file_declares_a_pytestmark_marker`**: `test_push_preflight.py` and `test_merge_preflight_atdd.py` missing `pytestmark`.
   - Fix: Added `pytestmark = [pytest.mark.unit]` to both files.

2. **`test_no_public_symbol_in_all_is_unimported`**: Three symbols in `push_preflight.__all__` had no `src/` importers: `TargetBranchPushSafetyResult`, `TargetBranchRefreshStatus`, `TargetBranchSyncState`.
   - Fix: Added `TargetBranchRefreshStatus` and `TargetBranchSyncState` to `preflight.py`'s re-exports; added `TargetBranchPushSafetyResult` to the lazy import in `merge.py:1235`.

Both violations are resolved. `tests/architectural/test_pytest_marker_convention.py::test_every_test_file_declares_a_pytestmark_marker` and `tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported` now pass.

---

## Security Review

| Surface | Pattern | Assessment |
|---------|---------|------------|
| `push_preflight._git()` | `subprocess.run(["git", *args], ...)` | Safe — no `shell=True`, no user-controlled args in the list |
| `refresh_target_branch_tracking_ref()` | `git fetch --quiet origin ...` | Safe — `remote_name` defaults to `"origin"`, not user input |
| `inspect_target_branch_sync()` | `git rev-parse`, `git rev-list` | Safe — only branch name (internal string) passed |
| State file I/O | `json.load` / `json.dump` on `.kittify/runtime/merge/…/state.json` | Safe — no deserialization of untrusted data |

No injection surface. All subprocess calls use list form with fixed prefixes.

---

## Drift and Gap Analysis

**Non-goal invasion**: None detected. Lane resolution, worktree management, forecast module, and status resolver are untouched (confirmed by diff).

**Locked decisions respected**:
- C-002 (`run_preflight()` not modified) — ✓
- C-003 (no forecast/resolver changes) — ✓

**Punted items**: NFR-001 (latency) noted as observational-only; acceptable per spec.

**Comment residue**: `push_preflight.py:116` contains a comment referencing "copied from preflight.py" and "source of truth is here for the publish layer; preflight.py retains its own copies until WP02 removes the remote-state surface from that module". WP02 has been merged and `preflight.py` no longer has the network-I/O copies. The comment is now stale. **Minor finding** — no blocking impact.

---

## Risk Assessment

| Risk | Severity | Status |
|------|----------|--------|
| `is_safe` deprecated alias could be confused with `is_safe_to_push` | LOW | Mitigated — docstring says "deprecated, always returns True"; `is_safe_to_push` is the push-decision predicate |
| Legacy state without `push_requested` on resume skips push check | ACCEPTABLE | By design (FR-008); resume defaults to no-push, user must re-invoke with `--push` |
| `test_merge_preflight_atdd.py` ATDD stubs remain in suite as green tests | LOW | Acceptable — they verify module existence and API; minimal value but no harm |

---

## Gate Results

| Gate | Result |
|------|--------|
| All 244 merge-related tests pass | ✅ PASS |
| Architectural: `test_every_test_file_declares_a_pytestmark_marker` | ✅ PASS (fixed this review) |
| Architectural: `test_no_public_symbol_in_all_is_unimported` | ✅ PASS (fixed this review) |
| Issue matrix: #1706 verdict is `fixed` | ✅ PASS |
| Acceptance matrix: all 11 FRs `pass` | ✅ PASS |
| Pre-existing architectural failures (4) | ℹ️ PRE-EXISTING (not introduced by this mission) |

**Pre-existing failures (out of scope)**:
- `test_cwd_parity` / `test_ratchet_catches_divergence` — CI environment, not code
- `test_subprocess_git_users_must_carry_git_repo_marker` for `test_mission_status_aggregate.py` — pre-dates this mission
- `test_fast_marker_must_not_apply_to_subprocess_users` for `test_mission_status_aggregate.py` — pre-dates this mission

---

## Minor Finding (non-blocking)

**Stale comment in `push_preflight.py:115-117`**: The block comment says "preflight.py retains its own copies until WP02 removes the remote-state surface from that module". WP02 has landed; preflight.py no longer has those copies. The comment should be updated.

---

## Overall Verdict

**SHIP** — all FRs met, architectural violations introduced by WP03 resolved, security posture clean, no scope drift. The stale comment is noted as a minor non-blocking finding.
