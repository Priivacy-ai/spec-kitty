"""CliRunner coverage for repository sharing and routing commands."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.auth.session import StoredSession, Team
from specify_cli.cli.commands import sync as sync_module
from specify_cli.sync.batch import BatchEventResult, BatchSyncResult

runner = CliRunner()
pytestmark = pytest.mark.fast


@pytest.fixture(autouse=True)
def _disable_teamspace_mission_state_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sync_module,
        "enforce_teamspace_mission_state_ready",
        lambda **_kwargs: None,
    )


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
    """Issue #829: logged-out sync now is unauthenticated, not generic sync failure."""
    unauthenticated_result = BatchSyncResult()
    unauthenticated_result.total_events = 3
    unauthenticated_result.error_count = 3
    unauthenticated_result.failed_ids = ["evt-1", "evt-2", "evt-3"]
    unauthenticated_result.error_messages = [
        "Not authenticated: no valid access token. Run `spec-kitty auth login`."
    ]
    unauthenticated_result.event_results = [
        BatchEventResult(
            event_id=f"evt-{index}",
            status="rejected",
            error="Not authenticated: no valid access token. Run `spec-kitty auth login`.",
            error_category="unauthenticated",
        )
        for index in range(1, 4)
    ]
    service = Mock()
    service.queue.size.return_value = 3
    service.sync_now.return_value = unauthenticated_result

    monkeypatch.setattr(sync_module, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr(
        "specify_cli.sync.background.get_sync_service",
        lambda: service,
    )
    report_path = tmp_path / "sync-failures.json"

    result = runner.invoke(sync_module.app, ["now", "--report", str(report_path)])

    assert result.exit_code == 1
    assert "unauthenticated" in result.stdout
    assert "spec-kitty auth login" in result.stdout
    assert "Errors:" in result.stdout
    assert "3" in result.stdout
    assert "Failure report written" in result.stdout
    assert "server_error" not in result.stdout
    report = json.loads(report_path.read_text())
    assert report["summary"]["failed"] == 3
    assert report["summary"]["categories"] == {"unauthenticated": 3}
    assert [failure["category"] for failure in report["failures"]] == [
        "unauthenticated",
        "unauthenticated",
        "unauthenticated",
    ]
