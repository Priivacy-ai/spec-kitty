"""CliRunner coverage for repository sharing and routing commands."""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.auth.session import StoredSession, Team
from specify_cli.cli.commands import sync as sync_module

runner = CliRunner()
pytestmark = pytest.mark.fast


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
