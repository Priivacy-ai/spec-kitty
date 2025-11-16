#!/usr/bin/env python3
"""Unit tests for guards module."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import Mock
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from specify_cli.guards import (  # noqa: E402
    GuardValidationError,
    WorktreeValidationResult,
    validate_git_clean,
    validate_worktree_location,
)


@pytest.fixture
def fake_project_root(tmp_path: Path) -> Path:
    """Return a fake project root for validation."""
    return tmp_path


def _make_completed_process(stdout: str = "", returncode: int = 0) -> Mock:
    """Helper to create subprocess.CompletedProcess-like objects."""
    proc = Mock()
    proc.stdout = stdout
    proc.returncode = returncode
    return proc


def test_validate_worktree_on_feature_branch(monkeypatch: pytest.MonkeyPatch, fake_project_root: Path) -> None:
    """validate_worktree_location should pass on feature branches."""

    def mock_run(cmd: Any, **kwargs: Any) -> Mock:
        assert cmd == ["git", "branch", "--show-current"]
        assert kwargs["cwd"] == fake_project_root
        return _make_completed_process(stdout="001-test-feature\n")

    monkeypatch.setattr("specify_cli.guards.subprocess.run", mock_run)

    result = validate_worktree_location(project_root=fake_project_root)

    assert isinstance(result, WorktreeValidationResult)
    assert result.is_valid is True
    assert result.is_feature_branch is True
    assert result.worktree_path == fake_project_root


def test_validate_worktree_on_main_branch(monkeypatch: pytest.MonkeyPatch, fake_project_root: Path) -> None:
    """validate_worktree_location should fail when on main."""

    def mock_run(cmd: Any, **kwargs: Any) -> Mock:
        return _make_completed_process(stdout="main\n")

    monkeypatch.setattr("specify_cli.guards.subprocess.run", mock_run)

    result = validate_worktree_location(project_root=fake_project_root)

    assert result.is_valid is False
    assert result.is_main_branch is True
    assert "main" in result.format_error()


def test_validate_git_clean_with_changes(monkeypatch: pytest.MonkeyPatch, fake_project_root: Path) -> None:
    """validate_git_clean should fail when git status shows changes."""

    def mock_run(cmd: Any, **kwargs: Any) -> Mock:
        assert cmd == ["git", "status", "--porcelain"]
        return _make_completed_process(stdout=" M src/file.py\n?? new.py\n")

    monkeypatch.setattr("specify_cli.guards.subprocess.run", mock_run)

    result = validate_git_clean(project_root=fake_project_root)

    assert result.is_valid is False
    assert result.errors


def test_validate_git_clean_without_changes(monkeypatch: pytest.MonkeyPatch, fake_project_root: Path) -> None:
    """validate_git_clean should pass when git status is clean."""

    def mock_run(cmd: Any, **kwargs: Any) -> Mock:
        return _make_completed_process(stdout="")

    monkeypatch.setattr("specify_cli.guards.subprocess.run", mock_run)

    result = validate_git_clean(project_root=fake_project_root)

    assert result.errors == []


def test_worktree_is_valid_without_branch() -> None:
    """WorktreeValidationResult is valid when no branch and no errors."""
    result = WorktreeValidationResult(
        current_branch="",
        is_feature_branch=False,
        is_main_branch=False,
        worktree_path=None,
        errors=[],
    )
    assert result.is_valid is True
    assert result.format_error() == ""


def test_validate_worktree_handles_non_git_repo(monkeypatch: pytest.MonkeyPatch, fake_project_root: Path) -> None:
    """validate_worktree_location should return error when git command fails."""

    def mock_run(cmd: Any, **kwargs: Any) -> Mock:
        return _make_completed_process(stdout="", returncode=1)

    monkeypatch.setattr("specify_cli.guards.subprocess.run", mock_run)

    result = validate_worktree_location(project_root=fake_project_root)

    assert "Not a git repository" in result.errors[0]


def test_validate_worktree_handles_missing_branch(monkeypatch: pytest.MonkeyPatch, fake_project_root: Path) -> None:
    """validate_worktree_location should error when branch cannot be determined."""

    def mock_run(cmd: Any, **kwargs: Any) -> Mock:
        return _make_completed_process(stdout="\n")

    monkeypatch.setattr("specify_cli.guards.subprocess.run", mock_run)

    result = validate_worktree_location(project_root=fake_project_root)

    assert "Unable to determine" in result.errors[0]


def test_validate_worktree_handles_unexpected_branch(monkeypatch: pytest.MonkeyPatch, fake_project_root: Path) -> None:
    """validate_worktree_location should error when branch format invalid."""

    def mock_run(cmd: Any, **kwargs: Any) -> Mock:
        return _make_completed_process(stdout="feature/foo\n")

    monkeypatch.setattr("specify_cli.guards.subprocess.run", mock_run)

    result = validate_worktree_location(project_root=fake_project_root)

    assert "Unexpected branch" in result.errors[0]


def test_validate_worktree_missing_git_binary(monkeypatch: pytest.MonkeyPatch, fake_project_root: Path) -> None:
    """validate_worktree_location should raise when git binary missing."""

    def mock_run(cmd: Any, **kwargs: Any) -> Mock:
        raise FileNotFoundError("git not found")

    monkeypatch.setattr("specify_cli.guards.subprocess.run", mock_run)

    with pytest.raises(GuardValidationError):
        validate_worktree_location(project_root=fake_project_root)


def test_validate_git_clean_handles_git_error(monkeypatch: pytest.MonkeyPatch, fake_project_root: Path) -> None:
    """validate_git_clean should return error when git status fails."""

    def mock_run(cmd: Any, **kwargs: Any) -> Mock:
        return _make_completed_process(stdout="", returncode=1)

    monkeypatch.setattr("specify_cli.guards.subprocess.run", mock_run)

    result = validate_git_clean(project_root=fake_project_root)

    assert "Unable to read git status." in result.errors


def test_validate_git_clean_missing_git_binary(monkeypatch: pytest.MonkeyPatch, fake_project_root: Path) -> None:
    """validate_git_clean should raise when git binary missing."""

    def mock_run(cmd: Any, **kwargs: Any) -> Mock:
        raise FileNotFoundError("git not found")

    monkeypatch.setattr("specify_cli.guards.subprocess.run", mock_run)

    with pytest.raises(GuardValidationError):
        validate_git_clean(project_root=fake_project_root)
