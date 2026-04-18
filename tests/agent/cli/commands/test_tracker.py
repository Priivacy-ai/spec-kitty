"""Scope: mock-boundary tests for tracker command registration, gating, and dispatch -- no real git."""

from __future__ import annotations

import importlib
import json
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.saas.readiness import ReadinessResult, ReadinessState
from specify_cli.tracker.config import TrackerProjectConfig
from specify_cli.tracker.discovery import BindCandidate, BindResult, ResolutionResult
from specify_cli.tracker.service import TrackerServiceError

pytestmark = pytest.mark.fast

runner = CliRunner()


# ---------------------------------------------------------------------------
# Autouse fixture: stub _check_readiness for all existing tests.
#
# New tests that want to exercise the real readiness dispatch use
# ``@pytest.mark.no_readiness_stub`` (or just patch things directly).
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _stub_check_readiness(request, monkeypatch):
    """Make _check_readiness a no-op for all tests unless marked otherwise.

    This preserves backward compatibility with existing tests that don't
    care about the readiness path.  Tests that explicitly test readiness
    should mark themselves with ``no_readiness_stub`` or use their own stubs.
    """
    if "no_readiness_stub" in {m.name for m in request.node.iter_markers()}:
        return
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker._check_readiness",
        lambda *, require_mission_binding, probe_reachability: None,
    )


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
    assert "issue-search" in result.output


def test_tracker_direct_invocation_fails_when_flag_disabled(monkeypatch) -> None:
    """Direct tracker invocation exits with code 1 and a flag-disabled message."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)

    from specify_cli.cli.commands import tracker as tracker_module

    result = runner.invoke(tracker_module.app, ["providers"])
    assert result.exit_code == 1
    assert "Hosted SaaS sync is not enabled" in result.output


# ---------------------------------------------------------------------------
# Helpers for command-level tests
# ---------------------------------------------------------------------------


def _make_app(monkeypatch) -> typer.Typer:
    """Return the tracker app with the feature flag enabled."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    from specify_cli.cli.commands import tracker as tracker_module

    return tracker_module.app


def _mock_identity():
    """Return a mock ProjectIdentity for ensure_identity patches."""
    identity = MagicMock()
    identity.project_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    identity.project_slug = "test-project"
    identity.node_id = "abc123def456"
    identity.repo_slug = "owner/repo"
    return identity


def _make_bind_result(
    *,
    provider: str = "linear",
    binding_ref: str = "br_abc123",
    display_label: str = "My Linear Team",
) -> BindResult:
    return BindResult(
        binding_ref=binding_ref,
        display_label=display_label,
        provider=provider,
        provider_context={},
        bound_at="2026-04-04T12:00:00Z",
    )


def _make_tracker_config(
    *,
    provider: str = "linear",
    binding_ref: str = "br_abc123",
    display_label: str = "My Linear Team",
) -> TrackerProjectConfig:
    return TrackerProjectConfig(
        provider=provider,
        binding_ref=binding_ref,
        display_label=display_label,
    )


def _make_candidates_resolution() -> ResolutionResult:
    return ResolutionResult(
        match_type="candidates",
        candidates=[
            BindCandidate(
                candidate_token="tok_1",
                display_label="Team Alpha",
                confidence="high",
                match_reason="Name matches repository slug",
                sort_position=0,
            ),
            BindCandidate(
                candidate_token="tok_2",
                display_label="Team Beta",
                confidence="medium",
                match_reason="Partial slug overlap",
                sort_position=1,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# bind: --project-slug is no longer accepted for SaaS
# ---------------------------------------------------------------------------


def test_bind_no_project_slug_flag(monkeypatch) -> None:
    """--project-slug is not accepted by bind command."""
    app = _make_app(monkeypatch)

    result = runner.invoke(
        app, ["bind", "--provider", "linear", "--project-slug", "my-proj"]
    )
    # typer rejects unknown options with exit code 2
    assert result.exit_code == 2
    assert "project-slug" in result.output.lower() or "no such option" in result.output.lower()


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
            "--credential",
            "api_key=xxx",
        ],
    )
    assert result.exit_code == 1
    assert "Direct provider credentials are no longer supported for linear" in result.output
    assert "spec-kitty auth login" in result.output
    assert "dashboard" in result.output.lower()


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
# bind: SaaS discovery auto-bind (exact match)
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
@patch("specify_cli.cli.commands.tracker.ensure_identity")
@patch("specify_cli.cli.commands.tracker.load_tracker_config")
def test_bind_auto_bind(
    mock_load_cfg, mock_ensure_id, mock_service_fn, monkeypatch,
) -> None:
    """SaaS bind with exact match auto-binds and shows success."""
    app = _make_app(monkeypatch)
    mock_ensure_id.return_value = _mock_identity()
    mock_load_cfg.return_value = TrackerProjectConfig()  # no existing binding
    mock_svc = MagicMock()
    mock_svc.bind.return_value = _make_bind_result()
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["bind", "--provider", "linear"])
    assert result.exit_code == 0, result.output
    assert "Tracker binding saved" in result.output
    assert "br_abc123" in result.output
    assert "My Linear Team" in result.output


