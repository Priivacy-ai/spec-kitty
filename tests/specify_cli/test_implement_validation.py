"""Unit tests for implement dependency validation utility."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer

from specify_cli.core.implement_validation import (
    validate_and_resolve_base,
    validate_base_workspace_exists,
)


class TestValidateAndResolveBase:
    """Tests for validate_and_resolve_base function."""

    def test_no_dependencies_no_base(self, tmp_path):
        """WP with no dependencies and no --base should branch from main."""
        # Create WP file with no dependencies
        wp_file = tmp_path / "WP01-task.md"
        wp_file.write_text(
            "---\n"
            "work_package_id: WP01\n"
            "dependencies: []\n"
            "---\n"
            "Task content\n",
            encoding="utf-8"
        )

        # Should return (None, False) - branch from main, no auto-merge
        base, auto_merge = validate_and_resolve_base(
            wp_id="WP01",
            wp_file=wp_file,
            base=None,
            feature_slug="001-test",
            repo_root=tmp_path
        )

        assert base is None
        assert auto_merge is False

    def test_no_dependencies_with_base(self, tmp_path):
        """WP with no dependencies but explicit --base should use provided base."""
        # Create WP file with no dependencies
        wp_file = tmp_path / "WP02-task.md"
        wp_file.write_text(
            "---\n"
            "work_package_id: WP02\n"
            "dependencies: []\n"
            "---\n"
            "Task content\n",
            encoding="utf-8"
        )

        # Should accept provided base (even if not declared)
        base, auto_merge = validate_and_resolve_base(
            wp_id="WP02",
            wp_file=wp_file,
            base="WP01",
            feature_slug="001-test",
            repo_root=tmp_path
        )

        assert base == "WP01"
        assert auto_merge is False

    def test_single_dependency_no_base_errors(self, tmp_path, capsys):
        """WP with single dependency but no --base should error."""
        # Create WP file with single dependency
        wp_file = tmp_path / "WP02-task.md"
        wp_file.write_text(
            "---\n"
            "work_package_id: WP02\n"
            "dependencies: [WP01]\n"
            "---\n"
            "Task content\n",
            encoding="utf-8"
        )

        # Should raise typer.Exit
        with pytest.raises(typer.Exit):
            validate_and_resolve_base(
                wp_id="WP02",
                wp_file=wp_file,
                base=None,
                feature_slug="001-test",
                repo_root=tmp_path
            )

        # Check error message suggests --base
        captured = capsys.readouterr()
        assert "WP02 depends on WP01" in captured.out
        assert "spec-kitty implement WP02 --base WP01" in captured.out

    def test_single_dependency_with_matching_base(self, tmp_path):
        """WP with single dependency and matching --base should succeed."""
        # Create WP file with single dependency
        wp_file = tmp_path / "WP02-task.md"
        wp_file.write_text(
            "---\n"
            "work_package_id: WP02\n"
            "dependencies: [WP01]\n"
            "---\n"
            "Task content\n",
            encoding="utf-8"
        )

        # Should return provided base
        base, auto_merge = validate_and_resolve_base(
            wp_id="WP02",
            wp_file=wp_file,
            base="WP01",
            feature_slug="001-test",
            repo_root=tmp_path
        )

        assert base == "WP01"
        assert auto_merge is False

    def test_single_dependency_with_mismatched_base_warns(self, tmp_path, capsys):
        """WP with single dependency but different --base should warn but allow."""
        # Create WP file declaring dependency on WP01
        wp_file = tmp_path / "WP03-task.md"
        wp_file.write_text(
            "---\n"
            "work_package_id: WP03\n"
            "dependencies: [WP01]\n"
            "---\n"
            "Task content\n",
            encoding="utf-8"
        )

        # User provides --base WP02 (doesn't match WP01)
        base, auto_merge = validate_and_resolve_base(
            wp_id="WP03",
            wp_file=wp_file,
            base="WP02",
            feature_slug="001-test",
            repo_root=tmp_path
        )

        # Should warn but allow
        assert base == "WP02"
        assert auto_merge is False

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "does not declare dependency on WP02" in captured.out

    def test_multi_parent_no_base_auto_merge(self, tmp_path, capsys):
        """WP with multiple dependencies and no --base should enter auto-merge mode."""
        # Create WP file with multiple dependencies
        wp_file = tmp_path / "WP04-task.md"
        wp_file.write_text(
            "---\n"
            "work_package_id: WP04\n"
            "dependencies: [WP02, WP03]\n"
            "---\n"
            "Task content\n",
            encoding="utf-8"
        )

        # Should return (None, True) - auto-merge mode
        base, auto_merge = validate_and_resolve_base(
            wp_id="WP04",
            wp_file=wp_file,
            base=None,
            feature_slug="001-test",
            repo_root=tmp_path
        )

        assert base is None
        assert auto_merge is True

        captured = capsys.readouterr()
        assert "Multi-parent dependency detected" in captured.out
        assert "WP02, WP03" in captured.out

    def test_multi_parent_with_base(self, tmp_path):
        """WP with multiple dependencies but explicit --base should use provided base."""
        # Create WP file with multiple dependencies
        wp_file = tmp_path / "WP04-task.md"
        wp_file.write_text(
            "---\n"
            "work_package_id: WP04\n"
            "dependencies: [WP02, WP03]\n"
            "---\n"
            "Task content\n",
            encoding="utf-8"
        )

        # User provides explicit base (overrides auto-merge)
        base, auto_merge = validate_and_resolve_base(
            wp_id="WP04",
            wp_file=wp_file,
            base="WP03",
            feature_slug="001-test",
            repo_root=tmp_path
        )

        assert base == "WP03"
        assert auto_merge is False

    def test_multi_parent_base_not_in_deps_warns(self, tmp_path, capsys):
        """Multi-parent WP with --base not in deps should warn."""
        # Create WP file with dependencies on WP02, WP03
        wp_file = tmp_path / "WP04-task.md"
        wp_file.write_text(
            "---\n"
            "work_package_id: WP04\n"
            "dependencies: [WP02, WP03]\n"
            "---\n"
            "Task content\n",
            encoding="utf-8"
        )

        # User provides --base WP01 (not in dependencies)
        base, auto_merge = validate_and_resolve_base(
            wp_id="WP04",
            wp_file=wp_file,
            base="WP01",
            feature_slug="001-test",
            repo_root=tmp_path
        )

        assert base == "WP01"
        assert auto_merge is False

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "doesn't declare WP01 as dependency" in captured.out


class TestValidateBaseWorkspaceExists:
    """Tests for validate_base_workspace_exists function."""

    def test_base_workspace_missing_errors(self, tmp_path, capsys):
        """Should error if base workspace doesn't exist."""
        # No .worktrees/001-test-WP01/ directory
        with pytest.raises(typer.Exit):
            validate_base_workspace_exists(
                base="WP01",
                feature_slug="001-test",
                repo_root=tmp_path
            )

        captured = capsys.readouterr()
        assert "Base workspace WP01 does not exist" in captured.out
        assert "spec-kitty implement WP01" in captured.out

    def test_base_workspace_exists_but_invalid(self, tmp_path, capsys):
        """Should error if base workspace exists but isn't a valid worktree."""
        # Create .worktrees/001-test-WP01/ but not a valid git worktree
        base_workspace = tmp_path / ".worktrees" / "001-test-WP01"
        base_workspace.mkdir(parents=True)
        (base_workspace / "some-file.txt").write_text("not a worktree")

        with pytest.raises(typer.Exit):
            validate_base_workspace_exists(
                base="WP01",
                feature_slug="001-test",
                repo_root=tmp_path
            )

        captured = capsys.readouterr()
        # Check for error message (normalize whitespace due to Rich formatting)
        output = re.sub(r'\s+', ' ', captured.out)  # Normalize all whitespace to single spaces
        assert "exists but is not a valid worktree" in output
        assert "rm -rf" in output

    @patch("subprocess.run")
    def test_base_workspace_valid(self, mock_run, tmp_path):
        """Should succeed if base workspace is a valid worktree."""
        # Create .worktrees/001-test-WP01/ directory
        base_workspace = tmp_path / ".worktrees" / "001-test-WP01"
        base_workspace.mkdir(parents=True)

        # Mock git rev-parse to return success
        mock_run.return_value = Mock(returncode=0)

        # Should not raise
        validate_base_workspace_exists(
            base="WP01",
            feature_slug="001-test",
            repo_root=tmp_path
        )

        # Verify git rev-parse was called in base workspace
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "rev-parse", "--git-dir"]
        assert call_args[1]["cwd"] == base_workspace
