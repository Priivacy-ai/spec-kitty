"""Unit tests for implement command."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import typer

from specify_cli.cli.commands.implement import (
    detect_feature_context,
    find_wp_file,
    implement,
    validate_workspace_path,
)


class TestDetectFeatureContext:
    """Tests for detect_feature_context()."""

    def test_detect_from_feature_branch(self):
        """Test detection from feature branch (###-feature-name)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="010-workspace-per-wp\n"
            )

            number, slug = detect_feature_context()

            assert number == "010"
            assert slug == "010-workspace-per-wp"

    def test_detect_from_wp_branch(self):
        """Test detection from WP branch (###-feature-name-WP##)."""
        with patch("subprocess.run") as mock_run:
            # WP branch pattern includes WP suffix
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="010-workspace-per-wp-WP01\n"
            )

            number, slug = detect_feature_context()

            assert number == "010"
            # When on a WP branch, the full branch name is NOT returned,
            # only the feature slug (minus -WP##)
            # But looking at the implementation, it actually returns the full match
            # Let me check the actual behavior...
            # Pattern 2 extracts the feature slug without -WP##
            assert slug == "010-workspace-per-wp"

    def test_detect_from_directory(self):
        """Test detection from current directory path."""
        with patch("subprocess.run") as mock_run:
            # Git command fails
            mock_run.return_value = MagicMock(returncode=1, stdout="")

            with patch("pathlib.Path.cwd") as mock_cwd:
                mock_cwd.return_value = Path("/repo/kitty-specs/010-test-feature/tasks")

                number, slug = detect_feature_context()

                assert number == "010"
                assert slug == "010-test-feature"

    def test_detect_failure(self):
        """Test failure when context cannot be detected."""
        with patch("subprocess.run") as mock_run:
            # Git command fails
            mock_run.return_value = MagicMock(returncode=1, stdout="")

            with patch("pathlib.Path.cwd") as mock_cwd:
                # Current directory doesn't contain feature pattern
                mock_cwd.return_value = Path("/repo/src/tests")

                with pytest.raises(typer.Exit):
                    detect_feature_context()


class TestFindWpFile:
    """Tests for find_wp_file()."""

    def test_find_wp_file_success(self, tmp_path):
        """Test finding WP file successfully."""
        # Create test structure
        tasks_dir = tmp_path / "kitty-specs" / "010-feature" / "tasks"
        tasks_dir.mkdir(parents=True)
        wp_file = tasks_dir / "WP01-setup.md"
        wp_file.write_text("# WP01")

        result = find_wp_file(tmp_path, "010-feature", "WP01")

        assert result == wp_file

    def test_find_wp_file_not_found(self, tmp_path):
        """Test error when WP file not found."""
        # Create tasks dir but no WP file
        tasks_dir = tmp_path / "kitty-specs" / "010-feature" / "tasks"
        tasks_dir.mkdir(parents=True)

        with pytest.raises(FileNotFoundError, match="WP file not found"):
            find_wp_file(tmp_path, "010-feature", "WP01")

    def test_find_wp_file_tasks_dir_missing(self, tmp_path):
        """Test error when tasks directory doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Tasks directory not found"):
            find_wp_file(tmp_path, "010-feature", "WP01")


class TestValidateWorkspacePath:
    """Tests for validate_workspace_path()."""

    def test_path_doesnt_exist(self, tmp_path):
        """Test when workspace path doesn't exist (should create)."""
        workspace = tmp_path / "workspace"

        result = validate_workspace_path(workspace, "WP01")

        assert result is False  # Should create

    def test_path_exists_valid_worktree(self, tmp_path):
        """Test when workspace exists and is valid worktree (should reuse)."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        with patch("subprocess.run") as mock_run:
            # git rev-parse succeeds (valid worktree)
            mock_run.return_value = MagicMock(returncode=0)

            result = validate_workspace_path(workspace, "WP01")

            assert result is True  # Reuse existing
            mock_run.assert_called_once()

    def test_path_exists_invalid_worktree(self, tmp_path):
        """Test when workspace exists but is not valid worktree (error)."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        with patch("subprocess.run") as mock_run:
            # git rev-parse fails (not a worktree)
            mock_run.return_value = MagicMock(returncode=1)

            with pytest.raises(typer.Exit):
                validate_workspace_path(workspace, "WP01")


