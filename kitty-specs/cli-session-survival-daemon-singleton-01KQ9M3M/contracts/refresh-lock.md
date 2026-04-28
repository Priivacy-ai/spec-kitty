# Contract — Machine-wide Refresh Lock

> Implements FR-001, FR-002, FR-016, FR-017, FR-018; NFR-002, NFR-008.
> Owned by WP01 (`src/specify_cli/core/file_lock.py`) and consumed by
> WP02 (`src/specify_cli/auth/refresh_transaction.py`) and WP06
> (`src/specify_cli/cli/commands/_auth_doctor.py`).

## Path

| Platform | Path |
|---|---|
| POSIX (macOS, Linux) | `~/.spec-kitty/auth/refresh.lock` |
| Windows | `%LOCALAPPDATA%\spec-kitty\auth\refresh.lock` (resolved via `specify_cli.paths.get_runtime_root()`) |

The directory is created (with parents) on first acquisition. Permissions
default to user-only (`0o700` directory, `0o600` file) on POSIX.

## OS-level primitive

| Platform | Call |
|---|---|
| POSIX | `fcntl.flock(fd, LOCK_EX \| LOCK_NB)` to acquire; `fcntl.flock(fd, LOCK_UN)` to release |
| Windows | `msvcrt.locking(fd, LK_NBLCK, 1)` to acquire; `msvcrt.locking(fd, LK_UNLCK, 1)` to release |

Both calls are non-blocking. Contention errors (`BlockingIOError`,
`EACCES`, `EAGAIN`, `EDEADLK`) are detected via the
`_is_daemon_lock_contention` predicate (lifted from `sync/daemon.py`
into `core/file_lock.py`).

## Content

The lock file holds a JSON record describing the current holder. After
the OS lock is acquired, the holder atomically writes:

```json
{
  "schema_version": 1,
  "pid": 12345,
  "started_at": "2026-04-28T10:30:00+00:00",
  "host": "robert-mbp.local",
  "version": "3.2.0a5"
}
```

| Field | Type | Source |
|---|---|---|
| `schema_version` | `int` | `1` for Tranche 1 |
| `pid` | `int` | `os.getpid()` |
| `started_at` | ISO-8601 UTC | `datetime.now(UTC).isoformat()` |
| `host` | `str` | `socket.gethostname()` |
| `version` | `str` | `importlib.metadata.version("spec-kitty-cli")` (with `"unknown"` fallback) |

Content is written via `specify_cli.core.atomic.atomic_write` so that
readers (such as `auth doctor`) never observe a partial record.

## Public Python API

```python
class LockRecord(BaseModel):  # frozen dataclass in implementation
    schema_version: int
    pid: int
    started_at: datetime  # tz-aware UTC
    host: str
    version: str

    @property
    def age_s(self) -> float: ...
    @property
    def is_stuck(self, threshold_s: float = 60.0) -> bool: ...


class MachineFileLock:
    """Async context manager. Acquires the OS lock, writes content, yields."""
    def __init__(
        self,
        path: Path,
        *,
        max_hold_s: float = 10.0,       # NFR-002 ceiling
        stale_after_s: float = 60.0,    # adopt-after-stale threshold (R2)
        acquire_timeout_s: float = 10.0,# bounded wait
    ) -> None: ...

    async def __aenter__(self) -> LockRecord: ...
    async def __aexit__(self, *args) -> None: ...


def read_lock_record(path: Path) -> LockRecord | None:
    """Read the lock record without acquiring the OS lock. Used by auth doctor."""

def force_release(path: Path, *, only_if_age_s: float = 60.0) -> bool:
    """Drop the lock file iff the record is older than `only_if_age_s`. Used by `auth doctor --unstick-lock`."""
```

## Semantics

### Acquisition

1. Open lock file for write (create if missing).
2. Loop up to `acquire_timeout_s`:
   1. Try OS lock. On success, write content via `atomic_write`, return.
   2. On contention error: read existing record. If `record.age_s > stale_after_s`, this process **may** delete the file and retry one more iteration to claim it. Otherwise sleep 100 ms and retry.
3. If `acquire_timeout_s` elapses, raise `LockAcquireTimeout`.

### Release

1. Truncate or remove the content file (best-effort).
2. Release the OS lock.
3. Close the FD.

The OS lock release is unconditional — it always happens via `try/finally`, even on exception in the protected block.

### Hold-ceiling enforcement

The protected block (the body of `async with MachineFileLock(...)`) **must** complete within `max_hold_s`. Callers enforce this with `asyncio.wait_for(...)` around their work. If the inner work raises `asyncio.TimeoutError`, the lock is released and the caller propagates the timeout.

This is how NFR-002 ("≤ 10 s lock hold") is enforced.

### Staleness rule

A lock with `record.age_s > stale_after_s` (default 60 s) is considered abandoned. Any process attempting to acquire **may** delete the lock file before retrying. This protects against process-killed-mid-transaction scenarios (R2). The threshold is generous (6× the hold ceiling) so that a slow but legitimate transaction is never preempted.

`auth doctor --unstick-lock` exposes this to the user: it calls `force_release(path, only_if_age_s=60.0)` and prints the outcome.

## Failure modes

| Mode | Behavior |
|---|---|
| Lock dir does not exist | Helper creates with parents and `0o700`. |
| Lock file is corrupt JSON | `read_lock_record()` returns `None`. Acquisition treats as `unheld` and rewrites on success. |
| Holder process is dead but lock file exists | Helper detects via `record.age_s > stale_after_s`; staleness rule applies. PID liveness check via `psutil.pid_exists` is consulted as a faster predicate but does not bypass age check (R7 — older CLI versions may not write the same content). |
| Holder is on a different host (NFS scenario) | `record.host != socket.gethostname()` triggers a warning surfaced through `auth doctor`. Lock is still respected on the local host; remote-host stuck locks are user-resolved. |

## Test contract

`tests/core/test_file_lock.py`:

| Test | Predicate |
|---|---|
| `test_acquire_and_release` | Single-process happy path; record on disk after acquire, gone after release. |
| `test_concurrent_acquire_serialized` | Two `asyncio.create_task` callers serialize through one lock. |
| `test_acquire_timeout_raises` | When held by a fixture process, second acquire raises `LockAcquireTimeout` after `acquire_timeout_s`. |
| `test_stale_lock_adopted` | Lock file with `started_at` 120 s ago is adopted on next acquire. |
| `test_force_release_only_when_stuck` | `force_release(only_if_age_s=60)` returns False on a fresh lock, True on a 120-s-old lock. |
| `test_atomic_content_write` | Reader never observes a half-written record (partial-failure injection). |
| `test_platform_dispatch` | On POSIX, `fcntl.flock` is invoked; on Windows, `msvcrt.locking`. (Marked with `pytest.mark.skipif`.) |
