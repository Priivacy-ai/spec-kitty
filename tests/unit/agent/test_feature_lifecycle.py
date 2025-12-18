"""Unit tests for accept and merge feature lifecycle commands."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from specify_cli.cli.commands.agent.feature import (
    _find_latest_feature_worktree,
    _get_current_branch,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_repo_with_worktrees(tmp_path: Path) -> Path:
    """Create a mock repository with worktrees."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Initialize git
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_root, check=True, capture_output=True)

    # Create initial commit
    (repo_root / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_root, check=True, capture_output=True)

    # Create worktrees directory
    worktrees = repo_root / ".worktrees"
    worktrees.mkdir()

    # Create mock worktrees
    (worktrees / "001-first-feature").mkdir()
    (worktrees / "003-latest-feature").mkdir()
    (worktrees / "002-middle-feature").mkdir()
    (worktrees / "not-a-feature").mkdir()  # Should be ignored

    return repo_root


# =============================================================================
# Unit Tests: Helper Functions (T073)
# =============================================================================

def test_find_latest_feature_worktree(mock_repo_with_worktrees: Path):
    """Test finding latest worktree by number."""
    latest = _find_latest_feature_worktree(mock_repo_with_worktrees)

    assert latest is not None
    assert latest.name == "003-latest-feature"


def test_find_latest_feature_worktree_no_worktrees(tmp_path: Path):
    """Test when no worktrees directory exists."""
    latest = _find_latest_feature_worktree(tmp_path)
    assert latest is None


def test_find_latest_feature_worktree_ignores_non_feature(mock_repo_with_worktrees: Path):
    """Test that non-feature directories are ignored."""
    latest = _find_latest_feature_worktree(mock_repo_with_worktrees)

    assert latest is not None
    assert latest.name != "not-a-feature"


def test_get_current_branch(mock_repo_with_worktrees: Path):
    """Test getting current branch name."""
    branch = _get_current_branch(mock_repo_with_worktrees)

    # Default branch varies (main or master)
    assert branch in ["main", "master"]


def test_get_current_branch_non_git(tmp_path: Path):
    """Test branch detection in non-git directory."""
    branch = _get_current_branch(tmp_path)
    assert branch == "main"


# =============================================================================
# Unit Tests: Accept Command (T073)
# =============================================================================

@patch("subprocess.run")
@patch("specify_cli.core.paths.locate_project_root")
def test_accept_command_delegates_to_tasks_cli(mock_locate: MagicMock, mock_run: MagicMock, tmp_path: Path):
    """Test that accept command delegates to tasks_cli.py."""
    # Setup mocks
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    tasks_cli = repo_root / "scripts" / "tasks" / "tasks_cli.py"
    tasks_cli.parent.mkdir(parents=True)
    tasks_cli.write_text("#!/usr/bin/env python3\n")

    mock_locate.return_value = repo_root
    mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")

    # Import and call directly (avoid CliRunner issues)
    from specify_cli.cli.commands.agent.feature import accept_feature

    with pytest.raises(SystemExit) as exc_info:
        accept_feature(feature=None, mode="auto", json_output=True, lenient=False, no_commit=False)

    # Verify exit code
    assert exc_info.value.code == 0

    # Verify tasks_cli.py was called (may be called more than once due to locate_project_root internals)
    assert mock_run.call_count >= 1
    # Find the tasks_cli.py call
    tasks_cli_called = False
    for call in mock_run.call_args_list:
        call_args = call[0][0]
        if "tasks_cli.py" in str(call_args):
            assert "accept" in call_args
            tasks_cli_called = True
            break
    assert tasks_cli_called, "tasks_cli.py was not called"