# ---------------------------------------------------------------------------
# bind: SaaS discovery with candidates (interactive)
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
@patch("specify_cli.cli.commands.tracker.ensure_identity")
@patch("specify_cli.cli.commands.tracker.load_tracker_config")
@patch("builtins.input")
def test_bind_candidates_interactive(
    mock_input, mock_load_cfg, mock_ensure_id, mock_service_fn, monkeypatch,
) -> None:
    """SaaS bind with candidates prompts user and binds selection."""
    app = _make_app(monkeypatch)
    mock_ensure_id.return_value = _mock_identity()
    mock_load_cfg.return_value = TrackerProjectConfig()
    mock_svc = MagicMock()
    # First call returns candidates, second call returns BindResult
    mock_svc.bind.side_effect = [
        _make_candidates_resolution(),
        _make_bind_result(display_label="Team Beta"),
    ]
    mock_service_fn.return_value = mock_svc
    mock_input.return_value = "2"  # Select second candidate

    result = runner.invoke(app, ["bind", "--provider", "linear"])
    assert result.exit_code == 0, result.output
    assert "Multiple resources found" in result.output
    assert "Team Alpha" in result.output
    assert "Team Beta" in result.output
    assert "Tracker binding saved" in result.output

    # Verify the second bind call included select_n=2
    assert mock_svc.bind.call_count == 2
    second_call = mock_svc.bind.call_args_list[1]
    assert second_call[1]["select_n"] == 2


# ---------------------------------------------------------------------------
# bind: SaaS no candidates
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
@patch("specify_cli.cli.commands.tracker.ensure_identity")
@patch("specify_cli.cli.commands.tracker.load_tracker_config")
def test_bind_no_candidates(
    mock_load_cfg, mock_ensure_id, mock_service_fn, monkeypatch,
) -> None:
    """SaaS bind with no match raises error with exit 1."""
    app = _make_app(monkeypatch)
    mock_ensure_id.return_value = _mock_identity()
    mock_load_cfg.return_value = TrackerProjectConfig()
    mock_svc = MagicMock()
    mock_svc.bind.side_effect = TrackerServiceError(
        "No bindable resources found for provider 'linear'."
    )
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["bind", "--provider", "linear"])
    assert result.exit_code == 1
    assert "No bindable resources" in result.output


# ---------------------------------------------------------------------------
# bind: --bind-ref valid
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
@patch("specify_cli.cli.commands.tracker.ensure_identity")
def test_bind_ref_valid(mock_ensure_id, mock_service_fn, monkeypatch) -> None:
    """--bind-ref with valid ref persists binding and shows success."""
    app = _make_app(monkeypatch)
    mock_ensure_id.return_value = _mock_identity()
    mock_svc = MagicMock()
    mock_svc.bind.return_value = _make_tracker_config(binding_ref="br_known_ref")
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(
        app, ["bind", "--provider", "linear", "--bind-ref", "br_known_ref"]
    )
    assert result.exit_code == 0, result.output
    assert "Tracker binding saved" in result.output
    assert "br_known_ref" in result.output

    # Verify bind was called with bind_ref
    call_kwargs = mock_svc.bind.call_args[1]
    assert call_kwargs["bind_ref"] == "br_known_ref"


