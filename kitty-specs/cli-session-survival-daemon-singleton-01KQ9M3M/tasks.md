# Tasks: CLI Session Survival and Daemon Singleton

**Mission**: cli-session-survival-daemon-singleton-01KQ9M3M
**Branch**: `main` (planning, base, and merge target — all `main`)
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)
**Generated**: 2026-04-28

---

## Branch Strategy

- **Current branch at workflow start**: `main`
- **Planning/base branch for this mission**: `main`
- **Final merge target for completed changes**: `main`
- **Branch matches target**: ✅ true

Per `spec-kitty agent context resolve`: *"Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main."*

Execution worktrees are allocated per computed lane from `lanes.json` after `finalize-tasks` runs. Agents working a WP MUST enter the workspace path printed by `spec-kitty implement WP##`, not reconstruct paths manually.

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Create `src/specify_cli/core/file_lock.py` skeleton with `LockRecord` dataclass and module docstring | WP01 | [D] | [D] |
| T002 | Implement `MachineFileLock` async context manager (acquire/release, hold-ceiling, atomic content write) | WP01 | [D] |
| T003 | Implement `read_lock_record()` and `force_release()` helpers for diagnostic + repair use | WP01 | [D] |
| T004 | Implement age-based stale-lock adoption (cooperate-after-timeout) + cross-platform primitive dispatch | WP01 | [D] |
| T005 | Author `tests/core/test_file_lock.py` (7 cases per `contracts/refresh-lock.md`) | WP01 | [D] |
| T006 | Create `src/specify_cli/auth/refresh_transaction.py` with `RefreshOutcome` enum + `run_refresh_transaction()` skeleton | WP02 | [D] |
| T007 | Implement reload-before-refresh (FR-004 `AdoptedNewer`) + lock-timeout adopt/error branches (FR-016/FR-017) | WP02 | [D] |
| T008 | Implement stale-grant reconciler (FR-005 `CurrentRejectionCleared` vs FR-006 `StaleRejectionPreserved`) | WP02 | [D] |
| T009 | Wire user-readable re-login message + recovery command on confirmed-current rejection (FR-007) | WP02 | [D] |
| T010 | Refactor `TokenManager.refresh_if_needed` to delegate to `run_refresh_transaction`; preserve in-process `asyncio.Lock` (FR-003); add INFO logs per outcome (FR-019) | WP02 | [D] |
| T011 | Extend `tests/auth/test_token_manager.py` with new internal-flow coverage and golden FR-020 status output check | WP02 | [D] |
| T012 | Author `tests/auth/concurrency/conftest.py` (in-process fake refresh server fixture + tmp-rooted auth-store env override) | WP03 | [D] |
| T013 | Author `tests/auth/concurrency/test_machine_refresh_lock.py` (concurrent same-process refresh produces one network call) and `tests/auth/concurrency/test_stale_grant_preservation.py` (rotate-then-stale-grant scenario + clear-message assertion) | WP03 | [D] |
| T014 | Author `tests/auth/concurrency/test_incident_regression.py` (subprocess-based two-worker test reproducing the incident under file barriers; ≤30 s wall-clock) | WP03 | [D] |
| T015 | Add `DAEMON_TICK_SECONDS=30` constant and `_start_self_check_tick(server, my_port)` helper in `sync/daemon.py` | WP04 | [D] |
| T016 | Wire the tick thread into `run_sync_daemon`; cancel on `serve_forever` exit | WP04 | [D] |
| T017 | Implement self-retirement decision (parse `DAEMON_STATE_FILE`; if recorded port ≠ self.port and record valid, call `server.shutdown()`); preserve no-rewrite invariant when state file missing/malformed | WP04 | [D] |
| T018 | Author `tests/sync/test_daemon_self_retirement.py` (4 cases: retires-on-mismatch, continues-on-match, continues-on-missing, continues-on-malformed) | WP04 | [D] |
| T019 | Create `src/specify_cli/sync/orphan_sweep.py` with `OrphanDaemon` and `SweepReport` frozen dataclasses + module docstring | WP05 | [D] |
| T020 | Implement `enumerate_orphans()` — port scan 9400-9450, /api/health probe, classify by `protocol_version`+`package_version`, exclude state-file port | WP05 | [D] |
| T021 | Implement `sweep_orphans()` — escalating shutdown (HTTP → terminate(1s) → kill(1s)) + state-file cleanup; return `SweepReport` | WP05 | [D] |
| T022 | Author `tests/sync/test_orphan_sweep.py` (7 cases per `contracts/daemon-singleton.md`) | WP05 | [D] |
| T023 | Create `src/specify_cli/cli/commands/_auth_doctor.py` with `DoctorReport` dataclass + `assemble_report()` (read-only data gathering only) | WP06 | [D] |
| T024 | Implement Rich rendering for all 7 sections (Identity, Tokens, Storage, Refresh Lock, Daemon, Orphans, Findings) reusing `_auth_status` formatters | WP06 | [D] |
| T025 | Implement findings-and-remediation logic (F-001..F-007) + exit-code policy (0 / 1 / 2) | WP06 | [D] |
| T026 | Implement `--json` mode with `schema_version: 1`; assert no network calls fire on default invocation (C-007) | WP06 | [D] |
| T027 | Wire `@app.command()` `doctor` in `cli/commands/auth.py` with `--reset`, `--unstick-lock`, `--stuck-threshold`, `--json` flags; `--reset` calls `sweep_orphans`; `--unstick-lock` calls `force_release` only when stuck | WP06 | [D] |
| T028 | Author `tests/auth/test_auth_doctor_report.py` + `tests/auth/test_auth_doctor_repair.py` + `tests/auth/test_auth_doctor_offline.py` (combined per the contract test tables) | WP06 | [D] |

