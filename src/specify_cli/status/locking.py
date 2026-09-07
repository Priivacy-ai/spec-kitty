"""Per-mission status locking for shared planning artifacts.

Serializes access to mission-level status artifacts that are written on the
planning checkout (`status.events.jsonl`, `status.json`, and `tasks.md`).
Parallel agents may run from separate worktrees, but they still converge on
the same planning repo paths, so these writes need an inter-process lock.

Lock rules (fsm-write-path-integrity-01M1TZV6 WP01, FR-003; the full
hierarchy is in that mission's ``design-notes/WP01-lock-rules.md``):

* (a)/(b) -- outage-shaped takes are bounded: every acquisition reachable
  from the verdict-save queue scope and the merge-path retrospective take
  passes a finite ``timeout`` (:data:`BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS`
  is the shared bound) and surfaces a :class:`FeatureStatusLockTimeoutError`
  that names the lock file and, when recorded, the holder.
* (c) -- one lock key: :func:`feature_status_lock_path` is keyed on the
  mission directory name (``feature_dir.name``), never on a mission slug
  (FR-004 / C-003). Two missions with colliding slugs get distinct lock files;
  a bare legacy slug directory's writers share the file its pipeline writers
  use.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator
from typing import Any

from filelock import FileLock

from kernel.clock import now_utc_iso
from kernel.git_topology import GitTopologyError, git_common_dir
from specify_cli.core.checkout_file_lock import LOCK_DIRECTORY, acquire_or_raise
from specify_cli.core.constants import KITTIFY_DIR

logger = logging.getLogger(__name__)

_thread_state = threading.local()

#: Finite bound (seconds) for the outage-shaped L1 takes (NFR-003 /
#: FR-003 a+b): the verdict-save-queue scope and the merge-path retrospective
#: take. Aligned with ``review.verdict_commit_queue.
#: DEFAULT_VERDICT_SAVE_TIMEOUT_SECONDS`` (pinned by a test, not imported --
#: ``review`` depends on ``status``, not the reverse). A status commit that
#: holds L1 (``BookkeepingTransaction``, the standing L1-across-git case on the
#: risk register, R9) completes well inside this bound; a slower holder is an
#: outage the caller must surface, not wait out indefinitely. The lock's own
#: default stays ``-1`` (unbounded) -- a finite *default* is research Q2's
#: follow-up.
BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS: float = 10.0

_HOLDER_SUFFIX = ".holder"


class FeatureStatusLockTimeoutError(RuntimeError):
    """Raised when the mission status lock cannot be acquired within budget.

    Structured (NFR-003): ``lock_path`` names the contended lock file,
    ``timeout`` the budget that expired, and ``holder`` the recorded holder
    (``pid`` / ``thread`` / ``acquired_at``) when the holder's sidecar was
    readable, else ``None``. The message renders all three.
    """

    def __init__(
        self,
        message: str,
        *,
        lock_path: Path | None = None,
        timeout: float | None = None,
        holder: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.lock_path = lock_path
        self.timeout = timeout
        self.holder = holder


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
    (worktree indirection collapsed the same way for both).

    When the probe cannot resolve a common dir (``repo_root`` is not a git
    repository, or git could not be invoked) locking degrades to a
    still-functional per-directory lock instead of raising -- this function's
    historical contract. The degrade location depends on whether a ``.git``
    directory already exists:

    * it does (a real checkout whose probe failed transiently): keep the
      historical ``<repo_root>/.git`` so the lock stays where every other
      process of that checkout expects it;
    * it does not (a genuinely non-git tree): use ``<repo_root>/.kittify``.
      Minting ``<repo_root>/.git/`` here used to turn the tree into a bogus
      repo root for every later ``resolve_canonical_root`` walk (the
      "fake repo root" trap ``tests/review/test_artifacts.py`` documents),
      which is a real side effect for any non-git consumer and a fixture
      hazard for every test that builds bare mission trees.
    """
    try:
        return git_common_dir(repo_root)
    except GitTopologyError:
        dot_git = repo_root / ".git"
        if dot_git.is_dir():
            return dot_git
        return Path(repo_root / KITTIFY_DIR)


