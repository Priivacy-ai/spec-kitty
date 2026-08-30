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


from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


runner = CliRunner()


def test_logged_out_teamspace_detector_does_not_create_project_identity(
    tmp_path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    (repo_root / ".kittify").mkdir()

    fake_tm = MagicMock()
    fake_tm.is_authenticated = False
    fake_tm.get_current_session.return_value = None
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: fake_tm)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    assert recovery.detect_logged_out_with_connected_teamspace(repo_root=repo_root) is None
    assert not (repo_root / ".kittify" / "config.yaml").exists()


# ---------------------------------------------------------------------------
# sync now  --  non-interactive structured exit
# ---------------------------------------------------------------------------


def _mock_unauth_sync_now(monkeypatch):
    """Wire `sync now` so it always hits the unauthenticated branch.

    WP03 (T012) added a preflight gate at the top of ``sync now`` that
    refuses with exit code 2 when the SaaS auth scope is absent. These
    recovery tests exercise the layer below that — they assume the
    preflight passes and the unauth detection happens against the live
    sync attempt. We stub the preflight here so the recovery layer keeps
    being exercised by these tests; the preflight itself has dedicated
    test coverage in ``test_sync_boundary_preflight.py``.

    WP12 retired the destructive ``service.sync_now()`` event drain; the
    journal dispatcher (``_run_event_sync_dispatch``) is now the sole event
    path. The "logged out with pending work" shape these tests exercise is
    now: ``queue.size() > 0`` (pending-work signal) plus an empty
    :class:`DispatchSummary` (nothing attempted), which
    ``_enforce_sync_now_exit_from_dispatch`` routes through the
    teamspace-aware recovery layer under test. The dispatcher and the
    retained-work probe are stubbed so the real project store in this
    checkout never leaks into the outcome (same seam as
    ``tests/agent/cli/commands/test_sync.py::TestSyncNowExitCodes``).
    """
    from specify_cli.delivery.dispatcher import DispatchSummary
    from specify_cli.sync import feature_flags as ff
    from specify_cli.sync.preflight import PreflightResult

    monkeypatch.setattr(ff, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr(
        "specify_cli.cli.commands._teamspace_mission_state_gate.enforce_teamspace_mission_state_ready",
        lambda *a, **k: None,
    )

    monkeypatch.setattr(
        "specify_cli.sync.preflight.run_preflight",
        lambda **kwargs: PreflightResult(
            ok=True,
            mismatches=(),
            orphan_records=(),
            legacy_event_rows=0,
            legacy_body_upload_rows=0,
            auth_present=True,
            auth_required=True,
        ),
    )

    # Pending work exists (queue.size() == 1) but the dispatcher attempts
    # nothing (empty summary, selected == 0): the exact "logged out, work
    # pending" shape that must route through teamspace-aware recovery.
    fake_service = MagicMock()
    fake_service.queue.size.return_value = 1
    fake_service.drain_body_uploads_only.return_value = None
    monkeypatch.setattr(
        "specify_cli.sync.background.get_sync_service",
        lambda: fake_service,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.sync._run_event_sync_dispatch",
        lambda: DispatchSummary.empty(),
    )
    # Keep the checkout's real project journal out of the outcome: retained
    # work with selected == 0 short-circuits to a strict exit 1 before the
    # recovery layer these tests assert on.
    monkeypatch.setattr(
        "specify_cli.cli.commands.sync._event_sync_retained_work_present",
        lambda: False,
    )
    return fake_service


class TestSyncNowRecovery:
    @pytest.fixture(autouse=True)
    def _stub_teamspace_gate(self, monkeypatch):
        """Bypass the M7 ``enforce_teamspace_mission_state_ready`` gate.

        Same rationale as ``TestSyncNowExitCodes._stub_teamspace_gate`` in
        ``tests/agent/cli/commands/test_sync.py``: spec-kitty's own
        ``.kittify/`` contains TeamSpace blockers in the test environment,
        which raises ``typer.Exit(1)`` before the recovery contract can be
        evaluated. These tests assert on the recovery layer specifically,
        so the gate is stubbed at the call-site in ``sync.py``.
        """
        import specify_cli.cli.commands.sync as sync_mod

        monkeypatch.setattr(
            sync_mod,
            "enforce_teamspace_mission_state_ready",
            lambda **kwargs: None,
        )

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
    fake_queue.db_path = "/nonexistent/queue.db"
    monkeypatch.setattr(
        "specify_cli.sync.queue.OfflineQueue",
        lambda: fake_queue,
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