**Total**: 28 subtasks across 6 work packages.

---

## Phase 1 — Setup

*(No setup WPs required; the dev environment is configured and the auth and sync subsystems already exist.)*

---

## Phase 2 — Foundational

### WP01 — Cross-platform machine-wide file lock helper

**Goal**: Build `src/specify_cli/core/file_lock.py` — a self-contained, cross-platform machine-wide lock helper used by the refresh transaction (WP02) and the doctor command (WP06). Wraps `fcntl.flock` (POSIX) and `msvcrt.locking` (Windows). Supports bounded acquisition, hold-ceiling enforcement, age-based staleness, and atomic JSON content for diagnostics.
**Priority**: P1 (blocks WP02, WP06)
**Estimated prompt size**: ~360 lines (5 subtasks × ~70 lines)
**Independent test**: `pytest tests/core/test_file_lock.py -v` passes.
**Dependencies**: none

**Included subtasks**:
- [x] T001 Module skeleton + LockRecord dataclass (WP01)
- [x] T002 MachineFileLock async context manager (WP01)
- [x] T003 read_lock_record + force_release helpers (WP01)
- [x] T004 Stale-lock adoption + cross-platform dispatch (WP01)
- [x] T005 Test suite — 7 cases per contract (WP01)

**Implementation sketch**: Stand up the dataclass and module docstring (T001), then build the `MachineFileLock` async context manager (T002) using a non-blocking `fcntl.flock`/`msvcrt.locking` acquire with a bounded-wait loop. Add `read_lock_record`/`force_release` (T003) for the doctor surface. Add age-based adoption (T004) so a process holding a stuck lock cannot block forever. Tests last (T005) cover all branches against a tmp-path lock root.

**Parallel opportunities**: T005 test scaffolding can be drafted alongside T002.

**Risks**: Cross-platform branch in T004 — Windows-only path is exercised on POSIX CI via `pytest.mark.skipif`. The lift of `_is_daemon_lock_contention` from `sync/daemon.py` is **deferred**: WP01 ships its own predicate locally; WP04 may import or unify later. This avoids overlapping `owned_files` between WP01 and WP04.

**Prompt file**: [tasks/WP01-machine-file-lock-helper.md](tasks/WP01-machine-file-lock-helper.md)

---

## Phase 3 — Story WPs

### WP02 — Refresh transaction with stale-grant preservation

**Goal**: Build `src/specify_cli/auth/refresh_transaction.py` and rewire `TokenManager.refresh_if_needed` to delegate through it. The transaction is bounded by `MachineFileLock` (WP01). It reloads persisted material before deciding, adopts newer-and-valid material when present (FR-004), and on `invalid_grant`/`session_invalid` reloads again to distinguish stale-token rejection (preserve session, FR-006) from current-token rejection (clear session + tell the user how to re-login, FR-005/FR-007).
**Priority**: P1 (the incident fix and the heart of the mission)
**Estimated prompt size**: ~480 lines (6 subtasks × ~80 lines)
**Independent test**: `pytest tests/auth/test_token_manager.py -v` passes; existing tests in this file remain green.
**Dependencies**: WP01

**Included subtasks**:
- [ ] T006 `refresh_transaction.py` skeleton + `RefreshOutcome` enum (WP02)
- [ ] T007 Reload-before-refresh + lock-timeout adopt/error (WP02)
- [ ] T008 Stale-grant reconciler — current-vs-stale rejection branches (WP02)
- [ ] T009 User-readable re-login message + recovery command (WP02)
- [ ] T010 `TokenManager.refresh_if_needed` delegates; preserve `asyncio.Lock`; INFO logs per outcome (WP02)
- [ ] T011 Extend `test_token_manager.py` with new-flow coverage + golden FR-020 status output (WP02)

