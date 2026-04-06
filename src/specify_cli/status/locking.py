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
from typing import Iterator

from filelock import FileLock, Timeout

_thread_state = threading.local()


class FeatureStatusLockTimeout(RuntimeError):
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
        raise FeatureStatusLockTimeout(
            f"Timed out acquiring feature status lock for {mission_slug}: {lock_path}"
        ) from exc

    held_locks[lock_key] = (lock, 1)
    try:
        yield lock_path
    finally:
        del held_locks[lock_key]
        lock.release()
