"""Tests for the sync command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from specify_cli.cli.commands.sync import (
    _detect_workspace_context,
    _display_changes_integrated,
    _display_conflicts,
    _git_repair,
    _jj_repair,
    sync_workspace,
)
from specify_cli.core.vcs import (
    ChangeInfo,
    ConflictInfo,
    ConflictType,
    SyncResult,
    SyncStatus,
    VCSBackend,
)


class TestDetectWorkspaceContext:
    """Tests for workspace context detection."""

    def test_detect_from_worktree_path(self, tmp_path):
        """Test detection from .worktrees directory path."""
        # Simulate being in a worktree
        worktree = tmp_path / ".worktrees" / "010-test-feature-WP01"
        worktree.mkdir(parents=True)

        with patch("pathlib.Path.cwd", return_value=worktree):
            workspace_path, feature_slug = _detect_workspace_context()

            assert workspace_path == worktree
            assert feature_slug == "010-test-feature"

    def test_detect_from_git_branch(self, tmp_path):
        """Test detection from git branch name."""
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="015-vcs-integration-WP03\n"
                )

                workspace_path, feature_slug = _detect_workspace_context()

                assert workspace_path == tmp_path
                assert feature_slug == "015-vcs-integration"

    def test_not_in_workspace(self, tmp_path):
        """Test when not in a workspace."""
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="main\n")

                workspace_path, feature_slug = _detect_workspace_context()

                assert workspace_path == tmp_path
                assert feature_slug is None


class TestDisplayFunctions:
    """Tests for display helper functions."""

    def test_display_changes_integrated_empty(self, capsys):
        """Test display with no changes."""
        _display_changes_integrated([])
        # Should not print anything
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_display_changes_integrated_truncates(self, capsys):
        """Test display truncates long lists."""
        from datetime import datetime

        changes = [
            ChangeInfo(
                change_id=None,
                commit_id=f"abc{i:04d}",
                message=f"Change {i}",
                message_full=f"Change {i}",
                author="Test",
                author_email="test@example.com",
                timestamp=datetime.now(),
                parents=[],
                is_merge=False,
                is_conflicted=False,
                is_empty=False,
            )
            for i in range(10)
        ]

        _display_changes_integrated(changes)
        captured = capsys.readouterr()

        # Should show "and 5 more"
        assert "5 more" in captured.out

    def test_display_conflicts(self, capsys):
        """Test conflict display."""
        conflicts = [
            ConflictInfo(
                file_path=Path("src/test.py"),
                conflict_type=ConflictType.CONTENT,
                line_ranges=[(10, 20), (30, 40)],
                sides=2,
                is_resolved=False,
                our_content=None,
                their_content=None,
                base_content=None,
            )
        ]

        _display_conflicts(conflicts)
        captured = capsys.readouterr()

        assert "src/test.py" in captured.out
        assert "content" in captured.out
        assert "To resolve conflicts" in captured.out


class TestRepairFunctions:
    """Tests for repair functions."""

    def test_git_repair_success(self, tmp_path):
        """Test successful git repair."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = _git_repair(tmp_path)

            assert result is True

    def test_git_repair_failure(self, tmp_path):
        """Test failed git repair."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            result = _git_repair(tmp_path)

            assert result is False

    def test_jj_repair_success(self, tmp_path):
        """Test successful jj repair."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = _jj_repair(tmp_path)

            assert result is True

    def test_jj_repair_fallback_to_update_stale(self, tmp_path):
        """Test jj repair falls back to update-stale."""
        with patch("subprocess.run") as mock_run:
            # First call (jj undo) fails, second (update-stale) succeeds
            mock_run.side_effect = [
                MagicMock(returncode=1),  # undo fails
                MagicMock(returncode=0),  # update-stale succeeds
            ]

            result = _jj_repair(tmp_path)

            assert result is True
            assert mock_run.call_count == 2


@pytest.mark.parametrize("backend", [
    "git",
    pytest.param("jj", marks=pytest.mark.jj),
])
class TestSyncCommand:
    """Tests for sync command."""

    def test_sync_up_to_date(self, tmp_path, backend):
        """Test sync when already up to date."""
        # Setup worktree path
        worktree = tmp_path / ".worktrees" / "010-feature-WP01"
        worktree.mkdir(parents=True)

        with patch("pathlib.Path.cwd", return_value=worktree):
            with patch("specify_cli.cli.commands.sync.get_vcs") as mock_get_vcs:
                mock_vcs = MagicMock()
                mock_vcs.backend = VCSBackend(backend)
                mock_vcs.sync_workspace.return_value = SyncResult(
                    status=SyncStatus.UP_TO_DATE,
                    conflicts=[],
                    files_updated=0,
                    files_added=0,
                    files_deleted=0,
                    changes_integrated=[],
                    message="Already up to date",
                )
                mock_get_vcs.return_value = mock_vcs

                # Run sync - should not raise (explicitly pass repair=False)
                sync_workspace(repair=False)

                mock_vcs.sync_workspace.assert_called_once()

    def test_sync_with_changes(self, tmp_path, backend):
        """Test sync with changes to integrate."""
        worktree = tmp_path / ".worktrees" / "010-feature-WP01"
        worktree.mkdir(parents=True)

        with patch("pathlib.Path.cwd", return_value=worktree):
            with patch("specify_cli.cli.commands.sync.get_vcs") as mock_get_vcs:
                mock_vcs = MagicMock()
                mock_vcs.backend = VCSBackend(backend)
                mock_vcs.sync_workspace.return_value = SyncResult(
                    status=SyncStatus.SYNCED,
                    conflicts=[],
                    files_updated=5,
                    files_added=2,
                    files_deleted=1,
                    changes_integrated=[],
                    message="Synced successfully",
                )
                mock_get_vcs.return_value = mock_vcs

                sync_workspace(repair=False)

                mock_vcs.sync_workspace.assert_called_once()