**Implementation sketch**: Build the new module top-down (skeleton → happy path → failure-mode reconciler → user-facing message). Then rewire `TokenManager` so the in-process `asyncio.Lock` runs first as a same-process fast path (FR-003) and `run_refresh_transaction` runs inside it. Tests assert each `RefreshOutcome` produces a unique observable side-effect (storage write or not, log line, exception class).

**Parallel opportunities**: T011 test additions can be drafted alongside T010 wiring once the `RefreshOutcome` enum is stable.

**Risks**: NFR-001's 50 ms p95 overhead is tight. The lock acquire path is the dominant cost; the bounded-acquire loop must use 100 ms sleep increments only when contended, not in the happy path. **Backward-compat**: `RefreshTokenExpiredError` and `SessionInvalidError` must still propagate so existing callers in `auth/transport.py` keep working.

**Prompt file**: [tasks/WP02-refresh-transaction.md](tasks/WP02-refresh-transaction.md)

---

### WP03 — Concurrency and multiprocess regression tests

**Goal**: Verify WP01+WP02 behavior under concurrent and multiprocess load. Three tests: same-process concurrent refresh (one network call), rotate-then-stale-grant scenario (session preserved + clear message on real rejection), and the incident regression (two real subprocesses driving the rotate-then-stale-grant ordering against a fake server, bounded ≤30 s wall-clock per NFR-005).
**Priority**: P1 (NFR-005 anchor)
**Estimated prompt size**: ~280 lines (3 subtasks × ~90 lines)
**Independent test**: `pytest tests/auth/concurrency -v` passes (all three tests).
**Dependencies**: WP01, WP02

**Included subtasks**:
- [ ] T012 `tests/auth/concurrency/conftest.py` — in-process fake refresh server + tmp-auth-store env override (WP03)
- [ ] T013 `test_machine_refresh_lock.py` + `test_stale_grant_preservation.py` (WP03)
- [ ] T014 `test_incident_regression.py` — subprocess-based two-worker test under file barriers (WP03)

**Implementation sketch**: Start with the conftest fixture (T012) so the rest of WP03 has a working harness. Add the deterministic single-process tests next (T013) to confirm the contract before scaling to subprocesses. Finish with T014 — the subprocess regression — using `subprocess.Popen` and file-system barriers (`tmp_path / "rotated.flag"`) to sequence Worker A (rotates) then Worker B (stale-grant) without `time.sleep`-based ordering.

**Parallel opportunities**: Once T012 lands, T013 and T014 can be drafted in parallel.

**Risks**: Multiprocess test flake on slow CI (R5). Counter-design: file-barrier sequencing only, hard 30 s wall-clock cap, no shared event loops.

**Prompt file**: [tasks/WP03-concurrency-and-incident-regression-tests.md](tasks/WP03-concurrency-and-incident-regression-tests.md)

---

### WP04 — Daemon self-retirement tick

**Goal**: Make every sync daemon poll `DAEMON_STATE_FILE` every `DAEMON_TICK_SECONDS=30`. If the recorded port differs from the daemon's own bound port, the daemon initiates clean shutdown. Closes the gap that allowed orphan daemons to accumulate after the existing daemon-spawn lock drift (FR-008/FR-010).
**Priority**: P1
**Estimated prompt size**: ~280 lines (4 subtasks × ~70 lines)
**Independent test**: `pytest tests/sync/test_daemon_self_retirement.py -v` passes.
**Dependencies**: none

**Included subtasks**:
- [x] T015 `DAEMON_TICK_SECONDS` constant + `_start_self_check_tick` helper (WP04)
- [x] T016 Wire tick thread into `run_sync_daemon`; cancel on serve_forever exit (WP04)
- [x] T017 Self-retirement decision: parse state file, compare port, server.shutdown() (WP04)
- [x] T018 Test suite — retires/continues across 4 state-file scenarios (WP04)

**Implementation sketch**: Add the constant and helper as additive code in `sync/daemon.py`. Wire the helper as a daemon thread started in `run_sync_daemon` and cancel it in the `finally` block. The retirement decision must NEVER rewrite the state file (state ownership is `_ensure_sync_daemon_running_locked` only).

**Parallel opportunities**: Independent of WP01, WP02, WP03, WP05.

**Risks**: R6 — two concurrent daemons each thinking they won. Counter-design: the state file is the tiebreaker; whichever daemon's port is **not** in the state file shuts down. Tick interval (30 s) trades convergence latency against disk noise.

**Prompt file**: [tasks/WP04-daemon-self-retirement-tick.md](tasks/WP04-daemon-self-retirement-tick.md)

---

### WP05 — Orphan daemon sweep

