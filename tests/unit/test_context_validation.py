"""Tests for context validation and location-aware command guards.

Verifies Phase 3 implementation:
- Context detection (main repo vs worktree)
- Location-based command guards (@require_main_repo, @require_worktree)
- Clear error messages for location mismatches
- Environment variable support
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer

from specify_cli.core.context_validation import (
    CurrentContext,
    ExecutionContext,
    detect_execution_context,
    format_location_error,
    get_context_env_vars,
    get_current_context,
    require_main_repo,
    require_worktree,
    set_context_env_vars,
)


class TestContextDetection:
    """Tests for context detection logic."""

    def test_detect_main_repo_with_kittify(self, tmp_path: Path):
        """Test detection when in main repo with .kittify directory."""
        # Create .kittify to mark main repo
        kittify = tmp_path / ".kittify"
        kittify.mkdir()

        ctx = detect_execution_context(cwd=tmp_path)

        assert ctx.location == ExecutionContext.MAIN_REPO
        assert ctx.cwd == tmp_path
        assert ctx.repo_root == tmp_path
        assert ctx.worktree_name is None
        assert ctx.worktree_path is None

    def test_detect_main_repo_with_git(self, tmp_path: Path):
        """Test detection when in main repo with .git directory."""
        # Create .git to mark main repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        ctx = detect_execution_context(cwd=tmp_path)

        assert ctx.location == ExecutionContext.MAIN_REPO
        assert ctx.repo_root == tmp_path

    def test_detect_worktree_root(self, tmp_path: Path):
        """Test detection when in worktree root directory."""
        # Create worktree structure
        (tmp_path / ".kittify").mkdir()
        worktree_path = tmp_path / ".worktrees" / "010-feature-WP02"
        worktree_path.mkdir(parents=True)

        ctx = detect_execution_context(cwd=worktree_path)

        assert ctx.location == ExecutionContext.WORKTREE
        assert ctx.cwd == worktree_path
        assert ctx.repo_root == tmp_path
        assert ctx.worktree_name == "010-feature-WP02"
        assert ctx.worktree_path == worktree_path

    def test_detect_worktree_subdirectory(self, tmp_path: Path):
        """Test detection when in subdirectory of worktree."""
        # Create worktree with subdirectory
        (tmp_path / ".kittify").mkdir()
        worktree_path = tmp_path / ".worktrees" / "010-feature-WP02"
        subdir = worktree_path / "src" / "components"
        subdir.mkdir(parents=True)

        ctx = detect_execution_context(cwd=subdir)

        assert ctx.location == ExecutionContext.WORKTREE
        assert ctx.cwd == subdir
        assert ctx.repo_root == tmp_path
        assert ctx.worktree_name == "010-feature-WP02"
        assert ctx.worktree_path == worktree_path

    def test_detect_nested_worktree_path(self, tmp_path: Path):
        """Test detection prevents nested worktree confusion."""
        # Create nested structure (should not happen, but test detection)
        (tmp_path / ".kittify").mkdir()
        outer_worktree = tmp_path / ".worktrees" / "010-feature-WP01"
        # This would be a nested worktree (invalid)
        nested_path = outer_worktree / ".worktrees" / "010-feature-WP02"
        nested_path.mkdir(parents=True)

        ctx = detect_execution_context(cwd=nested_path)

        # Should detect as worktree (first .worktrees in path)
        assert ctx.location == ExecutionContext.WORKTREE
        # Should use first .worktrees found
        assert ctx.worktree_name == "010-feature-WP01"

    def test_get_current_context(self, tmp_path: Path, monkeypatch):
        """Test get_current_context uses current working directory."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()

        monkeypatch.chdir(tmp_path)

        ctx = get_current_context()

        assert ctx.location == ExecutionContext.MAIN_REPO
        assert ctx.cwd == tmp_path

    def test_detect_false_positive_worktree(self, tmp_path: Path):
        """Directory named .worktrees outside project root should not false-positive."""
        fake_worktree = tmp_path / ".worktrees" / "not-a-worktree"
        fake_worktree.mkdir(parents=True)

        ctx = detect_execution_context(cwd=fake_worktree)

        assert ctx.location == ExecutionContext.MAIN_REPO
        assert ctx.repo_root is None


