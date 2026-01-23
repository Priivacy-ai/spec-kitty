"""
Tests for the ops command.

Tests operation history and undo functionality for both git and jj backends.
"""

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.core.vcs import (
    GIT_CAPABILITIES,
    JJ_CAPABILITIES,
    OperationInfo,
    VCSBackend,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def runner():
    """Create a Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def git_repo(tmp_path):
    """Create a minimal git repository for testing."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        capture_output=True,
    )

    # Create initial commit
    test_file = tmp_path / "README.md"
    test_file.write_text("# Test Repo\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        capture_output=True,
    )

    return tmp_path


@pytest.fixture
def mock_git_vcs():
    """Create a mock GitVCS for testing."""
    vcs = MagicMock()
    vcs.backend = VCSBackend.GIT
    vcs.capabilities = GIT_CAPABILITIES
    return vcs


@pytest.fixture
def mock_jj_vcs():
    """Create a mock JujutsuVCS for testing."""
    vcs = MagicMock()
    vcs.backend = VCSBackend.JUJUTSU
    vcs.capabilities = JJ_CAPABILITIES
    return vcs


@pytest.fixture
def sample_operations():
    """Create sample operation info for testing."""
    now = datetime.now(timezone.utc)
    return [
        OperationInfo(
            operation_id="abc123def456789",
            description="commit: Initial commit",
            timestamp=now,
            heads=["abc123"],
            working_copy_commit="abc123",
            is_undoable=True,
            parent_operation="parent1",
        ),
        OperationInfo(
            operation_id="def456abc123789",
            description="checkout: Switch to main",
            timestamp=now,
            heads=["def456"],
            working_copy_commit="def456",
            is_undoable=True,
            parent_operation="parent2",
        ),
        OperationInfo(
            operation_id="789abc123def456",
            description="new: Create workspace",
            timestamp=now,
            heads=["789abc"],
            working_copy_commit="789abc",
            is_undoable=True,
            parent_operation="parent3",
        ),
    ]


# =============================================================================
# Test: ops log for both backends
# =============================================================================


class TestOpsLog:
    """Tests for ops log subcommand."""

    @pytest.mark.parametrize("backend", [
        "git",
        pytest.param("jj", marks=pytest.mark.xfail(reason="jj not installed in CI environment")),
    ])
    def test_ops_log_shows_history(self, runner, backend, sample_operations, tmp_path):
        """ops log should show operation history for both backends."""
        # Import here to allow patching
        from specify_cli.cli.commands import ops as ops_module

        if backend == "git":
            mock_vcs = MagicMock()
            mock_vcs.backend = VCSBackend.GIT
            mock_vcs.capabilities = GIT_CAPABILITIES

            with patch.object(ops_module, "get_vcs", return_value=mock_vcs):
                with patch(
                    "specify_cli.core.vcs.git.git_get_reflog",
                    return_value=sample_operations,
                ):
                    with patch("os.getcwd", return_value=str(tmp_path)):
                        result = runner.invoke(ops_module.app, ["log"])

            assert result.exit_code == 0
            assert "Operation History" in result.output
            assert "git reflog" in result.output

        else:  # jj
            mock_vcs = MagicMock()
            mock_vcs.backend = VCSBackend.JUJUTSU
            mock_vcs.capabilities = JJ_CAPABILITIES

            with patch.object(ops_module, "get_vcs", return_value=mock_vcs):
                with patch(
                    "specify_cli.core.vcs.jujutsu.jj_get_operation_log",
                    return_value=sample_operations,
                ):
                    with patch("os.getcwd", return_value=str(tmp_path)):
                        result = runner.invoke(ops_module.app, ["log"])

            assert result.exit_code == 0
            assert "Operation History" in result.output
            assert "jj" in result.output

    def test_ops_log_respects_limit(self, runner, sample_operations, tmp_path):
        """ops log should respect the --limit option."""
        from specify_cli.cli.commands import ops as ops_module

        mock_vcs = MagicMock()
        mock_vcs.backend = VCSBackend.GIT
        mock_vcs.capabilities = GIT_CAPABILITIES

        # Track what limit was passed
        captured_limit = None

        def mock_reflog(path, limit=20):
            nonlocal captured_limit
            captured_limit = limit
            return sample_operations[:limit] if limit < len(sample_operations) else sample_operations

        with patch.object(ops_module, "get_vcs", return_value=mock_vcs):
            with patch(
                "specify_cli.core.vcs.git.git_get_reflog",
                side_effect=mock_reflog,
            ):
                with patch("os.getcwd", return_value=str(tmp_path)):
                    result = runner.invoke(ops_module.app, ["log", "--limit", "5"])

        assert result.exit_code == 0
        assert captured_limit == 5

    def test_ops_log_shows_empty_message(self, runner, tmp_path):
        """ops log should show appropriate message when no operations found."""
        from specify_cli.cli.commands import ops as ops_module

        mock_vcs = MagicMock()
        mock_vcs.backend = VCSBackend.GIT
        mock_vcs.capabilities = GIT_CAPABILITIES

        with patch.object(ops_module, "get_vcs", return_value=mock_vcs):
            with patch(
                "specify_cli.core.vcs.git.git_get_reflog",
                return_value=[],
            ):
                with patch("os.getcwd", return_value=str(tmp_path)):
                    result = runner.invoke(ops_module.app, ["log"])

        assert result.exit_code == 0
        assert "No operations found" in result.output

    def test_ops_log_verbose_shows_full_ids(self, runner, sample_operations, tmp_path):
        """ops log --verbose should show full operation IDs."""
        from specify_cli.cli.commands import ops as ops_module

        mock_vcs = MagicMock()
        mock_vcs.backend = VCSBackend.GIT
        mock_vcs.capabilities = GIT_CAPABILITIES

        with patch.object(ops_module, "get_vcs", return_value=mock_vcs):
            with patch(
                "specify_cli.core.vcs.git.git_get_reflog",
                return_value=sample_operations,
            ):
                with patch("os.getcwd", return_value=str(tmp_path)):
                    result = runner.invoke(ops_module.app, ["log", "--verbose"])

        assert result.exit_code == 0
        assert "Full operation IDs" in result.output
        # Should show the full ID in verbose output
        assert "abc123def456789" in result.output


