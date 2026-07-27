---
mission_id: 01KQ9M3M91HND8QRPQNJVQAFH5
mission_slug: cli-session-survival-daemon-singleton-01KQ9M3M
mission_type: software-dev
target_branch: main
---

# Implementation Plan — CLI Session Survival and Daemon Singleton

**Branch**: `main` (planning) → `main` (merge target). `branch_matches_target=true`.
**Date**: 2026-04-28.
**Spec**: [`./spec.md`](./spec.md).
**Input**: Feature specification from `/Users/robert/spec-kitty-dev/spec-kitty-20260428-102808-qXl2TZ/spec-kitty/kitty-specs/cli-session-survival-daemon-singleton-01KQ9M3M/spec.md`.

> Companion docs in this directory:
> - `spec.md` — WHAT and WHY (FR/NFR/C, scenarios, success criteria)
> - `research.md` — Phase 0 design decisions (D1…D11) with rationale
> - `data-model.md` — Phase 1 entity definitions
> - `contracts/refresh-lock.md` — machine-wide refresh lock contract
> - `contracts/daemon-singleton.md` — daemon convergence + orphan-sweep contract
> - `contracts/auth-doctor.md` — `auth doctor` CLI surface contract
> - `quickstart.md` — how to run, verify, and reproduce the incident

## Summary

Tranche 1 of the AUTH Resilience and Security Program closes the local-auth-loss
path that surfaced during a real incident: a stale sync daemon's
`invalid_grant` response deleted a still-valid local session because the
client cleared on rejection without checking whether the rejected material
was still current. The fix is a **machine-wide refresh transaction** that
reloads persisted state before *and* after every refresh, plus **daemon
convergence** (self-retirement when the user-level state file points at
another port) and **orphan sweep** (HTTP-probe + graceful kill). A new
`spec-kitty auth doctor` command surfaces the relevant state and offers
opt-in repairs (`--reset`, `--unstick-lock`).

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase).
**Primary Dependencies**: `typer`, `rich`, `psutil`, `httpx` (existing). No new third-party packages.
**Storage**: filesystem only — encrypted-file `SecureStorage` backend (`Literal["file"]`); machine-wide lock file under `~/.spec-kitty/auth/`.
**Testing**: `pytest`, `mypy --strict`. Existing concurrency directory `tests/auth/concurrency/` reused for the regression test. Charter coverage floor: 90% for new and modified code.
**Target Platform**: macOS, Linux (existing supported set). Windows compatibility preserved via the same `msvcrt.locking` pattern already used by `sync/daemon.py`.
**Project Type**: single Python package (`specify_cli`).
**Performance Goals**: NFR-001 ≤50 ms refresh-transaction overhead p95 single-process; NFR-006 ≤3 s `auth doctor` time-to-actionable.
**Constraints**: NFR-002 lock-hold ceiling 10 s; NFR-005 multiprocess regression ≤30 s; C-001 refresh tokens never made non-expiring; C-003 no hosted-SaaS calls without `SPEC_KITTY_ENABLE_SAAS_SYNC=1`; C-007 `auth doctor` makes no network calls; C-008 active repairs require explicit flags.
**Scale/Scope**: per-OS-user. Reserved daemon port range 9400–9450 (50 ports). One refresh lock file. One daemon state file.

## Charter Check

The charter at `.kittify/charter/charter.md` was loaded via `spec-kitty
charter context --action plan --json` (bootstrap, references_count=0).

