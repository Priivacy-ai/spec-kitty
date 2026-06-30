"""CliRunner coverage for repository sharing and routing commands."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, UTC
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.auth.session import StoredSession, Team
from specify_cli.cli.commands import sync as sync_module
from specify_cli.delivery.dispatcher import DispatchSummary

runner = CliRunner()
pytestmark = pytest.mark.fast


@pytest.fixture(autouse=True)
def _disable_teamspace_mission_state_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sync_module,
        "enforce_teamspace_mission_state_ready",
        lambda **_kwargs: None,
    )


@pytest.fixture(autouse=True)
def _isolate_home_for_preflight(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Isolate ``Path.home()`` so the WP03 boundary preflight (transitively
    invoked by sync share / unshare / opt-out via ``_require_daemon_owner_coherence``)
    does not refuse on the operator's real ``~/.spec-kitty/`` queue/owner
    state. Cross-platform per C-008 (patches the classmethod and both
    POSIX ``HOME`` and Windows ``USERPROFILE``)."""
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: home))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("LOCALAPPDATA", str(home / "AppData"))


def _session() -> StoredSession:
    now = datetime.now(UTC)
    return StoredSession(
        user_id="user-1",
        email="robert@example.com",
        name="Robert",
        teams=[
            Team(id="private-team", name="Robert Private Teamspace", role="owner", is_private_teamspace=True),
            Team(id="product-team", name="Product Team", role="member"),
        ],
        default_team_id="private-team",
        access_token="access",
        refresh_token="refresh",
        session_id="sess-1",
        issued_at=now,
        access_token_expires_at=now + timedelta(hours=1),
        refresh_token_expires_at=now + timedelta(days=30),
        scope="offline_access",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


def test_routes_command_renders_share_state(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_tm = Mock()
    fake_tm.get_current_session.return_value = _session()
    monkeypatch.setattr(sync_module, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: fake_tm)
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
    monkeypatch.setattr(
        "specify_cli.sync.sharing_client.list_repository_shares_sync",
        lambda source_project_uuid=None: [
            {
                "state": "shared",
                "active_sharer_count": 2,
                "team": {"name": "Product Team", "slug": "product-team"},
                "shared_project": {"project_slug": "spec-kitty"},
            }
        ],
    )

    result = runner.invoke(sync_module.app, ["routes"])

    assert result.exit_code == 0, result.stdout
    assert "Spec Kitty Teamspace Routing" in result.stdout
    assert "acme/spec-kitty" in result.stdout
    assert "Product Team" in result.stdout
    assert "shared" in result.stdout


def test_share_command_retries_after_materializing_private_source(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_tm = Mock()
    fake_tm.get_current_session.return_value = _session()
    monkeypatch.setattr(sync_module, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: fake_tm)
    monkeypatch.setattr(
        "specify_cli.sync.routing.resolve_checkout_sync_routing",
        lambda start=None: type(
            "Routing",
            (),
            {
                "repo_root": None,
                "repo_slug": "acme/spec-kitty",
                "project_uuid": "11111111-1111-1111-1111-111111111111",
                "project_slug": "spec-kitty-local",
                "build_id": "build-123",
                "effective_sync_enabled": True,
            },
        )(),
    )

    calls = {"count": 0}

    def _request_share(**_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            from specify_cli.sync.sharing_client import RepositorySharingClientError

            raise RepositorySharingClientError("Unknown private source project.", status_code=404)
        return {
            "share": {"state": "pending_approval"},
            "auto_approved": False,
        }

    with patch.object(sync_module, "_materialize_private_source_project") as mock_materialize:
        monkeypatch.setattr(
            "specify_cli.sync.sharing_client.request_repository_share_sync",
            _request_share,
        )
        result = runner.invoke(sync_module.app, ["share", "product-team"])

    assert result.exit_code == 0, result.stdout
    assert calls["count"] == 2
    mock_materialize.assert_called_once_with()
    assert "Share request recorded" in result.stdout
    assert "Waiting for a team admin" in result.stdout


def test_share_command_requires_persisted_project_uuid(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_tm = Mock()
    fake_tm.get_current_session.return_value = _session()
    request_share = Mock()
    monkeypatch.setattr(sync_module, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: fake_tm)
    monkeypatch.setattr(
        "specify_cli.sync.routing.resolve_checkout_sync_routing",
        lambda start=None: type(
            "Routing",
            (),
            {
                "repo_root": None,
                "repo_slug": "acme/spec-kitty",
                "project_uuid": None,
                "project_slug": "spec-kitty-local",
                "build_id": None,
                "effective_sync_enabled": True,
            },
        )(),
    )
    monkeypatch.setattr(
        "specify_cli.sync.sharing_client.request_repository_share_sync",
        request_share,
    )

    with patch.object(sync_module, "_materialize_private_source_project") as mock_materialize:
        result = runner.invoke(sync_module.app, ["share", "product-team"])

    assert result.exit_code == 1
    assert "Run `spec-kitty init` first" in result.stdout
    request_share.assert_not_called()
    mock_materialize.assert_not_called()


def test_routes_command_skips_share_lookup_without_project_uuid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_tm = Mock()
    fake_tm.get_current_session.return_value = _session()
    list_shares = Mock()
    monkeypatch.setattr(sync_module, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: fake_tm)
    monkeypatch.setattr(
        "specify_cli.sync.routing.resolve_checkout_sync_routing",
        lambda start=None: type(
            "Routing",
            (),
            {
                "repo_slug": "acme/spec-kitty",
                "project_uuid": None,
                "project_slug": "spec-kitty-local",
                "build_id": None,
                "effective_sync_enabled": True,
                "local_sync_enabled": None,
                "repo_default_sync_enabled": None,
            },
        )(),
    )
    monkeypatch.setattr(
        "specify_cli.sync.sharing_client.list_repository_shares_sync",
        list_shares,
    )

    result = runner.invoke(sync_module.app, ["routes"])

    assert result.exit_code == 0, result.stdout
    assert "Run `spec-kitty init` first" in result.stdout
    list_shares.assert_not_called()


def test_share_command_blocks_when_teamspace_mission_state_migration_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_share = Mock()
    monkeypatch.setattr(sync_module, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr(
        sync_module,
        "enforce_teamspace_mission_state_ready",
        Mock(side_effect=typer.Exit(1)),
    )
    monkeypatch.setattr(
        "specify_cli.sync.sharing_client.request_repository_share_sync",
        request_share,
    )

    result = runner.invoke(sync_module.app, ["share", "product-team"])

    assert result.exit_code == 1
    request_share.assert_not_called()


def test_opt_out_command_reports_purged_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.sync.routing.resolve_checkout_sync_routing",
        lambda start=None: type(
            "Routing",
            (),
            {
                "repo_root": "/tmp/repo",
                "repo_slug": "acme/spec-kitty",
                "project_slug": "spec-kitty-local",
                "project_uuid": "11111111-1111-1111-1111-111111111111",
            },
        )(),
    )
    monkeypatch.setattr(
        "specify_cli.sync.routing.disable_checkout_sync",
        lambda repo_root, remember_repo_default=True: type(
            "Result",
            (),
            {
                "removed_events": 3,
                "removed_body_uploads": 1,
                "remembered_for_repo": True,
            },
        )(),
    )

    result = runner.invoke(sync_module.app, ["opt-out"])

    assert result.exit_code == 0, result.stdout
    assert "Disabled SaaS sync for this checkout" in result.stdout
    assert "Removed 3 queued event(s) and 1 queued body upload(s)" in result.stdout


def test_unshare_command_stops_sharing_for_one_team(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_tm = Mock()
    fake_tm.get_current_session.return_value = _session()
    monkeypatch.setattr(sync_module, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: fake_tm)
    monkeypatch.setattr(
        "specify_cli.sync.routing.resolve_checkout_sync_routing",
        lambda start=None: type(
            "Routing",
            (),
            {
                "repo_root": "/tmp/repo",
                "repo_slug": "acme/spec-kitty",
                "project_slug": "spec-kitty-local",
                "project_uuid": "11111111-1111-1111-1111-111111111111",
            },
        )(),
    )
    monkeypatch.setattr(
        "specify_cli.sync.sharing_client.leave_repository_share_sync",
        lambda source_project_uuid=None, destination_team_slug=None: {"left": True},
    )

    result = runner.invoke(sync_module.app, ["unshare", "product-team"])

    assert result.exit_code == 0, result.stdout
    assert "Stopped sharing" in result.stdout
    assert "Private Teamspace data was kept intact" in result.stdout


def test_opt_out_command_can_delete_private_remote_data(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_tm = Mock()
    fake_tm.get_current_session.return_value = _session()
    monkeypatch.setattr(sync_module, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: fake_tm)
    monkeypatch.setattr(
        "specify_cli.sync.routing.resolve_checkout_sync_routing",
        lambda start=None: type(
            "Routing",
            (),
            {
                "repo_root": "/tmp/repo",
                "repo_slug": "acme/spec-kitty",
                "project_slug": "spec-kitty-local",
                "project_uuid": "11111111-1111-1111-1111-111111111111",
            },
        )(),
    )
    monkeypatch.setattr(
        "specify_cli.sync.routing.disable_checkout_sync",
        lambda repo_root, remember_repo_default=True: type(
            "Result",
            (),
            {
                "removed_events": 0,
                "removed_body_uploads": 0,
                "remembered_for_repo": False,
            },
        )(),
    )
    monkeypatch.setattr("specify_cli.sync.sharing_client.list_repository_shares_sync", lambda source_project_uuid=None: [])
    monkeypatch.setattr(
        "specify_cli.sync.sharing_client.delete_private_project_sync",
        lambda source_project_uuid=None: {
            "deleted_event_count": 4,
            "deleted_build_count": 1,
        },
    )
    monkeypatch.setattr("typer.confirm", lambda *args, **kwargs: True)

    result = runner.invoke(sync_module.app, ["opt-out", "--delete-private-data"])

    assert result.exit_code == 0, result.stdout
    assert "Deleted private SaaS data for this checkout" in result.stdout
    assert "4 event(s), 1 build(s)" in result.stdout


def test_now_logged_out_nonempty_queue_reports_unauthenticated_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Issue #829: a logged-out ``sync now`` with events to deliver is a
    *graceful* unauthenticated failure (exit 1), NOT a generic/teamspace-state
    exit (4).

    WP12 retired the destructive legacy ``service.sync_now()`` event drain in
    favour of the journal dispatcher (the single, non-destructive delivery
    path). A logged-out delivery now surfaces as a dispatch where events were
    *selected* and attempted but none were delivered — a 401 maps the whole
    batch to ``transient`` (see ``specify_cli.delivery.receivers``). That
    "attempted but nothing delivered" outcome is the dispatch analogue of the
    legacy per-event ``unauthenticated`` result and must keep the Issue #829
    exit-1 UX. It must NOT be reclassified as the "nothing attempted / blocked"
    teamspace-recovery exit (4) — verified passing on merge-base ``7530597a``.

    The autouse ``_isolate_home_for_preflight`` fixture redirects ``Path.home()``
    to a tmp dir so the WP03 boundary preflight (``require_auth=False``)
    evaluates against a clean state and falls through to the delivery path.
    """
    service = Mock()
    service.queue.size.return_value = 3
    service.drain_body_uploads_only.return_value = None

    # A logged-out dispatch: 3 events selected and attempted, none delivered
    # (the whole batch came back transient — the 401 classification).
    unauthenticated_summary = DispatchSummary(
        target_id="t-1",
        selected=3,
        delivered=0,
        duplicate=0,
        pending=0,
        rejected=0,
        transient=3,
        terminal_failed=0,
    )

    monkeypatch.setattr(sync_module, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr(
        "specify_cli.sync.background.get_sync_service",
        lambda: service,
    )
    monkeypatch.setattr(
        sync_module, "_run_event_sync_dispatch", lambda: unauthenticated_summary
    )
    report_path = tmp_path / "sync-report.json"

    result = runner.invoke(sync_module.app, ["now", "--report", str(report_path)])

    # Issue #829: graceful unauthenticated exit 1, not the teamspace-state exit 4.
    assert result.exit_code == 1, result.stdout
    assert "spec-kitty auth login" in result.stdout
    assert "not authenticated" in result.stdout.lower()
    # The dispatch report (the single delivery path's observable surface) lands.
    assert "report written" in result.stdout.lower()
    report = json.loads(report_path.read_text())
    assert report["dispatched"] is True
    assert report["selected"] == 3
    assert report["transient"] == 3
    assert report["delivered"] == 0