# =============================================================================
# Test: ops undo for jj
# =============================================================================


class TestOpsUndo:
    """Tests for ops undo subcommand."""

    def test_ops_undo_works_for_jj(self, runner, tmp_path):
        """ops undo should work for jj backend."""
        from specify_cli.cli.commands import ops as ops_module

        mock_vcs = MagicMock()
        mock_vcs.backend = VCSBackend.JUJUTSU
        mock_vcs.capabilities = JJ_CAPABILITIES

        with patch.object(ops_module, "get_vcs", return_value=mock_vcs):
            with patch(
                "specify_cli.core.vcs.jujutsu.jj_undo_operation",
                return_value=True,
            ):
                with patch("os.getcwd", return_value=str(tmp_path)):
                    result = runner.invoke(ops_module.app, ["undo"])

        assert result.exit_code == 0
        assert "Operation undone successfully" in result.output

    def test_ops_undo_fails_for_git(self, runner, tmp_path):
        """ops undo should fail gracefully for git backend."""
        from specify_cli.cli.commands import ops as ops_module

        mock_vcs = MagicMock()
        mock_vcs.backend = VCSBackend.GIT
        mock_vcs.capabilities = GIT_CAPABILITIES

        with patch.object(ops_module, "get_vcs", return_value=mock_vcs):
            with patch("os.getcwd", return_value=str(tmp_path)):
                result = runner.invoke(ops_module.app, ["undo"])

        assert result.exit_code == 1
        assert "Undo not supported" in result.output
        assert "git" in result.output.lower()
        # Should provide helpful alternatives
        assert "git reset" in result.output or "git revert" in result.output

    def test_ops_undo_with_operation_id(self, runner, tmp_path):
        """ops undo should accept an operation ID for jj."""
        from specify_cli.cli.commands import ops as ops_module

        mock_vcs = MagicMock()
        mock_vcs.backend = VCSBackend.JUJUTSU
        mock_vcs.capabilities = JJ_CAPABILITIES

        captured_op_id = None

        def mock_undo(path, op_id=None):
            nonlocal captured_op_id
            captured_op_id = op_id
            return True

        with patch.object(ops_module, "get_vcs", return_value=mock_vcs):
            with patch(
                "specify_cli.core.vcs.jujutsu.jj_undo_operation",
                side_effect=mock_undo,
            ):
                with patch("os.getcwd", return_value=str(tmp_path)):
                    result = runner.invoke(ops_module.app, ["undo", "abc123"])

        assert result.exit_code == 0
        assert captured_op_id == "abc123"

    def test_ops_undo_failure_shows_error(self, runner, tmp_path):
        """ops undo should show error message when undo fails."""
        from specify_cli.cli.commands import ops as ops_module

        mock_vcs = MagicMock()
        mock_vcs.backend = VCSBackend.JUJUTSU
        mock_vcs.capabilities = JJ_CAPABILITIES

        with patch.object(ops_module, "get_vcs", return_value=mock_vcs):
            with patch(
                "specify_cli.core.vcs.jujutsu.jj_undo_operation",
                return_value=False,
            ):
                with patch("os.getcwd", return_value=str(tmp_path)):
                    result = runner.invoke(ops_module.app, ["undo"])

        assert result.exit_code == 1
        assert "Undo failed" in result.output