| Doctrine item | Status | How this plan honors it |
|---|---|---|
| DIRECTIVE_003 — Decision Documentation | ✅ honored | `research.md` records D1…D11 with rationale and rejected alternatives. The mission-level decision moment `DM-01KQ9M41VJENF0T6H83VRK5DYQ` is open and resolved. |
| DIRECTIVE_010 — Specification Fidelity | ✅ honored | Every FR/NFR/C maps to a WP target, an existing-test-coverage assertion, or an explicit no-op marker. See "Requirement-to-WP Map" below. |
| `requirements-validation-workflow` | ✅ applied | `research.md` §6 reframes each FR as a testable predicate. NFR thresholds are tied to specific test gates. |
| `premortem-risk-identification` | ✅ applied | "Risks" section below names 7 failure modes and countermeasures. |
| `problem-decomposition` | ✅ applied | Work decomposes into 7 independently tractable WPs (see "Work Package Decomposition"). |
| `eisenhower-prioritisation` | ✅ applied | WP01 (lock primitive), WP02 (refresh transaction), WP03 (stale-grant preservation) ship first. WP06 (`auth doctor`) is downstream of WP01–WP05. |
| `stakeholder-alignment` | ✅ applied | Three personas (P-DEV, P-OPS, P-DIAG) named in `spec.md`; SC-001…SC-006 cover all three. |
| Charter dependency policy (typer / rich / pytest / mypy) | ✅ honored | No new third-party dependencies. |
| Charter test policy (≥90% coverage) | ✅ honored | Inherited as NFR-003. Per-WP coverage gates listed below. |

No charter conflicts. Re-evaluated post-Phase-1 — see "Post-Phase 1 Charter Re-check".

## Project Structure

### Documentation (this feature)

```
kitty-specs/cli-session-survival-daemon-singleton-01KQ9M3M/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   └── requirements.md
├── contracts/
│   ├── refresh-lock.md
│   ├── daemon-singleton.md
│   └── auth-doctor.md
├── decisions/
│   └── DM-01KQ9M41VJENF0T6H83VRK5DYQ.md
├── meta.json
└── tasks/                  # populated by /spec-kitty.tasks (not by this command)
    └── README.md
```

### Source code (existing layout — additive only)

```
src/specify_cli/
├── core/
│   ├── atomic.py                  # existing (atomic_write helper)
│   └── file_lock.py               # NEW (WP01) — machine-wide file-lock helper
├── auth/
│   ├── token_manager.py           # MODIFIED (WP02) — delegates to refresh_transaction
│   ├── refresh_transaction.py     # NEW (WP02, WP03) — bounded transaction + reconciler
│   ├── secure_storage/            # unchanged
│   ├── flows/refresh.py           # unchanged
│   └── session.py                 # unchanged
├── sync/
│   ├── daemon.py                  # MODIFIED (WP04) — self-retirement tick
│   └── orphan_sweep.py            # NEW (WP05) — enumerate + sweep
└── cli/commands/
    ├── auth.py                    # MODIFIED (WP06) — register `doctor` subcommand
    └── _auth_doctor.py            # NEW (WP06)

tests/
├── core/
│   └── test_file_lock.py          # NEW (WP01)
├── auth/
│   ├── test_token_manager.py      # MODIFIED (WP02)
│   ├── test_auth_doctor_report.py # NEW (WP06)
│   ├── test_auth_doctor_repair.py # NEW (WP06)
│   ├── test_auth_doctor_offline.py# NEW (WP06)
│   └── concurrency/
│       ├── test_machine_refresh_lock.py    # NEW (WP02)
│       ├── test_stale_grant_preservation.py# NEW (WP03)
│       └── test_incident_regression.py     # NEW (WP07)
└── sync/
    ├── test_daemon_self_retirement.py      # NEW (WP04)
    └── test_orphan_sweep.py                # NEW (WP05)
```

**Structure Decision**: single Python package (`specify_cli`) with the
existing layout. All additions are new modules (`core/file_lock.py`,
`auth/refresh_transaction.py`, `sync/orphan_sweep.py`,
`cli/commands/_auth_doctor.py`); only `auth/token_manager.py`,
`sync/daemon.py`, and `cli/commands/auth.py` are modified, and only
additively.

## Existing Code Anchors

The plan deliberately reuses existing infrastructure rather than inventing
new shapes. Key anchors found during Phase 0 investigation:

