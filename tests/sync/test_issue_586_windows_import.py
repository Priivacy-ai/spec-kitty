"""Regression test for issue #586: `spec-kitty --help` failed on Windows with
``ModuleNotFoundError: No module named 'fcntl'``.

The root cause was ``src/specify_cli/sync/daemon.py`` importing ``fcntl``
unconditionally at module top.  ``fcntl`` is a Unix-only stdlib module, so the
CLI could not even start on Windows — the daemon module is imported eagerly
via the dashboard command registration chain.

The fix branches on ``sys.platform == "win32"`` and uses ``msvcrt.locking``
instead.

Two tests are provided:

1. ``test_daemon_module_imports_on_windows`` (fast, POSIX-compatible) —
   simulates a Windows environment on a Unix host by stubbing ``sys.modules``
   so we can confirm the daemon module imports cleanly when ``fcntl`` is absent
   and ``msvcrt`` is the available locking backend.  Retained for fast
   feedback on POSIX CI runners.

2. ``test_sync_daemon_imports_on_windows_without_fcntl`` (windows_ci) —
   native import on the real ``windows-latest`` runner.  Runs without any
   monkeypatching so failures are genuine platform failures.

Spec IDs: FR-016, FR-017, SC-004
"""

from __future__ import annotations

import importlib
import sys
import types

import pytest

pytestmark = pytest.mark.fast


def test_daemon_module_imports_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """On Windows (no ``fcntl``), ``specify_cli.sync.daemon`` must still import."""
    import specify_cli.sync.daemon as daemon_module

    # Simulate a Windows interpreter.
    monkeypatch.setattr(sys, "platform", "win32")

    # On a Unix host ``msvcrt`` doesn't exist — provide a stub so the
    # ``import msvcrt`` branch succeeds.  Calls against it aren't exercised
    # by this test; we only verify the import does not raise.
    fake_msvcrt = types.SimpleNamespace(
        locking=lambda *_args, **_kwargs: None,
        LK_NBLCK=1,
        LK_UNLCK=2,
        LK_LOCK=3,
    )
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)

    try:
        module = importlib.reload(daemon_module)
        # Sanity: the module loaded and exposes its public API.
        assert hasattr(module, "ensure_sync_daemon_running")
        assert hasattr(module, "get_sync_daemon_status")
    finally:
        # Undo Windows monkeypatches eagerly so the reload below picks up the
        # real platform.  ``monkeypatch`` teardown would do this too, but only
        # *after* this finally block runs.
        monkeypatch.undo()
        importlib.reload(daemon_module)


@pytest.mark.windows_ci
def test_sync_daemon_imports_on_windows_without_fcntl() -> None:
    """On the real Windows runner, ``specify_cli.sync.daemon`` must import cleanly.

    This is the native counterpart to ``test_daemon_module_imports_on_windows``.
    No monkeypatching — if ``fcntl`` is accidentally re-introduced as an
    unconditional import, this test will fail with a genuine
    ``ModuleNotFoundError`` on the ``windows-latest`` CI job.
    """
    import specify_cli.sync.daemon as daemon_mod

    importlib.reload(daemon_mod)
    assert hasattr(daemon_mod, "__name__")

    # Exercise the locking surface at the reference level — we care about
    # *import-time* errors, not runtime acquisition success.
    if hasattr(daemon_mod, "acquire_lock"):
        try:
            _ = daemon_mod.acquire_lock  # reference only; do not invoke
        except ModuleNotFoundError as exc:  # pragma: no cover
            pytest.fail(f"Windows sync/daemon has fcntl dependency: {exc}")

    # Confirm the public API is reachable.
    assert hasattr(daemon_mod, "ensure_sync_daemon_running"), (
        "ensure_sync_daemon_running missing from sync.daemon on Windows"
    )
    assert hasattr(daemon_mod, "get_sync_daemon_status"), (
        "get_sync_daemon_status missing from sync.daemon on Windows"
    )
