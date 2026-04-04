"""WP12-owned tests for ``tracker status --all`` CLI behaviour.

Scope: mock-boundary tests for the --all flag on the status command,
installation-wide output formatting, SaaS-only guard, and error handling.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.tracker.service import TrackerServiceError

pytestmark = pytest.mark.fast

runner = CliRunner()


def _make_app(monkeypatch) -> typer.Typer:
    """Return the tracker app with the feature flag enabled."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    from specify_cli.cli.commands import tracker as tracker_module

    return tracker_module.app


# ---------------------------------------------------------------------------
# T063: test_status_all_displays_installation_summary
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_status_all_displays_installation_summary(mock_service_fn, monkeypatch) -> None:
    """--all flag renders installation-wide summary with Rich panel."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.status.return_value = {
        "provider": "linear",
        "connected": True,
        "bindings": 3,
        "resource_count": 42,
    }
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["status", "--all"])
    assert result.exit_code == 0
    mock_svc.status.assert_called_once_with(all=True)
    # The Rich panel title must be present
    assert "Installation-wide tracker status" in result.output
    assert "linear" in result.output


# ---------------------------------------------------------------------------
# T063: test_status_all_json
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_status_all_json(mock_service_fn, monkeypatch) -> None:
    """--all --json returns raw JSON without Rich formatting."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.status.return_value = {
        "provider": "linear",
        "connected": True,
        "bindings": 5,
    }
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["status", "--all", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["provider"] == "linear"
    assert data["bindings"] == 5
    # Rich panel should NOT appear in JSON mode
    assert "Installation-wide" not in result.output


# ---------------------------------------------------------------------------
# T063: test_status_all_local_provider_error
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_status_all_local_provider_error(mock_service_fn, monkeypatch) -> None:
    """--all with a local provider produces a clear error and exit 1."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.status.side_effect = TrackerServiceError(
        "Installation-wide status (--all) is only available for SaaS providers."
    )
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["status", "--all"])
    assert result.exit_code == 1
    assert "only available for SaaS providers" in result.output


# ---------------------------------------------------------------------------
# T063: test_status_all_service_error_generic
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_status_all_service_error_generic(mock_service_fn, monkeypatch) -> None:
    """TrackerServiceError during --all is rendered and exits 1."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.status.side_effect = TrackerServiceError("Network timeout")
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["status", "--all"])
    assert result.exit_code == 1
    assert "Network timeout" in result.output


# ---------------------------------------------------------------------------
# T063: test_status_default_project_scoped (unchanged behaviour)
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_status_default_project_scoped(mock_service_fn, monkeypatch) -> None:
    """Without --all, status shows project-scoped output as before."""
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
    mock_svc.status.assert_called_once_with(all=False)
    assert "Tracker status" in result.output
    assert "linear" in result.output
    # Installation-wide panel should NOT appear
    assert "Installation-wide" not in result.output


# ---------------------------------------------------------------------------
# T063: test_status_default_not_configured
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_status_default_not_configured(mock_service_fn, monkeypatch) -> None:
    """Without --all and no tracker configured, shows 'not configured'."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.status.return_value = {"configured": False}
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "not configured" in result.output


# ---------------------------------------------------------------------------
# T063: test_status_all_shows_binding_list
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_status_all_shows_binding_list(mock_service_fn, monkeypatch) -> None:
    """--all with bindings as a list renders individual projects."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.status.return_value = {
        "provider": "jira",
        "connected": True,
        "bindings": [
            {
                "project_name": "Project Alpha",
                "project_slug": "proj-a",
                "status": "active",
                "bound_at": "2026-04-04T10:00:00Z",
            },
            {
                "project_slug": "proj-b",
                "status": "paused",
            },
        ],
        "resource_count": 100,
    }
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["status", "--all"])
    assert result.exit_code == 0
    assert "Installation-wide tracker status" in result.output
    assert "jira" in result.output
    assert "Project Alpha" in result.output
    assert "proj-b" in result.output
    assert "active" in result.output
    assert "paused" in result.output
    assert "2026-04-04T10:00:00Z" in result.output
    assert "Bindings  2" not in result.output


# ---------------------------------------------------------------------------
# T063: test_status_all_error_does_not_print_rich_panel
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_status_all_error_does_not_print_rich_panel(mock_service_fn, monkeypatch) -> None:
    """On error, the Rich panel is not rendered -- only the error message."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.status.side_effect = TrackerServiceError("Auth expired")
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["status", "--all"])
    assert result.exit_code == 1
    assert "Installation-wide tracker status" not in result.output
    assert "Auth expired" in result.output