| Surface | What is already there | What this mission adds |
|---|---|---|
| `src/specify_cli/auth/token_manager.py` | `TokenManager` with `asyncio.Lock` single-flight refresh, `clear_session()`, `refresh_if_needed()`. **`refresh_if_needed` calls `clear_session()` on `RefreshTokenExpiredError`/`SessionInvalidError` without reload** — the incident path. | Wraps `refresh_if_needed` in a machine-wide `RefreshTransaction` (acquire lock → reload → decide → refresh → reconcile). |
| `src/specify_cli/auth/secure_storage/{abstract,file_fallback,windows_storage}.py` | `SecureStorage` ABC with `read()`, `write()`, `delete()`. | No interface change; reload-before-refresh just calls `read()` again. Identity comparison uses `(session_id, refresh_token)`. |
| `src/specify_cli/sync/daemon.py` | Machine-global daemon w/ `DAEMON_LOCK_FILE` (`fcntl.flock`/`msvcrt.locking`), `DAEMON_STATE_FILE` (URL/port/token/PID), version-recycle on mismatch, ports 9400-9450. **Has no orphan sweep across the port range** and **no self-retirement when state-file PID/port doesn't match self**. | Adds `sweep_orphan_daemons()` and a daemon-side self-check tick. |
| `src/specify_cli/cli/commands/auth.py` | Typer subapp with `login`, `logout`, `status`, `whoami`. Lazy-imports `_auth_<name>.py` per command. | Adds `doctor` command + `_auth_doctor.py`. |
| `src/specify_cli/cli/commands/_auth_status.py` | Rich-rendered status; formatters `format_duration`, `format_storage_backend`, `format_auth_method`. | Reused by `auth doctor` (renders the same session block at the top of the doctor report). |
| `src/specify_cli/core/atomic.py` | `atomic_write(path, content, mkdir=True)`. | Used for new lock-file content writes. |
| `tests/auth/concurrency/` | Existing concurrency test directory. | New `test_machine_refresh_lock.py`, `test_stale_grant_preservation.py`, `test_incident_regression.py`. |
| `tests/auth/test_token_manager.py` | Existing unit tests for the in-process refresh path. | Extended in place; no rewrites. |
| `tests/sync/test_daemon.py` | Existing daemon tests. | New tests beside it for orphan sweep and self-retirement. |

## Requirement-to-WP Map

| Requirement | Implementing WP | Verifying tests |
|---|---|---|
| FR-001, FR-016, FR-017, FR-018, NFR-002 | WP01 — `core/file_lock.py` machine-wide lock helper | `tests/core/test_file_lock.py` |
| FR-002, FR-003, FR-004, FR-019, FR-020, NFR-001 | WP02 — `auth/refresh_transaction.py` + `TokenManager` integration | `tests/auth/test_token_manager.py`, `tests/auth/concurrency/test_machine_refresh_lock.py` |
| FR-005, FR-006, FR-007 | WP03 — stale-grant reconciler in `refresh_transaction.py` | `tests/auth/concurrency/test_stale_grant_preservation.py` |
| FR-008, FR-010 | WP04 — daemon self-check tick & registration record | `tests/sync/test_daemon_self_retirement.py` |
| FR-009 | WP05 — `sync/orphan_sweep.py` | `tests/sync/test_orphan_sweep.py` |
| FR-011, FR-012, FR-015, NFR-006 | WP06 — `cli/commands/_auth_doctor.py` (read-only path) | `tests/auth/test_auth_doctor_report.py` |
| FR-013, FR-014, C-008 | WP06 — `--reset` and `--unstick-lock` flags | `tests/auth/test_auth_doctor_repair.py` |
| Multiprocess regression test, NFR-005 | WP07 — `tests/auth/concurrency/test_incident_regression.py` | the test itself |
| C-001, C-002, C-006 | preserved across all WPs (no behavioral change) | existing refresh / login / logout tests must still pass |
| C-003 | enforced by test fixtures stubbing all hosted endpoints | fixture audit in `tests/auth/conftest.py` |
| C-004 | tracked at the plan level (no SaaS dependency) | n/a |
| C-005 | preserved by leaving session-file shape untouched | covered by existing `test_secure_storage_file.py` |
| C-007 | enforced by `auth doctor` having no network code paths | `tests/auth/test_auth_doctor_offline.py` |
| NFR-003 | ≥90% coverage gate in CI | per-WP coverage check |
| NFR-004 | `mypy --strict` zero new errors | per-WP mypy gate |
| NFR-007 | preserved by additive-only file layout | `test_existing_session_still_loads` |
| NFR-008 | central `core/file_lock.py` chooses primitive once | `test_file_lock_platform_dispatch` |

