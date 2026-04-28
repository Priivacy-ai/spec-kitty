# Mission Review Report: cli-session-survival-daemon-singleton-01KQ9M3M

**Reviewer**: Claude Opus 4.7 (post-merge mission reviewer)
**Date**: 2026-04-28
**Mission**: `cli-session-survival-daemon-singleton-01KQ9M3M` — CLI Session Survival and Daemon Singleton (Tranche 1, Mission #105)
**Baseline commit**: `ac9da737`
**HEAD at review**: `8342c26c` (squash-merge `d5d5fa52`)
**WPs reviewed**: WP01..WP06 (all `done`, all approved with no rejection cycles)

---

## Gate Results

### Gate 1 — Contract tests

- Command: `cd src && PYTHONPATH=. python -m pytest ../tests/contract/ -v`
- Exit code: non-zero (1 failure / 235 pass / 1 skip)
- Result: **FAIL — environmental, not mission-defect**
- Notes: Sole failure is `tests/contract/test_cross_repo_consumers.py::test_spec_kitty_events_module_version_matches_resolved_pin` — `spec_kitty_events.__version__ = '4.0.0'` but `uv.lock` pins `4.1.0`. This is a workspace-environment drift independent of this mission's surface (auth / file lock / sync daemon). All 235 other contract tests (including auth-related contracts) pass cleanly. No mission-introduced contract drift was found.

### Gate 2 — Architectural tests

- Command: `cd src && PYTHONPATH=. python -m pytest ../tests/architectural/ -v`
- Exit code: 0 (90 passed / 1 skipped)
- Result: **PASS**
- Notes: All architectural-boundary tests green, including `test_layer_rules`, `test_pyproject_shape`, `test_shared_package_boundary`, and `test_safety_registry_completeness`. The mission's new modules (`src/specify_cli/core/file_lock.py`, `src/specify_cli/auth/refresh_transaction.py`, `src/specify_cli/sync/orphan_sweep.py`, `src/specify_cli/cli/commands/_auth_doctor.py`) introduce no layer or package-boundary violations.

### Gate 3 — Cross-Repo E2E

- Command: would be `cd ../spec-kitty-end-to-end-testing && SPEC_KITTY_ENABLE_SAAS_SYNC=1 pytest scenarios/ -v`
- Exit code: N/A
- Result: **N/A — gate not applicable to this mission**
- Notes: The cross-repo end-to-end testing repository at `../spec-kitty-end-to-end-testing/` does not exist in this workspace. The hard gate was defined for a different mission (`stability-and-hygiene-hardening-2026-04-01KQ4ARB`) and the four floor scenarios listed there (`dependent_wp_planning_lane.py`, `uninitialized_repo_fail_loud.py`, `saas_sync_enabled.py`, `contract_drift_caught.py`) cover orchestrator concerns, not auth/lock/daemon behavior. This mission is a pure CLI-internals fix; no cross-repo behavior is claimed.

### Gate 4 — Issue Matrix

- File: `kitty-specs/cli-session-survival-daemon-singleton-01KQ9M3M/issue-matrix.md`
- Rows: N/A
- Result: **N/A — artifact not applicable to this mission**
- Notes: Issue matrix is not present and not required by this mission's spec/plan/tasks. The matrix gate (FR-037) was added for the stability-and-hygiene mission. WP review history (in `status.events.jsonl`) shows zero rejection cycles and zero deferred items across all 6 WPs, so there is no implicit issue list that should have been documented in matrix form.

**Gate net**: Gates 1 & 2 effectively pass (Gate 1 failure is environmental; the tests for this mission's surface all pass). Gates 3 & 4 are N/A. Gate Results do not block release.

---

## FR Coverage Matrix

Legend: ADEQUATE = test constrains the required behavior with production code paths; PARTIAL = test exists but uses synthetic fixtures or only covers part of the requirement; MISSING = no test located.

| FR ID | Description (brief) | WP Owner | Test File(s) | Test Adequacy | Finding |
|-------|---------------------|----------|--------------|---------------|---------|
| FR-001 | Acquire machine-wide refresh lock before any refresh transaction | WP01/WP02 | `tests/auth/concurrency/test_machine_refresh_lock.py`; `tests/core/test_file_lock.py::test_concurrent_acquire_serialized` | ADEQUATE | — |
| FR-002 | Transaction order: acquire→reload→decide→refresh→persist→release | WP02 | `tests/auth/test_token_manager.py::test_adopts_newer_persisted_material_skips_network`, `test_current_grant_rejection_clears_and_propagates` | ADEQUATE | — |
| FR-003 | Preserve in-process single-flight `asyncio.Lock` (FR-003) | WP02 | `tests/auth/test_token_manager.py::test_concurrent_get_access_token_is_single_flight`, `test_second_burst_after_refresh_does_not_re_refresh` | ADEQUATE | — |
| FR-004 | Adopt persisted material if newer-and-valid; skip network | WP02 | `tests/auth/test_token_manager.py::test_adopts_newer_persisted_material_skips_network`; `tests/auth/concurrency/test_machine_refresh_lock.py` (ADOPTED_NEWER fast path) | ADEQUATE | — |
| FR-005 | Clear local session only when rejected material is current | WP02/WP03 | `tests/auth/test_token_manager.py::test_current_grant_rejection_clears_and_propagates`, `test_current_grant_session_invalid_propagates_session_invalid` | ADEQUATE | — |
| FR-006 | Preserve session when rejection is against stale material (THE incident fix) | WP02/WP03 | `tests/auth/test_token_manager.py::test_stale_grant_with_expired_persisted_preserves_session`; `tests/auth/concurrency/test_stale_grant_preservation.py`; `tests/auth/concurrency/test_incident_regression.py` | ADEQUATE | — |
| FR-007 | User-readable re-login message + recovery command | WP02 | `tests/auth/test_token_manager.py::test_current_grant_rejection_clears_and_propagates` (asserts message content includes `spec-kitty auth login`) | ADEQUATE | The message strings live in `src/specify_cli/auth/token_manager.py:259-265`; tests verify them. |
| FR-008 | Sync daemons converge to one user-level daemon | WP04 | `tests/sync/test_daemon_self_retirement.py::test_retires_on_port_mismatch_and_recorded_pid_alive` (named differently than contract `test_self_retires_when_port_mismatch` but covers the same predicate) | ADEQUATE | — |
| FR-009 | Detect+terminate orphans on user request | WP05 | `tests/sync/test_orphan_sweep.py::test_enumerate_finds_orphan`, `test_sweep_terminates_orphan`, `test_sweep_does_not_touch_singleton`, `test_sweep_records_failure_on_access_denied` | ADEQUATE | — |
| FR-010 | Orphans self-retire on next tick | WP04 | `tests/sync/test_daemon_self_retirement.py::test_retires_on_port_mismatch_and_recorded_pid_alive`; `test_does_not_retire_on_port_mismatch_when_recorded_pid_dead` | ADEQUATE | — |
| FR-011 | `auth doctor` reports 7 sections | WP06 | `tests/auth/test_auth_doctor_report.py` (multiple tests render and assert each section) | ADEQUATE | — |
| FR-012 | Remediation block names commands | WP06 | `tests/auth/test_auth_doctor_report.py` (asserts F-001..F-007 emit `Run: <cmd>`) | ADEQUATE | — |
| FR-013 | `--reset` sweeps orphans, never the singleton | WP06 | `tests/auth/test_auth_doctor_repair.py::test_reset_sweeps_orphans`, `test_reset_noop_when_no_orphans` | ADEQUATE | — |
| FR-014 | `--unstick-lock` only drops past age threshold | WP06 | `tests/auth/test_auth_doctor_repair.py::test_unstick_drops_old_lock`, `test_unstick_preserves_fresh_lock` | ADEQUATE | — |
| FR-015 | Default `auth doctor` MUST NOT mutate state | WP06 | `tests/auth/test_auth_doctor_offline.py` (patches `force_release`, `sweep_orphans`, `terminate`, `kill` and fails if any fire on default path) | ADEQUATE | — |
| FR-016 | Bounded lock-hold; release on timeout; treat as retryable | WP01/WP02 | `tests/auth/test_token_manager.py::test_lock_timeout_error_when_persisted_is_unusable`, `test_network_timeout_raises_lock_timeout_error` | ADEQUATE | — |
| FR-017 | Lock-acquire timeout adopts persisted-newer material if usable | WP01/WP02 | `tests/auth/test_token_manager.py::test_lock_timeout_adopts_when_persisted_is_fresh` | ADEQUATE | — |
| FR-018 | Tolerate killed-mid-transaction holders (age-based stale) | WP01 | `tests/core/test_file_lock.py::test_force_release_only_when_stuck`, `test_lock_record_age_and_is_stuck` | ADEQUATE | — |
| FR-019 | Log refresh-transaction outcomes at INFO | WP02 | `tests/auth/test_token_manager.py::test_refresh_logs_outcome_at_info` | ADEQUATE | — |
| FR-020 | `auth status` continues to behave correctly | WP02 | `tests/auth/test_auth_status_*` (existing) + `test_token_manager.py` does not regress; reviewer-renata's review record says "_auth_status.py byte-identical." | PARTIAL | A direct golden-output test for `auth status` against the new transaction logic was not added by this mission; the review note that `_auth_status.py` is byte-identical is the only positive evidence. Risk: low. |

| NFR ID | Threshold | Test / Verification | Adequacy | Finding |
|-------|-----------|---------------------|----------|---------|
| NFR-001 | ≤50 ms refresh-transaction overhead p95 | None — no perf benchmark in mission | MISSING | NFR-MISS — see DRIFT-1 |
| NFR-002 | ≤10 s lock-hold ceiling | `tests/auth/test_token_manager.py::test_network_timeout_raises_lock_timeout_error` (asserts the asyncio.wait_for ceiling triggers); also docstring constants `_REFRESH_MAX_HOLD_S = 10.0` and `MachineFileLock.max_hold_s = 10.0` | ADEQUATE | — |
| NFR-003 | ≥90 % coverage on new modules | Per WP02 review note ("99% coverage on owned files"), WP01 ("97% coverage"), WP05/WP06 ("mypy/ruff clean"). No CI-level enforcement assertion in mission tests | PARTIAL | No mission-level coverage gate test exists. Per-WP reviews captured the numbers anecdotally. |
| NFR-004 | `mypy --strict` zero new errors | Verified by post-merge run: `mypy --strict src/specify_cli/core/file_lock.py src/specify_cli/auth/refresh_transaction.py src/specify_cli/auth/token_manager.py src/specify_cli/sync/orphan_sweep.py src/specify_cli/cli/commands/_auth_doctor.py` → "Success: no issues found in 5 source files" | ADEQUATE | — |
| NFR-005 | Multiprocess regression ≤30 s | `tests/auth/concurrency/test_incident_regression.py:302-318` enforces a 30 s wall-clock cap via `subprocess.wait(timeout=...)` | ADEQUATE | — |
| NFR-006 | `auth doctor` ≤3 s typical | `tests/auth/test_auth_doctor_report.py::test_runs_under_three_seconds` (asserts <3 s); `tests/sync/test_orphan_sweep.py:366` covers the 50-port scan budget | ADEQUATE | — |
| NFR-007 | Backward-readable session storage | No new test added for "older CLI loads new session shape"; the implementation is additive only (lock files / state-file format unchanged); existing `test_secure_storage_file.py` still passes | PARTIAL | This mission added no schema; "additive only" plus the existing storage tests cover the contract by construction. Acceptable. |
| NFR-008 | Cross-platform via capability detection | `tests/core/test_file_lock.py::test_platform_dispatch_posix` + `test_platform_dispatch_windows` (skipped on POSIX). Code path uses `sys.platform == "win32"` once at module top to bind primitive | ADEQUATE | — |

---

## Drift Findings

### DRIFT-1: NFR-001 (≤50 ms p95 refresh overhead) is asserted in the spec but not measured in any test

**Type**: NFR-MISS
**Severity**: LOW
**Spec reference**: `spec.md` §"Non-Functional Requirements" — NFR-001
**Evidence**:
- `kitty-specs/cli-session-survival-daemon-singleton-01KQ9M3M/spec.md` lines 174-176 mandate "Refresh-transaction overhead added by the machine-wide lock in the single-process happy path. ≤ 50 ms additional wall time at the 95th percentile on the maintainer's reference development machine."
- No test in `tests/` measures or asserts the lock-acquisition cost in the single-process happy path. `tests/auth/concurrency/test_machine_refresh_lock.py` measures concurrency correctness, not latency.
- `plan.md` line 173 mentions NFR-001 in the requirement-to-WP map but provides no enforcement mechanism beyond an inline `_RETRY_SLEEP_S = 0.1` constant and "the bounded-acquire loop must use 100 ms sleep increments only when contended" prose.

**Analysis**: This is a documentation/measurement gap, not a code defect. The implementation acquires the OS lock non-blockingly and writes the JSON record in one syscall — the happy path is structurally cheap (likely sub-millisecond on a local SSD). However, the spec requires a 50 ms p95 budget that nothing currently verifies. Recommend: add a per-WP doctrine note that the single-process p95 was measured manually during WP02 review, OR add a `pytest-benchmark`-style regression test. **Not release-blocking** — the budget is generous and the hot-path code is straightforward.

### DRIFT-2: FR-020 lacks a direct golden-output regression test

**Type**: PUNTED-FR (test side)
**Severity**: LOW
**Spec reference**: `spec.md` line 170 — "FR-020: `spec-kitty auth status` MUST continue to report authenticated/not authenticated truthfully relative to persisted state, with no behavioral regression when only one process is involved."
**Evidence**:
- `grep "FR-020" tests/` finds matches in `tests/auth/test_token_manager.py:14-15` (docstring) but no test asserts the `auth status` console output explicitly post-refresh-transaction.
- The reviewer's evidence note for WP02 (`status.events.jsonl` event `01KQ9RYFCV67YM4VS4EYX9NVAC`) records "_auth_status.py byte-identical" as the rationale — this is a static-file-equality argument, not a behavior test.

**Analysis**: `_auth_status.py` was not modified by the mission, so the byte-identity argument is sound — `auth status` output cannot regress unless the underlying `TokenManager.get_current_session()` value changes. Tests in `test_token_manager.py` cover that surface. The risk is that future refactoring could touch `_auth_status` without re-validating; an explicit golden test would lock the contract. **Not release-blocking**.

---

## Risk Findings

### RISK-1: `MachineFileLock` deviation from contract — `_atomic_write_under_lock` instead of `atomic_write` (WP01 `core/file_lock.py:159-178`)

**Type**: BOUNDARY-CONDITION
**Severity**: LOW (already reviewed and explicitly justified by reviewer)
**Location**: `src/specify_cli/core/file_lock.py:159-178`
**Trigger condition**: A reader calling `read_lock_record()` mid-acquisition observes a half-truncated lock file.

**Analysis**: The contract at `contracts/refresh-lock.md:53-54` says: *"Content is written via `specify_cli.core.atomic.atomic_write` so that readers (such as auth doctor) never observe a partial record."* The implementation deliberately rejects this in favor of `os.ftruncate(fd, 0); os.write(fd, payload); os.fsync(fd)` directly on the held FD, with the in-source rationale (lines 159-169) that `os.replace`'s inode rotation breaks `flock` mutual exclusion for subsequent acquirers. The deviation is sound — `flock` is associated with the open FD's inode, so swapping inodes via rename would let two processes hold "the lock" on different inodes pointing at the same path.

The atomicity tradeoff is documented: a reader racing the `ftruncate` window observes an empty file, which `read_lock_record()` returns as `None` (line 249-250). For sub-`PIPE_BUF` writes (the JSON record is ~150 bytes, well under POSIX `PIPE_BUF=512`+) the single `os.write` is atomic by POSIX rules, ruling out partial reads of the new record. The test `test_atomic_content_write_failure_leaves_no_partial` verifies the atomicity contract.

**Why I'm logging it**: the deviation is correct, but the contract document itself was not updated to match — `contracts/refresh-lock.md:53-54` still asserts `atomic_write` is used. Future developers reading the contract will be surprised by the implementation. Recommend a follow-up doc edit.

### RISK-2: `force_release(only_if_age_s=stuck_threshold)` TOCTOU window in `_auth_doctor.doctor_impl` (lines 705-709)

**Type**: BOUNDARY-CONDITION (TOCTOU)
**Severity**: LOW
**Location**: `src/specify_cli/cli/commands/_auth_doctor.py:705-715`
**Trigger condition**: User invokes `spec-kitty auth doctor --unstick-lock` exactly as a legitimate refresh-transaction has just acquired the lock (record < `stuck_threshold` old) but is older than the age the report saw moments earlier.

**Analysis**: `force_release(path, only_if_age_s=stuck_threshold)` re-reads the lock record at unlink time (lines 267-276 of `file_lock.py`) and re-checks `record.age_s <= only_if_age_s` *before* unlinking. So the TOCTOU window is between `assemble_report()` (line 690) discovering F-003 with age > threshold and `force_release()` re-reading the record. If a fresh holder won the lock in that gap, `force_release` returns `False` and the doctor prints "lock not removed (fresh, missing, or unreadable)". This is the safe fallthrough path — no fresh lock is silently dropped.

Residual risk: the report displayed to the user can be inconsistent with the actual outcome (report said "stuck", but unstick said "no-op"). User may retry. The asymmetry is benign — the *destructive* check is gated correctly.

### RISK-3: `psutil.net_connections()` in `enumerate_orphans` may return 0 PIDs without elevated permissions on macOS

**Type**: ERROR-PATH
**Severity**: LOW (documented in `OrphanDaemon.pid` allowing `None`)
**Location**: `src/specify_cli/sync/orphan_sweep.py:135-165`, consumed by `_sweep_one` at lines 296-298

**Analysis**: `psutil.net_connections(kind="tcp")` requires elevated privileges on macOS (root or `sudo`) to return PIDs for connections owned by other processes. Without privileges it raises `psutil.AccessDenied`, which is caught at line 145 and returns `None`. `enumerate_orphans` then yields `OrphanDaemon(pid=None, …)` and `_sweep_one` falls back to HTTP-shutdown only (line 296-297, returning `"no_pid_after_http_shutdown_failed"`).

This means on a typical macOS user invocation, `auth doctor --reset` against an orphan that won't comply with the (ignored, 403-returning) HTTP shutdown will record `failed=[(orphan, "no_pid_after_http_shutdown_failed")]` rather than terminate the orphan. The sweep is not dangerous — it just degrades to "report only" silently. The user has no UX hint that running with elevated privileges would help.

**Recommend**: documentation note or a finding-level warning in the doctor output when `pid=None` orphans were detected.

### RISK-4: `sweep_orphans` deadline math is `timeout_s × len(orphans)` not `timeout_s` (line 351)

**Type**: BOUNDARY-CONDITION
**Severity**: INFO (matches contract, but documentation is ambiguous)
**Location**: `src/specify_cli/sync/orphan_sweep.py:350-351`

**Analysis**: The contract at `contracts/daemon-singleton.md:142` says: *"Total bounded duration: `timeout_s × len(orphans)` worst case. Default `timeout_s=5.0`."* — and the implementation matches. But the function docstring (lines 339-349) says "`timeout_s` bounds the overall sweep wall-clock", which is misleading: 5 orphans × 5 s = 25 s worst case, not 5 s. Internal contract holds; user-facing docstring should clarify that `timeout_s` is per-orphan, not total. Not release-blocking.

### RISK-5: `_decide_self_retire` does not retire when recorded PID is dead — possible orphan accumulation (daemon.py:443-485)

**Type**: BOUNDARY-CONDITION
**Severity**: LOW (documented invariant, but the comment-as-code is the only enforcement)
**Location**: `src/specify_cli/sync/daemon.py:467-475`

**Analysis**: `_decide_self_retire` early-returns with `not _is_process_alive(parsed_pid)` so a daemon whose recorded PID is dead **does not retire**. The comment on lines 472-475 explains: *"the file is stale; the next `ensure_running` call will reconcile it, so we keep running."* The invariant is: state-file ownership belongs to `_ensure_sync_daemon_running_locked` exclusively (lines 446-450). Two daemons each booted from independent `ensure_running` calls cannot both mistakenly self-retire because `ensure_running` sequences them under the existing `DAEMON_LOCK_FILE` flock (preserved, not modified by this mission).

The risk is the inverse: a daemon X recorded in the state file dies, then another long-running daemon Y on a different port runs its tick — Y reads state-file=X, sees X is dead, and continues running. This is correct per the design (Y waits for the next `ensure_running` to reset state). But if `ensure_running` is never called again (no new CLI commands fire for the user), Y could continue running on a port that does not match the state file indefinitely, until a CLI invocation triggers reconciliation. Practical impact: Y serves stale sync, and the user's actual `ensure_running` may pick a third port. Mitigated by `auth doctor --reset` which sweeps Y as an orphan.

**Test coverage**: `test_does_not_retire_on_port_mismatch_when_recorded_pid_dead` asserts this branch.

### RISK-6: `_storage.read()` exception handler in `_detect_persisted_drift` swallows all errors silently (lines 211-214)

**Type**: ERROR-PATH (silent-failure candidate)
**Severity**: LOW
**Location**: `src/specify_cli/cli/commands/_auth_doctor.py:211-214`

**Analysis**: `try: persisted = tm._storage.read(); except Exception: return False` — any storage backend hiccup (corrupted bytes, decryption error, OS error) is reported as "no drift" rather than surfacing the underlying error. Comment (lines 209-211) explicitly notes this is intentional for transient hiccups. Acceptable for a diagnostic — but in the rare case where storage is genuinely corrupted, the doctor will fail to trip F-006 and the user has to discover the corruption through other means. The doctor's other sections will still expose the corruption indirectly (Identity section shows session is loaded but storage drift goes silent).

### RISK-7: Cross-WP integration — `_auth_doctor.py:62-66` imports from `sync.orphan_sweep`, indirectly importing `psutil` at module load

**Type**: CROSS-WP-INTEGRATION
**Severity**: INFO
**Location**: `src/specify_cli/cli/commands/_auth_doctor.py:62`

**Analysis**: Loading `auth doctor` synchronously imports `orphan_sweep` (which imports `psutil`). On a user without `psutil` installed (it's an existing dependency in `pyproject.toml`, so this is hypothetical) the entire `auth doctor` command would fail at import time. Since `psutil` is already a hard dependency for the existing `sync.daemon`, this is not a new risk — but it's worth recording that the diagnostic surface now also depends on it. No remediation needed.

### RISK-8: `auth.py:122-128` swallows ALL doctor exceptions and exits with code 2

**Type**: ERROR-PATH
**Severity**: LOW
**Location**: `src/specify_cli/cli/commands/auth.py:122-128`

**Analysis**: `try: ... except Exception as exc: console.print(...); raise typer.Exit(2)` — every internal error in `doctor_impl` is converted to exit-code 2 with a single-line print. The contract at `contracts/auth-doctor.md:113-114` specifies "exit 2 — Internal error (exception during diagnostic gathering). Stack trace printed; report is partial." but the implementation only prints `f"Internal error during doctor: {exc}"` — no stack trace. Users diagnosing a misbehaving doctor cannot see what went wrong. Recommend: if `--json` mode, emit a machine-readable error envelope; if Rich mode, optionally print the traceback.

---

## Silent Failure Candidates

| Location | Condition | Silent result | Spec impact |
|----------|-----------|---------------|-------------|
| `src/specify_cli/cli/commands/_auth_doctor.py:211-214` | `tm._storage.read()` raises | `_detect_persisted_drift` returns `False` (no drift) | F-006 not surfaced even if storage is genuinely drifting; documented as intentional |
| `src/specify_cli/cli/commands/_auth_doctor.py:280-283` | `importlib.metadata.version("spec-kitty-cli")` raises | `_installed_package_version` returns `None`; F-004 silently disabled | Daemon-version-mismatch finding never fires when CLI install is metadata-corrupt |
| `src/specify_cli/cli/commands/_auth_doctor.py:373-376` | `from specify_cli.saas.rollout import is_saas_sync_enabled` raises | `rollout_enabled = False`; F-005 silently disabled | Acceptable; SaaS module not always present |
| `src/specify_cli/sync/orphan_sweep.py:117-120` | Health probe non-200 / non-JSON | `_probe_health` returns `None`; port skipped (not classified as orphan) | Correct R4 invariant; orphan classification gates on positive identity match |
| `src/specify_cli/sync/orphan_sweep.py:204-209` | HTTP shutdown best-effort | `_http_shutdown_no_token` swallows all exceptions; sweep falls through to terminate/kill | By design — HTTP shutdown is the gentlest escalation step |
| `src/specify_cli/auth/refresh_transaction.py:219` | `LockAcquireTimeout` from MachineFileLock | Tries persisted-newer adopt; else returns `LOCK_TIMEOUT_ERROR` | Correct FR-016/FR-017 — surfaces retryable error to caller |
| `src/specify_cli/auth/token_manager.py:111-114` | `self._storage.read()` raises during boot | `_session = None`; user shows "Not authenticated" | Existing behavior, not new risk |
| `src/specify_cli/auth/token_manager.py:124-128` | `self._storage.delete()` raises | logged warning; `_session` already cleared | Logout must not raise; documented |
| `src/specify_cli/sync/daemon.py:497-503` | Tick action raises any exception | `logger.exception` then chain continues | Defensive: never let a tick raise |
| `src/specify_cli/sync/daemon.py:455-457` | `_parse_daemon_file` raises | `logger.debug` then return; daemon continues running | Acceptable — state-file parse error treated as "no record", continue |

None of these constitute a hidden critical bug. Each is either documented intent (diagnostic resilience), or matches an existing pattern (storage-read-tolerance), or correctly preserves an invariant (orphan classification requires positive ID).

---

## Security Notes

| Finding | Location | Risk class | Recommendation |
|---------|----------|------------|----------------|
| `force_release(only_if_age_s=...)` TOCTOU is benign — re-checks age inside `force_release` | `src/specify_cli/core/file_lock.py:267-276` | LOCK-TOCTOU | None — design is correct; `auth doctor --unstick-lock` cannot drop a fresh lock even if the report data is mid-stale. |
| Refresh-transaction lock scope covers the full read-decide-refresh-reconcile sequence | `src/specify_cli/auth/refresh_transaction.py:207-218` | LOCK-TOCTOU | None — `MachineFileLock` is held for the entire `_run_locked` body, including `storage.read()`, the network call (bounded by `asyncio.wait_for`), and the rejection-reconcile re-read. |
| `(session_id, refresh_token)` byte-equality identity check | `src/specify_cli/auth/refresh_transaction.py:148-159` | CREDENTIAL-RACE | None — `_identity_matches` uses `bool(a == b)` for both fields, requires both to match to count as "current". This is the actual incident-fix invariant. |
| Reload-before-clear correctness | `src/specify_cli/auth/refresh_transaction.py:284-316` | CREDENTIAL-RACE | None — `repersisted = storage.read()` happens AFTER the rejection (line 294), then identity-checked against `persisted` (the material we sent). This is the documented WP03 reconciler. |
| Orphan sweep R4 invariant — orphan classification requires BOTH `protocol_version` AND `package_version` | `src/specify_cli/sync/orphan_sweep.py:130-132` | PROCESS-MISIDENTIFICATION | None — implementation matches contract (`contracts/daemon-singleton.md:108-115`). Anything that lacks either key is left alone, protecting non-Spec-Kitty processes that happen to listen on 9400-9450. |
| HTTP shutdown without auth token | `src/specify_cli/sync/orphan_sweep.py:191-209` | UNAUTHENTICATED-SHUTDOWN | LOW — modern daemons return 403 on POST `/api/shutdown` without a token. This is the gentlest escalation step; it does not introduce an attack surface (an attacker who can reach 127.0.0.1 already has user-level access). The HTTP request is to `127.0.0.1` only (verified by inspection). |
| SIGKILL escalation has 1 s grace | `src/specify_cli/sync/orphan_sweep.py:323-336` | LOCAL-DOS-MITIGATION | None — escalation is HTTP→SIGTERM(1s)→SIGKILL(1s). Bounded and recoverable. |
| `force_release` performs no PID-liveness check before unlinking | `src/specify_cli/core/file_lock.py:258-276` | LOCK-DESTRUCTION | INFO — the age-based gate is the only protection. If a process holds the lock for >`only_if_age_s` legitimately (e.g., SaaS network call took 70 s under packet loss), `--unstick-lock` will yank it. This is mitigated by `_REFRESH_MAX_HOLD_S = 10.0` enforcing the network leg ≤10 s; legitimate holders cannot exceed 10 s by construction. The default `--stuck-threshold=60.0` is 6× that ceiling, providing a generous safety margin. |
| HTTP probes use `127.0.0.1` exclusively (no DNS, no external connect) | `src/specify_cli/sync/orphan_sweep.py:108-127` | NETWORK-EXFILTRATION | None — verified by inspection; all `urlopen` calls hit `http://127.0.0.1:{port}/...`. |
| `MachineFileLock` POSIX `fcntl.flock` semantics — inode-bound | `src/specify_cli/core/file_lock.py:135-156` | LOCK-CORRECTNESS | None — implementation explicitly rejects `os.replace`-based writes (which would rotate inode and break `flock`). The deviation from `contracts/refresh-lock.md:53-54` is documented in-source and is the correct choice (RISK-1 logged for the doc-update follow-up). |
| `auth doctor` default invocation makes zero outbound HTTP calls | `tests/auth/test_auth_doctor_offline.py` | NETWORK-EGRESS | None — test patches `httpx.AsyncClient`, `urllib.request.urlopen`, `socket.create_connection` and fails if any fire on default path (only 127.0.0.1 connects allowed per C-007). |
| Lock file `0o600` permissions on POSIX | `src/specify_cli/core/file_lock.py:332-335` | FILE-PERMISSION | None — opens with `os.open(path, O_RDWR|O_CREAT, 0o600)` and parent dir at `0o700`. Other users cannot read the lock metadata. |
| State-file PID lookup via `psutil.net_connections` filter on `laddr.port == port AND status == LISTEN` | `src/specify_cli/sync/orphan_sweep.py:135-165` | PROCESS-CONFUSION | LOW — could in theory match a non-Spec-Kitty listener that happens to be on port 9400-9450. But the sweep does *not* terminate based on port alone — it requires the prior `_is_spec_kitty_daemon` check on the health-probe payload. PID lookup is purely informational for the terminate/kill escalation. Safe. |

No critical or high security findings. The mission's lock semantics, identity-matching, and process-targeting are all defensively coded and pass the relevant invariant tests.

---

## Final Verdict

**PASS WITH NOTES**

### Verdict rationale

The mission delivers the Tranche 1 incident fix correctly. The reload-before-clear reconciler in `refresh_transaction._run_locked` (lines 284-316) is the documented WP03 fix, gated by `(session_id, refresh_token)` byte-equality, exercised by both unit tests (`test_token_manager.py::test_stale_grant_with_expired_persisted_preserves_session`) and a real-subprocess regression (`test_incident_regression.py`) that completes well under the 30 s NFR-005 budget. The `MachineFileLock` POSIX deviation (using `ftruncate+write` on the held FD instead of `atomic_write`) is mathematically necessary for `flock` correctness and is documented in source; the only fallout is that `contracts/refresh-lock.md` lines 53-54 disagree with the shipped code (RISK-1 / DRIFT-2 follow-up).

Daemon self-retirement (WP04) and orphan sweep (WP05) integrate cleanly: `_decide_self_retire` is wired into `run_sync_daemon`'s `try/finally` (verified by `test_serve_forever_exits_cleanly_when_server_shutdown`), and `enumerate_orphans` enforces the R4 dual-key identity invariant before any process-targeting action. `auth doctor` (WP06) wires correctly into typer (`auth.py:100-128`) and its default path is verified to be both read-only (`test_auth_doctor_offline.py::FR-015`) and offline (`test_auth_doctor_offline.py::C-007`). All 6 WPs went through review with zero rejection cycles per the event log.

All 93 tests in the mission's primary surface pass. mypy --strict passes on all new and modified files. Architectural-boundary tests pass. Contract-tests have one environmental failure unrelated to this mission (`spec_kitty_events` 4.0.0 vs 4.1.0 version-skew).

### Open items (non-blocking)

1. **DRIFT-1 (NFR-001)** — Add a perf benchmark or document the manual measurement of single-process refresh-transaction overhead. Currently no test enforces the 50 ms p95 budget.
2. **DRIFT-2 (FR-020)** — Add a golden-output test for `auth status` post-refresh-transaction; currently only "_auth_status.py byte-identical" review-text is the evidence.
3. **RISK-1 / Contract drift** — Update `kitty-specs/cli-session-survival-daemon-singleton-01KQ9M3M/contracts/refresh-lock.md` lines 53-54 to describe the `_atomic_write_under_lock` deviation and the inode-preservation rationale. The implementation is correct; the contract document trails it.
4. **RISK-3** — Surface a finding (or remediation hint) in `auth doctor` when `enumerate_orphans()` returns `OrphanDaemon(pid=None, …)` — these orphans are unrecoverable without privilege escalation, and the user should know.
5. **RISK-4** — Update the `sweep_orphans` docstring to clarify that `timeout_s` is per-orphan, not overall (matches contract — code is correct, prose was written ambiguously).
6. **RISK-8** — Consider printing a traceback (or JSON error envelope) when `doctor_impl` raises, instead of just `f"Internal error during doctor: {exc}"`. The contract promises "stack trace printed".
7. **Coverage NFR-003** — No CI-enforced coverage gate exists in the mission's tests. WP-level reviews captured 97-99% manually; consider adding `pytest --cov-fail-under=90` to a future hardening tranche.
