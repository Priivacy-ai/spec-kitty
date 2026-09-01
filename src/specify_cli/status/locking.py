"""Per-feature status locking for shared planning artifacts.

Serializes access to feature-level status artifacts that are written on the
planning checkout (`status.events.jsonl`, `status.json`, and `tasks.md`).
Parallel agents may run from separate worktrees, but they still converge on
the same planning repo paths, so these writes need an inter-process lock.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator

from filelock import FileLock

from kernel.git_topology import GitTopologyError, git_common_dir
from specify_cli.core.checkout_file_lock import LOCK_DIRECTORY, acquire_or_raise

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
    """Resolve the git common dir shared by the repo and its worktrees.

    Delegates to the canonical :func:`kernel.git_topology.git_common_dir`
    probe -- the same resolver ``specify_cli.review.verdict_commit_queue``
    uses -- so this lock and the checkout-wide verdict-save queue converge on
    the identical, symlink-canonicalized common dir for a given checkout
    (worktree indirection collapsed the same way for both). Falls back to
    ``<repo_root>/.git`` when the probe cannot resolve a common dir at all
    (``repo_root`` is not a git repository, or git could not be invoked) --
    this function's historical contract, preserved so a transient git failure
    degrades status locking to a still-functional per-directory lock instead
    of raising.
    """
    try:
        return git_common_dir(repo_root)
    except GitTopologyError:
        return repo_root / ".git"


def feature_status_lock_path(repo_root: Path, mission_slug: str) -> Path:
    """Return the per-feature lock file path under the git common dir."""
    common_dir = _git_common_dir(repo_root)
    return common_dir / LOCK_DIRECTORY / f"{mission_slug}.status.lock"


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
    acquire_or_raise(
        lock,
        lock_path,
        timeout_seconds=timeout,
        build_timeout_error=lambda: FeatureStatusLockTimeoutError(
            f"Timed out acquiring status lock: {lock_path}"
        ),
    )

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
        _git_common_dir(repo_root) / LOCK_DIRECTORY / f"{_PROJECT_LOCK_SENTINEL}.status.lock"
    )
    with _named_status_lock(lock_path, timeout=timeout) as held_path:
        yield held_path
