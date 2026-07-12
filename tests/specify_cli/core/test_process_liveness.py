"""NFR-004 matrix for ``core.process_liveness.is_process_alive``.

``is_process_alive`` is the single canonical liveness check (C-002), promoted
verbatim from ``sync/daemon._is_process_alive``. NFR-004 requires it to be
conservative and to NEVER raise for absent, unparseable-elsewhere, dead, or
recycled PIDs — every case below asserts both the return value AND the
absence of a propagated exception.
"""

from __future__ import annotations

import psutil
import pytest

from specify_cli.core.process_liveness import (
    capture_creation_time_baseline,
    is_claiming_process_alive,
    is_process_alive,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


class _FakeAliveProcess:
    """Minimal stand-in for ``psutil.Process`` reporting a running process."""

    def is_running(self) -> bool:
        return True


class _FakeDeadProcess:
    """Minimal stand-in for ``psutil.Process`` reporting a non-running process."""

    def is_running(self) -> bool:
        return False


def test_alive_pid_returns_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """A process that reports itself as running -> True."""
    monkeypatch.setattr(
        "specify_cli.core.process_liveness.psutil.Process",
        lambda pid: _FakeAliveProcess(),
    )
    try:
        result = is_process_alive(4242)
    except Exception as exc:  # pragma: no cover - failure path
        pytest.fail(f"is_process_alive raised unexpectedly: {exc!r}")
    assert result is True


def test_absent_pid_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """A nonexistent PID (psutil.NoSuchProcess) -> False, never raises."""

    def _raise_no_such_process(pid: int) -> None:
        raise psutil.NoSuchProcess(pid)

    monkeypatch.setattr(
        "specify_cli.core.process_liveness.psutil.Process",
        _raise_no_such_process,
    )
    try:
        result = is_process_alive(999999)
    except Exception as exc:  # pragma: no cover - failure path
        pytest.fail(f"is_process_alive raised unexpectedly: {exc!r}")
    assert result is False


def test_dead_pid_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """A PID that resolves but reports not-running -> False."""
    monkeypatch.setattr(
        "specify_cli.core.process_liveness.psutil.Process",
        lambda pid: _FakeDeadProcess(),
    )
    try:
        result = is_process_alive(4243)
    except Exception as exc:  # pragma: no cover - failure path
        pytest.fail(f"is_process_alive raised unexpectedly: {exc!r}")
    assert result is False


def test_access_denied_returns_true_conservative(monkeypatch: pytest.MonkeyPatch) -> None:
    """AccessDenied (e.g. a different user's process) -> True: cannot prove death."""

    def _raise_access_denied(pid: int) -> None:
        raise psutil.AccessDenied(pid)

    monkeypatch.setattr(
        "specify_cli.core.process_liveness.psutil.Process",
        _raise_access_denied,
    )
    try:
        result = is_process_alive(1)
    except Exception as exc:  # pragma: no cover - failure path
        pytest.fail(f"is_process_alive raised unexpectedly: {exc!r}")
    assert result is True


def test_unexpected_psutil_error_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unexpected psutil/OS error (not NoSuchProcess/AccessDenied) -> False, never raises.

    This exercises the bare ``except Exception`` fallback branch with a
    platform-specific ``OSError`` that is neither ``NoSuchProcess`` nor
    ``AccessDenied``. NOTE: this does NOT exercise PID-reuse detection —
    ``is_process_alive`` has no identity check and cannot itself distinguish
    a recycled PID from the original claiming process (that is what
    :func:`~specify_cli.core.process_liveness.is_claiming_process_alive`
    is for, see ``test_claiming_process_alive_*`` below). This test only
    pins the conservative "not provably alive" default for a generic
    unexpected error.
    """

    def _raise_unexpected(pid: int) -> None:
        raise OSError("simulated unexpected psutil error")

    monkeypatch.setattr(
        "specify_cli.core.process_liveness.psutil.Process",
        _raise_unexpected,
    )
    try:
        result = is_process_alive(65535)
    except Exception as exc:  # pragma: no cover - failure path
        pytest.fail(f"is_process_alive raised unexpectedly: {exc!r}")
    assert result is False


def test_never_raises_for_negative_pid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Even a nonsensical (negative) pid value must never propagate an exception.

    ``psutil.Process`` itself may raise ``ValueError`` for negative pids on
    some platforms — this must still land in the bare ``except Exception``
    branch and return ``False``, not propagate.
    """
    try:
        result = is_process_alive(-1)
    except Exception as exc:  # pragma: no cover - failure path
        pytest.fail(f"is_process_alive raised unexpectedly: {exc!r}")
    assert result is False


def test_real_spawn_then_kill_liveness() -> None:
    """Real process spawn->kill: is_process_alive tracks the actual OS lifecycle.

    FR-006/T015: a genuine (non-monkeypatched) subprocess is confirmed alive
    while running and confirmed dead after it exits -- the exited-PID path
    exercised against the real ``psutil``/OS liveness stack, not a fake.
    """
    import subprocess
    import sys

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    try:
        assert is_process_alive(proc.pid) is True
    finally:
        proc.terminate()
        proc.wait(timeout=5.0)

    assert is_process_alive(proc.pid) is False


def test_claiming_process_alive_baseline_absent_preserves_live_pid_trust(monkeypatch: pytest.MonkeyPatch) -> None:
    """D3a: an absent baseline (legacy claim) preserves is_process_alive(pid) exactly.

    No identity compare happens -- a live PID with no baseline is trusted,
    matching pre-fix behavior so no claim written before this WP regresses.
    """
    monkeypatch.setattr(
        "specify_cli.core.process_liveness.psutil.Process",
        lambda pid: _FakeAliveProcess(),
    )
    try:
        result = is_claiming_process_alive(4242, None)
    except Exception as exc:  # pragma: no cover - failure path
        pytest.fail(f"is_claiming_process_alive raised unexpectedly: {exc!r}")
    assert result is True


class _FakeProcessWithCreateTime:
    """Stand-in for ``psutil.Process`` that reports a fixed ``create_time()``."""

    def __init__(self, create_time: float) -> None:
        self._create_time = create_time

    def create_time(self) -> float:
        return self._create_time


def test_claiming_process_alive_baseline_mismatch_returns_not_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    """T014: a present-but-mismatched baseline (simulated PID reuse) -> not alive.

    This is the deterministic reuse seam (a simulated mismatch, not an OS
    PID-recycle): the live process at ``pid`` has a DIFFERENT creation time
    than the persisted baseline, so the claim is treated as NOT alive --
    callers (stale_detection.check_wp_staleness) then fall through to the
    commit-timestamp heuristic rather than hard-flagging stale.
    """
    monkeypatch.setattr(
        "specify_cli.core.process_liveness.psutil.Process",
        lambda pid: _FakeProcessWithCreateTime(1700000000.0),
    )
    try:
        result = is_claiming_process_alive(4242, "1699999999.123456")
    except Exception as exc:  # pragma: no cover - failure path
        pytest.fail(f"is_claiming_process_alive raised unexpectedly: {exc!r}")
    assert result is False


def test_claiming_process_alive_baseline_matches_returns_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    """T014 (positive branch): a present baseline that MATCHES -> alive.

    Coverage note: the match branch is new code introduced by this WP and
    must be exercised directly, not only the mismatch branch.
    """
    monkeypatch.setattr(
        "specify_cli.core.process_liveness.psutil.Process",
        lambda pid: _FakeProcessWithCreateTime(1700000000.0),
    )
    try:
        result = is_claiming_process_alive(4242, "1700000000.0")
    except Exception as exc:  # pragma: no cover - failure path
        pytest.fail(f"is_claiming_process_alive raised unexpectedly: {exc!r}")
    assert result is True


def test_claiming_process_alive_never_raises_on_baseline_compare_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """NFR-004: an unexpected error while comparing a present baseline -> not alive, never raises."""

    def _raise_unexpected(pid: int) -> None:
        raise OSError("simulated psutil surprise during baseline compare")

    monkeypatch.setattr(
        "specify_cli.core.process_liveness.psutil.Process",
        _raise_unexpected,
    )
    try:
        result = is_claiming_process_alive(4242, "1700000000.0")
    except Exception as exc:  # pragma: no cover - failure path
        pytest.fail(f"is_claiming_process_alive raised unexpectedly: {exc!r}")
    assert result is False


def test_capture_creation_time_baseline_returns_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """capture_creation_time_baseline returns a string form of create_time()."""
    monkeypatch.setattr(
        "specify_cli.core.process_liveness.psutil.Process",
        lambda pid: _FakeProcessWithCreateTime(1700000000.5),
    )
    assert capture_creation_time_baseline(4242) == "1700000000.5"


def test_capture_creation_time_baseline_returns_none_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """capture_creation_time_baseline is best-effort (C-007): errors -> None, never raises."""

    def _raise_no_such_process(pid: int) -> None:
        raise psutil.NoSuchProcess(pid)

    monkeypatch.setattr(
        "specify_cli.core.process_liveness.psutil.Process",
        _raise_no_such_process,
    )
    try:
        result = capture_creation_time_baseline(999999)
    except Exception as exc:  # pragma: no cover - failure path
        pytest.fail(f"capture_creation_time_baseline raised unexpectedly: {exc!r}")
    assert result is None


def test_module_imports_only_psutil_and_stdlib() -> None:
    """Guard the layering invariant (C-002): no ``specify_cli`` imports here.

    ``core/process_liveness.py`` must stay import-cycle-free so ``sync/daemon.py``
    (and future ``core``/``lanes`` consumers) can depend on it without dragging
    in the daemon's socket/HTTPServer machinery.
    """
    import ast
    import inspect

    from specify_cli.core import process_liveness

    source = inspect.getsource(process_liveness)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("specify_cli"), (
                f"process_liveness.py must not import specify_cli.* (found: {node.module})"
            )
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("specify_cli"), (
                    f"process_liveness.py must not import specify_cli.* (found: {alias.name})"
                )