# ---------------------------------------------------------------------------
# bind: --bind-ref invalid
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
@patch("specify_cli.cli.commands.tracker.ensure_identity")
def test_bind_ref_invalid(mock_ensure_id, mock_service_fn, monkeypatch) -> None:
    """--bind-ref with invalid ref shows error and exits 1."""
    app = _make_app(monkeypatch)
    mock_ensure_id.return_value = _mock_identity()
    mock_svc = MagicMock()
    mock_svc.bind.side_effect = TrackerServiceError(
        "Binding ref 'br_bad' is not valid: deleted on host."
    )
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(
        app, ["bind", "--provider", "linear", "--bind-ref", "br_bad"]
    )
    assert result.exit_code == 1
    assert "not valid" in result.output


# ---------------------------------------------------------------------------
# bind: --select N valid
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
@patch("specify_cli.cli.commands.tracker.ensure_identity")
@patch("specify_cli.cli.commands.tracker.load_tracker_config")
def test_bind_select_n(
    mock_load_cfg, mock_ensure_id, mock_service_fn, monkeypatch,
) -> None:
    """--select 1 auto-selects candidate without prompts."""
    app = _make_app(monkeypatch)
    mock_ensure_id.return_value = _mock_identity()
    mock_load_cfg.return_value = TrackerProjectConfig()
    mock_svc = MagicMock()
    mock_svc.bind.return_value = _make_bind_result(display_label="Team Alpha")
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(
        app, ["bind", "--provider", "linear", "--select", "1"]
    )
    assert result.exit_code == 0, result.output
    assert "Tracker binding saved" in result.output
    assert "Team Alpha" in result.output

    # Verify select_n was passed
    call_kwargs = mock_svc.bind.call_args[1]
    assert call_kwargs["select_n"] == 1


# ---------------------------------------------------------------------------
# bind: --select N out of range
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
@patch("specify_cli.cli.commands.tracker.ensure_identity")
@patch("specify_cli.cli.commands.tracker.load_tracker_config")
def test_bind_select_out_of_range(
    mock_load_cfg, mock_ensure_id, mock_service_fn, monkeypatch,
) -> None:
    """--select 99 with out-of-range selection shows error and exits 1."""
    app = _make_app(monkeypatch)
    mock_ensure_id.return_value = _mock_identity()
    mock_load_cfg.return_value = TrackerProjectConfig()
    mock_svc = MagicMock()
    mock_svc.bind.side_effect = TrackerServiceError(
        "Selection 99 is out of range. Valid range: 1-2."
    )
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(
        app, ["bind", "--provider", "linear", "--select", "99"]
    )
    assert result.exit_code == 1
    assert "out of range" in result.output


# ---------------------------------------------------------------------------
# bind: re-bind confirmed
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
@patch("specify_cli.cli.commands.tracker.ensure_identity")
@patch("specify_cli.cli.commands.tracker.load_tracker_config")
@patch("builtins.input")
def test_bind_rebind_confirmed(
    mock_input, mock_load_cfg, mock_ensure_id, mock_service_fn, monkeypatch,
) -> None:
    """Re-bind with existing binding: user confirms 'y' -> proceeds."""
    app = _make_app(monkeypatch)
    mock_ensure_id.return_value = _mock_identity()
    mock_load_cfg.return_value = TrackerProjectConfig(
        provider="linear",
        binding_ref="br_old",
        display_label="Old Team",
    )
    mock_svc = MagicMock()
    mock_svc.bind.return_value = _make_bind_result(display_label="New Team")
    mock_service_fn.return_value = mock_svc
    mock_input.return_value = "y"

    result = runner.invoke(app, ["bind", "--provider", "linear"])
    assert result.exit_code == 0, result.output
    assert "Existing binding" in result.output
    assert "Tracker binding saved" in result.output