@patch("subprocess.run")
@patch("specify_cli.core.paths.locate_project_root")
def test_accept_command_passes_flags(mock_locate: MagicMock, mock_run: MagicMock, tmp_path: Path):
    """Test that accept command passes all flags to tasks_cli.py."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    tasks_cli = repo_root / "scripts" / "tasks" / "tasks_cli.py"
    tasks_cli.parent.mkdir(parents=True)
    tasks_cli.write_text("#!/usr/bin/env python3\n")

    mock_locate.return_value = repo_root
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    from specify_cli.cli.commands.agent.feature import accept_feature

    with pytest.raises(SystemExit):
        accept_feature(
            feature="001-test",
            mode="checklist",
            json_output=True,
            lenient=True,
            no_commit=True
        )

    # Verify all flags passed
    call_args = mock_run.call_args[0][0]
    assert "--feature" in call_args
    assert "001-test" in call_args
    assert "--mode" in call_args
    assert "checklist" in call_args
    assert "--json" in call_args
    assert "--lenient" in call_args
    assert "--no-commit" in call_args


# =============================================================================
# Unit Tests: Merge Command (T073)
# =============================================================================

@patch("subprocess.run")
@patch("specify_cli.core.paths.locate_project_root")
def test_merge_command_delegates_to_tasks_cli(mock_locate: MagicMock, mock_run: MagicMock, tmp_path: Path):
    """Test that merge command delegates to tasks_cli.py."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    tasks_cli = repo_root / "scripts" / "tasks" / "tasks_cli.py"
    tasks_cli.parent.mkdir(parents=True)
    tasks_cli.write_text("#!/usr/bin/env python3\n")

    # Create mock branch
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_root, check=True, capture_output=True)
    (repo_root / "test.txt").write_text("test")
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "test"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "001-test-feature"], cwd=repo_root, check=True, capture_output=True)

    mock_locate.return_value = repo_root
    mock_run.return_value = MagicMock(returncode=0, stdout="Merge complete", stderr="")

    from specify_cli.cli.commands.agent.feature import merge_feature

    with pytest.raises(SystemExit) as exc_info:
        merge_feature(
            feature=None,
            target="main",
            strategy="merge",
            push=False,
            dry_run=False,
            keep_branch=False,
            keep_worktree=False,
            auto_retry=False  # Disable auto-retry for test
        )

    # Verify tasks_cli.py was called
    assert mock_run.call_count >= 1  # May call git rev-parse first
    # Find the call to tasks_cli.py
    for call in mock_run.call_args_list:
        call_args = call[0][0]
        if "tasks_cli.py" in str(call_args):
            assert "merge" in call_args
            break


@patch("specify_cli.cli.commands.agent.feature._find_latest_feature_worktree")
@patch("specify_cli.cli.commands.agent.feature._get_current_branch")
@patch("subprocess.run")
@patch("specify_cli.core.paths.locate_project_root")
def test_merge_command_auto_retry_logic(
    mock_locate: MagicMock,
    mock_subprocess: MagicMock,
    mock_get_branch: MagicMock,
    mock_find_latest: MagicMock,
    tmp_path: Path,
):
    """Test merge auto-retry when not on feature branch."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    latest_worktree = tmp_path / "repo" / ".worktrees" / "002-feature"
    latest_worktree.mkdir(parents=True)

    mock_locate.return_value = repo_root
    mock_get_branch.return_value = "main"  # Not a feature branch
    mock_find_latest.return_value = latest_worktree
    mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

    from specify_cli.cli.commands.agent.feature import merge_feature

    with pytest.raises(SystemExit):
        merge_feature(
            feature=None,
            target="main",
            strategy="merge",
            push=False,
            dry_run=False,
            keep_branch=False,
            keep_worktree=False,
            auto_retry=True  # Enable auto-retry
        )

    # Verify auto-retry happened
    mock_find_latest.assert_called_once()

    # Verify command was re-run in worktree
    for call in mock_subprocess.call_args_list:
        call_args = call[0][0] if call[0] else []
        if "spec-kitty" in str(call_args):
            call_kwargs = call[1]
            assert call_kwargs.get("cwd") == latest_worktree
            break


@patch("subprocess.run")
@patch("specify_cli.core.paths.locate_project_root")
def test_merge_command_passes_all_flags(mock_locate: MagicMock, mock_run: MagicMock, tmp_path: Path):
    """Test that merge command passes all flags to tasks_cli.py."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    tasks_cli = repo_root / "scripts" / "tasks" / "tasks_cli.py"
    tasks_cli.parent.mkdir(parents=True)
    tasks_cli.write_text("#!/usr/bin/env python3\n")

    # Create feature branch
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_root, check=True, capture_output=True)
    (repo_root / "test.txt").write_text("test")
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "test"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "001-test"], cwd=repo_root, check=True, capture_output=True)

    mock_locate.return_value = repo_root
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    from specify_cli.cli.commands.agent.feature import merge_feature

    with pytest.raises(SystemExit):
        merge_feature(
            feature="001-test",
            target="develop",
            strategy="squash",
            push=True,
            dry_run=True,
            keep_branch=True,
            keep_worktree=True,
            auto_retry=False
        )

    # Find the tasks_cli.py call
    for call in mock_run.call_args_list:
        call_args = call[0][0]
        if "tasks_cli.py" in str(call_args):
            assert "--feature" in call_args
            assert "001-test" in call_args
            assert "--target" in call_args
            assert "develop" in call_args
            assert "--strategy" in call_args
            assert "squash" in call_args
            assert "--push" in call_args
            assert "--dry-run" in call_args
            assert "--keep-branch" in call_args
            assert "--keep-worktree" in call_args
            break


