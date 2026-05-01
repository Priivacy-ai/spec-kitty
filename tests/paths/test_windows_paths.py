"""Tests for RuntimeRoot and get_runtime_root() platform dispatch."""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.paths import get_runtime_root


def test_get_runtime_root_on_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    fake_localappdata = tmp_path / "LocalAppData"
    with patch(
        "specify_cli.paths.windows_paths.platformdirs.user_data_dir",
        return_value=str(fake_localappdata / "spec-kitty"),
    ):
        root = get_runtime_root()
    assert root.platform == "win32"
    assert root.base == fake_localappdata / "spec-kitty"
    assert root.auth_dir == root.base / "auth"
    assert root.tracker_dir == root.base / "tracker"
    assert root.sync_dir == root.base / "sync"
    assert root.daemon_dir == root.base / "daemon"
    assert root.cache_dir == root.base / "cache"


def test_get_runtime_root_on_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    root = get_runtime_root()
    assert root.platform == "linux"
    assert root.base == Path.home() / ".spec-kitty"


def test_get_runtime_root_on_darwin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    root = get_runtime_root()
    assert root.platform == "darwin"
    assert root.base == Path.home() / ".spec-kitty"


def test_runtime_root_is_frozen() -> None:
    root = get_runtime_root()
    assert dataclasses.is_dataclass(root)
    # Attempting mutation must raise FrozenInstanceError
    with pytest.raises(dataclasses.FrozenInstanceError):
        root.base = Path("/tmp/other")  # type: ignore[misc]