# ---------------------------------------------------------------------------
# bind: re-bind cancelled
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
@patch("specify_cli.cli.commands.tracker.ensure_identity")
@patch("specify_cli.cli.commands.tracker.load_tracker_config")
@patch("builtins.input")
def test_bind_rebind_cancelled(
    mock_input, mock_load_cfg, mock_ensure_id, mock_service_fn, monkeypatch,
) -> None:
    """Re-bind with existing binding: user declines -> exit 0, no bind."""
    app = _make_app(monkeypatch)
    mock_ensure_id.return_value = _mock_identity()
    mock_load_cfg.return_value = TrackerProjectConfig(
        provider="linear",
        binding_ref="br_old",
        display_label="Old Team",
    )
    mock_svc = MagicMock()
    mock_service_fn.return_value = mock_svc
    mock_input.return_value = "n"

    result = runner.invoke(app, ["bind", "--provider", "linear"])
    assert result.exit_code == 0
    assert "Bind cancelled" in result.output
    mock_svc.bind.assert_not_called()


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
def test_sync_push_saas_requires_items_json(mock_service_fn, mock_load_cfg, mock_repo_root, monkeypatch, tmp_path) -> None:
    """SaaS push without --items-json fails with clear guidance."""
    from specify_cli.tracker.config import TrackerProjectConfig

    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_service_fn.return_value = mock_svc
    mock_load_cfg.return_value = TrackerProjectConfig(provider="jira", project_slug="proj")
    mock_repo_root.return_value = tmp_path

    result = runner.invoke(app, ["sync", "push"])
    assert result.exit_code == 1
    assert "--items-json is required" in result.output
    assert "tracker sync run" in result.output
    # Verify sync_push was never called (we errored before reaching it)
    mock_svc.sync_push.assert_not_called()


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