# =============================================================================
# Test: ops restore for jj
# =============================================================================


class TestOpsRestore:
    """Tests for ops restore subcommand."""

    def test_ops_restore_works_for_jj(self, runner, tmp_path):
        """ops restore should work for jj backend."""
        from specify_cli.cli.commands import ops as ops_module

        mock_vcs = MagicMock()
        mock_vcs.backend = VCSBackend.JUJUTSU
        mock_vcs.capabilities = JJ_CAPABILITIES

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch.object(ops_module, "get_vcs", return_value=mock_vcs):
            with patch("subprocess.run", return_value=mock_result):
                with patch("os.getcwd", return_value=str(tmp_path)):
                    result = runner.invoke(ops_module.app, ["restore", "abc123"])

        assert result.exit_code == 0
        assert "Restored successfully" in result.output

    def test_ops_restore_fails_for_git(self, runner, tmp_path):
        """ops restore should fail gracefully for git backend."""
        from specify_cli.cli.commands import ops as ops_module

        mock_vcs = MagicMock()
        mock_vcs.backend = VCSBackend.GIT
        mock_vcs.capabilities = GIT_CAPABILITIES

        with patch.object(ops_module, "get_vcs", return_value=mock_vcs):
            with patch("os.getcwd", return_value=str(tmp_path)):
                result = runner.invoke(ops_module.app, ["restore", "abc123"])

        assert result.exit_code == 1
        assert "Restore not supported" in result.output
        assert "git" in result.output.lower()

    def test_ops_restore_requires_operation_id(self, runner, tmp_path):
        """ops restore should require an operation ID."""
        from specify_cli.cli.commands import ops as ops_module

        mock_vcs = MagicMock()
        mock_vcs.backend = VCSBackend.JUJUTSU
        mock_vcs.capabilities = JJ_CAPABILITIES

        with patch.object(ops_module, "get_vcs", return_value=mock_vcs):
            with patch("os.getcwd", return_value=str(tmp_path)):
                result = runner.invoke(ops_module.app, ["restore"])

        # Typer should report missing argument
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "OPERATION_ID" in result.output


# =============================================================================
# Test: VCS detection errors
# =============================================================================


class TestVCSDetection:
    """Tests for VCS detection handling."""

    def test_ops_log_handles_vcs_detection_error(self, runner, tmp_path):
        """ops log should handle VCS detection errors gracefully."""
        from specify_cli.cli.commands import ops as ops_module

        with patch.object(ops_module, "get_vcs", side_effect=Exception("Not a VCS repo")):
            with patch("os.getcwd", return_value=str(tmp_path)):
                result = runner.invoke(ops_module.app, ["log"])

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Failed to detect VCS" in result.output


# =============================================================================
# Test: Display formatting
# =============================================================================