**Goal**: Build `src/specify_cli/sync/orphan_sweep.py` with `enumerate_orphans()` (probe ports 9400-9450 via /api/health and classify by `protocol_version`+`package_version`) and `sweep_orphans()` (escalating shutdown: HTTP → SIGTERM → SIGKILL). Provides the user-triggered recovery path consumed by `auth doctor --reset` (WP06).
**Priority**: P1
**Estimated prompt size**: ~340 lines (4 subtasks × ~85 lines)
**Independent test**: `pytest tests/sync/test_orphan_sweep.py -v` passes (7 cases).
**Dependencies**: none

**Included subtasks**:
- [ ] T019 `orphan_sweep.py` skeleton — `OrphanDaemon` and `SweepReport` dataclasses (WP05)
- [ ] T020 `enumerate_orphans()` — port scan + identity probe (WP05)
- [ ] T021 `sweep_orphans()` — escalating shutdown + state-file cleanup (WP05)
- [ ] T022 Test suite — 7 cases per `contracts/daemon-singleton.md` (WP05)

**Implementation sketch**: Module skeleton first (T019). The probe (T020) must use a tight per-port `connect_ex` timeout (50 ms) so the worst-case 50-port scan stays within NFR-006's 3 s ceiling. The sweep (T021) escalates: HTTP shutdown without token (best-effort, 403 expected), then `psutil.Process.terminate()` (1 s wait), then `kill()` (1 s wait). State-file cleanup is best-effort.

**Parallel opportunities**: Independent of WP02, WP03, WP04. Can run in parallel with WP04 in a different lane.

**Risks**: R4 — non-Spec-Kitty process listening on the same port. Counter-design: orphan classification requires both `protocol_version` and `package_version` JSON keys in the response; anything else is left alone.

**Prompt file**: [tasks/WP05-orphan-daemon-sweep.md](tasks/WP05-orphan-daemon-sweep.md)

---

### WP06 — `spec-kitty auth doctor` command

**Goal**: Add the `auth doctor` typer command. Default invocation is read-only and reports 7 sections (Identity, Tokens, Storage, Refresh Lock, Daemon, Orphans, Findings/Remediation). `--reset` calls `sweep_orphans()` from WP05. `--unstick-lock` calls `force_release()` from WP01 only when the lock is older than `--stuck-threshold` (default 60 s). `--json` emits the schema in `data-model.md`. C-007 forbids network calls on the default path.
**Priority**: P1
**Estimated prompt size**: ~520 lines (6 subtasks × ~85 lines — slightly over target because all paths share one rendering surface and need cohesive guidance)
**Independent test**: `pytest tests/auth/test_auth_doctor_report.py tests/auth/test_auth_doctor_repair.py tests/auth/test_auth_doctor_offline.py -v` passes.
**Dependencies**: WP01 (lock introspection), WP05 (orphan listing).

**Included subtasks**:
- [x] T023 `_auth_doctor.py` skeleton — `DoctorReport` + `assemble_report()` (read-only) (WP06)
- [x] T024 Rich rendering of 7 sections (reuse `_auth_status` formatters) (WP06)
- [x] T025 Findings + remediation (F-001..F-007) + exit-code policy (WP06)
- [x] T026 `--json` mode with `schema_version: 1`; assert no-network on default (WP06)
- [x] T027 Wire `doctor` typer subcommand with all flags in `cli/commands/auth.py` (WP06)
- [x] T028 Test suite — report + repair + offline (3 test files combined per contract) (WP06)

**Implementation sketch**: Build the data layer first (T023): pure functions reading session, lock, daemon, and orphan state into a `DoctorReport`. Add Rich rendering (T024) on top, reusing formatters from `_auth_status.py`. Layer findings/remediation logic (T025), then `--json` (T026). Wire typer last (T027). Tests gate every path including the C-007 offline guarantee (T028).

**Parallel opportunities**: T024 (rendering) and T026 (--json) can be drafted in parallel once T023 lands.

**Risks**: NFR-006's 3 s ceiling is tight if the port scan is naive. Counter-design: `connect_ex` with 50 ms per-port timeout filters closed ports fast; HTTP probe only fires for ports that accepted the connection.

**Prompt file**: [tasks/WP06-auth-doctor-command.md](tasks/WP06-auth-doctor-command.md)

---

## Phase 4 — Polish

*(No polish WPs required. Documentation updates are folded into each WP's DoD as needed.)*

---

## Lane partition (proposed; finalize-tasks will compute)

- **Lane A (sequential foundation)**: WP01 → WP02 → WP03 → WP06
- **Lane B (independent)**: WP04
- **Lane C (independent)**: WP05

WP06 must follow WP01 + WP05; running WP06 in Lane A means it waits for both. If `finalize-tasks` chooses to put WP05 into a fourth lane, WP06 must rebase across both before merging.

## Implementation order recommendation

WP01 first (foundation; blocks WP02 and WP06). Then WP02 (the incident fix). WP03 verifies WP01+WP02. WP04 and WP05 are independent and can run in parallel after WP01 lands. WP06 lands last because it consumes both WP01 and WP05.