## Work Package Decomposition

> Detailed WP files are produced by `/spec-kitty.tasks` (do not generate them here).
> This sketch is what `/spec-kitty.tasks` will pick up.

1. **WP01 — Cross-platform machine-wide file lock helper**
   - New module: `src/specify_cli/core/file_lock.py`
   - Public surface: `MachineFileLock(path, *, max_hold_s, stale_after_s)` async context manager; `read_lock_record(path) -> LockRecord | None`; `force_release(path) -> bool`.
   - Wraps `fcntl.flock` (POSIX) and `msvcrt.locking` (Windows) using the existing `_is_daemon_lock_contention` predicate (lifted into the same module).
   - Records `{pid, started_at, host, version}` JSON content for `auth doctor` introspection.
   - Tests: bounded acquisition, contention, age-based stale detection, atomic content write, stale lock release.
   - **Lock-hold ceiling: 10 s (NFR-002).** Caller passes `max_hold_s`.

2. **WP02 — Refresh transaction in `auth/`**
   - New module: `src/specify_cli/auth/refresh_transaction.py`
   - Public surface: `async def run_refresh_transaction(storage, in_memory_session, refresh_flow, *, lock_path) -> RefreshOutcome`.
   - Flow: acquire `MachineFileLock(max_hold_s=10)` → `storage.read()` → identity-compare with `in_memory_session` → if persisted is newer-and-valid, return `Outcome.AdoptedNewer` → else call `refresh_flow.refresh(persisted)` → `storage.write(updated)` → `Outcome.Refreshed`.
   - Outcomes enum: `AdoptedNewer | Refreshed | StaleRejectionPreserved | CurrentRejectionCleared | LockTimeoutAdopted | LockTimeoutError`.
   - `TokenManager.refresh_if_needed` is rewritten to delegate to this transaction. The in-process `asyncio.Lock` remains as a same-process fast path (FR-003).
   - Diagnostic logging at `logging.INFO` for every Outcome (FR-019).

3. **WP03 — Stale-grant reconciler (the incident fix)**
   - In the refresh transaction's `except` clauses for `RefreshTokenExpiredError` and `SessionInvalidError`, **reload storage** and compare the rejected refresh token to the freshly persisted one. Only call `clear_session()` when they match. Otherwise return `StaleRejectionPreserved`.
   - Identity is `(session_id, refresh_token)` string equality. Hashing is unnecessary.
   - Tests: `tests/auth/concurrency/test_stale_grant_preservation.py` exercises the rotate-then-stale-grant ordering deterministically using two `TokenManager` instances backed by one storage and a `MockRefreshFlow` that returns `RefreshTokenExpiredError` on the second call.

4. **WP04 — Daemon self-check tick + registration record**
   - In `sync/daemon.py` HTTP server loop, every `DAEMON_TICK_SECONDS=30` the daemon reads `DAEMON_STATE_FILE`. If the recorded port differs from `self.port` (i.e. another daemon won), the daemon initiates `server.shutdown()` cleanly. This is FR-008/FR-010 self-retirement.
   - The state-file format is unchanged (URL/port/token/PID, atomic write). Backward-compatible.
   - Tests: `tests/sync/test_daemon_self_retirement.py` writes a state file pointing at a "winner" port, starts a daemon on a different port, asserts the daemon retires within 2 ticks.

