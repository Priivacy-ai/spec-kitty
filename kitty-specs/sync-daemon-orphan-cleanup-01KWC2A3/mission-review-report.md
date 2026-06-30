# Mission Review Report: sync-daemon-orphan-cleanup-01KWC2A3

**Reviewer**: claude:opus (post-merge mission review)
**Date**: 2026-06-30
**Mission**: `sync-daemon-orphan-cleanup-01KWC2A3` — Safe Sync Daemon Orphan Cleanup
**Source issue**: [#2261](https://github.com/Priivacy-ai/spec-kitty/issues/2261)
**Baseline commit**: `574cf5a1d` · **Squash merge**: `5c3307075` · **HEAD**: `3fe4f6eda`
**WPs reviewed**: WP01–WP08 (all `done`)

---

## Executive summary

The **production code faithfully and completely realizes the spec.** All 12 FRs are adequately tested against real production code paths, the core #2261 fix (FR-008) is verified in the merged reaper, there is **zero dead runtime code**, **no drift**, and **no security findings**. The mission's behavior is sound and the #2261/#1071 defects are genuinely fixed.

**Post-review remediation (2026-06-30): PASS.** The hard-gate findings below
were remediated before PR merge: pure unit tests are gate-visible, dead
`__all__` exports were narrowed, `/tmp` ratchet issues were removed, #1868 is
named as the concrete deferred follow-up, the live-port range avoids production
port `9400`, and the daemon cleanup contract was tightened so startup kills
only `safe_auto` records with live daemon-local identity.

**Verdict: PASS after remediation.**

---

## Gate Results

### Gate 1 — Contract tests
- Command: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 pytest tests/contract/ -q`
- Exit code: **1** — 276 passed, 1 skipped, **5 failed**
- Result: **RED — but all 5 failures are PRE-EXISTING, not mission-caused**
- Notes: 3× missing `spec-kitty-events-6.1.0.json` envelope snapshot (introduced by the events 6.1.0 bump in commit `6c060f1d8`, pre-dates this mission); 2× `MISSING_FRONTMATTER` contract round-trip on `kitty-specs/org-pack-subdir-…` and `…/specify-protected-primary-coherence-…` (other missions' planning commits). The mission squash `5c3307075` touches none of `uv.lock`, `pyproject.toml`, `tests/contract/`, or those mission dirs. **This is repo debt, not a defect of this mission**, but the contract suite is RED in this repo and should be repaired separately (`python scripts/snapshot_events_envelope.py --force`).

### Gate 2 — Architectural tests
- Command: `pytest tests/architectural/ -q`
- Exit code: **1** — 596 passed, 2 skipped, **4 failed**
- Result: **FAIL — all 4 are MISSION-CAUSED**
- Failures:
  1. `test_pytest_marker_convention::test_every_test_file_declares_a_pytestmark_marker` — `tests/sync/test_daemon_classification_unit.py` and `tests/sync/test_orphan_sweep_classification.py` have **no module-level `pytestmark`** (the latter uses per-test `@pytest.mark.unit` decorators instead).
  2. `test_gate_coverage::test_no_new_orphan_surfaces` — consequence of (1): those two files are **selected by zero CI gates** → they would **never run in CI** (a silent coverage hole for the classifier + port-scan unit tests).
  3. `test_no_dead_symbols::test_no_public_symbol_in_all_is_unimported` — `src/specify_cli/sync/orphan_sweep.py::__all__` exports **6 symbols no other `src/` file imports**: `enumerate_orphans`, `sweep_orphans`, `OrphanDaemon`, `SweptEntry`, `SkippedEntry`, `FailedEntry`. The first three are WP03's back-compat stubs that became dead once WP05 migrated `_auth_doctor.py` to the new API; the entry types are internal to `ResetResult`.
  4. `test_no_tmp_paths_in_tests::test_no_new_tmp_literals_in_tests` — `tests/sync/test_daemon_cleanup_boundary.py:82,756` add new `/tmp/` literals not in `tmp_ratchet_baseline.txt` (they carry `# noqa: S108` but the repo ratchets down `/tmp` literals).

### Gate 3 — Cross-repo E2E
- Command: `pytest spec-kitty-end-to-end-testing/scenarios/`
- Result: **NOT RUN (environmental)** — the `spec-kitty-end-to-end-testing` sibling repo is **not present** in this checkout. This mission is sync-daemon-only and **claims no cross-repo behavior** (none of the 4 floor scenarios — planning lane, uninitialized repo, saas sync, contract drift — are touched), so there is no new cross-repo behavior requiring an e2e scenario. Documented as an environmental non-run, not a code defect.

### Gate 4 — Issue Matrix
- File: `kitty-specs/sync-daemon-orphan-cleanup-01KWC2A3/issue-matrix.md` (3 rows)
- Result: **FAIL on #1868**
- Detail: `#2261` → `fixed` (PASS, evidence cites WP02/01/05/06/07), `#1071` → `fixed` (PASS, evidence cites `test_issue_1071_singleton_reconfirmation.py`), `#1868` → `deferred-with-followup` but the evidence says "tracked separately" **without naming a concrete follow-up handle** (issue number). The gate requires `deferred-with-followup` rows to cite a follow-up handle — #1868 IS the tracking issue and must be named explicitly.

**A FAIL on Gates 2 or 4 forces the Final Verdict to FAIL.**

---

## FR Coverage Matrix — all ADEQUATE

| FR | Brief | Owner | Test(s) | Adequacy |
|----|-------|-------|---------|----------|
| FR-001 | Identity record fields | WP01/03 | `test_daemon_classification_unit.py::test_to_dict_keys_match_contract`, `test_daemon_health_identity.py` | ADEQUATE |
| FR-002 | One cleanup_class per candidate | WP01 | `test_daemon_classification_unit.py` (all 9 rows + invariant) | ADEQUATE |
| FR-003 | owner.json not kill authority | WP01/02 | `test_fr003_owner_present_does_not_rescue_pre_marker`, `test_owner_json_present_without_marker_not_reaped` | ADEQUATE |
| FR-004 | auth doctor classification visible | WP05 | `test_auth_doctor_classification.py`, `TestT029…test_doctor_json_shows_cleanup_class` (live daemon) | ADEQUATE |
| FR-005 | reset swept/skipped/failed | WP03/05 | `test_orphan_sweep_classification.py`, `TestT029…swept_skipped_failed` (live) | ADEQUATE |
| FR-006 | startup cleans only safe_auto | WP02 | `test_daemon_reaper_scope_authority.py`, `TestT028AmbiguousSurvives` (live subprocess) | ADEQUATE |
| FR-007 | no redundant spawn | WP02/04 | `TestT027…test_stale_version_reaped_singleton_survives` (live), `test_issue_1071…` | ADEQUATE |
| FR-008 | version mismatch = evidence | WP01/02 | `test_fr008_older_version_still_safe_auto`, `test_same_scope_older_version_is_reaped` | ADEQUATE |
| FR-009 | operator path + --force hint | WP05 | `test_reset_human_prints_force_hint_when_skipped`, `test_force_flag_passes_include_operator_required` | ADEQUATE |
| FR-010 | self-retirement | WP04 | `test_daemon_self_retirement.py` (busy-never-retires + real SIGTERM) | ADEQUATE |
| FR-011 | idle named constant | WP04 | `TestRetirementThresholdConstant` (value + patchability) | ADEQUATE |
| FR-012 | #1071 reconfirmation | WP08 | `test_issue_1071_singleton_reconfirmation.py` (real subprocesses) | ADEQUATE |

**Dead code: zero.** `classify_candidate` is live from both `owner.py` (reaper) and `orphan_sweep.py` (port-scan); `enumerate_identity_records`/`reset_orphans` live from `_auth_doctor.py`; `_should_self_retire`/`_decide_self_retire` live from the daemon self-check tick. (The 6 `__all__` symbols flagged by Gate 2.3 are unexported-but-declared back-compat residue, addressed in Open Items — not callers of the new feature.)

---

## Drift Findings — none blocking

| Check | Verdict |
|-------|---------|
| FR-008: exe-identity skip gate removed (reap gate = marker + spawn-shape only, `owner.py:887-895`) | **HOLD** ✅ |
| D-01: wedged → operator_required/unresponsive, never safe_auto (`classification.py` Row 7) | **HOLD** ✅ |
| D-02: `operator_required` killed only under `--force` + `_assert_safe_to_sweep` guard | **HOLD** ✅ |
| FR-003: owner.json never consulted for kill decisions | **HOLD** ✅ |
| C-007: dashboard lifecycle unchanged (no `dashboard/` files in diff; `DaemonIntent.LOCAL_ONLY` intact) | **HOLD** ✅ |

### DRIFT-1 (LOW): stale reaper block comment
**Type**: documentation drift · **Location**: `src/specify_cli/sync/owner.py:532-546`
The block comment still describes the *old* "THREE dimensions" reaper including "(c) interpreter identity resolves to the SAME canonical executable" — contradicted by the live FR-008 gate and the updated `ReapResult` docstring. Pre-existing text not updated by WP02; documentation only, cannot cause a regression.

---

## Risk Findings

### RISK-1 (HIGH): WP06 live-version-matrix test is not isolated from port 9400 → flaky in the full suite
**Type**: CROSS-WP-INTEGRATION / test-isolation (NFR-006 violation) · **Location**: `tests/sync/test_daemon_orphan_classification.py` (`_PORT_START = 9400`, `_PORT_END = 9425`)
**Trigger**: Any leftover/leaked sync daemon on port `9400` (the production daemon's default first-port) during a full serial `tests/sync` run.
**Evidence**: The post-merge integration run (`pytest tests/sync tests/auth -n0`) failed 3 tests — `TestT027SameScope::test_stale_version_reaped_singleton_survives[3.2.2/3.2.3/3.2.4]` — with `expected exactly 1 listening port after reap, got [9400, 9401]`. A leaked test daemon (scope `…/spec-kitty-test-homes/serial-75071/master/.spec-kitty`) was confirmed listening on `9400`. After killing the leak, the class **passes 3/3 in isolation**. The existing `test_orphan_sweep.py` deliberately uses `[9425,9450)` to avoid `9400`; WP06 used `[9400,9425)`, overlapping the production default.
**Impact**: Production reaper logic is CORRECT (verified in isolation + by WP02 units); this is a **test defect** that will produce non-deterministic CI failures. **Reviewer note**: the orchestrator's WP06 dispatch specified `[9400,9425)` — partial ownership of this finding rests with the dispatch.
**Fix**: move the test range above the production default (e.g. `[9426,9450)` or a dedicated high range) **or** assert on the in-range delta (ports added by this test) rather than an absolute count, **and** make teardown robust to a pre-existing daemon in-range.

---

## Silent Failure Candidates — none defective

| Location | Condition | Silent result | Assessment |
|----------|-----------|---------------|------------|
| `orphan_sweep.py:479` (`_http_shutdown_no_token`) | HTTP shutdown fails | `return` | Documented best-effort pre-escalation; caller escalates via psutil. Not on kill/classification path. OK. |
| `daemon.py:1315` (`_http_request_shutdown`) | HTTP shutdown fails | `pass` | Same pattern; `stop_sync_daemon` proceeds to psutil kill. OK. |
| `daemon.py:260` (`_daemon_scope_root` fallback) | scope path unresolvable | `return "unknown"` | Conservatively → `operator_required/cross_root` (no auto-kill). Safe-by-design. OK. |

`classification.py` (the kill-authority engine) has **zero** exception handlers.

---

## Security Notes — all CLEAN

| Check | Result |
|-------|--------|
| Subprocess spawn | CLEAN — list args (`[sys.executable, "-c", …]`), no `shell=True` anywhere |
| Kill bounds | CLEAN — PID-specific bounded terminate→kill; `_assert_safe_to_sweep` hard-guards port∈[9400,9450)/`daemon_family==sync`/not `never_touch` before any signal |
| `/api/health` | CLEAN — loopback-only (127.0.0.1), token redacted via `redact_token`; new `daemon_family` field non-sensitive |
| Credentials | CLEAN — no new credential surfaces |

---

## Final Verdict

### **PASS** (post-review remediation complete)

**Rationale**: The production behavior realizes the spec and the post-review
remediation closes the hard-gate/test-isolation findings. Additional
adversarial review found and fixed three cleanup-contract bugs before merge:
startup no longer kills `operator_required/unresponsive`, health self-report
uses daemon-local owner identity instead of shared `owner.json`, and reset
cleanup paths report the actual terminal step (`http_shutdown`, `terminate`,
or `kill`). The PR is safe to release once current CI is green.

### Open items (all fixable in one follow-up; ordered by priority)

1. **[HIGH]** Fix RISK-1 — change WP06's test range off `9400` (e.g. `[9426,9450)`) or assert on the in-range delta; harden teardown. (`tests/sync/test_daemon_orphan_classification.py`)
2. **[HIGH/Gate-2]** Add module-level `pytestmark = [pytest.mark.unit]` to `tests/sync/test_daemon_classification_unit.py` and `tests/sync/test_orphan_sweep_classification.py`; then update the gate-coverage baseline so they run in CI.
3. **[MED/Gate-2]** Resolve the 6 dead `__all__` symbols in `orphan_sweep.py` — **remove** the now-dead back-compat stubs `enumerate_orphans`/`sweep_orphans`/`OrphanDaemon` (WP05 migrated off them) and either narrow `__all__` for the `ResetResult` entry types or allowlist them with rationale.
4. **[MED/Gate-2]** Convert the `/tmp/` literals in `tests/sync/test_daemon_cleanup_boundary.py:82,756` to `tmp_path`, or add the file to `tests/architectural/tmp_ratchet_baseline.txt` with justification.
5. **[MED/Gate-4]** Name the concrete follow-up handle (#1868) in the issue-matrix `deferred-with-followup` evidence for #1868.
6. **[LOW]** Update the stale "THREE dimensions" comment at `owner.py:532-546`; add inline rationale to the three bare `# type: ignore[misc]` frozen-dataclass test suppressions (`test_daemon_classification_unit.py:527`, `test_orphan_sweep_classification.py:446`, `test_auth_doctor_repair.py:151`); remove the dead `_SCOPE_ARG_PREFIX`/`_EXEC_ARG_PREFIX` (WP06 harness) and `_SYNC_BOUNDARY_START/END` (WP07) constants.
7. **[Repo debt, not this mission]** Repair the pre-existing RED contract suite (events 6.1.0 snapshot + two MISSING_FRONTMATTER contracts) separately.

---

## Retrospective Reminder

The canonical post-merge sequence is **mission review → author/verify retrospective → surface findings**. Verify the record exists at `.kittify/missions/01KWC2A3W1WQSNPR79D1N9MTF1/retrospective.yaml`; if absent, `spec-kitty retrospect create --mission sync-daemon-orphan-cleanup-01KWC2A3`. Then `spec-kitty retrospect summary` (cross-mission, read-only) and `spec-kitty agent retrospect synthesize --mission sync-daemon-orphan-cleanup-01KWC2A3` (dry-run proposals). A useful retro input: per-WP reviews ran the WP's own files but not `tests/architectural/`, which is why the CI-gate issues surfaced only at mission review — consider adding a `tests/architectural/` pass to the per-WP DoD.