def feature_status_lock_path(repo_root: Path, lock_key: str) -> Path:
    """Return the per-mission lock file path under the git common dir.

    ``lock_key`` MUST be the mission directory name (``feature_dir.name``;
    for a ``BookkeepingTransaction`` the ``<slug>-<mid8>`` dir name it
    composes) -- never a bare mission slug (FR-004 / C-003). Keying on the
    slug over-serialized two missions with colliding slugs and, worse, let a
    bare legacy slug directory's writers lock on a file none of its ordinary
    writers used (serializing against nobody).
    """
    common_dir = _git_common_dir(repo_root)
    return Path(common_dir / LOCK_DIRECTORY / f"{lock_key}.status.lock")


#: Lock-path key for the project-level canonical event log
#: (``<repo_root>/.kittify/canonical-events.jsonl``). ``ProjectInitialized``
#: has no mission directory to key a lock file on (F2-T1 / F2.md section
#: 3.3, section 6.3) so this fixed sentinel stands in for one. Never written
#: into any log row -- lock-path key only.
_PROJECT_LOCK_SENTINEL = "__project__"


def _holder_path(lock_path: Path) -> Path:
    """Sidecar recording the current holder of *lock_path*.

    A sidecar rather than the lock file's own contents: ``filelock`` opens the
    lock file with ``O_TRUNC`` on every acquire *attempt*, so a waiting
    contender would wipe anything the holder wrote there.
    """
    return lock_path.with_name(lock_path.name + _HOLDER_SUFFIX)


def _record_holder(lock_path: Path) -> None:
    """Best-effort: write who holds *lock_path* so a timeout can name them."""
    payload = {
        "pid": os.getpid(),
        "thread": threading.current_thread().name,
        "acquired_at": now_utc_iso(),
    }
    try:
        _holder_path(lock_path).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    except OSError as exc:
        logger.debug("could not record holder for %s: %s", lock_path, exc)


def _clear_holder(lock_path: Path) -> None:
    """Best-effort: remove the holder sidecar on release."""
    try:
        _holder_path(lock_path).unlink(missing_ok=True)
    except OSError as exc:
        logger.debug("could not clear holder for %s: %s", lock_path, exc)


def _read_holder(lock_path: Path) -> dict[str, Any] | None:
    """Best-effort: return the recorded holder of *lock_path*, or ``None``."""
    try:
        raw = _holder_path(lock_path).read_text(encoding="utf-8")
        parsed = json.loads(raw)
    except (OSError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _describe_holder(holder: dict[str, Any] | None) -> str:
    if holder is None:
        return "holder unknown (no holder record)"
    return (
        f"held by pid {holder.get('pid', '?')} "
        f"(thread {holder.get('thread', '?')}) since {holder.get('acquired_at', '?')}"
    )


def _build_timeout_error(lock_path: Path, timeout: float) -> FeatureStatusLockTimeoutError:
    holder = _read_holder(lock_path)
    return FeatureStatusLockTimeoutError(
        f"Timed out acquiring status lock {lock_path} after {timeout}s: {_describe_holder(holder)}",
        lock_path=lock_path,
        timeout=timeout,
        holder=holder,
    )


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
        build_timeout_error=lambda: _build_timeout_error(lock_path, timeout),
    )
    _record_holder(lock_path)

    held_locks[lock_key] = (lock, 1)
    try:
        yield lock_path
    finally:
        del held_locks[lock_key]
        _clear_holder(lock_path)
        lock.release()


@contextmanager
def feature_status_lock(
    repo_root: Path,
    lock_key: str,
    *,
    timeout: float = -1,
) -> Iterator[Path]:
    """Acquire the per-mission status lock.

    ``lock_key`` is the mission directory name (see
    :func:`feature_status_lock_path`). Uses the git common dir so main
    checkouts and worktrees coordinate on the same lock file. Locking is
    re-entrant within a single thread so callers can safely wrap a larger
    transaction around helpers that also acquire the lock. ``timeout`` is in
    seconds; ``-1`` waits indefinitely, a finite value raises
    :class:`FeatureStatusLockTimeoutError` (naming the lock file and the
    recorded holder) once it expires.
    """
    lock_path = feature_status_lock_path(repo_root, lock_key)
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
    :data:`_PROJECT_LOCK_SENTINEL` instead of a mission directory name (that
    log has no mission to key on). Re-entrant per thread via the same shared
    bookkeeping. Serializes every writer of the project-level canonical event
    log, independently of any mission-level lock (F2-T1, F2.md section 3.3).
    """
    lock_path = (
        _git_common_dir(repo_root) / LOCK_DIRECTORY / f"{_PROJECT_LOCK_SENTINEL}.status.lock"
    )
    with _named_status_lock(lock_path, timeout=timeout) as held_path:
        yield held_path
