"""``sync status`` surfaces daemon PID/port and orphan-singleton diagnostics (#1071).

The singleton invariant (one live ``run_sync_daemon`` per
``DAEMON_STATE_FILE``) is testable via ``scan_sync_daemons``. Wire those
helpers into the user-facing ``sync status --check`` output so operators
can see the daemon PID/port and any orphan processes without grepping
``ps`` themselves.

The ``status`` command imports ``get_sync_daemon_status`` / ``scan_sync_daemons``
inside the function body, so these tests patch the source module
(``specify_cli.sync.daemon``) rather than the importing command module.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from kernel.clock import now_utc, timedelta
from typer.testing import CliRunner

from specify_cli.auth.session import StoredSession, Team
from specify_cli.cli.commands import sync as sync_command
from specify_cli.cli.commands.sync import app
from specify_cli.sync.daemon import (
    DaemonSingletonReport,
    OrphanDaemonInfo,
    SyncDaemonStatus,
)


from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


runner = CliRunner()


def _authenticated_session() -> StoredSession:
    now = now_utc()
    return StoredSession(
        user_id="status-test-user",
        email="tester@example.com",
        name="Status Test",
        teams=(Team(id="t-private", name="Private", role="owner", is_private_teamspace=True),),
        default_team_id="t-private",
        access_token="access",
        refresh_token="refresh",
        session_id="status-test-session",
        issued_at=now,
        access_token_expires_at=now + timedelta(hours=1),
        refresh_token_expires_at=now + timedelta(days=1),
        scope="offline_access",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


def _healthy_status(pid: int = 4242, port: int = 9400) -> SyncDaemonStatus:
    return SyncDaemonStatus(
        healthy=True,
        url=f"http://127.0.0.1:{port}",
        port=port,
        token="t",
        pid=pid,
        sync_running=True,
        last_sync=None,
        consecutive_failures=0,
        websocket_status="Connected",
        protocol_version=1,
        package_version="3.2.0",
    )


def test_status_check_includes_daemon_pid_and_port(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The daemon PID and port appear in the ``sync status --check`` table.

    Authenticate a foreground identity so the FR-004 auth-required gate
    does not trip — this test's intent is to verify field rendering, not
    the auth gate behavior (which is exercised in
    ``test_status_check_flags_orphan_daemons`` and the WP03 boundary tests).
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.setattr(sync_command, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / ".spec-kitty"))
    from specify_cli.sync.consent import record_project_opt_in
    from specify_cli.sync.project_store import ProjectSyncStore
    import specify_cli.sync.routing as routing

    project_uuid = "aaaaaaaa-0000-0000-8000-000000001071"
    record_project_opt_in(project_uuid, actor="status-singleton-test")
    store = ProjectSyncStore(project_uuid)
    authority = store.layout_generation()
    authority.begin_cutover("status-singleton-test")
    authority.publish_project_only("status-singleton-test", verify_exact=lambda: True)
    with store.unit_of_work():
        pass
    routed = SimpleNamespace(
        project_uuid=store.project_uuid,
        project_slug="status-singleton-test",
        repo_slug="tests/status-singleton",
        build_id=None,
        repo_root=tmp_path,
    )
    monkeypatch.setattr(routing, "resolve_checkout_sync_routing_readonly", lambda *_a, **_k: routed)
    token_manager = SimpleNamespace(
        is_authenticated=True,
        get_current_session=lambda: _authenticated_session(),
        rehydrate_membership_if_needed=lambda **_kwargs: True,
    )
    monkeypatch.setattr("specify_cli.auth.manager.get_token_manager", lambda: token_manager)
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: token_manager)

    # Stage a foreground identity with a real auth scope so the
    # auth-required-and-absent failure does not trip the boundary gate.
    cred_dir = tmp_path / ".spec-kitty"
    cred_dir.mkdir(parents=True, exist_ok=True)
    (cred_dir / "credentials").write_text(
        '[user]\nusername = "tester@example.com"\nteam_slug = "t-private"\n[server]\nurl = "https://spec-kitty-dev.fly.dev"\n',
        encoding="utf-8",
    )

    with (
        patch(
            "specify_cli.sync.daemon.get_sync_daemon_status",
            return_value=_healthy_status(pid=12345, port=9400),
        ),
        patch(
            "specify_cli.sync.daemon.scan_sync_daemons",
            return_value=DaemonSingletonReport(
                state_pid=12345,
                state_file_present=True,
                orphan_processes=(),
            ),
        ),
        patch.object(
            sync_command,
            "_check_server_connection",
            return_value=("Reachable", None),
        ),
    ):
        result = runner.invoke(app, ["status", "--check"])

    assert result.exit_code == 0, result.output
    assert "Daemon PID" in result.output
    assert "12345" in result.output
    assert "Daemon Port" in result.output
    assert "9400" in result.output
    # No orphans -> Singleton row should be present and green-OK.
    assert "Singleton" in result.output
    assert "OK" in result.output


def test_status_check_flags_orphan_daemons(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Orphan ``run_sync_daemon`` processes are surfaced with PIDs in the output."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.setattr(sync_command, "is_saas_sync_enabled", lambda: True)

    orphans = (
        OrphanDaemonInfo(
            pid=99001,
            cmdline=("python", "-c", "run_sync_daemon(9401, 'tok')"),
        ),
        OrphanDaemonInfo(
            pid=99002,
            cmdline=("python", "-c", "run_sync_daemon(9402, 'tok')"),
        ),
    )

    with (
        patch(
            "specify_cli.sync.daemon.get_sync_daemon_status",
            return_value=_healthy_status(pid=4242, port=9400),
        ),
        patch(
            "specify_cli.sync.daemon.scan_sync_daemons",
            return_value=DaemonSingletonReport(
                state_pid=4242,
                state_file_present=True,
                orphan_processes=orphans,
            ),
        ),
        patch.object(
            sync_command,
            "_check_server_connection",
            return_value=("Reachable", None),
        ),
    ):
        result = runner.invoke(app, ["status", "--check"])

    # FR-004 + WP-followup live-orphan-scan gate: ``--check`` exits 2 when
    # any of the documented split-brain shapes are present, including live
    # ``run_sync_daemon`` orphans (#1071 failure mode).
    assert result.exit_code == 2, result.output
    # The Singleton table cell reports the count.
    assert "2 orphan daemon(s)" in result.output
    # The follow-up section lists each orphan PID with its cmdline.
    assert "99001" in result.output
    assert "99002" in result.output
    assert "run_sync_daemon(9401" in result.output
    assert "spec-kitty sync doctor" in result.output
    assert "Identity boundary check FAILED" in result.output
    # The orphan-scan failure line surfaces in the gate output (#1071).
    assert "live `run_sync_daemon` process(es) detected" in result.output


def test_status_without_check_skips_orphan_scan(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """``sync status`` without ``--check`` is the fast path; no scan is run."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.setattr(sync_command, "is_saas_sync_enabled", lambda: True)

    scan_called = {"count": 0}

    def fail_if_called() -> None:
        scan_called["count"] += 1
        raise AssertionError("scan_sync_daemons must not run on fast path")

    with (
        patch(
            "specify_cli.sync.daemon.get_sync_daemon_status",
            return_value=_healthy_status(),
        ),
        patch(
            "specify_cli.sync.daemon.scan_sync_daemons",
            side_effect=fail_if_called,
        ),
    ):
        result = runner.invoke(app, ["status"])

    assert result.exit_code == 0, result.output
    assert scan_called["count"] == 0
    # Singleton row only renders behind --check.
    assert "Singleton" not in result.output