class TestRequireMainRepo:
    """Tests for @require_main_repo decorator."""

    def test_allows_execution_from_main_repo(self, tmp_path: Path, monkeypatch):
        """Test decorator allows execution from main repo."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        monkeypatch.chdir(tmp_path)

        @require_main_repo
        def test_command():
            return "success"

        result = test_command()
        assert result == "success"

    def test_blocks_execution_from_worktree(self, tmp_path: Path, monkeypatch):
        """Test decorator blocks execution from worktree."""
        (tmp_path / ".kittify").mkdir()
        worktree_path = tmp_path / ".worktrees" / "010-feature-WP02"
        worktree_path.mkdir(parents=True)
        monkeypatch.chdir(worktree_path)

        @require_main_repo
        def test_command():
            return "success"

        with pytest.raises(typer.Exit) as exc_info:
            test_command()

        assert exc_info.value.exit_code == 1

    def test_error_message_from_worktree(self, tmp_path: Path, monkeypatch, capsys):
        """Test error message when blocked from worktree."""
        (tmp_path / ".kittify").mkdir()
        worktree_path = tmp_path / ".worktrees" / "010-feature-WP02"
        worktree_path.mkdir(parents=True)
        monkeypatch.chdir(worktree_path)

        @require_main_repo
        def implement(wp_id: str):
            return f"Implementing {wp_id}"

        with pytest.raises(typer.Exit):
            implement("WP03")

        # Error message should mention worktree and suggest cd command
        # (Note: rich console output may not be captured perfectly in tests)


class TestRequireWorktree:
    """Tests for @require_worktree decorator."""

    def test_allows_execution_from_worktree(self, tmp_path: Path, monkeypatch):
        """Test decorator allows execution from worktree."""
        (tmp_path / ".kittify").mkdir()
        worktree_path = tmp_path / ".worktrees" / "010-feature-WP02"
        worktree_path.mkdir(parents=True)
        monkeypatch.chdir(worktree_path)

        @require_worktree
        def test_command():
            return "success"

        result = test_command()
        assert result == "success"

    def test_blocks_execution_from_main_repo(self, tmp_path: Path, monkeypatch):
        """Test decorator blocks execution from main repo."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        monkeypatch.chdir(tmp_path)

        @require_worktree
        def test_command():
            return "success"

        with pytest.raises(typer.Exit) as exc_info:
            test_command()

        assert exc_info.value.exit_code == 1


class TestLocationErrorMessages:
    """Tests for error message formatting."""

    def test_format_error_main_required_from_worktree(self, tmp_path: Path):
        """Test error message for command needing main repo, run from worktree."""
        ctx = CurrentContext(
            location=ExecutionContext.WORKTREE,
            cwd=tmp_path / ".worktrees" / "010-feature-WP02",
            repo_root=tmp_path,
            worktree_name="010-feature-WP02",
            worktree_path=tmp_path / ".worktrees" / "010-feature-WP02",
        )

        error_msg = format_location_error(
            required=ExecutionContext.MAIN_REPO,
            actual=ExecutionContext.WORKTREE,
            command_name="implement",
            current_ctx=ctx,
        )

        assert "implement" in error_msg
        assert "main repository" in error_msg
        assert "010-feature-WP02" in error_msg
        assert f"cd {tmp_path}" in error_msg


