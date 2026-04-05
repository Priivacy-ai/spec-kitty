"""Tests for mission detection.

Auto-detection was removed in the big-bang refactor (2026-03).
_detect_current_feature now always returns None; callers must pass --feature explicitly.
"""

import pytest
from specify_cli.cli.commands.mission import _detect_current_feature

pytestmark = pytest.mark.fast


def test_detect_current_feature_always_returns_none_no_auto_detection(tmp_path, monkeypatch):
    """_detect_current_feature returns None regardless of directory (auto-detection removed)."""
    # Even when inside a kitty-specs feature directory, returns None
    feature_dir = tmp_path / "kitty-specs" / "001-research"
    feature_dir.mkdir(parents=True)
    monkeypatch.chdir(feature_dir)

    result = _detect_current_feature(tmp_path)
    assert result is None, "Auto-detection removed: must use --feature explicitly"


def test_detect_current_feature_returns_none_from_worktree(tmp_path, monkeypatch):
    """_detect_current_feature returns None even from worktree (auto-detection removed)."""
    worktree_dir = tmp_path / ".worktrees" / "001-research-lane-a"
    worktree_dir.mkdir(parents=True)
    monkeypatch.chdir(worktree_dir)

    result = _detect_current_feature(tmp_path)
    assert result is None, "Auto-detection removed: must use --feature explicitly"


def test_detect_current_feature_returns_none_from_project_root(tmp_path, monkeypatch):
    """_detect_current_feature returns None from project root."""
    monkeypatch.chdir(tmp_path)

    result = _detect_current_feature(tmp_path)
    assert result is None


def test_detect_current_feature_returns_none_from_unusual_path(tmp_path, monkeypatch):
    """_detect_current_feature returns None and does not crash on unusual paths."""
    unusual_dir = tmp_path / "some" / "unusual" / "path"
    unusual_dir.mkdir(parents=True)
    monkeypatch.chdir(unusual_dir)

    result = _detect_current_feature(tmp_path)
    assert result is None
