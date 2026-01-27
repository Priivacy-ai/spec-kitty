"""Unit tests for git validation in move-task command.

Tests the validation that prevents moving WPs to "done" status
when there are uncommitted changes in the worktree.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app

runner = CliRunner()


@pytest.fixture
def git_repo_with_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """Create a git repository with a worktree for testing.

    Returns:
        Tuple of (repo_root, worktree_path)
    """
    repo = tmp_path / "test-repo"
    repo.mkdir()

    # Initialize git repo with explicit branch name
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create .kittify marker with a file inside (git won't track empty directories)
    (repo / ".kittify").mkdir()
    (repo / ".kittify" / "config.yaml").write_text("# Config\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create feature directory and task file
    feature_dir = repo / "kitty-specs" / "017-test-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    task_file = tasks_dir / "WP01-test-task.md"
    task_content = """---
work_package_id: "WP01"
title: "Test Task"
lane: "doing"
agent: "test-agent"
shell_pid: ""
---

# Work Package: WP01 - Test Task

Test content here.

## Activity Log

- 2025-01-01T00:00:00Z – system – lane=planned – Initial creation
"""
    task_file.write_text(task_content)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add task file"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create worktree with branch that has commits beyond main
    worktree_dir = repo / ".worktrees" / "017-test-feature-WP01"
    subprocess.run(
        ["git", "worktree", "add", "-b", "017-test-feature-WP01", str(worktree_dir), "main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Add a commit in the worktree (so branch has commits beyond main)
    (worktree_dir / "implementation.txt").write_text("Implementation work\n")
    subprocess.run(["git", "add", "."], cwd=worktree_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add implementation"],
        cwd=worktree_dir,
        check=True,
        capture_output=True,
    )

    return repo, worktree_dir


class TestMoveTaskGitValidation:
    """Tests for git validation when moving tasks to done."""

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_move_to_done_with_uncommitted_changes_fails(
        self, mock_slug: Mock, mock_root: Mock, git_repo_with_worktree: tuple[Path, Path]
    ):
        """Should fail when moving to done with uncommitted changes."""
        repo_root, worktree = git_repo_with_worktree
        mock_root.return_value = repo_root
        mock_slug.return_value = "017-test-feature"

        # Create uncommitted file in worktree
        (worktree / "uncommitted.txt").write_text("Uncommitted work\n")

        # Try to move to done (should fail)
        result = runner.invoke(app, ["move-task", "WP01", "--to", "done", "--json"])

        # Verify failure
        assert result.exit_code == 1
        # Parse only the first JSON object (CLI may output multiple)
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output
        assert "uncommitted" in output["error"].lower() or "changes" in output["error"].lower()

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_move_to_done_with_committed_changes_succeeds(
        self, mock_slug: Mock, mock_root: Mock, git_repo_with_worktree: tuple[Path, Path]
    ):
        """Should succeed when moving to done with all changes committed."""
        repo_root, worktree = git_repo_with_worktree
        mock_root.return_value = repo_root
        mock_slug.return_value = "017-test-feature"

        # Worktree already has committed changes (from fixture)
        # Verify no uncommitted changes
        result_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result_status.stdout.strip() == ""

        # Move to done (should succeed)
        result = runner.invoke(app, ["move-task", "WP01", "--to", "done", "--json"])

        # Verify success
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["result"] == "success"
        assert output["new_lane"] == "done"

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_move_to_done_with_force_bypasses_validation(
        self, mock_slug: Mock, mock_root: Mock, git_repo_with_worktree: tuple[Path, Path]
    ):
        """Should succeed when using --force flag even with uncommitted changes."""
        repo_root, worktree = git_repo_with_worktree
        mock_root.return_value = repo_root
        mock_slug.return_value = "017-test-feature"

        # Create uncommitted file in worktree
        (worktree / "uncommitted.txt").write_text("Uncommitted work\n")

        # Move to done with --force (should succeed)
        result = runner.invoke(
            app, ["move-task", "WP01", "--to", "done", "--force", "--json"]
        )

        # Verify success despite uncommitted changes
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["result"] == "success"
        assert output["new_lane"] == "done"

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_move_to_for_review_still_validates(
        self, mock_slug: Mock, mock_root: Mock, git_repo_with_worktree: tuple[Path, Path]
    ):
        """Should still validate when moving to for_review (existing behavior)."""
        repo_root, worktree = git_repo_with_worktree
        mock_root.return_value = repo_root
        mock_slug.return_value = "017-test-feature"

        # Create uncommitted file in worktree
        (worktree / "uncommitted.txt").write_text("Uncommitted work\n")

        # Try to move to for_review (should fail)
        result = runner.invoke(app, ["move-task", "WP01", "--to", "for_review", "--json"])

        # Verify failure (existing behavior preserved)
        assert result.exit_code == 1
        # Parse only the first JSON object (CLI may output multiple)
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output
        assert "uncommitted" in output["error"].lower() or "changes" in output["error"].lower()

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_move_to_done_with_staged_but_uncommitted_fails(
        self, mock_slug: Mock, mock_root: Mock, git_repo_with_worktree: tuple[Path, Path]
    ):
        """Should fail when moving to done with staged but uncommitted changes."""
        repo_root, worktree = git_repo_with_worktree
        mock_root.return_value = repo_root
        mock_slug.return_value = "017-test-feature"

        # Create and stage a file (but don't commit)
        (worktree / "staged.txt").write_text("Staged but not committed\n")
        subprocess.run(["git", "add", "."], cwd=worktree, check=True, capture_output=True)

        # Try to move to done (should fail)
        result = runner.invoke(app, ["move-task", "WP01", "--to", "done", "--json"])

        # Verify failure
        assert result.exit_code == 1
        # Parse only the first JSON object (CLI may output multiple)
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output
        assert "uncommitted" in output["error"].lower() or "changes" in output["error"].lower()