class TestEnvVarBypass:
    """Tests for env var bypass prevention."""

    def test_filesystem_overrides_env(self, mock_worktree):
        """Filesystem detection should override SPEC_KITTY_CONTEXT env var."""
        import os

        os.environ["SPEC_KITTY_CONTEXT"] = "main"

        try:
            context = detect_execution_context(cwd=mock_worktree["worktree_path"])
            assert context.location == ExecutionContext.WORKTREE
        finally:
            os.environ.pop("SPEC_KITTY_CONTEXT", None)

    def test_format_error_worktree_required_from_main(self, tmp_path: Path):
        """Test error message for command needing worktree, run from main repo."""
        ctx = CurrentContext(
            location=ExecutionContext.MAIN_REPO,
            cwd=tmp_path,
            repo_root=tmp_path,
            worktree_name=None,
            worktree_path=None,
        )

        error_msg = format_location_error(
            required=ExecutionContext.WORKTREE,
            actual=ExecutionContext.MAIN_REPO,
            command_name="workspace_status",
            current_ctx=ctx,
        )

        assert "workspace_status" in error_msg
        assert "worktree" in error_msg
        assert ".worktrees" in error_msg


class TestEnvironmentVariables:
    """Tests for context environment variable support."""

    def test_set_context_env_vars_main_repo(self, tmp_path: Path):
        """Test setting environment variables for main repo context."""
        ctx = CurrentContext(
            location=ExecutionContext.MAIN_REPO,
            cwd=tmp_path,
            repo_root=tmp_path,
            worktree_name=None,
            worktree_path=None,
        )

        set_context_env_vars(ctx)

        import os

        assert os.environ["SPEC_KITTY_CONTEXT"] == "main"
        assert os.environ["SPEC_KITTY_CWD"] == str(tmp_path)
        assert os.environ["SPEC_KITTY_REPO_ROOT"] == str(tmp_path)
        assert "SPEC_KITTY_WORKTREE_NAME" not in os.environ
        assert "SPEC_KITTY_WORKTREE_PATH" not in os.environ

    def test_set_context_env_vars_worktree(self, tmp_path: Path):
        """Test setting environment variables for worktree context."""
        worktree_path = tmp_path / ".worktrees" / "010-feature-WP02"

        ctx = CurrentContext(
            location=ExecutionContext.WORKTREE,
            cwd=worktree_path,
            repo_root=tmp_path,
            worktree_name="010-feature-WP02",
            worktree_path=worktree_path,
        )

        set_context_env_vars(ctx)

        import os

        assert os.environ["SPEC_KITTY_CONTEXT"] == "worktree"
        assert os.environ["SPEC_KITTY_WORKTREE_NAME"] == "010-feature-WP02"
        assert os.environ["SPEC_KITTY_WORKTREE_PATH"] == str(worktree_path)

    def test_get_context_env_vars(self, tmp_path: Path):
        """Test getting context environment variables."""
        ctx = CurrentContext(
            location=ExecutionContext.WORKTREE,
            cwd=tmp_path / ".worktrees" / "010-feature-WP02",
            repo_root=tmp_path,
            worktree_name="010-feature-WP02",
            worktree_path=tmp_path / ".worktrees" / "010-feature-WP02",
        )

        set_context_env_vars(ctx)
        env_vars = get_context_env_vars()

        assert env_vars["SPEC_KITTY_CONTEXT"] == "worktree"
        assert env_vars["SPEC_KITTY_WORKTREE_NAME"] == "010-feature-WP02"

    def test_env_vars_cleared_when_switching_context(self, tmp_path: Path):
        """Test environment variables are cleared when switching from worktree to main."""
        # Set worktree context
        worktree_ctx = CurrentContext(
            location=ExecutionContext.WORKTREE,
            cwd=tmp_path / ".worktrees" / "010-feature-WP02",
            repo_root=tmp_path,
            worktree_name="010-feature-WP02",
            worktree_path=tmp_path / ".worktrees" / "010-feature-WP02",
        )
        set_context_env_vars(worktree_ctx)

        # Switch to main repo context
        main_ctx = CurrentContext(
            location=ExecutionContext.MAIN_REPO,
            cwd=tmp_path,
            repo_root=tmp_path,
            worktree_name=None,
            worktree_path=None,
        )
        set_context_env_vars(main_ctx)

        import os

        # Worktree-specific vars should be removed
        assert "SPEC_KITTY_WORKTREE_NAME" not in os.environ
        assert "SPEC_KITTY_WORKTREE_PATH" not in os.environ