class TestDisplayFormatting:
    """Tests for operation display formatting."""

    def test_operation_id_truncation(self, runner, tmp_path):
        """Long operation IDs should be truncated in display."""
        from specify_cli.cli.commands import ops as ops_module

        mock_vcs = MagicMock()
        mock_vcs.backend = VCSBackend.GIT
        mock_vcs.capabilities = GIT_CAPABILITIES

        # Create operation with long ID
        long_id = "a" * 40  # 40 char SHA
        ops = [
            OperationInfo(
                operation_id=long_id,
                description="Test operation",
                timestamp=datetime.now(timezone.utc),
                heads=["abc123"],
                working_copy_commit="abc123",
                is_undoable=False,
                parent_operation=None,
            )
        ]

        with patch.object(ops_module, "get_vcs", return_value=mock_vcs):
            with patch(
                "specify_cli.core.vcs.git.git_get_reflog",
                return_value=ops,
            ):
                with patch("os.getcwd", return_value=str(tmp_path)):
                    result = runner.invoke(ops_module.app, ["log"])

        assert result.exit_code == 0
        # Full 40-char ID should not appear in table (truncated to 12)
        assert long_id not in result.output
        # But truncated version should
        assert long_id[:12] in result.output

    @pytest.mark.xfail(reason="jj not installed in CI environment")
    def test_jj_shows_undoable_column(self, runner, tmp_path):
        """jj backend should show Undoable column."""
        from specify_cli.cli.commands import ops as ops_module

        mock_vcs = MagicMock()
        mock_vcs.backend = VCSBackend.JUJUTSU
        mock_vcs.capabilities = JJ_CAPABILITIES

        ops = [
            OperationInfo(
                operation_id="abc123",
                description="Test operation",
                timestamp=datetime.now(timezone.utc),
                heads=["abc123"],
                working_copy_commit="abc123",
                is_undoable=True,
                parent_operation=None,
            )
        ]

        with patch.object(ops_module, "get_vcs", return_value=mock_vcs):
            with patch(
                "specify_cli.core.vcs.jujutsu.jj_get_operation_log",
                return_value=ops,
            ):
                with patch("os.getcwd", return_value=str(tmp_path)):
                    result = runner.invoke(ops_module.app, ["log"])

        assert result.exit_code == 0
        assert "Undoable" in result.output

    def test_description_truncation(self, runner, tmp_path):
        """Long descriptions should be truncated."""
        from specify_cli.cli.commands import ops as ops_module

        mock_vcs = MagicMock()
        mock_vcs.backend = VCSBackend.GIT
        mock_vcs.capabilities = GIT_CAPABILITIES

        long_desc = "A" * 100  # 100 char description
        ops = [
            OperationInfo(
                operation_id="abc123",
                description=long_desc,
                timestamp=datetime.now(timezone.utc),
                heads=["abc123"],
                working_copy_commit="abc123",
                is_undoable=False,
                parent_operation=None,
            )
        ]

        with patch.object(ops_module, "get_vcs", return_value=mock_vcs):
            with patch(
                "specify_cli.core.vcs.git.git_get_reflog",
                return_value=ops,
            ):
                with patch("os.getcwd", return_value=str(tmp_path)):
                    result = runner.invoke(ops_module.app, ["log"])

        assert result.exit_code == 0
        # Full description should not appear (truncated at 60)
        assert long_desc not in result.output
        # But truncated version with ellipsis should (unicode or ascii)
        assert "..." in result.output or "…" in result.output


# =============================================================================
# Integration tests (using real git)
# =============================================================================


class TestIntegration:
    """Integration tests using real git repository.

    Note: These tests use mocking to force git backend because the auto-detection
    may prefer jj if it's installed. For true integration tests, we mock just
    the backend detection.
    """

    def test_real_git_reflog(self, runner, git_repo):
        """Test ops log with real git repository."""
        from specify_cli.cli.commands import ops as ops_module
        from specify_cli.core.vcs.git import GitVCS

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(git_repo)
            # Force git backend for this test
            with patch.object(ops_module, "get_vcs", return_value=GitVCS()):
                result = runner.invoke(ops_module.app, ["log"])
        finally:
            os.chdir(original_dir)

        assert result.exit_code == 0
        assert "git reflog" in result.output
        # Should show Initial commit or similar
        assert "commit" in result.output.lower() or "HEAD" in result.output

    def test_real_git_undo_fails(self, runner, git_repo):
        """Test that undo fails for git with helpful message."""
        from specify_cli.cli.commands import ops as ops_module
        from specify_cli.core.vcs.git import GitVCS

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(git_repo)
            # Force git backend for this test
            with patch.object(ops_module, "get_vcs", return_value=GitVCS()):
                result = runner.invoke(ops_module.app, ["undo"])
        finally:
            os.chdir(original_dir)

        assert result.exit_code == 1
        assert "Undo not supported" in result.output
        # Should suggest alternatives
        assert "git reset" in result.output or "git revert" in result.output

    def test_real_git_restore_fails(self, runner, git_repo):
        """Test that restore fails for git with helpful message."""
        from specify_cli.cli.commands import ops as ops_module
        from specify_cli.core.vcs.git import GitVCS

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(git_repo)
            # Force git backend for this test
            with patch.object(ops_module, "get_vcs", return_value=GitVCS()):
                result = runner.invoke(ops_module.app, ["restore", "abc123"])
        finally:
            os.chdir(original_dir)

        assert result.exit_code == 1
        assert "Restore not supported" in result.output