5. **WP05 — Orphan daemon sweep**
   - New module: `src/specify_cli/sync/orphan_sweep.py`
   - Public surface: `enumerate_orphans() -> list[OrphanDaemon]`, `sweep_orphans(orphans, *, timeout_s=5.0) -> SweepReport`.
   - `enumerate_orphans()` scans `[DAEMON_PORT_START, DAEMON_PORT_START+DAEMON_PORT_MAX_ATTEMPTS)` (9400-9450). For each open port, probes `GET /api/health`. A daemon is "ours" if response carries both `protocol_version` and `package_version`. The "current" daemon's port matches `DAEMON_STATE_FILE`. Everything else is an orphan.
   - `sweep_orphans()` calls best-effort graceful shutdown first, escalates to `psutil.Process(pid).terminate()` then `kill()` after 1 s. PID is read from any state file present, otherwise from `psutil.net_connections()` lookup.
   - Tests: `tests/sync/test_orphan_sweep.py` spawns two real daemon subprocesses on adjacent ports with different state files, asserts only the non-current one is identified and terminated.

6. **WP06 — `spec-kitty auth doctor` command**
   - New module: `src/specify_cli/cli/commands/_auth_doctor.py`
   - New `@app.command()` `doctor` in `cli/commands/auth.py` (lazy import).
   - Default report sections (FR-011): Identity (reuses `_print_identity` from `_auth_status.py`); Tokens (access remaining, refresh remaining); Storage (backend label, persisted-vs-in-memory drift indicator); Refresh Lock (holder PID / start time, or `unheld`); Daemon (active PID / port / version, or `not-running`); Orphans (count + per-port table); Remediation (FR-012; FR-015 — never mutates).
   - Flags: `--reset` (FR-013, calls `sweep_orphans()`), `--unstick-lock` (FR-014, calls `force_release()` only when `record.started_at` is older than `STALE_LOCK_THRESHOLD_S=60`), `--json` (machine-readable output).
   - All paths: no network calls (C-007).
   - Tests: `tests/auth/test_auth_doctor_report.py` (default invocation under various states); `tests/auth/test_auth_doctor_repair.py` (flag-gated repair behaviors); `tests/auth/test_auth_doctor_offline.py` (asserts no `httpx`/`urllib` calls fire on default invocation).

7. **WP07 — Multiprocess regression test for the incident**
   - New test: `tests/auth/concurrency/test_incident_regression.py`
   - Spawns two CLI worker processes via `subprocess.Popen` with `python -c`. Each worker imports `TokenManager`, points at a `tmp_path`-rooted auth store via env-overridden home directory. Drives the rotate-then-stale-grant ordering against an in-test fake refresh server. File barriers (`tmp_path / "rotated.flag"`) sequence the two workers — no `time.sleep`-based ordering.
   - Bounded ≤30 s wall-clock (NFR-005).

Implementation order: **WP01 → WP02 → WP03 → WP04 → WP05 → WP06 → WP07**.
WP01 is the only true foundation; WP02–WP05 are independent given WP01.
WP06 depends on WP01 (lock introspection) and WP05 (orphan listing).
WP07 depends on WP02 + WP03 (subject under test).

`/spec-kitty.tasks` will compute the actual lane partition. The above is a
linear suggestion; `/spec-kitty.tasks` may parallelize WP02/WP04/WP05 once
WP01 is in place.

## Phase 0 — Outline & Research

See `research.md` for the Phase 0 output. Summary: 11 design decisions
(D1…D11) recorded with rationale, alternatives, and rejection reasons.
All `[NEEDS CLARIFICATION]` markers from `spec.md` were resolved before
the spec phase ended (the spec carries none).

## Phase 1 — Design & Contracts

See:

