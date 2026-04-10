"""Tests for `spec-kitty sync doctor` command (issue #306)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from specify_cli.cli.commands.sync import format_queue_health
from specify_cli.sync.queue import DEFAULT_MAX_QUEUE_SIZE, QueueStats

pytestmark = pytest.mark.fast


def _make_fake_session(
    *,
    access_expires_at: datetime,
    refresh_expires_at: datetime | None,
    email: str = "testuser@example.com",
    team_id: str = "test-team",
) -> MagicMock:
    """Build a MagicMock that quacks like a StoredSession for sync doctor."""
    session = MagicMock()
    session.access_token_expires_at = access_expires_at
    session.refresh_token_expires_at = refresh_expires_at
    session.email = email
    session.name = email
    session.default_team_id = team_id
    team = MagicMock()
    team.id = team_id
    session.teams = [team]
    return session


class TestFormatQueueHealthCapacity:
    """format_queue_health now shows capacity and percentage."""

    def test_shows_capacity_and_percentage(self):
        stats = QueueStats(
            total_queued=80_000,
            max_queue_size=DEFAULT_MAX_QUEUE_SIZE,
            total_retried=0,
            retry_distribution={"0 retries": 80_000},
            top_event_types=[("Test", 80_000)],
        )
        buf = StringIO()
        test_console = Console(file=buf, force_terminal=False, width=120)
        format_queue_health(stats, test_console)
        output = buf.getvalue()

        assert "80,000" in output
        assert "100,000" in output
        assert "80%" in output

    def test_full_queue_shows_100_percent(self):
        stats = QueueStats(
            total_queued=DEFAULT_MAX_QUEUE_SIZE,
            max_queue_size=DEFAULT_MAX_QUEUE_SIZE,
            total_retried=0,
            retry_distribution={"0 retries": DEFAULT_MAX_QUEUE_SIZE},
            top_event_types=[("Test", DEFAULT_MAX_QUEUE_SIZE)],
        )
        buf = StringIO()
        test_console = Console(file=buf, force_terminal=False, width=120)
        format_queue_health(stats, test_console)
        output = buf.getvalue()

        assert "100%" in output


class TestDoctorCommand:
    """Smoke tests for the doctor subcommand output."""

    @patch("specify_cli.sync.queue.OfflineQueue")
    @patch("specify_cli.cli.commands.sync._check_server_connection")
    @patch("specify_cli.auth.get_token_manager")
    @patch("specify_cli.sync.config.SyncConfig")
    def test_doctor_healthy(self, mock_config_cls, mock_get_tm, mock_check, mock_queue_cls, capsys):
        """Doctor reports no issues when queue is empty, auth is valid, server reachable."""
        mock_queue = MagicMock()
        mock_queue.get_queue_stats.return_value = QueueStats(total_queued=0)
        mock_queue.db_path = "/tmp/test.db"
        mock_queue_cls.return_value = mock_queue

        mock_config = MagicMock()
        mock_config.get_server_url.return_value = "https://test.example.com"
        mock_config_cls.return_value = mock_config

        now = datetime.now(timezone.utc)
        session = _make_fake_session(
            access_expires_at=now + timedelta(days=30),
            refresh_expires_at=now + timedelta(days=30),
        )
        fake_tm = MagicMock()
        fake_tm.get_current_session.return_value = session
        mock_get_tm.return_value = fake_tm

        mock_check.return_value = ("[green]Connected[/green]", "Server reachable.")

        from specify_cli.cli.commands.sync import doctor
        doctor()

        captured = capsys.readouterr()
        assert "No issues detected" in captured.out

    @patch("specify_cli.sync.queue.OfflineQueue")
    @patch("specify_cli.cli.commands.sync._check_server_connection")
    @patch("specify_cli.auth.get_token_manager")
    @patch("specify_cli.sync.config.SyncConfig")
    def test_doctor_full_queue_expired_auth(self, mock_config_cls, mock_get_tm, mock_check, mock_queue_cls, capsys):
        """Doctor reports issues when queue is full and auth is expired."""
        mock_queue = MagicMock()
        mock_queue.get_queue_stats.return_value = QueueStats(
            total_queued=DEFAULT_MAX_QUEUE_SIZE,
            max_queue_size=DEFAULT_MAX_QUEUE_SIZE,
            top_event_types=[("MissionDossierArtifactIndexed", 79_000)],
        )
        mock_queue.db_path = "/tmp/test.db"
        mock_queue_cls.return_value = mock_queue

        mock_config = MagicMock()
        mock_config.get_server_url.return_value = "https://test.example.com"
        mock_config_cls.return_value = mock_config

        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        session = _make_fake_session(
            access_expires_at=past,
            refresh_expires_at=past,
        )
        fake_tm = MagicMock()
        fake_tm.get_current_session.return_value = session
        mock_get_tm.return_value = fake_tm

        mock_check.return_value = ("[red]Unreachable[/red]", "Connection refused.")

        from specify_cli.cli.commands.sync import doctor
        doctor()

        captured = capsys.readouterr()
        assert "Issues found" in captured.out
        assert "FULL" in captured.out or "evicted" in captured.out.lower()
        assert "spec-kitty auth login" in captured.out
