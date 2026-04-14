"""Regression test for issue #586: `spec-kitty --help` failed on Windows with
``ModuleNotFoundError: No module named 'fcntl'``.

The root cause was ``src/specify_cli/sync/daemon.py`` importing ``fcntl``
unconditionally at module top.  ``fcntl`` is a Unix-only stdlib module, so the
CLI could not even start on Windows — the daemon module is imported eagerly
via the dashboard command registration chain.

The fix branches on ``sys.platform == "win32"`` and uses ``msvcrt.locking``
instead.  This test simulates the Windows environment on a Unix host by
stubbing ``sys.modules`` so we can confirm the daemon module imports cleanly
when ``fcntl`` is absent and ``msvcrt`` is the available locking backend.
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
