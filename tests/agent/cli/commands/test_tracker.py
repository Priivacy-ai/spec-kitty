"""Scope: mock-boundary tests for tracker command registration, gating, and dispatch — no real git."""

from __future__ import annotations

import importlib
import json
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

pytestmark = pytest.mark.fast

runner = CliRunner()


def _build_root_app(*, enabled: bool, monkeypatch) -> typer.Typer:
    if enabled:
        monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    else:
        monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)

    import specify_cli.cli.commands as commands_module

    commands_module = importlib.reload(commands_module)
    app = typer.Typer()
    commands_module.register_commands(app)
    return app


# ---------------------------------------------------------------------------
# Feature flag gating tests (pre-existing)
# ---------------------------------------------------------------------------


def test_tracker_not_registered_when_flag_disabled(monkeypatch) -> None:
    """Tracker sub-command absent from help when SAAS_SYNC flag is off."""
    app = _build_root_app(enabled=False, monkeypatch=monkeypatch)
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "tracker" not in result.output


def test_tracker_registered_when_flag_enabled(monkeypatch) -> None:
    """Tracker sub-command appears in help when SAAS_SYNC flag is on."""
    app = _build_root_app(enabled=True, monkeypatch=monkeypatch)
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "tracker" in result.output


def test_tracker_direct_invocation_fails_when_flag_disabled(monkeypatch) -> None:
    """Direct tracker invocation exits with code 1 and a flag-disabled message."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)

    from specify_cli.cli.commands import tracker as tracker_module

    result = runner.invoke(tracker_module.app, ["providers"])
    assert result.exit_code == 1
    assert "SaaS sync is disabled by feature flag" in result.output


# ---------------------------------------------------------------------------
# Helpers for command-level tests
# ---------------------------------------------------------------------------


def _make_app(monkeypatch) -> typer.Typer:
    """Return the tracker app with the feature flag enabled."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    from specify_cli.cli.commands import tracker as tracker_module

    return tracker_module.app


# ---------------------------------------------------------------------------
# bind: SaaS provider with --project-slug
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_bind_saas_provider_with_project_slug(mock_service_fn, monkeypatch) -> None:
    """SaaS bind with --project-slug calls service.bind correctly."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_config = MagicMock()
    mock_config.provider = "linear"
    mock_config.project_slug = "my-proj"
    mock_svc.bind.return_value = mock_config
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["bind", "--provider", "linear", "--project-slug", "my-proj"])
    assert result.exit_code == 0
    mock_svc.bind.assert_called_once_with(provider="linear", project_slug="my-proj")
    assert "Tracker binding saved" in result.output


# ---------------------------------------------------------------------------
# bind: SaaS provider --credential hard-fail
# ---------------------------------------------------------------------------


def test_bind_saas_provider_credential_hard_fail(monkeypatch) -> None:
    """SaaS bind with --credential must hard-fail with dashboard guidance."""
    app = _make_app(monkeypatch)

    result = runner.invoke(
        app,
        [
            "bind",
            "--provider",
            "linear",
            "--project-slug",
            "p",
            "--credential",
            "api_key=xxx",
        ],
    )
    assert result.exit_code == 1
    assert "credentials are not accepted for SaaS-backed providers" in result.output
    assert "spec-kitty auth login" in result.output
    assert "dashboard" in result.output.lower()


# ---------------------------------------------------------------------------
# bind: SaaS provider missing --project-slug
# ---------------------------------------------------------------------------


def test_bind_saas_provider_missing_project_slug(monkeypatch) -> None:
    """SaaS bind without --project-slug must hard-fail."""
    app = _make_app(monkeypatch)

    result = runner.invoke(app, ["bind", "--provider", "jira"])
    assert result.exit_code == 1
    assert "--project-slug is required" in result.output


# ---------------------------------------------------------------------------
# bind: Azure DevOps hard-fail
# ---------------------------------------------------------------------------


def test_bind_azure_devops_hard_fail(monkeypatch) -> None:
    """Azure DevOps bind must hard-fail with 'no longer supported' message."""
    app = _make_app(monkeypatch)

    result = runner.invoke(
        app, ["bind", "--provider", "azure_devops", "--workspace", "w"]
    )
    assert result.exit_code == 1
    assert "no longer supported" in result.output


# ---------------------------------------------------------------------------
# bind: local provider with --workspace --credential
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_bind_local_provider(mock_service_fn, monkeypatch) -> None:
    """Local bind with --workspace and --credential dispatches correctly."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_config = MagicMock()
    mock_config.provider = "beads"
    mock_config.workspace = "w"
    mock_config.doctrine_mode = "external_authoritative"
    mock_config.doctrine_field_owners = {}
    mock_svc.bind.return_value = mock_config
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(
        app,
        [
            "bind",
            "--provider",
            "beads",
            "--workspace",
            "w",
            "--credential",
            "command=beads",
        ],
    )
    assert result.exit_code == 0
    mock_svc.bind.assert_called_once()
    call_kwargs = mock_svc.bind.call_args[1]
    assert call_kwargs["provider"] == "beads"
    assert call_kwargs["workspace"] == "w"
    assert call_kwargs["credentials"] == {"command": "beads"}
    assert "Tracker binding saved" in result.output