- `data-model.md` — the four conceptual entities from `spec.md` made concrete with field-level types, lifecycle states, and identity rules.
- `contracts/refresh-lock.md` — lock file path, content schema, semantics.
- `contracts/daemon-singleton.md` — state-file shape, self-retirement rule, orphan-identification rule.
- `contracts/auth-doctor.md` — exact CLI surface, exit codes, output schema (with a `--json` variant for diagnostic capture).
- `quickstart.md` — how to run; how to reproduce the incident manually; how to verify SC-001…SC-006.

## Post-Phase 1 Charter Re-check

After Phase 1 design:

- DIRECTIVE_003 ✅ — all four contracts and `research.md` carry the rationale and trade-off block required for material decisions.
- DIRECTIVE_010 ✅ — every FR/NFR/C now has either an implementing WP, an enforcement constraint inside an existing test file, or an explicit no-op marker. No spec drift.
- Charter dependency policy ✅ — no new third-party packages introduced.

No new charter gaps surfaced. Plan is ready for `/spec-kitty.tasks`.

## Risks (premortem-risk-identification)

| ID | Failure mode | Pre-emptive countermeasure |
|---|---|---|
| R1 | Refresh lock-hold exceeds 10 s under slow network and stalls all CLI processes. | NFR-002 sets a hard 10 s release ceiling. WP02 wraps the network call in a timeout matching the lock TTL; the timeout path returns `LockTimeoutError` and releases the lock before re-raising. |
| R2 | A process dies holding the refresh lock; subsequent processes wait forever. | WP01 lock helper uses age-based staleness. After `stale_after_s=60` any process can adopt the lock. `auth doctor --unstick-lock` is the manual override (FR-014). |
| R3 | `auth doctor` itself depends on the broken refresh path and hangs. | C-007 forbids network calls in `auth doctor`. WP06 tests assert no `httpx`/`urllib` calls fire on default invocation. |
| R4 | Orphan sweep kills a non-spec-kitty process listening on the same port range. | Orphan probe (WP05) requires a 200 response with both `protocol_version` and `package_version` JSON keys before classifying as a Spec Kitty daemon. Anything else is left alone. |
| R5 | Multiprocess regression test is flaky on slow CI. | WP07 uses explicit file barriers between rotation and stale-grant phases — no `time.sleep`-based ordering. NFR-005 caps total runtime at 30 s. |
| R6 | Two well-behaved daemons start at the same instant and both win their respective locks. | WP04 self-retirement tick: each daemon, on its first tick, reads the state file. Whichever daemon's PID/port is **not** in the state file shuts down. Tie-breaker is the state file itself (whoever wrote it last and is still alive). |
| R7 | An older CLI version (without these changes) running concurrently still deletes the session. | Out of scope for Tranche 1; `start-here.md` accepts a one-time bump as the user upgrades. The new lock files are additive; older CLIs simply ignore them and continue to mis-behave until upgraded. NFR-007 documents this. |

## Complexity Tracking

No charter violations. Section intentionally empty.

## Out of Scope (carried from spec)

- Server-side token-family/generation tracking (Tranche 2)
- RFC 7009-style revocation endpoint and CLI logout truthfulness (Tranche 2)
- WebSocket auth contract changes / bearer-in-URL removal (Tranche 3)
- OS keychain storage and `SECRET_KEY` separation (Tranche 4)
- Privileged-action gating, API-key scopes, connector OAuth, rate-limit hardening (Tranche 5)
- Cross-repo adversarial validation suite, soak runbook, release gate (Tranche 6)

## Ready for `/spec-kitty.tasks`

This plan is complete through Phase 1.

- All FR/NFR/C are mapped to a WP, an existing-test-coverage assertion, or an explicit no-op note.
- All design decisions are recorded with rationale.
- Risk register lists 7 named failure modes with countermeasures.
- The branch contract for the next step is unchanged: planning/base `main`,
  merge target `main`, `branch_matches_target=true`.

`/spec-kitty.tasks` is the next user-invoked step.
