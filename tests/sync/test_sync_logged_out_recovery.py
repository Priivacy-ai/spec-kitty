"""Integration tests for teamspace-aware recovery on logged-out sync commands.

Covers FR-006 (legacy path byte-identical when no teamspace) and FR-007 (sync
now / sync doctor route through the recovery facade). The status / routes /
share branches are exercised via their own focused tests under
``tests/sync/test_sync_status_check.py`` and ``tests/cli/commands/
test_sync_routes.py``; the cases this file adds are the ones unique to the
new behavior.

These tests invoke the Typer ``app`` via :class:`typer.testing.CliRunner` so
the real argument parsing path is exercised. Token-manager and detector calls
are mocked at the seam.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import _auth_recovery as recovery
from specify_cli.cli.commands._auth_recovery import RecoveryOutcome
from specify_cli.cli.commands.sync import app


pytestmark = pytest.mark.fast


runner = CliRunner()


# ---------------------------------------------------------------------------
# sync now  --  non-interactive structured exit
# ---------------------------------------------------------------------------


def _mock_unauth_sync_now(monkeypatch):
    """Wire `sync now` so it always hits the unauthenticated branch."""
    from specify_cli.sync import feature_flags as ff

    monkeypatch.setattr(ff, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr(
        "specify_cli.cli.commands._teamspace_mission_state_gate.enforce_teamspace_mission_state_ready",
        lambda *a, **k: None,
    )

    fake_service = MagicMock()
    fake_service.queue.size.return_value = 1

    fake_result = MagicMock(
        total_events=0,
        synced_count=0,
        duplicate_count=0,
        error_count=0,
        failed_results=(),
    )
    fake_service.sync_now.return_value = fake_result
    monkeypatch.setattr(
        "specify_cli.sync.background.get_sync_service",
        lambda: fake_service,
    )
    return fake_service


class TestSyncNowRecovery:
    def test_non_interactive_with_teamspace_exits_4(self, monkeypatch):
        _mock_unauth_sync_now(monkeypatch)
        monkeypatch.setattr(
            recovery,
            "detect_logged_out_with_connected_teamspace",
            lambda: "acme-eng",
        )
        monkeypatch.setattr(recovery, "is_interactive", lambda: False)
        result = runner.invoke(app, ["now"])
        assert result.exit_code == 4
        assert (
            "spec-kitty: logged_out_on_connected_teamspace "
            "teamspace=acme-eng command=sync now "
            "action=run-spec-kitty-auth-login"
        ) in result.stderr

    def test_non_interactive_no_teamspace_keeps_legacy_exit_1(self, monkeypatch):
        _mock_unauth_sync_now(monkeypatch)
        monkeypatch.setattr(
            recovery,
            "detect_logged_out_with_connected_teamspace",
            lambda: None,
        )
        result = runner.invoke(app, ["now"])
        assert result.exit_code == 1
        assert "logged_out_on_connected_teamspace" not in result.stderr
        assert "spec-kitty auth login" in result.stdout

    def test_interactive_skip_falls_through_to_legacy_exit_1(self, monkeypatch):
        _mock_unauth_sync_now(monkeypatch)
        monkeypatch.setattr(
            recovery,
            "detect_logged_out_with_connected_teamspace",
            lambda: "acme-eng",
        )
        monkeypatch.setattr(recovery, "is_interactive", lambda: True)
        monkeypatch.setattr(
            recovery,
            "offer_login_recovery",
            lambda **kwargs: RecoveryOutcome.SKIPPED,
        )
        result = runner.invoke(app, ["now"])
        assert result.exit_code == 1
        assert "logged_out_on_connected_teamspace" not in result.stderr

    def test_interactive_login_succeeds_and_exits_zero(self, monkeypatch):
        _mock_unauth_sync_now(monkeypatch)
        monkeypatch.setattr(
            recovery,
            "detect_logged_out_with_connected_teamspace",
            lambda: "acme-eng",
        )
        monkeypatch.setattr(recovery, "is_interactive", lambda: True)
        monkeypatch.setattr(
            recovery,
            "offer_login_recovery",
            lambda **kwargs: RecoveryOutcome.LOGGED_IN,
        )
        result = runner.invoke(app, ["now"])
        assert result.exit_code == 0
        assert "Re-run" in result.stdout
        assert "spec-kitty sync now" in result.stdout


# ---------------------------------------------------------------------------
# sync doctor  --  non-interactive structured exit
# ---------------------------------------------------------------------------


def _mock_doctor_logged_out(monkeypatch):
    """Wire `sync doctor` so the auth issue ('No credentials') fires."""
    from specify_cli.sync.queue import QueueStats

    fake_queue = MagicMock()
    fake_queue.get_queue_stats.return_value = QueueStats(
        total_queued=0,
        max_queue_size=100_000,
    )
    fake_queue.db_path = "/tmp/queue.db"
    monkeypatch.setattr(
        "specify_cli.sync.queue.OfflineQueue",
        lambda: fake_queue,
    )

    fake_body_queue = MagicMock()
    monkeypatch.setattr(
        "specify_cli.sync.body_queue.OfflineBodyUploadQueue",
        lambda **kwargs: fake_body_queue,
    )
    monkeypatch.setattr(
        "specify_cli.sync.diagnose.diagnose_body_queue",
        lambda q: {
            "body_queue": {
                "total_tasks": 0,
                "recorded_failure_count": 0,
                "recent_failures": [],
            }
        },
    )

    fake_tm = MagicMock()
    fake_tm.get_current_session.return_value = None
    monkeypatch.setattr(
        "specify_cli.auth.get_token_manager",
        lambda: fake_tm,
    )

    monkeypatch.setattr(
        "specify_cli.cli.commands.sync._check_server_connection",
        lambda url: ("[red]Unreachable[/red]", "Network down."),
    )


class TestSyncDoctorRecovery:
    def test_non_interactive_with_teamspace_exits_4(self, monkeypatch):
        _mock_doctor_logged_out(monkeypatch)
        monkeypatch.setattr(
            recovery,
            "detect_logged_out_with_connected_teamspace",
            lambda: "acme-eng",
        )
        monkeypatch.setattr(recovery, "is_interactive", lambda: False)
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 4
        assert (
            "spec-kitty: logged_out_on_connected_teamspace "
            "teamspace=acme-eng command=sync doctor "
            "action=run-spec-kitty-auth-login"
        ) in result.stderr

    def test_non_interactive_no_teamspace_keeps_legacy_behavior(self, monkeypatch):
        _mock_doctor_logged_out(monkeypatch)
        monkeypatch.setattr(
            recovery,
            "detect_logged_out_with_connected_teamspace",
            lambda: None,
        )
        result = runner.invoke(app, ["doctor"])
        # Doctor never exits non-zero on its own for auth issues; it just
        # reports them. When no teamspace is detected we should keep that
        # behavior (exit 0) and never write the structured stderr line.
        assert result.exit_code == 0
        assert "logged_out_on_connected_teamspace" not in result.stderr
        assert "spec-kitty auth login" in result.stdout


# ---------------------------------------------------------------------------
# sync routes  --  non-zero exits from recovery must propagate
# ---------------------------------------------------------------------------


def _mock_routes_logged_out(monkeypatch):
    """Wire `sync routes` so the unauthenticated branch is reached."""
    from specify_cli.sync import feature_flags as ff

    monkeypatch.setattr(ff, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr(
        "specify_cli.cli.commands._teamspace_mission_state_gate.enforce_teamspace_mission_state_ready",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "specify_cli.sync.routing.resolve_checkout_sync_routing",
        lambda start=None: type(
            "Routing",
            (),
            {
                "repo_slug": "acme/spec-kitty",
                "project_uuid": "11111111-1111-1111-1111-111111111111",
                "project_slug": "spec-kitty-local",
                "build_id": "build-123",
                "effective_sync_enabled": True,
                "local_sync_enabled": None,
                "repo_default_sync_enabled": False,
            },
        )(),
    )
    fake_tm = MagicMock()
    fake_tm.get_current_session.return_value = None
    monkeypatch.setattr(
        "specify_cli.auth.get_token_manager",
        lambda: fake_tm,
    )


class TestSyncRoutesRecovery:
    def test_sync_routes_propagates_exit_4_from_recovery(self, monkeypatch):
        """Regression: `routes` must not swallow Exit(4) from auth recovery.

        Previously the bare `except typer.Exit:` in `routes()` caught every
        Exit, including the structured recovery exit code 4, and silently
        returned 0. Non-interactive CI users saw success when they should
        have seen the documented exit 4 + structured stderr.
        """
        _mock_routes_logged_out(monkeypatch)
        monkeypatch.setattr(
            recovery,
            "detect_logged_out_with_connected_teamspace",
            lambda: "acme-eng",
        )
        monkeypatch.setattr(recovery, "is_interactive", lambda: False)
        result = runner.invoke(app, ["routes"])
        assert result.exit_code == 4
        assert (
            "spec-kitty: logged_out_on_connected_teamspace "
            "teamspace=acme-eng command=sync routes "
            "action=run-spec-kitty-auth-login"
        ) in result.stderr
