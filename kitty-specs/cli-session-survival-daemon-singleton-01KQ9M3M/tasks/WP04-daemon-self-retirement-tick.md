---
work_package_id: WP04
title: Daemon self-retirement tick
dependencies: []
requirement_refs:
- FR-008
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
created_at: '2026-04-28T09:17:32+00:00'
subtasks:
- T015
- T016
- T017
- T018
history:
- at: '2026-04-28T09:17:32Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
mission_slug: cli-session-survival-daemon-singleton-01KQ9M3M
owned_files:
- src/specify_cli/sync/daemon.py
- tests/sync/test_daemon_self_retirement.py
priority: P1
status: planned
tags: []
agent_profile: python-pedro
role: implementer
agent: claude
---

# WP04 — Daemon self-retirement tick

## ⚡ Do This First: Load Agent Profile

Load the assigned agent profile via `/ad-hoc-profile-load <agent_profile>` before any other tool call.

## Objective

Add a periodic self-check to the running sync daemon. Every `DAEMON_TICK_SECONDS` (30 s), the daemon reads `DAEMON_STATE_FILE`. If the recorded port differs from `self.port` and the recorded record looks valid (port present, PID alive), the daemon initiates a clean shutdown via `server.shutdown()`. This implements FR-008 (convergence to one user-level daemon) and FR-010 (orphan daemons self-retire instead of operating on stale token state).

## Context

The existing `sync/daemon.py` already enforces single-spawn via `DAEMON_LOCK_FILE` and version-recycle on health-probe mismatch. What it lacks is a daemon-side self-check: if a new daemon successfully spawns and writes the state file (because the existing one missed its lock window or was unreachable during the spawn check), the older daemon keeps running on the now-orphaned port. The fix is one short tick that lets the older daemon retire gracefully.

**Key spec references**:
- FR-008: many temp checkouts converge to one user-level daemon.
- FR-010: orphan daemons self-retire within their next lifecycle tick.

**Key planning references**:
- `contracts/daemon-singleton.md` §"Self-retirement tick".
- `research.md` D6 (convergence rule).

## Branch Strategy

- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP04`. Independent of WP01/02/03 — runs in its own lane.

To start work:
```bash
spec-kitty implement WP04
```

## Subtasks

### T015 — `DAEMON_TICK_SECONDS` constant + `_start_self_check_tick` helper

**Purpose**: Add the periodic-tick scaffolding inside `sync/daemon.py` as a private helper. Pure additive change — no existing function modified yet.

**Steps**:
1. Add `DAEMON_TICK_SECONDS: int = 30` near the existing `DAEMON_PROTOCOL_VERSION` constant.
2. Define `def _start_self_check_tick(server: HTTPServer, my_port: int, *, interval_s: float = float(DAEMON_TICK_SECONDS)) -> threading.Timer`:
   - Create a `threading.Timer` that calls a private `_self_check(server, my_port)` after `interval_s`.
   - Make the Timer a daemon thread (`timer.daemon = True`) so it doesn't block process exit.
   - Inside `_self_check`, call `_decide_self_retire(server, my_port)` (T017), then schedule the next Timer if the server is still running.
   - Return the first Timer so the caller can `.cancel()` it on shutdown.
3. Stub `_decide_self_retire(server, my_port)` to log "self-check tick" at DEBUG. T017 fills it in.
4. `from __future__ import annotations` already at top of the module — preserved.

**Files**: `src/specify_cli/sync/daemon.py`.

**Validation**: `python -c "from specify_cli.sync.daemon import DAEMON_TICK_SECONDS, _start_self_check_tick"` succeeds.

### T016 — Wire tick into `run_sync_daemon`

**Purpose**: Start the tick when the daemon HTTP server starts, cancel it when the server exits.

**Steps**:
1. In `run_sync_daemon(port, daemon_token)`:
   - Start the tick: `tick = _start_self_check_tick(server, my_port=port)`.
   - Wrap `server.serve_forever()` in `try / finally`. In `finally`: `tick.cancel()`.

The new code:
```python
def run_sync_daemon(port: int, daemon_token: str | None) -> None:
    from specify_cli.sync.runtime import get_runtime
    get_runtime()
    handler_class = type(
        "SyncDaemonRouter",
        (SyncDaemonHandler,),
        {"daemon_token": daemon_token},
    )
    server = HTTPServer(("127.0.0.1", port), handler_class)
    tick = _start_self_check_tick(server, my_port=port)
    try:
        server.serve_forever()
    finally:
        tick.cancel()