@patch("specify_cli.cli.commands.tracker._service")
def test_map_list_with_provider_dispatches_without_bound_repo(mock_service_fn, monkeypatch) -> None:
    """map list --provider uses the provider-scoped service path."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.map_list.return_value = [{"wp_id": "WP01", "external_id": "123"}]
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["map", "list", "--provider", "linear", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["mappings"][0]["wp_id"] == "WP01"
    mock_service_fn.assert_called_once_with(allow_unbound=True)
    mock_svc.map_list.assert_called_once_with(provider="linear")


@patch("specify_cli.cli.commands.tracker._service")
def test_issue_search_root_dispatches(mock_service_fn, monkeypatch) -> None:
    """issue-search dispatches through the tracker service and returns JSON array."""
    app = _build_root_app(enabled=True, monkeypatch=monkeypatch)
    mock_svc = MagicMock()
    mock_svc.issue_search.return_value = [
        {
            "identifier": "PRI-17",
            "title": "Wire hosted tracker reads",
            "url": "https://linear.app/priivacy/issue/PRI-17",
            "state": {"name": "todo"},
            "team": {"key": "PRI"},
            "assignee": None,
            "created_at": None,
            "updated_at": None,
            "body": "body",
        }
    ]
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(
        app,
        ["issue-search", "--provider", "linear", "--query", "PRI-17", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload[0]["identifier"] == "PRI-17"
    mock_service_fn.assert_called_once_with(allow_unbound=True)
    mock_svc.issue_search.assert_called_once_with(provider="linear", query="PRI-17")


@patch("specify_cli.cli.commands.tracker._service")
def test_list_tickets_dispatches(mock_service_fn, monkeypatch) -> None:
    """tracker list-tickets dispatches through the provider-scoped service path."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.list_tickets.return_value = [
        {
            "identifier": "PRI-1",
            "title": "First ticket",
            "url": "https://linear.app/priivacy/issue/PRI-1",
            "state": {"name": "todo"},
            "team": {"key": "PRI"},
            "assignee": None,
            "created_at": None,
            "updated_at": None,
            "body": None,
        }
    ]
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(
        app,
        ["list-tickets", "--provider", "linear", "--limit", "20", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload[0]["identifier"] == "PRI-1"
    mock_service_fn.assert_called_once_with(allow_unbound=True)
    mock_svc.list_tickets.assert_called_once_with(provider="linear", limit=20)


# ---------------------------------------------------------------------------
# T024: Rollout × readiness matrix tests
# ---------------------------------------------------------------------------


@pytest.mark.no_readiness_stub
def test_tracker_hidden_when_rollout_disabled_root_app(monkeypatch) -> None:
    """Tracker sub-command absent from root app help when rollout is off."""
    app = _build_root_app(enabled=False, monkeypatch=monkeypatch)
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "tracker" not in result.output


@pytest.mark.no_readiness_stub
def test_tracker_visible_when_rollout_enabled_root_app(monkeypatch) -> None:
    """Tracker sub-command appears in root app help when rollout is on."""
    app = _build_root_app(enabled=True, monkeypatch=monkeypatch)
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "tracker" in result.output


@pytest.mark.no_readiness_stub
def test_providers_ignores_hosted_readiness(monkeypatch) -> None:
    """`tracker providers` is static informational output.

    It must run successfully even when hosted readiness would otherwise
    fail (e.g. no auth token, no SaaS host config).  The rollout gate is
    still enforced by the conditional registration in
    ``cli/commands/__init__.py`` and by the defense-in-depth check in
    ``tracker_callback()``, but the per-command readiness chain is
    deliberately NOT consulted for this command.
    """
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    from specify_cli.cli.commands import tracker as tracker_module

    # Set a trip-wire: if any code path called evaluate_readiness,
    # the command would exit 1 with this failing state.  The fact that
    # the command exits 0 is the proof that readiness is no longer
    # consulted.
    trip_wire = ReadinessResult(
        state=ReadinessState.MISSING_AUTH,
        message="tripwire: readiness should not be consulted by providers",
        next_action="Do not run readiness for providers.",
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.evaluate_readiness",
        lambda **_kwargs: trip_wire,
    )

    result = runner.invoke(tracker_module.app, ["providers"])
    assert result.exit_code == 0, result.output
    assert "tripwire" not in result.output
    assert "Supported providers" in result.output
    assert "linear" in result.output  # a SaaS provider
    assert "beads" in result.output  # a local provider


@pytest.mark.no_readiness_stub
def test_providers_still_blocked_when_rollout_disabled(monkeypatch) -> None:
    """When the rollout gate is off, `tracker providers` is unreachable.

    The command group is hidden at registration time in
    ``cli/commands/__init__.py``; this test exercises the defense-in-depth
    guard in ``tracker_callback`` by invoking the tracker app object
    directly with the env var unset.  This verifies that removing the
    per-command readiness call did not accidentally open a hole in the
    rollout gate itself.
    """
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    from specify_cli.cli.commands import tracker as tracker_module

    result = runner.invoke(tracker_module.app, ["providers"])
    assert result.exit_code == 1
    assert "not enabled" in result.output.lower()


@pytest.mark.no_readiness_stub
def test_status_readiness_missing_auth_message(monkeypatch, tmp_path) -> None:
    """status command exits 1 with MISSING_AUTH wording when auth probe fails."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    from specify_cli.cli.commands import tracker as tracker_module
    from specify_cli.saas.readiness import _WORDING  # noqa: PLC2701

    msg, action = _WORDING[ReadinessState.MISSING_AUTH]
    failing_result = ReadinessResult(
        state=ReadinessState.MISSING_AUTH,
        message=msg,
        next_action=action,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.evaluate_readiness",
        lambda **_kwargs: failing_result,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.require_repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker._resolve_active_feature_slug",
        lambda _repo_root: None,
    )

    result = runner.invoke(tracker_module.app, ["status"])
    assert result.exit_code == 1
    assert msg in result.output
    assert action in result.output


@pytest.mark.no_readiness_stub
def test_status_readiness_ready_passes_through(monkeypatch, tmp_path) -> None:
    """When readiness is READY, status proceeds to the service call."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    from specify_cli.cli.commands import tracker as tracker_module

    ready_result = ReadinessResult(
        state=ReadinessState.READY,
        message="",
        next_action=None,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.evaluate_readiness",
        lambda **_kwargs: ready_result,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.require_repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker._resolve_active_feature_slug",
        lambda _repo_root: None,
    )

    mock_svc = MagicMock()
    mock_svc.status.return_value = {
        "configured": True,
        "provider": "linear",
        "identity_path": {"type": "saas", "provider": "linear"},
        "sync_state": "idle",
    }

    with patch("specify_cli.cli.commands.tracker._service", return_value=mock_svc):
        result = runner.invoke(tracker_module.app, ["status"])
    assert result.exit_code == 0
    assert "linear" in result.output


# ---------------------------------------------------------------------------
# T024: Manual-mode tests
# ---------------------------------------------------------------------------


@pytest.mark.no_readiness_stub
def test_sync_pull_manual_mode_exits_zero(monkeypatch, tmp_path) -> None:
    """sync pull exits 0 and prints manual-mode message when policy=manual."""
    from specify_cli.sync.config import BackgroundDaemonPolicy, SyncConfig

    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    from specify_cli.cli.commands import tracker as tracker_module

    # Stub readiness to READY
    ready_result = ReadinessResult(
        state=ReadinessState.READY,
        message="",
        next_action=None,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.evaluate_readiness",
        lambda **_kwargs: ready_result,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.require_repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker._resolve_active_feature_slug",
        lambda _repo_root: None,
    )
    # Stub daemon policy to MANUAL by patching SyncConfig in its home module
    mock_cfg = MagicMock(spec=SyncConfig)
    mock_cfg.get_background_daemon.return_value = BackgroundDaemonPolicy.MANUAL
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.SyncConfig",
        lambda: mock_cfg,
    )

    result = runner.invoke(tracker_module.app, ["sync", "pull"])
    assert result.exit_code == 0, result.output
    assert "manual mode" in result.output
    assert "spec-kitty sync run" in result.output


@pytest.mark.no_readiness_stub
def test_sync_run_manual_mode_proceeds(monkeypatch, tmp_path) -> None:
    """sync run prints the one-shot message and proceeds (does not exit 0)."""
    from specify_cli.sync.config import BackgroundDaemonPolicy, SyncConfig
    from specify_cli.cli.commands.tracker import _MANUAL_MODE_SYNC_RUN_MESSAGE

    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    from specify_cli.cli.commands import tracker as tracker_module

    # Stub readiness to READY
    ready_result = ReadinessResult(
        state=ReadinessState.READY,
        message="",
        next_action=None,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.evaluate_readiness",
        lambda **_kwargs: ready_result,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.require_repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker._resolve_active_feature_slug",
        lambda _repo_root: None,
    )
    # Stub daemon policy to MANUAL by patching SyncConfig in its home module
    mock_cfg = MagicMock(spec=SyncConfig)
    mock_cfg.get_background_daemon.return_value = BackgroundDaemonPolicy.MANUAL
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.SyncConfig",
        lambda: mock_cfg,
    )
    # sync run MUST proceed to the service (not exit 0)
    mock_svc = MagicMock()
    mock_svc.sync_run.return_value = {
        "status": "complete",
        "summary": {"total": 0, "succeeded": 0, "failed": 0, "skipped": 0},
    }

    with patch("specify_cli.cli.commands.tracker._service", return_value=mock_svc):
        result = runner.invoke(tracker_module.app, ["sync", "run"])
    assert result.exit_code == 0, result.output
    assert _MANUAL_MODE_SYNC_RUN_MESSAGE in result.output
    # Verify sync_run was actually called (did not exit early)
    mock_svc.sync_run.assert_called_once()