class TestSyncWithConflicts:
    """Tests for conflict handling in sync."""

    @pytest.mark.jj
    def test_sync_with_conflicts_jj_succeeds(self, tmp_path):
        """Test jj sync succeeds even with conflicts."""
        worktree = tmp_path / ".worktrees" / "010-feature-WP01"
        worktree.mkdir(parents=True)

        with patch("pathlib.Path.cwd", return_value=worktree):
            with patch("specify_cli.cli.commands.sync.get_vcs") as mock_get_vcs:
                mock_vcs = MagicMock()
                mock_vcs.backend = VCSBackend.JUJUTSU
                mock_vcs.sync_workspace.return_value = SyncResult(
                    status=SyncStatus.CONFLICTS,
                    conflicts=[
                        ConflictInfo(
                            file_path=Path("src/test.py"),
                            conflict_type=ConflictType.CONTENT,
                            line_ranges=[(10, 20)],
                            sides=2,
                            is_resolved=False,
                            our_content=None,
                            their_content=None,
                            base_content=None,
                        )
                    ],
                    files_updated=3,
                    files_added=0,
                    files_deleted=0,
                    changes_integrated=[],
                    message="Synced with conflicts",
                )
                mock_get_vcs.return_value = mock_vcs

                # jj: sync completes without raising
                sync_workspace(repair=False)

                mock_vcs.sync_workspace.assert_called_once()

    def test_sync_with_conflicts_git_reports(self, tmp_path):
        """Test git sync reports conflicts (may fail)."""
        worktree = tmp_path / ".worktrees" / "010-feature-WP01"
        worktree.mkdir(parents=True)

        with patch("pathlib.Path.cwd", return_value=worktree):
            with patch("specify_cli.cli.commands.sync.get_vcs") as mock_get_vcs:
                mock_vcs = MagicMock()
                mock_vcs.backend = VCSBackend.GIT
                mock_vcs.sync_workspace.return_value = SyncResult(
                    status=SyncStatus.FAILED,
                    conflicts=[
                        ConflictInfo(
                            file_path=Path("src/test.py"),
                            conflict_type=ConflictType.CONTENT,
                            line_ranges=[(10, 20)],
                            sides=2,
                            is_resolved=False,
                            our_content=None,
                            their_content=None,
                            base_content=None,
                        )
                    ],
                    files_updated=0,
                    files_added=0,
                    files_deleted=0,
                    changes_integrated=[],
                    message="Rebase failed due to conflicts",
                )
                mock_get_vcs.return_value = mock_vcs

                # git: sync fails with exit code
                with pytest.raises(typer.Exit) as exc:
                    sync_workspace(repair=False)

                assert exc.value.exit_code == 1


class TestSyncRepair:
    """Tests for --repair flag."""

    @pytest.mark.parametrize("backend", [
        "git",
        pytest.param("jj", marks=pytest.mark.jj),
    ])
    def test_repair_success(self, tmp_path, backend):
        """Test successful repair."""
        worktree = tmp_path / ".worktrees" / "010-feature-WP01"
        worktree.mkdir(parents=True)

        with patch("pathlib.Path.cwd", return_value=worktree):
            with patch("specify_cli.cli.commands.sync.get_vcs") as mock_get_vcs:
                mock_vcs = MagicMock()
                mock_vcs.backend = VCSBackend(backend)
                mock_get_vcs.return_value = mock_vcs

                repair_func = "_jj_repair" if backend == "jj" else "_git_repair"
                with patch(f"specify_cli.cli.commands.sync.{repair_func}") as mock_repair:
                    mock_repair.return_value = True

                    sync_workspace(repair=True)

                    mock_repair.assert_called_once()

    @pytest.mark.parametrize("backend", [
        "git",
        pytest.param("jj", marks=pytest.mark.jj),
    ])
    def test_repair_failure(self, tmp_path, backend):
        """Test failed repair."""
        worktree = tmp_path / ".worktrees" / "010-feature-WP01"
        worktree.mkdir(parents=True)

        with patch("pathlib.Path.cwd", return_value=worktree):
            with patch("specify_cli.cli.commands.sync.get_vcs") as mock_get_vcs:
                mock_vcs = MagicMock()
                mock_vcs.backend = VCSBackend(backend)
                mock_get_vcs.return_value = mock_vcs

                repair_func = "_jj_repair" if backend == "jj" else "_git_repair"
                with patch(f"specify_cli.cli.commands.sync.{repair_func}") as mock_repair:
                    mock_repair.return_value = False

                    with pytest.raises(typer.Exit) as exc:
                        sync_workspace(repair=True)

                    assert exc.value.exit_code == 1


class TestSyncNotInWorkspace:
    """Tests for running sync outside a workspace."""

    def test_sync_not_in_workspace_exits(self, tmp_path):
        """Test sync exits with error when not in workspace."""
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="main\n")

                with pytest.raises(typer.Exit) as exc:
                    sync_workspace(repair=False)

                assert exc.value.exit_code == 1
