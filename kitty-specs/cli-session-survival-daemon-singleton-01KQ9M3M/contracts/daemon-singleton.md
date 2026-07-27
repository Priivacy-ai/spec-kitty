# Contract — Daemon Convergence and Orphan Sweep

> Implements FR-008, FR-009, FR-010.
> Owned by WP04 (`src/specify_cli/sync/daemon.py` modifications) and
> WP05 (`src/specify_cli/sync/orphan_sweep.py` new module). Consumed by
> WP06 (`auth doctor`).

## Reserved port range (existing, unchanged)

```python
DAEMON_PORT_START = 9400        # src/specify_cli/sync/daemon.py
DAEMON_PORT_MAX_ATTEMPTS = 50   # i.e. 9400 .. 9449
```

A "Spec Kitty sync daemon port" is any TCP port in `[9400, 9450)`.

## State file (existing, unchanged)

`~/.spec-kitty/sync-daemon` (POSIX) or
`%LOCALAPPDATA%\spec-kitty\daemon\sync-daemon` (Windows). Plain text,
four lines:

```
http://127.0.0.1:9400      # url
9400                        # port
<bearer-token-hex>          # token (POST auth for trigger/publish/shutdown)
<pid>                       # owner pid
```

Atomically written by `_write_daemon_file`. **No format change.**

## Singleton rule

The daemon whose port matches the recorded port in `DAEMON_STATE_FILE`
is the user-level singleton. Only one daemon process can be the
singleton at any moment.

Ownership transitions only via `_ensure_sync_daemon_running_locked`,
which is gated by the existing `DAEMON_LOCK_FILE`
(`~/.spec-kitty/sync-daemon.lock`, `fcntl.flock` / `msvcrt.locking`).
No new lock is introduced for daemon ownership.

## Self-retirement tick (NEW — WP04)

```python
DAEMON_TICK_SECONDS: int = 30
```

Inside `run_sync_daemon`, a daemon-side scheduled task fires every
`DAEMON_TICK_SECONDS`. On each tick:

1. Read `DAEMON_STATE_FILE` via the existing `_parse_daemon_file`.
2. If the parsed `port` equals `self.port`: continue running (this
   process is the singleton).
3. If the parsed `port` differs from `self.port` *and* the parsed
   record looks valid (port and PID present, PID alive): initiate
   `server.shutdown()` and exit cleanly.
4. If the state file is missing or malformed: continue running but
   **do not** rewrite the state file from this code path (state file
   is owned by `_ensure_sync_daemon_running_locked` only).

Implementation: a `threading.Timer`-style daemon thread inside
`run_sync_daemon` is sufficient; the existing `BaseHTTPRequestHandler`
loop continues to handle requests in parallel.

### Implementation note

`run_sync_daemon` becomes:

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

    # NEW — WP04: self-retirement tick.
    tick_thread = _start_self_check_tick(server, my_port=port)
    try:
        server.serve_forever()
    finally:
        tick_thread.cancel()
```

## Orphan identification (NEW — WP05)

```python
@dataclass(frozen=True)
class OrphanDaemon:
    pid: int | None
    port: int
    package_version: str | None
    protocol_version: int | None


def enumerate_orphans() -> list[OrphanDaemon]: ...
```

Algorithm:

1. Read `DAEMON_STATE_FILE` once, capture `current_port` (or `None`).
2. For each `port` in `[9400, 9450)`:
   1. Open a TCP probe socket; if `connect` fails, skip.
   2. Issue `GET http://127.0.0.1:{port}/api/health` with `timeout=0.5`.
   3. Parse response JSON. If `protocol_version` and `package_version`
      keys are both present, this is a Spec Kitty daemon.
   4. If `port == current_port`: skip (singleton, not an orphan).
   5. Otherwise: append `OrphanDaemon` with PID looked up via
      `psutil.net_connections()` filter `laddr.port == port` and
      `status == "LISTEN"`.

Anything that does not respond, or whose response lacks both required
keys, is **not** classified as a Spec Kitty daemon. Sweep never
touches it.

## Orphan sweep (NEW — WP05)

```python
@dataclass(frozen=True)
class SweepReport:
    swept: list[OrphanDaemon]
    failed: list[tuple[OrphanDaemon, str]]  # (orphan, reason)
    duration_s: float


def sweep_orphans(orphans: list[OrphanDaemon], *, timeout_s: float = 5.0) -> SweepReport: ...
```

Per orphan, escalate in order until the port stops listening:

1. **Graceful HTTP shutdown**: `POST http://127.0.0.1:{port}/api/shutdown` without a token. Today this returns 403. Pre-existing daemons stay alive — that's fine; we escalate.
2. **`SIGTERM` via psutil**: `psutil.Process(orphan.pid).terminate()`. Wait up to 1 s for port to free.
3. **`SIGKILL` via psutil**: `psutil.Process(orphan.pid).kill()`. Wait up to 1 s.
4. **State-file cleanup**: if a state file points at the orphan port, remove it.

Each step's failure (no PID, AccessDenied, port still listening) is recorded in `SweepReport.failed`.

Total bounded duration: `timeout_s × len(orphans)` worst case. Default `timeout_s=5.0`.

## Test contract

### `tests/sync/test_daemon_self_retirement.py`

| Test | Predicate |
|---|---|
| `test_self_retires_when_port_mismatch` | Start daemon on port A; write state file pointing at port B; daemon exits within 2 ticks. |
| `test_continues_when_port_matches` | Start daemon on port A; state file points at port A; daemon stays alive over 3 ticks. |
| `test_continues_when_state_file_missing` | Start daemon; remove state file; daemon stays alive (does not self-rewrite). |
| `test_continues_when_state_file_malformed` | Start daemon; corrupt state file; daemon stays alive. |

### `tests/sync/test_orphan_sweep.py`

| Test | Predicate |
|---|---|
| `test_enumerate_finds_singleton_only` | One daemon on 9400; state file points at 9400; `enumerate_orphans()` returns `[]`. |
| `test_enumerate_finds_orphan` | Two daemons on 9400 and 9401; state file points at 9400; `enumerate_orphans()` returns one entry on 9401. |
| `test_enumerate_skips_non_spec_kitty` | Plain HTTP server on 9402 returning 200 without our keys; not classified as orphan. |
| `test_enumerate_skips_closed_ports` | No process on 9402; not in the result. |
| `test_sweep_terminates_orphan` | Orphan running; after `sweep_orphans()`, port is closed and report `swept` lists it. |
| `test_sweep_does_not_touch_singleton` | Singleton + orphan; only the orphan is terminated. |
| `test_sweep_records_failure_on_access_denied` | Orphan PID exists but `terminate()` raises `AccessDenied`; recorded in `failed`. |