@pytest.mark.no_readiness_stub
def test_sync_push_manual_mode_exits_zero(monkeypatch, tmp_path) -> None:
    """sync push exits 0 with manual-mode message when policy=manual."""
    from specify_cli.sync.config import BackgroundDaemonPolicy, SyncConfig

    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    from specify_cli.cli.commands import tracker as tracker_module

    ready_result = ReadinessResult(
        state=ReadinessState.READY,
        message="",
        next_action=None,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.evaluate_readiness",
        lambda **_kwargs: ready_result,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.require_repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker._resolve_active_feature_slug",
        lambda _repo_root: None,
    )
    mock_cfg = MagicMock(spec=SyncConfig)
    mock_cfg.get_background_daemon.return_value = BackgroundDaemonPolicy.MANUAL
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.SyncConfig",
        lambda: mock_cfg,
    )

    result = runner.invoke(tracker_module.app, ["sync", "push"])
    assert result.exit_code == 0, result.output
    assert "manual mode" in result.output


# ---------------------------------------------------------------------------
# Provider-aware sync readiness (local-provider bypass)
# ---------------------------------------------------------------------------
#
# Local tracker providers (beads, fp) use direct connectors and do not
# interact with the SaaS background daemon or the hosted readiness chain.
# Sync commands for local-provider bindings must NOT trip on manual daemon
# policy, missing auth, missing host config, or reachability failures —
# those are SaaS concerns.  These tests assert that the provider-aware
# helpers in ``tracker.py`` (``_is_local_binding`` and
# ``_check_sync_readiness``) short-circuit correctly.


def _local_binding_config():
    """Return a TrackerProjectConfig that reports a local (beads) binding."""
    from specify_cli.tracker.config import TrackerProjectConfig

    return TrackerProjectConfig(
        provider="beads",
        workspace="local-workspace",
    )