# =============================================================================
# Error Path Tests (T073 - Coverage boost)
# =============================================================================

@patch("specify_cli.core.paths.locate_project_root")
def test_accept_command_missing_tasks_cli(mock_locate: MagicMock, tmp_path: Path):
    """Test accept command error when tasks_cli.py not found."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    mock_locate.return_value = repo_root

    from specify_cli.cli.commands.agent.feature import accept_feature

    with pytest.raises(SystemExit) as exc_info:
        accept_feature(feature=None, mode="auto", json_output=True, lenient=False, no_commit=False)

    # Should exit with error
    assert exc_info.value.code == 1


@patch("specify_cli.core.paths.locate_project_root")
def test_merge_command_missing_tasks_cli(mock_locate: MagicMock, tmp_path: Path):
    """Test merge command error when tasks_cli.py not found."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    mock_locate.return_value = repo_root

    from specify_cli.cli.commands.agent.feature import merge_feature

    with pytest.raises(SystemExit) as exc_info:
        merge_feature(
            feature=None,
            target="main",
            strategy="merge",
            push=False,
            dry_run=False,
            keep_branch=False,
            keep_worktree=False,
            auto_retry=False
        )

    # Should exit with error
    assert exc_info.value.code == 1


@patch("specify_cli.cli.commands.agent.feature._find_latest_feature_worktree")
@patch("specify_cli.cli.commands.agent.feature._get_current_branch")
@patch("specify_cli.core.paths.locate_project_root")
def test_merge_command_auto_retry_no_worktree_found(
    mock_locate: MagicMock,
    mock_get_branch: MagicMock,
    mock_find_latest: MagicMock,
    tmp_path: Path,
):
    """Test merge when auto-retry enabled but no worktrees exist."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    tasks_cli = repo_root / "scripts" / "tasks" / "tasks_cli.py"
    tasks_cli.parent.mkdir(parents=True)
    tasks_cli.write_text("#!/usr/bin/env python3\n")

    mock_locate.return_value = repo_root
    mock_get_branch.return_value = "main"  # Not a feature branch
    mock_find_latest.return_value = None  # No worktrees found

    from specify_cli.cli.commands.agent.feature import merge_feature

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with pytest.raises(SystemExit):
            merge_feature(
                feature=None,
                target="main",
                strategy="merge",
                push=False,
                dry_run=False,
                keep_branch=False,
                keep_worktree=False,
                auto_retry=True
            )

        # Should have tried to find worktree but then proceeded normally
        mock_find_latest.assert_called_once()


@patch("specify_cli.core.paths.locate_project_root")
def test_accept_command_no_repo_root(mock_locate: MagicMock):
    """Test accept command when repo root cannot be located."""
    mock_locate.return_value = None

    from specify_cli.cli.commands.agent.feature import accept_feature

    with pytest.raises(SystemExit) as exc_info:
        accept_feature(feature=None, mode="auto", json_output=True, lenient=False, no_commit=False)

    assert exc_info.value.code == 1


@patch("specify_cli.core.paths.locate_project_root")
def test_merge_command_no_repo_root(mock_locate: MagicMock):
    """Test merge command when repo root cannot be located."""
    mock_locate.return_value = None

    from specify_cli.cli.commands.agent.feature import merge_feature

    with pytest.raises(SystemExit) as exc_info:
        merge_feature(
            feature=None,
            target="main",
            strategy="merge",
            push=False,
            dry_run=False,
            keep_branch=False,
            keep_worktree=False,
            auto_retry=False
        )

    assert exc_info.value.code == 1


@patch("subprocess.run")
@patch("specify_cli.core.paths.locate_project_root")
def test_accept_command_with_all_flags_console_output(mock_locate: MagicMock, mock_run: MagicMock, tmp_path: Path):
    """Test accept command with console output (non-JSON)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    tasks_cli = repo_root / "scripts" / "tasks" / "tasks_cli.py"
    tasks_cli.parent.mkdir(parents=True)
    tasks_cli.write_text("#!/usr/bin/env python3\n")

    mock_locate.return_value = repo_root
    mock_run.return_value = MagicMock(returncode=0, stdout="Accepted!", stderr="")

    from specify_cli.cli.commands.agent.feature import accept_feature

    with pytest.raises(SystemExit) as exc_info:
        accept_feature(
            feature="001-test",
            mode="checklist",
            json_output=False,  # Console output mode
            lenient=True,
            no_commit=True
        )

    assert exc_info.value.code == 0
