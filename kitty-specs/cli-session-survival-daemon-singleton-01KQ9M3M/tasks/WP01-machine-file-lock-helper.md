---
work_package_id: WP01
title: Cross-platform machine-wide file lock helper
dependencies: []
requirement_refs:
- FR-001
- FR-016
- FR-017
- FR-018
- NFR-002
- NFR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-cli-session-survival-daemon-singleton-01KQ9M3M
base_commit: 33c66fca6b1e1a92d6fe973d6d586298e0c4a542
created_at: '2026-04-28T09:37:09.830179+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: claude
shell_pid: '17188'
history:
- at: '2026-04-28T09:17:32Z'
  actor: claude
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/
execution_mode: code_change
mission_slug: cli-session-survival-daemon-singleton-01KQ9M3M
owned_files:
- src/specify_cli/core/file_lock.py
- tests/core/__init__.py
- tests/core/test_file_lock.py
priority: P1
role: implementer
status: planned
tags: []
---

# WP01 — Cross-platform machine-wide file lock helper

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this work package, load the assigned agent profile via `/ad-hoc-profile-load`. The profile defines your identity, governance scope, and the boundaries inside which you operate for this WP. Do NOT begin reading the spec, plan, or code surfaces until the profile is loaded.

```
/ad-hoc-profile-load <agent_profile from frontmatter>
```

The profile-load step must complete before any tool call against this repository.

## Objective

Build `src/specify_cli/core/file_lock.py` — a self-contained cross-platform helper for **machine-wide advisory locks** under a chosen path. It is consumed by the refresh transaction (WP02) to serialize OAuth refresh attempts across CLI processes, and by `auth doctor` (WP06) to introspect and unstick a stale lock. It wraps `fcntl.flock` on POSIX and `msvcrt.locking` on Windows, using a non-blocking acquire loop with a bounded wait, and writes a JSON content record describing the holder for diagnostic use.

## Context

The mission's incident root cause was that two CLI processes from different temp checkouts shared one auth store, and a stale process used a rotated-out refresh token, got `invalid_grant`, and deleted the still-valid local session. The fix is a refresh transaction that wraps every refresh in a machine-wide lock plus reload-before-clear logic. WP01 ships only the lock primitive — no refresh logic, no auth wiring. WP02 consumes WP01.

**Key spec references** (see `spec.md`):
- FR-001: machine-wide refresh lock under the auth store root.
- FR-016: bounded lock-hold; release on network timeout.
- FR-017: lock-acquisition timeout that reloads persisted state and adopts it when valid.
- FR-018: tolerate process holding the lock being killed mid-transaction.
- NFR-002: lock MUST be released within 10 s of acquisition.
- NFR-008: cross-platform support, capability-based dispatch (no silent fallthrough).

**Key planning references**:
- `contracts/refresh-lock.md` — the canonical contract this WP fulfils.
- `research.md` D1 (lock primitive choice) and D2 (lock file location).
- `data-model.md` §"MachineRefreshLock".

## Branch Strategy

- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP01` and resolved from `lanes.json`. Do NOT reconstruct paths manually.

To start work:
```bash
spec-kitty implement WP01
```

The command prints the resolved workspace path. `cd` into it before editing.

## Subtasks

### T001 — Create `core/file_lock.py` skeleton with `LockRecord`

**Purpose**: Lay down the new module with a docstring, the `LockRecord` frozen dataclass, public `__all__`, and stubs that subsequent subtasks fill in. Establishes the import surface that WP02 and WP06 will depend on.

**Files to create**:
- `src/specify_cli/core/file_lock.py` — module with the `LockRecord` dataclass, the `MachineFileLock` class signature, and stub `read_lock_record`/`force_release` raising `NotImplementedError`.
- `tests/core/__init__.py` — empty marker so pytest discovers the new test directory.

**Steps**:
1. Module docstring stating purpose, the (POSIX, Windows) primitive split, and the consumer list (WP02, WP06).
2. Define `LockRecord` per `data-model.md` §"MachineRefreshLock":
   ```python
   @dataclass(frozen=True)
   class LockRecord:
       schema_version: int
       pid: int
       started_at: datetime  # tz-aware UTC
       host: str
       version: str
       @property
       def age_s(self) -> float: ...
       def is_stuck(self, threshold_s: float = 60.0) -> bool: ...
   ```
3. Define `MachineFileLock` signature with `__init__`, `__aenter__`, `__aexit__`. Body raises `NotImplementedError("WP01 T002")`.
4. Define `read_lock_record(path: Path) -> LockRecord | None` and `force_release(path: Path, *, only_if_age_s: float = 60.0) -> bool` stubs raising `NotImplementedError`.
5. `from __future__ import annotations` at the top; full type signatures throughout.

**Validation**: `python -c "from specify_cli.core.file_lock import MachineFileLock, LockRecord, read_lock_record, force_release"` succeeds.

### T002 — Implement `MachineFileLock` async context manager

**Purpose**: Build the acquire/release path with a bounded-wait acquire, atomic content write under the OS lock, and unconditional release on exit.

**Steps**:
1. Implement the OS-primitive switch:
   - On POSIX: `import fcntl`; `fcntl.flock(fd, LOCK_EX | LOCK_NB)` to acquire; `fcntl.flock(fd, LOCK_UN)` to release.
   - On Windows: `import msvcrt`; `msvcrt.locking(fd, LK_NBLCK, 1)` / `msvcrt.locking(fd, LK_UNLCK, 1)`.
   - Place the import inside platform-guarded `if sys.platform == "win32"` blocks (matching `sync/daemon.py`'s pattern).
2. Implement a private `_is_contention_error(exc: OSError) -> bool` predicate: `BlockingIOError`; or POSIX errno in `{EACCES, EAGAIN}`; or Windows errno in `{EACCES, EDEADLK}`. Return `False` for any other error so genuine I/O errors propagate.
3. In `__aenter__`:
   - Open lock file for write (create-if-missing, mode `0o600`).
   - Loop up to `acquire_timeout_s` (default 10 s):
     1. Try OS lock (non-blocking). On success, build a `LockRecord` (`pid=os.getpid()`, `started_at=datetime.now(UTC)`, `host=socket.gethostname()`, `version=importlib.metadata.version("spec-kitty-cli")` with `"unknown"` fallback, `schema_version=1`), write via `specify_cli.core.atomic.atomic_write`, return the record.
     2. On contention: read existing record via `read_lock_record(self.path)`; if `record is not None and record.age_s > stale_after_s`, attempt one staleness adoption (delete file, retry once); else `await asyncio.sleep(0.1)`.
   - Past `acquire_timeout_s`, raise `LockAcquireTimeout(path=str(self.path))`.
4. In `__aexit__`: truncate or unlink the content file (best-effort) and unconditionally release the OS lock and close the FD inside `try/finally`.

**Files**: `src/specify_cli/core/file_lock.py`.

**Validation**: a unit test acquires the lock, asserts `read_lock_record(path)` returns a `LockRecord` with the current PID, exits the context, asserts `read_lock_record(path) is None`.

**Edge cases**: Lock file dir doesn't exist → helper creates with `parents=True, mode=0o700` on POSIX. The OS lock release is unconditional (`finally`).

### T003 — Implement `read_lock_record` and `force_release`

**Purpose**: Diagnostic helpers consumed by `auth doctor`. Read-only `read_lock_record` returns the current holder's record. `force_release` removes a stuck lock — but only if its age exceeds the threshold (so a healthy in-flight lock cannot be ripped out from under).

**Steps**:
1. `read_lock_record(path)`:
   - If file missing: return `None`.
   - Read bytes, parse JSON. If parse fails or required keys missing: return `None`.
   - Construct `LockRecord(...)` with tz-aware `started_at` from ISO-8601 string.
2. `force_release(path, *, only_if_age_s=60.0)`:
   - Call `read_lock_record(path)`. If `None`: return `False`.
   - If `record.age_s <= only_if_age_s`: return `False` (lock is fresh, do not touch).
   - Otherwise: `path.unlink(missing_ok=True)` and return `True`.

**Files**: `src/specify_cli/core/file_lock.py`.

**Validation**: tests assert `read_lock_record` returns `None` for missing/corrupt files; `force_release` is a no-op on fresh locks and returns `True` for stale ones.

### T004 — Stale-lock adoption + cross-platform dispatch coverage

**Purpose**: Wrap up cross-platform branches and the staleness contract. Adoption (a process discovers an abandoned lock and reclaims it) must be safe on both POSIX and Windows.

**Steps**:
1. Confirm the staleness adoption path (T002 step 3.2) works correctly: when a process attempts to acquire and observes `record.age_s > stale_after_s`, it deletes the file and retries the OS lock once. If still contended (someone else also detected and adopted), continue the bounded-wait loop normally.
2. Add `LockAcquireTimeout(Exception)` and re-export from `__all__`.
3. Add a module-level `STALE_AFTER_S_DEFAULT = 60.0` constant; surface it as the default for `force_release(only_if_age_s=)` and `MachineFileLock(stale_after_s=)`.
4. Verify Windows path with a `pytest.mark.skipif(sys.platform != "win32", ...)` test that imports `msvcrt` and exercises the basic acquire/release.

**Files**: `src/specify_cli/core/file_lock.py`.

**Validation**: `mypy --strict src/specify_cli/core/file_lock.py` passes with zero errors.

### T005 — `tests/core/test_file_lock.py` — 7 cases per contract

**Purpose**: Cover every branch in `contracts/refresh-lock.md` §"Test contract".

**Steps**: implement these tests:
1. `test_acquire_and_release` — record on disk inside the context, gone after.
2. `test_concurrent_acquire_serialized` — two `asyncio.create_task` callers serialize.
3. `test_acquire_timeout_raises` — when held by a fixture, second acquire raises `LockAcquireTimeout` after `acquire_timeout_s`.
4. `test_stale_lock_adopted` — manually write a record dated 120 s ago; next acquire succeeds.
5. `test_force_release_only_when_stuck` — `force_release(only_if_age_s=60)` returns `False` on a fresh lock and `True` on a 120-s-old lock.
6. `test_atomic_content_write` — patch `atomic_write` to fail mid-write; assert `read_lock_record` returns `None` (no half-written record visible).
7. `test_platform_dispatch` — POSIX-only path imports `fcntl`; Windows path is exercised via `pytest.mark.skipif`.

**Files**: `tests/core/test_file_lock.py`, `tests/core/__init__.py`.

**Validation**: `pytest tests/core/test_file_lock.py -v` exits zero. `coverage run -m pytest tests/core/test_file_lock.py` shows ≥ 90 % line coverage of `core/file_lock.py`.

## Definition of Done

- All 5 subtasks complete with tests green.
- `mypy --strict src/specify_cli/core/file_lock.py` zero errors.
- `ruff check src/specify_cli/core/file_lock.py tests/core/test_file_lock.py` clean.
- Coverage ≥ 90 % for `core/file_lock.py`.
- `LockAcquireTimeout` exported from `specify_cli.core.file_lock`.
- No modifications to `sync/daemon.py` or any auth file (those are WP02/WP04 territory).

## Risks

- **Cross-platform dispatch**: Windows is exercised in CI via skipif-protected test; if no Windows runner is configured, manual smoke-test on a Windows machine before merge.
- **Lock file on shared filesystem (NFS/SMB)**: documented limitation; the helper records `host` so `auth doctor` can flag mismatches. Out of scope for full network-fs correctness in Tranche 1.

## Reviewer Guidance

Verify:
1. The OS lock is acquired BEFORE writing content (otherwise readers race).
2. `__aexit__` releases the OS lock unconditionally via `try/finally`.
3. `force_release(only_if_age_s=)` cannot drop a fresh lock — assert with a unit test.
4. Tests cover all 7 cases in `contracts/refresh-lock.md`.
5. No `# type: ignore` comments. No `# noqa` outside platform-guarded imports.
