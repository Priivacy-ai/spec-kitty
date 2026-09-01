"""Shared bounded-wait ``filelock.FileLock`` primitive (#3773 item 4).

``specify_cli.review.verdict_commit_queue`` (the checkout-wide verdict-save
queue) and ``specify_cli.status.locking`` (the per-feature status lock) each
build the identical low-level primitive: a ``filelock.FileLock`` rooted under
``<git-common-dir>/spec-kitty-locks/``, whose ``filelock.Timeout`` is
translated into a caller-specific typed exception. Before this module, both
call sites hardcoded the ``"spec-kitty-locks"`` directory name and duplicated
the "create the parent directory, attempt a bounded acquire, translate the
untyped ``Timeout``" sequence.

This module is the single place those two behaviors live. It does **not**
merge the two locks: each caller still constructs its *own* ``FileLock`` for
its *own* lock path, keeps its *own* re-entrancy bookkeeping (the queue's
context-local "already held" refusal vs. the status lock's per-thread
reentrant depth counter), and raises its *own* typed timeout exception. Only
the plumbing around that per-lock ``FileLock`` instance -- the directory
constant and the acquire/translate step -- is shared.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from filelock import FileLock, Timeout

LOCK_DIRECTORY = "spec-kitty-locks"
"""Directory name, under a checkout's git common dir, holding Spec Kitty's file locks.

The single named constant for a literal that used to be hardcoded separately
in ``verdict_commit_queue.py`` and ``status/locking.py`` (Sonar S1192 across
the module boundary).
"""

__all__ = ["LOCK_DIRECTORY", "acquire_or_raise"]


def acquire_or_raise(
    lock: FileLock,
    lock_path: Path,
    *,
    timeout_seconds: float,
    build_timeout_error: Callable[[], Exception],
) -> None:
    """Create ``lock_path``'s parent directory and acquire ``lock`` within budget.

    ``lock`` must already be constructed by the caller (with the caller's own
    lock-file path and any constructor-level timeout it wants) -- this helper
    only owns the shared mkdir-then-acquire-then-translate sequence, not lock
    construction or release. Callers remain responsible for releasing a lock
    they successfully acquired (typically via a ``try/finally`` around the
    protected section) and for any re-entrancy bookkeeping around the call.

    Args:
        lock: An unacquired ``filelock.FileLock`` for ``lock_path``.
        lock_path: The lock file path ``lock`` guards, used only to ensure its
            parent directory exists before the acquire attempt.
        timeout_seconds: Forwarded verbatim to ``lock.acquire(timeout=...)``.
            A negative value blocks indefinitely (``filelock`` semantics).
        build_timeout_error: Builds the caller's own typed exception when the
            acquire attempt exceeds ``timeout_seconds``. Called with no
            arguments; the caller's closure already has whatever context
            (lock path, mission slug, timeout) its exception needs.

    Raises:
        Exception: Whatever ``build_timeout_error()`` returns, chained from
            the underlying ``filelock.Timeout`` via ``raise ... from exc``.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock.acquire(timeout=timeout_seconds)
    except Timeout as exc:
        raise build_timeout_error() from exc
