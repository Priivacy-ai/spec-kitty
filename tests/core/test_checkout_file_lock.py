"""Focused unit coverage for the shared ``checkout_file_lock`` primitive (#3773 item 4).

``specify_cli.review.verdict_commit_queue`` and ``specify_cli.status.locking``
each build a ``filelock.FileLock`` under ``<git-common-dir>/spec-kitty-locks/``
and translate ``filelock.Timeout`` into their own typed exception. This module
is the single place that mkdir/acquire/translate sequence now lives; these
tests exercise it directly, independent of either caller's git-topology
resolution or re-entrancy bookkeeping (which stay in each caller by design --
see the module docstring).
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path
from typing import Any

import pytest
from filelock import FileLock, Timeout

from specify_cli.core.checkout_file_lock import LOCK_DIRECTORY, acquire_or_raise


class _CustomTimeoutError(RuntimeError):
    """A stand-in for a caller's own typed timeout exception."""


@pytest.mark.unit
@pytest.mark.fast
def test_lock_directory_is_the_single_named_constant() -> None:
    """The literal both callers used to hardcode now lives in exactly one place."""
    assert LOCK_DIRECTORY == "spec-kitty-locks"


@pytest.mark.unit
@pytest.mark.fast
def test_acquire_or_raise_creates_parent_directory_and_acquires(tmp_path: Path) -> None:
    """A fresh, nested lock path gets its parent directory created and locked."""
    lock_path = tmp_path / "nested" / "checkout" / "example.lock"
    lock = FileLock(str(lock_path))

    acquire_or_raise(
        lock,
        lock_path,
        timeout_seconds=1.0,
        build_timeout_error=lambda: pytest.fail("must not time out against an unheld lock"),
    )
    try:
        assert lock_path.parent.is_dir()
        assert lock.is_locked
    finally:
        lock.release()


@pytest.mark.unit
@pytest.mark.fast
def test_acquire_or_raise_raises_callers_typed_error_on_timeout(tmp_path: Path) -> None:
    """A live holder excludes a contender past its budget with the CALLER's exception type."""
    lock_path = tmp_path / LOCK_DIRECTORY / "contended.lock"
    holder = FileLock(str(lock_path))
    holder.acquire(timeout=5)
    try:
        contender = FileLock(str(lock_path))

        with pytest.raises(_CustomTimeoutError) as raised:
            acquire_or_raise(
                contender,
                lock_path,
                timeout_seconds=0.2,
                build_timeout_error=lambda: _CustomTimeoutError("busy"),
            )

        # The typed exception is chained from the underlying filelock.Timeout,
        # so a caller's own diagnostics can still inspect the real cause.
        assert isinstance(raised.value.__cause__, Timeout)
        assert not contender.is_locked
    finally:
        holder.release()


@pytest.mark.unit
@pytest.mark.fast
def test_acquire_or_raise_does_not_release_a_lock_it_never_acquired(tmp_path: Path) -> None:
    """On a failed acquire, the helper must not touch ``.release()`` at all.

    Mirrors the contract ``verdict_commit_queue``'s own test suite pins for its
    call site (``RefusingLock.release`` fails the test if invoked): a lock that
    was never successfully acquired must not be released by this primitive --
    that would be a caller bug (or, at the OS level, drop someone else's lock).
    """
    lock_path = tmp_path / LOCK_DIRECTORY / "refused.lock"

    class _RefusingLock:
        def acquire(self, *, timeout: float) -> None:
            del timeout
            raise Timeout(str(lock_path))

        def release(self) -> None:
            pytest.fail("a lock that was never acquired must not be released")

    with pytest.raises(_CustomTimeoutError):
        acquire_or_raise(
            _RefusingLock(),  # type: ignore[arg-type]  # duck-typed FileLock double
            lock_path,
            timeout_seconds=0.1,
            build_timeout_error=lambda: _CustomTimeoutError("refused"),
        )


@pytest.mark.unit
@pytest.mark.fast
def test_acquire_or_raise_is_reusable_across_two_independent_lock_files(tmp_path: Path) -> None:
    """The shared helper has no hidden global state.

    Two distinct lock paths -- as two independent callers, each with their own
    lock filename, would use -- acquire independently without interfering with
    each other.
    """
    lock_path_a = tmp_path / LOCK_DIRECTORY / "caller-a.lock"
    lock_path_b = tmp_path / LOCK_DIRECTORY / "caller-b.lock"
    lock_a = FileLock(str(lock_path_a))
    lock_b = FileLock(str(lock_path_b))

    acquire_or_raise(lock_a, lock_path_a, timeout_seconds=1.0, build_timeout_error=AssertionError)
    acquire_or_raise(lock_b, lock_path_b, timeout_seconds=1.0, build_timeout_error=AssertionError)
    try:
        assert lock_a.is_locked
        assert lock_b.is_locked
    finally:
        lock_a.release()
        lock_b.release()


def _hold_then_release_on_signal(lock_path_str: str, ready: Any, release: Any) -> None:
    """Spawn-safe worker: acquire ``lock_path_str``, signal readiness, then
    release once the parent sets ``release``.

    A real second OS process is required here (not a background thread in
    this same process): ``filelock.FileLock`` defaults to
    ``thread_local=True``, so releasing a lock from a different THREAD than
    the one that acquired it is a silent no-op (the release thread sees its
    own empty thread-local context, not the acquiring thread's held fd).
    Cross-process contention has no such gotcha -- the OS-level ``flock``
    genuinely serializes independent processes.
    """
    lock = FileLock(lock_path_str)
    lock.acquire(timeout=5)
    ready.set()
    release.wait(10)
    lock.release()


@pytest.mark.integration
def test_acquire_or_raise_bounded_wait_unblocks_promptly_after_release(tmp_path: Path) -> None:
    """A contender queued behind a live holder acquires as soon as it releases.

    Proves this is a real bounded WAIT (not an immediate refusal): the
    contender's ``acquire_or_raise`` call blocks until the release, well
    inside its own timeout budget. Uses a real spawned process as the holder
    (see ``_hold_then_release_on_signal``'s docstring for why a thread will
    not do).
    """
    lock_path = tmp_path / LOCK_DIRECTORY / "handoff.lock"
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    holder = context.Process(target=_hold_then_release_on_signal, args=(str(lock_path), ready, release))
    holder.start()
    try:
        assert ready.wait(10), "spawned holder never acquired the lock"

        contender = FileLock(str(lock_path))
        release.set()
        acquire_or_raise(
            contender,
            lock_path,
            timeout_seconds=5.0,
            build_timeout_error=lambda: pytest.fail("must acquire once the holder releases"),
        )
        try:
            assert contender.is_locked
        finally:
            contender.release()
        holder.join(timeout=10)
        assert not holder.is_alive()
        assert holder.exitcode == 0
    finally:
        release.set()
        if holder.is_alive():
            holder.terminate()
            holder.join(timeout=10)