# ---------------------------------------------------------------------------
# bind: local provider missing --workspace
# ---------------------------------------------------------------------------


def test_bind_local_provider_missing_workspace(monkeypatch) -> None:
    """Local bind without --workspace must hard-fail."""
    app = _make_app(monkeypatch)

    result = runner.invoke(app, ["bind", "--provider", "beads"])
    assert result.exit_code == 1
    assert "--workspace is required" in result.output


# ---------------------------------------------------------------------------
# providers: categorized list (SaaS vs Local)
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_providers_list(mock_service_fn, monkeypatch) -> None:
    """Providers command shows SaaS and local, no azure_devops."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["providers"])
    assert result.exit_code == 0
    assert "SaaS-backed" in result.output
    assert "Local" in result.output
    for p in ("github", "gitlab", "jira", "linear"):
        assert p in result.output
    for p in ("beads", "fp"):
        assert p in result.output
    assert "azure_devops" not in result.output


# ---------------------------------------------------------------------------
# providers: JSON output
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_providers_json(mock_service_fn, monkeypatch) -> None:
    """Providers --json returns structured JSON with categorization."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["providers", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "saas" in data
    assert "local" in data
    assert "linear" in data["saas"]
    assert "beads" in data["local"]


# ---------------------------------------------------------------------------
# sync pull: JSON output for SaaS envelope
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_sync_pull_json(mock_service_fn, monkeypatch) -> None:
    """sync pull --json outputs the raw envelope dict."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.sync_pull.return_value = {
        "status": "complete",
        "identity_path": {"type": "saas", "provider": "linear"},
        "summary": {"total": 10, "succeeded": 9, "failed": 1, "skipped": 0},
        "items": [],
    }
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["sync", "pull", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "complete"
    assert data["summary"]["total"] == 10


# ---------------------------------------------------------------------------
# sync push: JSON output for SaaS envelope
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker.require_repo_root")
@patch("specify_cli.cli.commands.tracker.load_tracker_config")
@patch("specify_cli.cli.commands.tracker._service")
def test_sync_push_saas_with_items_json(mock_service_fn, mock_load_cfg, mock_repo_root, monkeypatch, tmp_path) -> None:
    """SaaS push with --items-json sends items to the service."""
    from specify_cli.tracker.config import TrackerProjectConfig

    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.sync_push.return_value = {
        "status": "ok",
        "summary": {"total": 1, "succeeded": 1, "failed": 0, "skipped": 0},
    }
    mock_service_fn.return_value = mock_svc
    mock_load_cfg.return_value = TrackerProjectConfig(provider="linear", project_slug="proj")
    mock_repo_root.return_value = tmp_path

    items_file = tmp_path / "items.json"
    items_file.write_text('[{"ref": {"system": "linear", "id": "LIN-1", "workspace": "team"}, "action": "update"}]')

    result = runner.invoke(app, ["sync", "push", "--items-json", str(items_file), "--json"])
    assert result.exit_code == 0, result.output
    mock_svc.sync_push.assert_called_once()
    call_kwargs = mock_svc.sync_push.call_args[1]
    assert len(call_kwargs["items"]) == 1
    assert call_kwargs["items"][0]["action"] == "update"


@patch("specify_cli.cli.commands.tracker.require_repo_root")
@patch("specify_cli.cli.commands.tracker.load_tracker_config")
@patch("specify_cli.cli.commands.tracker._service")
def test_sync_push_saas_no_items_no_mappings(mock_service_fn, mock_load_cfg, mock_repo_root, monkeypatch, tmp_path) -> None:
    """SaaS push with no items and no mappings exits with guidance."""
    from specify_cli.tracker.config import TrackerProjectConfig

    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.map_list.return_value = []
    mock_service_fn.return_value = mock_svc
    mock_load_cfg.return_value = TrackerProjectConfig(provider="jira", project_slug="proj")
    mock_repo_root.return_value = tmp_path

    result = runner.invoke(app, ["sync", "push"])
    # Exit code 0 — not an error, just nothing to push
    assert "No pending changes" in result.output


@patch("specify_cli.cli.commands.tracker._service")
def test_sync_push_local_uses_limit(mock_service_fn, monkeypatch) -> None:
    """Local push passes limit kwarg (not items)."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.sync_push.return_value = {
        "provider": "beads",
        "stats": {"pushed_created": 2, "pushed_updated": 0, "skipped": 0},
        "conflicts": [],
        "errors": [],
    }
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["sync", "push", "--limit", "50"])
    assert result.exit_code == 0
    mock_svc.sync_push.assert_called_once_with(limit=50)