@pytest.mark.no_readiness_stub
def test_sync_pull_local_provider_ignores_manual_daemon_policy(monkeypatch, tmp_path) -> None:
    """Local-provider sync pull proceeds even when daemon policy is MANUAL.

    Regression guard against the P2 bug where the manual-mode check
    suppressed local sync commands that have no relationship to the SaaS
    background daemon.
    """
    from specify_cli.sync.config import BackgroundDaemonPolicy, SyncConfig

    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    from specify_cli.cli.commands import tracker as tracker_module

    # Trip-wire: if readiness is ever called, the command would fail with
    # this message.  A passing test proves that the local-binding
    # short-circuit fired before readiness was consulted.
    trip_wire = ReadinessResult(
        state=ReadinessState.MISSING_AUTH,
        message="tripwire: local bindings must skip readiness",
        next_action="Do not run readiness for local providers.",
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.evaluate_readiness",
        lambda **_kwargs: trip_wire,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.require_repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.load_tracker_config",
        lambda _repo_root: _local_binding_config(),
    )
    # Daemon policy is MANUAL — would normally suppress sync pull with
    # the SaaS manual-mode message and exit 0 before the service call.
    mock_cfg = MagicMock(spec=SyncConfig)
    mock_cfg.get_background_daemon.return_value = BackgroundDaemonPolicy.MANUAL
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.SyncConfig",
        lambda: mock_cfg,
    )

    mock_svc = MagicMock()
    mock_svc.sync_pull.return_value = {
        "provider": "beads",
        "stats": {"pulled_created": 1, "pulled_updated": 0, "skipped": 0},
    }
    with patch("specify_cli.cli.commands.tracker._service", return_value=mock_svc):
        result = runner.invoke(tracker_module.app, ["sync", "pull"])

    assert result.exit_code == 0, result.output
    assert "tripwire" not in result.output
    assert "manual mode" not in result.output.lower()
    # The service call must have actually run — not exited early.
    mock_svc.sync_pull.assert_called_once()
    assert "beads" in result.output


@pytest.mark.no_readiness_stub
def test_sync_push_local_provider_ignores_manual_daemon_policy(monkeypatch, tmp_path) -> None:
    """Local-provider sync push proceeds even when daemon policy is MANUAL."""
    from specify_cli.sync.config import BackgroundDaemonPolicy, SyncConfig

    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    from specify_cli.cli.commands import tracker as tracker_module

    trip_wire = ReadinessResult(
        state=ReadinessState.MISSING_HOST_CONFIG,
        message="tripwire: local bindings must skip readiness",
        next_action="Do not run readiness for local providers.",
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.evaluate_readiness",
        lambda **_kwargs: trip_wire,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.require_repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.load_tracker_config",
        lambda _repo_root: _local_binding_config(),
    )
    mock_cfg = MagicMock(spec=SyncConfig)
    mock_cfg.get_background_daemon.return_value = BackgroundDaemonPolicy.MANUAL
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.SyncConfig",
        lambda: mock_cfg,
    )

    mock_svc = MagicMock()
    mock_svc.sync_push.return_value = {
        "provider": "beads",
        "stats": {"pushed_created": 0, "pushed_updated": 1, "skipped": 0},
    }
    with patch("specify_cli.cli.commands.tracker._service", return_value=mock_svc):
        result = runner.invoke(tracker_module.app, ["sync", "push"])

    assert result.exit_code == 0, result.output
    assert "tripwire" not in result.output
    assert "manual mode" not in result.output.lower()
    mock_svc.sync_push.assert_called_once()


