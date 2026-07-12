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

from specify_cli.core.process_liveness import is_process_alive

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


def test_recycled_pid_generic_exception_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """A recycled PID or any other unexpected psutil error -> False, never raises.

    Simulates the class of surprises a recycled PID can produce (e.g. an
    internal psutil ``ZombieProcess`` or platform-specific ``OSError``) that
    are not ``NoSuchProcess``/``AccessDenied`` — the bare ``except Exception``
    fallback must still hold the conservative "not provably alive" default.
    """

    def _raise_unexpected(pid: int) -> None:
        raise OSError("simulated recycled-pid surprise")

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
