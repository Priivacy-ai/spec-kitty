"""Tests for `spec-kitty sync doctor` command (issue #306)."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.fast

from rich.console import Console

from specify_cli.cli.commands.sync import format_queue_health
from specify_cli.sync.queue import DEFAULT_MAX_QUEUE_SIZE, QueueStats


class TestFormatQueueHealthCapacity:
    """format_queue_health now shows capacity and percentage."""

    def test_shows_capacity_and_percentage(self):
        stats = QueueStats(
            total_queued=8000,
            max_queue_size=10000,
            total_retried=0,
            retry_distribution={"0 retries": 8000},
            top_event_types=[("Test", 8000)],
        )
        buf = StringIO()
        test_console = Console(file=buf, force_terminal=False, width=120)
        format_queue_health(stats, test_console)
        output = buf.getvalue()

        assert "8,000" in output
        assert "10,000" in output
        assert "80%" in output

    def test_full_queue_shows_100_percent(self):
        stats = QueueStats(
            total_queued=10000,
            max_queue_size=10000,
            total_retried=0,
            retry_distribution={"0 retries": 10000},
            top_event_types=[("Test", 10000)],
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
    @patch("specify_cli.sync.auth.CredentialStore")
    @patch("specify_cli.sync.config.SyncConfig")
    def test_doctor_healthy(self, mock_config_cls, mock_store_cls, mock_check, mock_queue_cls, capsys):
        """Doctor reports no issues when queue is empty, auth is valid, server reachable."""
        mock_queue = MagicMock()
        mock_queue.get_queue_stats.return_value = QueueStats(total_queued=0)
        mock_queue.db_path = "/tmp/test.db"
        mock_queue_cls.return_value = mock_queue

        mock_config = MagicMock()
        mock_config.get_server_url.return_value = "https://test.example.com"
        mock_config_cls.return_value = mock_config

        mock_store = MagicMock()
        mock_store.exists.return_value = True
        mock_store.get_token_expiry_info.return_value = {
            "access_expires_at": "2099-01-01T00:00:00+00:00",
            "refresh_expires_at": "2099-01-01T00:00:00+00:00",
        }
        mock_store.get_username.return_value = "testuser"
        mock_store.get_team_slug.return_value = "test-team"
        mock_store_cls.return_value = mock_store

        mock_check.return_value = ("[green]Connected[/green]", "Server reachable.")

        from specify_cli.cli.commands.sync import doctor
        doctor()

        captured = capsys.readouterr()
        assert "No issues detected" in captured.out

    @patch("specify_cli.sync.queue.OfflineQueue")
    @patch("specify_cli.cli.commands.sync._check_server_connection")
    @patch("specify_cli.sync.auth.CredentialStore")
    @patch("specify_cli.sync.config.SyncConfig")
    def test_doctor_full_queue_expired_auth(self, mock_config_cls, mock_store_cls, mock_check, mock_queue_cls, capsys):
        """Doctor reports issues when queue is full and auth is expired."""
        mock_queue = MagicMock()
        mock_queue.get_queue_stats.return_value = QueueStats(
            total_queued=10000,
            max_queue_size=10000,
            top_event_types=[("MissionDossierArtifactIndexed", 7900)],
        )
        mock_queue.db_path = "/tmp/test.db"
        mock_queue_cls.return_value = mock_queue

        mock_config = MagicMock()
        mock_config.get_server_url.return_value = "https://test.example.com"
        mock_config_cls.return_value = mock_config

        mock_store = MagicMock()
        mock_store.exists.return_value = True
        mock_store.get_token_expiry_info.return_value = {
            "access_expires_at": "2020-01-01T00:00:00+00:00",
            "refresh_expires_at": "2020-01-01T00:00:00+00:00",
        }
        mock_store.get_username.return_value = "testuser"
        mock_store.get_team_slug.return_value = "test-team"
        mock_store_cls.return_value = mock_store

        mock_check.return_value = ("[red]Unreachable[/red]", "Connection refused.")

        from specify_cli.cli.commands.sync import doctor
        doctor()

        captured = capsys.readouterr()
        assert "Issues found" in captured.out
        assert "FULL" in captured.out or "evicted" in captured.out.lower()
        assert "spec-kitty auth login" in captured.out
