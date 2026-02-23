"""Tests for the sync command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.cli.commands.sync import (
    _detect_workspace_context,
    _display_changes_integrated,
    _display_conflicts,
    _git_repair,
    _jj_repair,
    app as sync_app,
    sync_server,
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
from specify_cli.sync.feature_flags import SAAS_SYNC_ENV_VAR


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


class TestSyncGroupHelp:
    """Tests for sync command group help behavior."""

    def test_sync_without_subcommand_shows_help(self):
        """Invoking sync with no args should print help, not error."""
        runner = CliRunner()
        result = runner.invoke(sync_app, [])

        # Typer may exit with code 2 for "missing command" while still
        # rendering the command group's help text. We care about UX output.
        assert "Usage:" in result.output
        assert "Synchronization commands" in result.output


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


class TestSyncServerCommand:
    """Tests for sync server URL command."""

    def test_show_server_url(self, capsys):
        """Shows configured server URL and config file path."""
        mock_config = MagicMock()
        mock_config.get_server_url.return_value = "https://spec-kitty-dev.fly.dev"
        mock_config.config_file = Path("/tmp/config.toml")

        with patch("specify_cli.sync.config.SyncConfig", return_value=mock_config):
            sync_server(url=None)

        captured = capsys.readouterr()
        assert "https://spec-kitty-dev.fly.dev" in captured.out
        assert "/tmp/config.toml" in captured.out

    def test_set_server_url_normalizes_trailing_slash(self):
        """Setting URL strips trailing slash before persisting."""
        mock_config = MagicMock()
        with patch("specify_cli.sync.config.SyncConfig", return_value=mock_config):
            sync_server(url="https://spec-kitty-dev.fly.dev/")

        mock_config.set_server_url.assert_called_once_with(
            "https://spec-kitty-dev.fly.dev"
        )

    def test_set_server_url_rejects_non_https(self):
        """Non-HTTPS URL is rejected."""
        mock_config = MagicMock()
        with patch("specify_cli.sync.config.SyncConfig", return_value=mock_config):
            with pytest.raises(typer.Exit) as exc:
                sync_server(url="http://spec-kitty-dev.fly.dev")
        assert exc.value.exit_code == 1
        mock_config.set_server_url.assert_not_called()


class TestSyncNowExitCodes:
    """Tests for sync now --strict/--no-strict exit semantics."""

    def _make_service(self, queue_size: int, result: MagicMock) -> MagicMock:
        """Build a mock sync service with given queue size and result."""
        svc = MagicMock()
        svc.queue.size.return_value = queue_size
        svc.sync_now.return_value = result
        return svc

    def _make_result(
        self,
        synced: int = 0,
        duplicate: int = 0,
        errors: int = 0,
    ) -> MagicMock:
        """Build a mock BatchSyncResult."""
        r = MagicMock()
        r.synced_count = synced
        r.duplicate_count = duplicate
        r.error_count = errors
        r.failed_results = [MagicMock()] * errors if errors else []
        return r

    def test_strict_exits_1_on_errors(self):
        """Default strict mode exits 1 when error_count > 0."""
        result = self._make_result(synced=2, errors=1)
        svc = self._make_service(queue_size=3, result=result)

        runner = CliRunner()
        with patch("specify_cli.sync.background.get_sync_service", return_value=svc):
            with patch("specify_cli.sync.batch.format_sync_summary", return_value="summary"):
                with patch("specify_cli.sync.batch.write_failure_report"):
                    res = runner.invoke(sync_app, ["now"])
        assert res.exit_code == 1

    def test_now_returns_0_when_saas_feature_disabled(self, monkeypatch):
        """sync now should no-op safely when SaaS flag is disabled."""
        monkeypatch.delenv(SAAS_SYNC_ENV_VAR, raising=False)

        runner = CliRunner()
        with patch("specify_cli.sync.background.get_sync_service") as get_service:
            res = runner.invoke(sync_app, ["now"])

        assert res.exit_code == 0
        assert "disabled by feature flag" in res.output.lower()
        get_service.assert_not_called()

    def test_strict_exits_0_on_success(self):
        """Strict mode exits 0 when all events sync successfully."""
        result = self._make_result(synced=3)
        svc = self._make_service(queue_size=3, result=result)

        runner = CliRunner()
        with patch("specify_cli.sync.background.get_sync_service", return_value=svc):
            with patch("specify_cli.sync.batch.format_sync_summary", return_value="summary"):
                res = runner.invoke(sync_app, ["now"])
        assert res.exit_code == 0

    def test_no_strict_exits_0_even_with_errors(self):
        """--no-strict exits 0 regardless of errors."""
        result = self._make_result(synced=1, errors=2)
        svc = self._make_service(queue_size=3, result=result)

        runner = CliRunner()
        with patch("specify_cli.sync.background.get_sync_service", return_value=svc):
            with patch("specify_cli.sync.batch.format_sync_summary", return_value="summary"):
                with patch("specify_cli.sync.batch.write_failure_report"):
                    res = runner.invoke(sync_app, ["now", "--no-strict"])
        assert res.exit_code == 0

    def test_empty_queue_exits_0(self):
        """Empty queue always exits 0 (nothing to do)."""
        svc = self._make_service(queue_size=0, result=MagicMock())

        runner = CliRunner()
        with patch("specify_cli.sync.background.get_sync_service", return_value=svc):
            res = runner.invoke(sync_app, ["now"])
        assert res.exit_code == 0

    def test_strict_with_report_still_exits_1(self, tmp_path):
        """Strict exits 1 and still writes report when errors present."""
        result = self._make_result(synced=1, errors=1)
        svc = self._make_service(queue_size=2, result=result)

        runner = CliRunner()
        report_path = tmp_path / "failures.json"
        with patch("specify_cli.sync.background.get_sync_service", return_value=svc):
            with patch("specify_cli.sync.batch.format_sync_summary", return_value="summary"):
                with patch("specify_cli.sync.batch.write_failure_report") as write_mock:
                    res = runner.invoke(sync_app, ["now", "--report", str(report_path)])
        assert res.exit_code == 1
        write_mock.assert_called_once()

    def test_strict_exits_1_on_auth_missing(self):
        """Strict exits 1 when queue non-empty but all-zero result (auth missing)."""
        result = self._make_result(synced=0, duplicate=0, errors=0)
        svc = self._make_service(queue_size=5, result=result)

        runner = CliRunner()
        with patch("specify_cli.sync.background.get_sync_service", return_value=svc):
            with patch("specify_cli.sync.batch.format_sync_summary", return_value="summary"):
                res = runner.invoke(sync_app, ["now"])
        assert res.exit_code == 1
        assert "not authenticated" in res.output
