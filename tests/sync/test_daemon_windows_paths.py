"""Windows-native path tests for sync daemon (T029).

These tests are marked ``windows_ci`` and run on ``windows-latest`` only.
On POSIX they are deselected by the marker filter — they still collect
cleanly, however, so CI configuration errors are caught early.
"""

from __future__ import annotations

import pytest


@pytest.mark.windows_ci
def test_sync_daemon_paths_under_localappdata() -> None:
    """On Windows, _sync_root() resolves under %LOCALAPPDATA%\\spec-kitty\\sync."""
    from specify_cli.sync import daemon

    sync_root = daemon._sync_root()
    assert sync_root is not None, "_sync_root() must not return None"
    s = str(sync_root)
    assert "AppData" in s and "Local" in s, f"Expected path under AppData\\Local, got: {s}"
    assert "spec-kitty" in s.lower(), f"Expected 'spec-kitty' in path, got: {s}"
    assert "sync" in s.lower(), f"Expected 'sync' in path, got: {s}"


@pytest.mark.windows_ci
def test_daemon_root_under_localappdata() -> None:
    """On Windows, _daemon_root() resolves under %LOCALAPPDATA%\\spec-kitty\\daemon."""
    from specify_cli.sync import daemon

    daemon_root = daemon._daemon_root()
    assert daemon_root is not None, "_daemon_root() must not return None"
    s = str(daemon_root)
    assert "AppData" in s and "Local" in s, f"Expected path under AppData\\Local, got: {s}"
    assert "spec-kitty" in s.lower(), f"Expected 'spec-kitty' in path, got: {s}"
    assert "daemon" in s.lower(), f"Expected 'daemon' in path, got: {s}"


@pytest.mark.windows_ci
def test_sync_root_returns_path_object() -> None:
    """_sync_root() returns a pathlib.Path, not a str."""
    from pathlib import Path

    from specify_cli.sync import daemon

    result = daemon._sync_root()
    assert isinstance(result, Path), f"Expected Path, got {type(result)}"


@pytest.mark.windows_ci
def test_daemon_state_file_under_daemon_root() -> None:
    """DAEMON_STATE_FILE resolves under _daemon_root() on Windows."""
    from specify_cli.sync import daemon

    daemon_root = daemon._daemon_root()
    state_file = daemon.DAEMON_STATE_FILE
    # The state file parent must be (or be under) the daemon root
    assert str(state_file).startswith(str(daemon_root)), f"DAEMON_STATE_FILE {state_file} not under daemon root {daemon_root}"