```

**Files**: `src/specify_cli/sync/daemon.py`.

**Validation**: a smoke test starts a daemon on a tmp port, lets it run for 1 s, calls `server.shutdown()` from another thread, and confirms the daemon thread exits cleanly (no leaked Timer threads).

### T017 — Self-retirement decision in `_decide_self_retire`

**Purpose**: Implement the actual retirement logic. Read state file → compare port → optionally `server.shutdown()`. Must NEVER rewrite the state file.

**Steps**:
1. In `_decide_self_retire(server, my_port)`:
   - Try `_parse_daemon_file(DAEMON_STATE_FILE)`; on any exception log a DEBUG message and return (don't retire on parse error — state file ownership belongs to `_ensure_sync_daemon_running_locked`).
   - If parsed port is `None`: return (malformed file; do not retire).
   - If parsed port equals `my_port`: return (we are the singleton).
   - If parsed port differs from `my_port`:
     - Verify the recorded PID is alive (`_is_process_alive(parsed.pid)`); if not alive, the recorded daemon is dead but didn't clean up — do NOT retire (we're the de-facto singleton, even if the file is stale; let the next `_ensure_sync_daemon_running_locked` reconcile).
     - If alive: log INFO "self-retiring (state file points at port=%s, our port=%s)", call `server.shutdown()` (which causes `serve_forever` to return cleanly).
2. Make sure no code path inside `_decide_self_retire` calls `_write_daemon_file` or `DAEMON_STATE_FILE.unlink` — state ownership is preserved.

**Files**: `src/specify_cli/sync/daemon.py`.

**Validation**: T018 covers all four scenarios (mismatch+alive, mismatch+dead, match, missing).

**Edge cases**:
- Race between tick and `_ensure_sync_daemon_running_locked`: harmless. If the daemon retires unnecessarily, the next CLI call respawns it.
- `server.shutdown()` can deadlock if called from inside `serve_forever`'s thread; the tick runs from a Timer thread, so this is safe.

### T018 — `tests/sync/test_daemon_self_retirement.py` — 4 cases

**Purpose**: Cover every branch of `_decide_self_retire`.

**Steps**: implement these tests:
1. `test_self_retires_when_port_mismatch_and_recorded_pid_alive` — start daemon on port A; write state file pointing at port B with the current process's PID; assert daemon shuts down within 2 ticks.
2. `test_does_not_retire_when_port_mismatch_and_recorded_pid_dead` — write state file with port B and a non-existent PID; assert daemon stays alive over 3 ticks.
3. `test_continues_when_port_matches` — state file points at the daemon's own port; daemon stays alive.
4. `test_continues_when_state_file_missing_or_malformed` — remove state file (and corrupt it in another sub-case); daemon stays alive.

Speed up tests by patching `DAEMON_TICK_SECONDS` to `0.1` for the test scope.

**Files**: `tests/sync/test_daemon_self_retirement.py`.

**Validation**: `pytest tests/sync/test_daemon_self_retirement.py -v` passes; total runtime ≤ 5 s.

## Definition of Done

- All 4 subtasks complete.
- `mypy --strict` zero errors on modifications to `sync/daemon.py`.
- `ruff check` clean.
- Coverage ≥ 90 % on new and modified lines in `sync/daemon.py`.
- Existing daemon tests in `tests/sync/test_daemon.py` still pass.
- `_decide_self_retire` proven to never rewrite the state file (assertion in tests).

## Risks

- **R6** — two daemons each tick at the same instant. Counter-design: state-file ownership is the tiebreaker. If both daemons see a mismatch, only the one whose port doesn't match the recorded port retires.
- **Timer thread leakage**: ensure `tick.cancel()` runs on every exit path of `run_sync_daemon`. Test asserts no leaked threads after shutdown.

## Reviewer Guidance

Verify:
1. `_decide_self_retire` makes ZERO writes to `DAEMON_STATE_FILE` (grep the function body and assert by code review).
2. Timer thread is daemonized (`timer.daemon = True`) so it cannot keep the process alive.
3. `tick.cancel()` lives in a `finally` block.
4. The retirement decision excludes the dead-PID case (don't retire when the recorded PID is dead — that's not our job).
