"""Windows-native path tests for tracker credentials (T028).

These tests are marked ``windows_ci`` and run on ``windows-latest`` only.
On POSIX they are deselected by the marker filter — they still collect
cleanly, however, so CI configuration errors are caught early.
"""
from __future__ import annotations

import pytest


@pytest.mark.windows_ci
def test_tracker_credentials_path_under_localappdata() -> None:
    """On Windows, _tracker_root() resolves under %LOCALAPPDATA%\\spec-kitty\\tracker."""
    from specify_cli.tracker import credentials

    path = credentials._tracker_root()
    s = str(path)
    # Must be under AppData\Local
    assert "AppData" in s and "Local" in s, (
        f"Expected path under AppData\\Local, got: {s}"
    )
    # Must contain the app name
    assert "spec-kitty" in s.lower(), (
        f"Expected 'spec-kitty' in path, got: {s}"
    )
    # Must be the tracker subdirectory
    assert "tracker" in s.lower(), (
        f"Expected 'tracker' in path, got: {s}"
    )


@pytest.mark.windows_ci
def test_tracker_root_returns_path_object() -> None:
    """_tracker_root() returns a pathlib.Path, not a str."""
    from pathlib import Path

    from specify_cli.tracker import credentials

    result = credentials._tracker_root()
    assert isinstance(result, Path), f"Expected Path, got {type(result)}"


@pytest.mark.windows_ci
def test_tracker_credentials_path_is_absolute() -> None:
    """The credentials path resolved under _tracker_root() is absolute."""
    from specify_cli.tracker import credentials

    root = credentials._tracker_root()
    assert root.is_absolute(), f"Expected absolute path, got: {root}"