@patch("specify_cli.cli.commands.tracker._service")
def test_sync_push_json(mock_service_fn, monkeypatch) -> None:
    """sync push --json outputs the raw envelope dict (local provider path)."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.sync_push.return_value = {
        "status": "complete",
        "summary": {"total": 5, "succeeded": 5, "failed": 0, "skipped": 0},
    }
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["sync", "push", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "complete"


# ---------------------------------------------------------------------------
# sync run: JSON output
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_sync_run_json(mock_service_fn, monkeypatch) -> None:
    """sync run --json outputs the raw envelope dict."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.sync_run.return_value = {
        "status": "complete",
        "summary": {"total": 8, "succeeded": 8, "failed": 0, "skipped": 0},
    }
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["sync", "run", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "complete"


# ---------------------------------------------------------------------------
# status: dispatches through facade
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_status_command(mock_service_fn, monkeypatch) -> None:
    """Status command dispatches through the facade."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.status.return_value = {
        "configured": True,
        "provider": "linear",
        "identity_path": {"type": "saas", "provider": "linear"},
        "sync_state": "idle",
    }
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "linear" in result.output


# ---------------------------------------------------------------------------
# status: JSON output
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_status_json(mock_service_fn, monkeypatch) -> None:
    """Status --json outputs the raw dict."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.status.return_value = {
        "configured": True,
        "provider": "linear",
    }
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["status", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["provider"] == "linear"


# ---------------------------------------------------------------------------
# map add: hard-fail for SaaS is handled by service
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_map_add_dispatches(mock_service_fn, monkeypatch) -> None:
    """map add dispatches through the facade."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(
        app,
        [
            "map",
            "add",
            "--wp-id",
            "WP01",
            "--external-id",
            "123",
        ],
    )
    assert result.exit_code == 0
    mock_svc.map_add.assert_called_once()


# ---------------------------------------------------------------------------
# map list: dispatches through facade
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_map_list_dispatches(mock_service_fn, monkeypatch) -> None:
    """map list dispatches through the facade."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.map_list.return_value = [
        {"wp_id": "WP01", "external_id": "123", "external_key": "PROJ-1", "system": "linear"},
    ]
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["map", "list"])
    assert result.exit_code == 0
    assert "WP01" in result.output
