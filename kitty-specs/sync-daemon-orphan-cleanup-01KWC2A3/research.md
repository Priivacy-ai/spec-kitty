# Phase 0 Research: Safe Sync Daemon Orphan Cleanup

**Mission**: `sync-daemon-orphan-cleanup-01KWC2A3` · **Source**: issue [#2261](https://github.com/Priivacy-ai/spec-kitty/issues/2261)

This document consolidates the codebase investigation and the resolved planning decisions. All file:line anchors were captured from the current `fix/sync-daemon-orphan-cleanup` checkout.

## Root-cause analysis (why 18 orphans accumulated)

Two cleanup surfaces exist today with **different and incompatible identity models**:

| Surface | Entry | Identity model | Reporting |
|---------|-------|----------------|-----------|
| Startup canonical reaper | `reap_orphan_daemons` (`src/specify_cli/sync/owner.py:707-789`), invoked from `_reap_same_executable_orphans` (`sync/daemon.py:1143-1162`) at spawn | **3-part AND-filter**: (1) daemon-root scope marker matches, (2) production spawn-shape, (3) **executable identity matches foreground** | `ReapResult{reaped, failed, skipped_out_of_scope}` (`owner.py:544-559`) |
| `auth doctor --reset` port sweep | `enumerate_orphans` / `sweep_orphans` (`sync/orphan_sweep.py:273-380`) | listener answers `/api/health` with `protocol_version`+`package_version` keys (`_is_spec_kitty_daemon`) | `SweepReport{swept, failed}` (`orphan_sweep.py:107-120`) — counts only |

**The leak**: the startup reaper requires **executable identity to match the foreground** (skip-condition 3, `owner.py:767-777`). Daemons left by a *prior installed version* frequently resolve to a different `executable_path` / `source_checkout_path`, or predate the daemon-root marker, so the reaper logs them as `skipped_out_of_scope` and **never reaps them**. They keep listening on `9401, 9402, …`, exactly the 18-orphan / `3.2.2`–`3.2.4` symptom in the issue.

**The fix (FR-008)** is therefore architectural, not a tuning tweak: make the **daemon-root scope marker** (`DAEMON_SCOPE_ARG_PREFIX = "--spec-kitty-daemon-root="`, `daemon.py:815`; resolved scope `_daemon_scope_root()`, `daemon.py:818-830`) the **primary kill authority**, and **demote executable/version mismatch from a skip-gate to stale-version evidence**. A daemon whose scope marker proves it shares this runtime's daemon root is *ours*; a different version is then a reason to clean it, not to skip it.

## What already exists (reuse, do not rebuild)

- **Identity data**: `DaemonOwnerRecord` (`owner.py:86-148`) already carries `pid, port, package_version, executable_path, source_checkout_path, server_url, auth_principal, auth_team, auth_scope, queue_db_path, started_at`. The redacted record is already surfaced on `/api/health` (`daemon.py:514-520`).
- **Scope + identity helpers**: `_cmdline_daemon_root_marker`, `_cmdline_has_daemon_spawn_signature`, `_process_executable_scopes` (`owner.py:573-641`).
- **Kill escalation**: canonical `_sweep_daemon_process` (terminate→kill) (`owner.py:644-705`), used by both surfaces.
- **Version handling**: `DAEMON_PROTOCOL_VERSION = 1` (`daemon.py:204`), `_get_package_version()` (`daemon.py:238-250`, reads `SPEC_KITTY_CLI_VERSION` env first), `_daemon_version_matches` (`daemon.py:378-393`).
- **Self-retirement**: a tick already exists (`tests/sync/test_daemon_self_retirement.py`) — extend it, do not invent.
- **Live-subprocess test harness**: `_DaemonHarness` + `_spawn_daemon` (real `run_sync_daemon` subprocess via `python -c`, `start_new_session=True`) and port helpers in `tests/sync/test_orphan_sweep.py:35-197`; record/state fabricators `_build_record` (`tests/sync/test_daemon_owner_record.py:55-73`) and `_write_state` (`tests/sync/test_daemon_self_retirement.py:41-47`); per-worker HOME isolation (`tests/conftest.py:32-268`).
- **Dashboard boundary**: `_cleanup_orphaned_dashboards_in_range` (`dashboard/lifecycle.py:199-256`) is already range-isolated to `[9237,9337)`; `DaemonIntent.LOCAL_ONLY` (`daemon.py:181-186`) already makes the dashboard skip sync auto-start (`server.py:81-85`, `daemon.py:961`). These need **regression-locking**, not change.

## Resolved decisions

### D-01 — Classification of a wedged/unresponsive in-range listener → `operator_required`
- **Decision** (`DM-01KWC36NQBY670Q52B7C4SX2KH`): `safe_auto` **requires a live `/api/health` self-report** whose reported `pid`/`port` match the actual listener. A listener that is in range and cmdline-scope-proven but does **not** answer health (wedged/hung) is `operator_required` — surfaced and cleanable via `--reset`, never auto-killed at startup.
- **Rationale**: Matches the issue's literal `safe_auto` wording ("self-reported PID/port match the listener") and the never-silently-kill-ambiguous philosophy. The real-world 18 orphans are *responsive* (that is how the port sweep detects them), so this does not slow the primary goal; it only protects the genuinely ambiguous hung-daemon edge case.
- **Alternatives considered**: trust cmdline scope-proof alone (auto-kill wedged daemons). Rejected: a daemon hung mid-work would be killed without a self-report, contradicting the safety envelope; `--reset` still reaches it.

### D-02 — `auth doctor --reset` guards `operator_required` behind `--force`/confirmation
- **Decision** (`DM-01KWC36QG4ZH8J79J9G1Y06FCD`): `--reset` auto-cleans `safe_auto`. For `operator_required` it requires an interactive `y/N` confirmation, or `--force` in `--json`/non-interactive contexts, before killing.
- **Rationale**: `operator_required` includes **cross-root / different-`$HOME`** daemons that belong to another scope — the dangerous cross-boundary case. The common upgrade orphans are same-scope and classify as `safe_auto`, so the two-command remediation (SC-005) still works without `--force`. `--force` only gates the genuinely ambiguous kills.
- **Alternatives considered**: `--reset` kills everything cleanable in one shot. Rejected: would let one scope's `--reset` terminate another scope's daemon without explicit consent.

### D-03 — #1071 reconfirmation via an automated harness test
- **Decision** (`DM-01KWC36SFC7XVDVA9QQTN1NAK8`): add a live-subprocess regression test reproducing the same-`$HOME` singleton scenario from #1071 and assert it is now handled; close #1071 with that test as evidence.
- **Rationale**: the live harness is being built for NFR-004 anyway; an automated test is durable evidence and prevents regression. Manual-only reconfirmation rots.

## Derived design decisions (no user input required)

### DD-01 — One classification engine, two families kept separate
A new pure module `src/specify_cli/sync/classification.py` exposes `classify_candidate(...) -> DaemonIdentityRecord` (with `cleanup_class`). Both sync surfaces (startup reaper path and the `auth doctor` port sweep) feed candidates through it; `auth doctor` renders it, `--reset` and startup act on the verdict. This keeps the change **local** (DIRECTIVE_024) to the `sync/` package and preserves the **sync/dashboard separation** (DIRECTIVE_001). The dashboard cleanup path is **not** merged or touched beyond regression tests.

### DD-02 — `daemon_family` becomes explicit
The identity record carries `daemon_family="sync"`. Sync classification/cleanup refuses to signal any PID whose listening port is outside `[9400,9450)` (NFR-001), giving a hard, asserted family boundary on top of the existing range isolation. Shared low-level helpers (`_fetch_health_payload`, `_is_process_alive`, `_sweep_daemon_process`) stay shared but are only ever called by the family-scoped sync module for sync cleanup; dashboard keeps its own range-scoped path.

### DD-03 — Self-retirement constant + default
A named constant `SYNC_DAEMON_IDLE_RETIREMENT_SECONDS` (proposed default **900s / 15 min**) governs general idle/no-auth/no-work retirement (FR-011); tests patch it to a low value. A **superseded** daemon (no longer the recorded singleton for its scope, FR-010) retires promptly once `sync.is_running` is false and no queue work is pending — it does not wait the full idle window, since it is pure waste. The 15-min idle default trades a small daemon cold-start cost on the next command for avoiding churn; it is a constant, easily tuned later.

### DD-04 — Version matrix in tests via `SPEC_KITTY_CLI_VERSION`
Because `_get_package_version()` reads `SPEC_KITTY_CLI_VERSION` first (`daemon.py:238-250`), the harness spawns production-shaped daemons reporting `3.2.2`/`3.2.3`/`3.2.4` by setting that env on the subprocess — no packaging gymnastics. This is the enabler for NFR-004's multi-version requirement.

### DD-05 — ADR + docs (C-005, DIRECTIVE_003/037)
Add `docs/adr/3.x/2026-06-30-1-sync-daemon-identity-and-cleanup-classification.md` recording the identity-contract change (scope marker as primary kill authority; `cleanup_class`; explicit `daemon_family`; `owner.json` is reporting data, not kill authority). Update the operator remediation runbook (`auth doctor` → `auth doctor --reset [--force]`).

## Premortem — top risks & mitigations

| Risk | Mitigation |
|------|------------|
| Relaxed authority wrongly kills a **same-scope but legitimately distinct** daemon | `safe_auto` still requires marker==scope **and** live self-report **and** not-the-recorded-singleton; cross-root stays `operator_required` behind `--force` (D-02) |
| Killing the **current healthy singleton** | Recorded singleton (state file pid/port, `daemon.py:270-304`) is always excluded from cleanup and reported as the live daemon |
| **Cross-family** kill (sync touches dashboard or vice-versa) | Sync cleanup asserts port ∈ `[9400,9450)` (NFR-001); explicit `daemon_family`; dedicated boundary regression matrix across all 4 entrypoints (IC-05) |
| **Third-party** process on a reserved port killed | `never_touch` unless positively identified as SK sync (spawn-signature or SK self-report); C-004 |
| Real-port test **flakiness** | Reuse `_DaemonHarness` port→PID map (handles macOS `AccessDenied`), isolated sub-range, serial `-n0` (NFR-006) |
| **Windows** lacks real-socket parity | `skipif(sys.platform == "win32")` on real-socket tests, mirroring existing suites; logic stays cross-platform |

## Outputs

- Entities → `data-model.md`
- Contracts → `contracts/` (classification, `auth doctor --json`/`--reset --json`, extended `/api/health`)
- Operator + developer walkthrough → `quickstart.md`
