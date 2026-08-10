"""Tests for `spec-kitty sync doctor` command (issue #306)."""

from __future__ import annotations

from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from kernel.clock import UTC, datetime, now_utc, timedelta
from specify_cli.cli.commands.sync import format_queue_health
from specify_cli.sync.config import ConfigRead
from specify_cli.sync.queue import DEFAULT_MAX_QUEUE_SIZE, QueueStats

pytestmark = pytest.mark.fast


@pytest.fixture(autouse=True)
def _isolated_runtime_root(tmp_path, monkeypatch):
    """Keep these tests off the developer's / runner's real spec-kitty state.

    Every other input to ``doctor`` in this file is mocked, but #3030 T021 added a
    per-project journal section that opens the event journal for the CURRENT
    producer scope. Without this fixture, ``test_doctor_healthy``'s verdict depends
    on what happens to be in the journal of the machine running the suite. An
    isolated home makes that journal genuinely absent, which the section reports as
    such without raising an issue.

    Precisely which contents would redden it is narrower than it looks, and the
    first version of this docstring got it wrong: it is NOT "non-consented events".
    ``@patch("specify_cli.sync.config.SyncConfig")`` reaches the lazy import inside
    ``consent.py``'s resolver, so every project resolves to a truthy ``MagicMock``
    and reads as consented. Only unresolved-identity rows, or a report that fails to
    reconcile, can redden this test. The fixture is still load-bearing — it is what
    keeps that from depending on the host.

    Not a mirror of a production fail-open: ``get_repository_sync_enabled`` guards
    with ``isinstance(enabled, bool)``, so only a mocked ``SyncConfig`` behaves this
    way.
    """
    home = tmp_path / "spec-kitty-home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.setenv("HOME", str(tmp_path / "user-home"))
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    from specify_cli.event_journal.journal import reset_journal_cache

    reset_journal_cache()


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

    @patch("specify_cli.sync.owner.list_orphan_records", return_value=[])
    @patch("specify_cli.sync.daemon.scan_sync_daemons")
    @patch("specify_cli.sync.diagnose.diagnose_body_queue")
    @patch("specify_cli.sync.body_queue.OfflineBodyUploadQueue")
    @patch("specify_cli.sync.queue.OfflineQueue")
    @patch("specify_cli.cli.commands.sync._check_server_connection")
    @patch("specify_cli.auth.get_token_manager")
    @patch("specify_cli.sync.config.SyncConfig")
    def test_doctor_healthy(
        self,
        mock_config_cls,
        mock_get_tm,
        mock_check,
        mock_queue_cls,
        mock_body_queue_cls,
        mock_body_diag,
        mock_scan_daemons,
        _mock_orphan_records,
        capsys,
    ):
        """Doctor reports no issues when queue is empty, auth is valid, server reachable."""
        mock_scan_daemons.return_value = SimpleNamespace(
            orphan_count=0,
            orphan_processes=[],
        )
        mock_queue = MagicMock()
        mock_queue.get_queue_stats.return_value = QueueStats(total_queued=0)
        mock_queue.db_path = "/nonexistent/test.db"
        mock_queue_cls.return_value = mock_queue
        mock_body_queue_cls.return_value = MagicMock()
        mock_body_diag.return_value = {
            "body_queue": {
                "total_tasks": 0,
                "ready_to_send": 0,
                "in_backoff": 0,
                "max_retry_count": 0,
                "oldest_task_age_seconds": None,
                "retry_distribution": {},
                "recorded_failure_count": 0,
                "recent_failures": [],
            }
        }

        mock_config = MagicMock()
        mock_config.get_server_url.return_value = "https://test.example.com"
        # Doctor now reads the resolved runtime target for the Server URL row (#2146).
        mock_config.resolve_runtime_target.return_value.resolved_server_url = (
            "https://test.example.com"
        )
        # #3030 FR-020: doctor now asks whether the consent index is READABLE, via
        # `SyncConfig().read()`. A bare MagicMock answers that with a truthy `.fault`
        # -- i.e. "unreadable" -- so the healthy answer has to be stated here, or the
        # command reports a consent fault this test's own stub invented.
        mock_config.read.return_value = ConfigRead(data={}, fault=None)
        mock_config_cls.return_value = mock_config

        now = now_utc()
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

    @patch("specify_cli.sync.owner.list_orphan_records", return_value=[])
    @patch("specify_cli.sync.daemon.scan_sync_daemons")
    @patch("specify_cli.sync.diagnose.diagnose_body_queue")
    @patch("specify_cli.sync.body_queue.OfflineBodyUploadQueue")
    @patch("specify_cli.sync.queue.OfflineQueue")
    @patch("specify_cli.cli.commands.sync._check_server_connection")
    @patch("specify_cli.auth.get_token_manager")
    @patch("specify_cli.sync.config.SyncConfig")
    def test_doctor_full_queue_expired_auth(
        self,
        mock_config_cls,
        mock_get_tm,
        mock_check,
        mock_queue_cls,
        mock_body_queue_cls,
        mock_body_diag,
        mock_scan_daemons,
        _mock_orphan_records,
        capsys,
    ):
        """Doctor reports issues when queue is full and auth is expired."""
        mock_scan_daemons.return_value = SimpleNamespace(
            orphan_count=0,
            orphan_processes=[],
        )
        mock_queue = MagicMock()
        mock_queue.get_queue_stats.return_value = QueueStats(
            total_queued=DEFAULT_MAX_QUEUE_SIZE,
            max_queue_size=DEFAULT_MAX_QUEUE_SIZE,
            top_event_types=[("MissionDossierArtifactIndexed", 79_000)],
        )
        mock_queue.db_path = "/nonexistent/test.db"
        mock_queue_cls.return_value = mock_queue
        mock_body_queue_cls.return_value = MagicMock()
        mock_body_diag.return_value = {
            "body_queue": {
                "total_tasks": 1,
                "ready_to_send": 0,
                "in_backoff": 1,
                "max_retry_count": 0,
                "oldest_task_age_seconds": None,
                "retry_distribution": {},
                "recorded_failure_count": 1,
                "recent_failures": [
                    {
                        "artifact_path": "research/evidence-log.csv",
                        "failure_reason": "bad_request: content_body: This field may not be blank.",
                        "failure_count": 3,
                        "mission_slug": "047-feat",
                        "target_branch": "main",
                        "last_failed_at": 0.0,
                    }
                ],
            }
        }

        mock_config = MagicMock()
        mock_config.get_server_url.return_value = "https://test.example.com"
        # Doctor now reads the resolved runtime target for the Server URL row (#2146).
        mock_config.resolve_runtime_target.return_value.resolved_server_url = (
            "https://test.example.com"
        )
        # #3030 FR-020: doctor now asks whether the consent index is READABLE, via
        # `SyncConfig().read()`. A bare MagicMock answers that with a truthy `.fault`
        # -- i.e. "unreadable" -- so the healthy answer has to be stated here, or the
        # command reports a consent fault this test's own stub invented.
        mock_config.read.return_value = ConfigRead(data={}, fault=None)
        mock_config_cls.return_value = mock_config

        past = datetime(2020, 1, 1, tzinfo=UTC)
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
        assert "Recent Body Upload Failures" in captured.out
        assert "research/evidence-log.csv" in captured.out