@pytest.mark.no_readiness_stub
def test_sync_run_local_provider_ignores_manual_daemon_policy(monkeypatch, tmp_path) -> None:
    """Local-provider sync run proceeds to the service call under MANUAL policy."""
    from specify_cli.sync.config import BackgroundDaemonPolicy, SyncConfig

    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    from specify_cli.cli.commands import tracker as tracker_module

    trip_wire = ReadinessResult(
        state=ReadinessState.MISSING_MISSION_BINDING,
        message="tripwire: local bindings must skip readiness",
        next_action="Do not run readiness for local providers.",
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.evaluate_readiness",
        lambda **_kwargs: trip_wire,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.require_repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.load_tracker_config",
        lambda _repo_root: _local_binding_config(),
    )
    mock_cfg = MagicMock(spec=SyncConfig)
    mock_cfg.get_background_daemon.return_value = BackgroundDaemonPolicy.MANUAL
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.SyncConfig",
        lambda: mock_cfg,
    )

    mock_svc = MagicMock()
    mock_svc.sync_run.return_value = {
        "provider": "beads",
        "stats": {"pulled_created": 1, "pushed_created": 1, "skipped": 0},
    }
    with patch("specify_cli.cli.commands.tracker._service", return_value=mock_svc):
        result = runner.invoke(tracker_module.app, ["sync", "run"])

    assert result.exit_code == 0, result.output
    assert "tripwire" not in result.output
    # sync_run's manual-mode message is informational (not an early exit);
    # for local bindings the message must not appear at all.
    assert "manual mode" not in result.output.lower()
    mock_svc.sync_run.assert_called_once()


@pytest.mark.no_readiness_stub
def test_sync_publish_local_provider_ignores_manual_daemon_policy(monkeypatch, tmp_path) -> None:
    """Local-provider sync publish proceeds under MANUAL policy."""
    from specify_cli.sync.config import BackgroundDaemonPolicy, SyncConfig

    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    from specify_cli.cli.commands import tracker as tracker_module

    trip_wire = ReadinessResult(
        state=ReadinessState.HOST_UNREACHABLE,
        message="tripwire: local bindings must skip readiness",
        next_action="Do not run readiness for local providers.",
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.evaluate_readiness",
        lambda **_kwargs: trip_wire,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.require_repo_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.load_tracker_config",
        lambda _repo_root: _local_binding_config(),
    )
    mock_cfg = MagicMock(spec=SyncConfig)
    mock_cfg.get_background_daemon.return_value = BackgroundDaemonPolicy.MANUAL
    monkeypatch.setattr(
        "specify_cli.cli.commands.tracker.SyncConfig",
        lambda: mock_cfg,
    )

    mock_svc = MagicMock()
    mock_svc.sync_publish.return_value = {
        "provider": "beads",
        "status": "complete",
    }
    with patch("specify_cli.cli.commands.tracker._service", return_value=mock_svc):
        result = runner.invoke(tracker_module.app, ["sync", "publish"])

    assert result.exit_code == 0, result.output
    assert "tripwire" not in result.output
    assert "manual mode" not in result.output.lower()
    mock_svc.sync_publish.assert_called_once()


# ---------------------------------------------------------------------------
# Module-level import structural guardrail (RISK-2 from mission review)
# ---------------------------------------------------------------------------


def test_tracker_keeps_readiness_imports_at_module_level() -> None:
    """Structural guardrail: ``evaluate_readiness`` / ``SyncConfig`` must be
    module-level imports on ``specify_cli.cli.commands.tracker``.

    The manual-mode tests in this file and the readiness-failure tests in
    the discover/status modules all patch these names via
    ``monkeypatch.setattr("specify_cli.cli.commands.tracker.<name>", ...)``.
    If a future refactor moves either import back to function-local (e.g.
    to avoid a perceived circular dependency), those patches would silently
    stop applying and every manual-mode / readiness-failure test would
    regress into false passes.  This guardrail fails loudly instead.
    """
    from specify_cli.cli.commands import tracker as tracker_module
    from specify_cli.saas import readiness as readiness_module
    from specify_cli.sync import config as config_module

    assert hasattr(tracker_module, "evaluate_readiness"), (
        "tracker.py must import evaluate_readiness at module level so tests "
        "can monkeypatch the consumer binding."
    )
    assert tracker_module.evaluate_readiness is readiness_module.evaluate_readiness

    assert hasattr(tracker_module, "SyncConfig"), (
        "tracker.py must import SyncConfig at module level so tests can "
        "monkeypatch the consumer binding."
    )
    assert tracker_module.SyncConfig is config_module.SyncConfig

    assert hasattr(tracker_module, "BackgroundDaemonPolicy"), (
        "tracker.py must import BackgroundDaemonPolicy at module level so "
        "tests can inspect the daemon policy decision."
    )
    assert tracker_module.BackgroundDaemonPolicy is config_module.BackgroundDaemonPolicy
