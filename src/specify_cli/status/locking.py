"""Per-feature status locking for shared planning artifacts.

Serializes access to feature-level status artifacts that are written on the
planning checkout (`status.events.jsonl`, `status.json`, and `tasks.md`).
Parallel agents may run from separate worktrees, but they still converge on
the same planning repo paths, so these writes need an inter-process lock.
"""

from __future__ import annotations

import subprocess
import threading
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator

from filelock import FileLock, Timeout

_thread_state = threading.local()


class FeatureStatusLockTimeoutError(RuntimeError):
    """Raised when the feature status lock cannot be acquired."""


def _get_thread_locks() -> dict[str, tuple[FileLock, int]]:
    """Return per-thread lock bookkeeping for re-entrant acquisitions."""
    locks = getattr(_thread_state, "locks", None)
    if locks is None:
        locks = {}
        _thread_state.locks = locks
    return locks


def _git_common_dir(repo_root: Path) -> Path:
    """Resolve the git common dir shared by the repo and its worktrees."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return repo_root / ".git"

    common_dir = result.stdout.strip()
    if not common_dir:
        return repo_root / ".git"

    resolved = Path(common_dir)
    if not resolved.is_absolute():
        resolved = (repo_root / resolved).resolve()
    return resolved


def feature_status_lock_path(repo_root: Path, mission_slug: str) -> Path:
    """Return the per-feature lock file path under the git common dir."""
    common_dir = _git_common_dir(repo_root)
    return common_dir / "spec-kitty-locks" / f"{mission_slug}.status.lock"


#: Lock-path key for the project-level canonical event log
#: (``<repo_root>/.kittify/canonical-events.jsonl``). ``ProjectInitialized``
#: has no ``mission_slug`` to key a lock file on (F2-T1 / F2.md section 3.3,
#: section 6.3) so this fixed sentinel stands in for one. Never written into
#: any log row -- lock-path key only.
_PROJECT_LOCK_SENTINEL = "__project__"


@contextmanager
def _named_status_lock(lock_path: Path, *, timeout: float) -> Iterator[Path]:
    """Shared re-entrant FileLock acquisition, parameterized by *lock_path*.

    Both :func:`feature_status_lock` and :func:`project_event_log_lock`
    delegate here so the re-entrancy bookkeeping (``_get_thread_locks``) and
    the underlying ``FileLock`` mechanics exist in exactly one place (F2-T1:
    a second independently-maintained locking implementation is the same
    anti-pattern that produced the unlocked-writer race this lock family
    exists to close).
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    held_locks = _get_thread_locks()
    lock_key = str(lock_path)
    held = held_locks.get(lock_key)
    if held is not None:
        lock, depth = held
        held_locks[lock_key] = (lock, depth + 1)
        try:
            yield lock_path
        finally:
            lock, depth = held_locks[lock_key]
            held_locks[lock_key] = (lock, depth - 1)
        return

    lock = FileLock(str(lock_path), timeout=timeout)
    try:
        lock.acquire()
    except Timeout as exc:
        raise FeatureStatusLockTimeoutError(
            f"Timed out acquiring status lock: {lock_path}"
        ) from exc

    held_locks[lock_key] = (lock, 1)
    try:
        yield lock_path
    finally:
        del held_locks[lock_key]
        lock.release()


@contextmanager
def feature_status_lock(
    repo_root: Path,
    mission_slug: str,
    *,
    timeout: float = -1,
) -> Iterator[Path]:
    """Acquire the per-feature status lock.

    Uses the git common dir so main checkouts and worktrees coordinate on the
    same lock file. Locking is re-entrant within a single thread so callers can
    safely wrap a larger transaction around helpers that also acquire the lock.
    """
    lock_path = feature_status_lock_path(repo_root, mission_slug)
    with _named_status_lock(lock_path, timeout=timeout) as held_path:
        yield held_path


@contextmanager
def project_event_log_lock(
    repo_root: Path,
    *,
    timeout: float = -1,
) -> Iterator[Path]:
    """Acquire the project-level lock for ``.kittify/canonical-events.jsonl``.

    Same ``FileLock``-over-git-common-dir mechanism as
    :func:`feature_status_lock`, keyed by the fixed
    :data:`_PROJECT_LOCK_SENTINEL` instead of a ``mission_slug`` (that log has
    no mission to key on). Re-entrant per thread via the same shared
    bookkeeping. Serializes every writer of the project-level canonical event
    log, independently of any mission-level lock (F2-T1, F2.md section 3.3).
    """
    lock_path = (
        _git_common_dir(repo_root) / "spec-kitty-locks" / f"{_PROJECT_LOCK_SENTINEL}.status.lock"
    )
    with _named_status_lock(lock_path, timeout=timeout) as held_path:
        yield held_path