class TestImplementCommand:
    """Integration tests for implement command."""

    def test_implement_no_dependencies(self, tmp_path):
        """Test implement WP01 creates workspace from main."""
        # Setup
        wp_file = tmp_path / "kitty-specs" / "010-feature" / "tasks" / "WP01-setup.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            "---\nwork_package_id: WP01\ndependencies: []\n---\n# WP01"
        )

        with patch("specify_cli.cli.commands.implement.find_repo_root") as mock_repo_root:
            mock_repo_root.return_value = tmp_path

            with patch("specify_cli.cli.commands.implement.detect_feature_context") as mock_detect:
                mock_detect.return_value = ("010", "010-feature")

                with patch("subprocess.run") as mock_run:
                    # Mock git commands
                    mock_run.return_value = MagicMock(
                        returncode=0,
                        stdout=b"",
                        stderr=b""
                    )

                    # Run implement
                    implement("WP01", base=None)

                    # Verify git worktree add was called
                    worktree_calls = [
                        c for c in mock_run.call_args_list
                        if "worktree" in str(c)
                    ]
                    assert len(worktree_calls) > 0

                    # Verify command structure (branching from main)
                    last_call = worktree_calls[-1]
                    args = last_call[0][0]  # First positional arg (command list)
                    assert "worktree" in args
                    assert "add" in args
                    assert "-b" in args
                    # Should NOT have a fourth argument (base branch)
                    # Command should be: git worktree add path -b branch
                    assert len([a for a in args if "010-feature-WP01" in a]) >= 2

    def test_implement_with_base(self, tmp_path):
        """Test implement WP02 --base WP01 creates workspace from WP01 branch."""
        # Setup
        wp_file = tmp_path / "kitty-specs" / "010-feature" / "tasks" / "WP02-feature.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            '---\nwork_package_id: WP02\ndependencies: ["WP01"]\n---\n# WP02'
        )

        # Create base workspace
        base_workspace = tmp_path / ".worktrees" / "010-feature-WP01"
        base_workspace.mkdir(parents=True)

        with patch("specify_cli.cli.commands.implement.find_repo_root") as mock_repo_root:
            mock_repo_root.return_value = tmp_path

            with patch("specify_cli.cli.commands.implement.detect_feature_context") as mock_detect:
                mock_detect.return_value = ("010", "010-feature")

                with patch("subprocess.run") as mock_run:
                    # Mock different git commands
                    def run_side_effect(cmd, *args, **kwargs):
                        if "rev-parse" in cmd and "--git-dir" in cmd:
                            # Validating worktree
                            return MagicMock(returncode=0)
                        elif "rev-parse" in cmd and "--verify" in cmd:
                            # Verifying base branch exists
                            return MagicMock(returncode=0)
                        elif "worktree" in cmd and "add" in cmd:
                            # Creating worktree
                            return MagicMock(returncode=0, stdout=b"", stderr=b"")
                        return MagicMock(returncode=0)

                    mock_run.side_effect = run_side_effect

                    # Run implement
                    implement("WP02", base="WP01")

                    # Verify git worktree add was called with base branch
                    worktree_calls = [
                        c for c in mock_run.call_args_list
                        if "worktree" in str(c) and "add" in str(c)
                    ]
                    assert len(worktree_calls) > 0

                    # Verify command includes base branch
                    last_call = worktree_calls[-1]
                    args = last_call[0][0]
                    assert "010-feature-WP01" in args  # Base branch

    def test_implement_missing_base_workspace(self, tmp_path):
        """Test error when base workspace doesn't exist."""
        wp_file = tmp_path / "kitty-specs" / "010-feature" / "tasks" / "WP02-feature.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            '---\nwork_package_id: WP02\ndependencies: ["WP01"]\n---\n# WP02'
        )

        with patch("specify_cli.cli.commands.implement.find_repo_root") as mock_repo_root:
            mock_repo_root.return_value = tmp_path

            with patch("specify_cli.cli.commands.implement.detect_feature_context") as mock_detect:
                mock_detect.return_value = ("010", "010-feature")

                # Base workspace doesn't exist
                with pytest.raises(typer.Exit):
                    implement("WP02", base="WP01")

    def test_implement_has_deps_no_base_flag(self, tmp_path):
        """Test error when WP has dependencies but --base not provided."""
        wp_file = tmp_path / "kitty-specs" / "010-feature" / "tasks" / "WP02-feature.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            '---\nwork_package_id: WP02\ndependencies: ["WP01"]\n---\n# WP02'
        )

        with patch("specify_cli.cli.commands.implement.find_repo_root") as mock_repo_root:
            mock_repo_root.return_value = tmp_path

            with patch("specify_cli.cli.commands.implement.detect_feature_context") as mock_detect:
                mock_detect.return_value = ("010", "010-feature")

                # No --base flag provided
                with pytest.raises(typer.Exit):
                    implement("WP02", base=None)

    def test_implement_workspace_already_exists(self, tmp_path):
        """Test reusing existing valid workspace."""
        wp_file = tmp_path / "kitty-specs" / "010-feature" / "tasks" / "WP01-setup.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            "---\nwork_package_id: WP01\ndependencies: []\n---\n# WP01"
        )

        # Create existing workspace
        workspace = tmp_path / ".worktrees" / "010-feature-WP01"
        workspace.mkdir(parents=True)

        with patch("specify_cli.cli.commands.implement.find_repo_root") as mock_repo_root:
            mock_repo_root.return_value = tmp_path

            with patch("specify_cli.cli.commands.implement.detect_feature_context") as mock_detect:
                mock_detect.return_value = ("010", "010-feature")

                with patch("subprocess.run") as mock_run:
                    # git rev-parse succeeds (valid worktree)
                    mock_run.return_value = MagicMock(returncode=0)

                    # Run implement - should reuse existing
                    implement("WP01", base=None)

                    # Verify NO git worktree add was called
                    worktree_add_calls = [
                        c for c in mock_run.call_args_list
                        if "worktree" in str(c) and "add" in str(c)
                    ]
                    assert len(worktree_add_calls) == 0

    def test_workspace_naming_convention(self, tmp_path):
        """Test workspace naming follows convention."""
        # Use the feature slug that will be detected
        wp_file = tmp_path / "kitty-specs" / "010-workspace-per-wp" / "tasks" / "WP01-setup.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            "---\nwork_package_id: WP01\ndependencies: []\n---\n# WP01"
        )

        with patch("specify_cli.cli.commands.implement.find_repo_root") as mock_repo_root:
            mock_repo_root.return_value = tmp_path

            with patch("specify_cli.cli.commands.implement.detect_feature_context") as mock_detect:
                mock_detect.return_value = ("010", "010-workspace-per-wp")

                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")

                    # Run implement
                    implement("WP01", base=None)

                    # Verify workspace path and branch name
                    worktree_calls = [
                        c for c in mock_run.call_args_list
                        if "worktree" in str(c) and "add" in str(c)
                    ]
                    assert len(worktree_calls) > 0

                    args = worktree_calls[-1][0][0]
                    # Workspace name should be: ###-feature-WP##
                    assert ".worktrees/010-workspace-per-wp-WP01" in " ".join(args)
                    assert "010-workspace-per-wp-WP01" in args  # Branch name