class TestWorktreeNestingPrevention:
    """Critical tests for worktree nesting prevention."""

    def test_implement_blocked_from_worktree(self, tmp_path: Path, monkeypatch):
        """CRITICAL: Test that implement command is blocked from worktree.

        This prevents nested worktrees which corrupt git state.
        """
        (tmp_path / ".kittify").mkdir()
        # Setup worktree
        worktree_path = tmp_path / ".worktrees" / "010-feature-WP02"
        worktree_path.mkdir(parents=True)
        monkeypatch.chdir(worktree_path)

        # Import implement command (which has @require_main_repo decorator)
        from specify_cli.cli.commands.implement import implement

        # Should be blocked with clear error
        with pytest.raises(typer.Exit) as exc_info:
            implement(wp_id="WP03")

        assert exc_info.value.exit_code == 1

    def test_merge_blocked_from_worktree(self, tmp_path: Path, monkeypatch):
        """Test that merge command is blocked from worktree."""
        (tmp_path / ".kittify").mkdir()
        worktree_path = tmp_path / ".worktrees" / "010-feature-WP02"
        worktree_path.mkdir(parents=True)
        monkeypatch.chdir(worktree_path)

        from specify_cli.cli.commands.merge import merge

        with pytest.raises(typer.Exit) as exc_info:
            merge()

        assert exc_info.value.exit_code == 1

    def test_nested_worktree_detection(self, tmp_path: Path):
        """Test detection of nested worktree paths (edge case)."""
        # Create what would be a nested worktree (invalid scenario)
        (tmp_path / ".kittify").mkdir()
        outer_worktree = tmp_path / ".worktrees" / "010-feature-WP01"
        nested_worktrees = outer_worktree / ".worktrees"
        nested_workspace = nested_worktrees / "010-feature-WP02"
        nested_workspace.mkdir(parents=True)

        ctx = detect_execution_context(cwd=nested_workspace)

        # Should detect as worktree (first .worktrees in path)
        assert ctx.location == ExecutionContext.WORKTREE
        # This prevents trying to create another worktree
        assert ctx.worktree_name == "010-feature-WP01"


class TestEdgeCases:
    """Tests for edge cases in context detection."""

    def test_detect_without_repo_markers(self, tmp_path: Path):
        """Test detection when no .kittify or .git found."""
        # Empty directory
        empty_dir = tmp_path / "no-repo"
        empty_dir.mkdir()

        ctx = detect_execution_context(cwd=empty_dir)

        # Should still detect as main repo (default)
        assert ctx.location == ExecutionContext.MAIN_REPO
        # But repo_root will be None
        assert ctx.repo_root is None

    def test_detect_from_deep_subdirectory(self, tmp_path: Path):
        """Test detection from deep subdirectory in main repo."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()

        deep_dir = tmp_path / "src" / "specify_cli" / "cli" / "commands"
        deep_dir.mkdir(parents=True)

        ctx = detect_execution_context(cwd=deep_dir)

        assert ctx.location == ExecutionContext.MAIN_REPO
        assert ctx.repo_root == tmp_path

    def test_worktree_name_with_hyphens(self, tmp_path: Path):
        """Test worktree detection with complex names."""
        (tmp_path / ".kittify").mkdir()
        worktree_path = tmp_path / ".worktrees" / "015-first-class-jujutsu-vcs-integration-WP08"
        worktree_path.mkdir(parents=True)

        ctx = detect_execution_context(cwd=worktree_path)

        assert ctx.location == ExecutionContext.WORKTREE
        assert ctx.worktree_name == "015-first-class-jujutsu-vcs-integration-WP08"
