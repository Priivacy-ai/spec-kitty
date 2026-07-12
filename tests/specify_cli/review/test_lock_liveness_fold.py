"""Characterization tests for WP05 — review-lock liveness fold (#2568).

Pins the branch-equivalence of ``ReviewLock.is_stale()`` after it was folded
onto the canonical ``core/process_liveness.is_process_alive`` seam, replacing
the improvised ``os.kill(pid, 0)`` liveness probe (C-003).

Verified equivalence (branch-by-branch, ``is_stale() == not is_process_alive(pid)``):

- live PID                              -> is_process_alive True  -> is_stale False
- dead PID (psutil.NoSuchProcess)       -> is_process_alive False -> is_stale True
- permission-denied (psutil.AccessDenied) -> is_process_alive True  -> is_stale False

FR-010 / NFR-001: the review lock's staleness verdict must be branch-equivalent
to the prior ``os.kill(pid, 0)`` implementation for live / dead / permission-denied
inputs.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from specify_cli.review.lock import ReviewLock

pytestmark = pytest.mark.fast


def _make_lock(pid: int) -> ReviewLock:
    return ReviewLock(
        worktree_path="/nonexistent/review-lock-wt",  # sentinel; is_stale never reads it
        wp_id="WP01",
        agent="claude",
        started_at="2026-07-12T12:00:00+00:00",
        pid=pid,
    )


def test_is_stale_delegates_to_canonical_is_process_alive() -> None:
    """is_stale() consumes the canonical seam, not an improvised probe (C-003)."""
    lock = _make_lock(pid=4242)

    with patch("specify_cli.review.lock.is_process_alive") as mock_alive:
        mock_alive.return_value = True
        lock.is_stale()

    mock_alive.assert_called_once_with(4242)


def test_is_stale_live_pid_is_not_stale() -> None:
    """Live PID: is_process_alive True -> is_stale() False (branch-equivalent)."""
    lock = _make_lock(pid=4242)

    with patch("specify_cli.review.lock.is_process_alive", return_value=True):
        assert lock.is_stale() is False


def test_is_stale_dead_pid_is_stale() -> None:
    """Dead PID (NoSuchProcess): is_process_alive False -> is_stale() True.

    Branch-equivalent to the prior ``ProcessLookupError`` -> True mapping.
    """
    lock = _make_lock(pid=999999999)

    with patch("specify_cli.review.lock.is_process_alive", return_value=False):
        assert lock.is_stale() is True


def test_is_stale_permission_denied_is_not_stale() -> None:
    """Permission-denied (AccessDenied): is_process_alive True -> is_stale() False.

    Branch-equivalent to the prior conservative ``PermissionError`` -> False
    mapping (process exists but belongs to another user — cannot prove dead).
    """
    lock = _make_lock(pid=1234)

    with patch("specify_cli.review.lock.is_process_alive", return_value=True):
        assert lock.is_stale() is False
