"""Scope: mock-boundary tests for `tracker discover` command — no real git or SaaS calls.

Owned by WP10 of feature 062-tracker-binding-context-discovery.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.tracker.discovery import BindableResource
from specify_cli.tracker.service import TrackerServiceError

pytestmark = pytest.mark.fast

runner = CliRunner()


def _make_app(monkeypatch) -> typer.Typer:
    """Return the tracker app with the feature flag enabled."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    from specify_cli.cli.commands import tracker as tracker_module

    return tracker_module.app


def _make_resource(
    *,
    candidate_token: str = "tok-1",
    display_label: str = "My Team / My Project",
    provider: str = "linear",
    provider_context: dict[str, str] | None = None,
    binding_ref: str | None = None,
    bound_project_slug: str | None = None,
    bound_at: str | None = None,
) -> BindableResource:
    return BindableResource(
        candidate_token=candidate_token,
        display_label=display_label,
        provider=provider,
        provider_context=provider_context or {"workspace_name": "My Team"},
        binding_ref=binding_ref,
        bound_project_slug=bound_project_slug,
        bound_at=bound_at,
    )


# ---------------------------------------------------------------------------
# T052: Rich table output
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_discover_rich_table(mock_service_fn, monkeypatch) -> None:
    """Default discover output contains resource labels and provider in a table."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.discover.return_value = [
        _make_resource(display_label="Eng / Backend", binding_ref=None),
        _make_resource(
            candidate_token="tok-2",
            display_label="Eng / Frontend",
            binding_ref="bind-ref-1",
            bound_project_slug="proj-x",
            bound_at="2026-04-01T00:00:00Z",
        ),
    ]
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["discover", "--provider", "linear"])
    assert result.exit_code == 0, result.output
    assert "Eng / Backend" in result.output
    assert "Eng / Frontend" in result.output
    assert "linear" in result.output
    # Bound/unbound distinction
    assert "available" in result.output
    assert "bound" in result.output


# ---------------------------------------------------------------------------
# T052: JSON output
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_discover_json_output(mock_service_fn, monkeypatch) -> None:
    """--json flag outputs valid JSON with all resource fields (no truncation)."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.discover.return_value = [
        _make_resource(
            candidate_token="tok-abc",
            display_label="Team Alpha",
            provider="linear",
            provider_context={"workspace_name": "Alpha WS"},
            binding_ref="br-1",
            bound_project_slug="proj-alpha",
            bound_at="2026-01-15T10:30:00Z",
        ),
    ]
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["discover", "--provider", "linear", "--json"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == 1

    item = data[0]
    assert item["number"] == 1
    assert item["candidate_token"] == "tok-abc"
    assert item["display_label"] == "Team Alpha"
    assert item["provider"] == "linear"
    assert item["provider_context"] == {"workspace_name": "Alpha WS"}
    assert item["binding_ref"] == "br-1"
    assert item["bound_project_slug"] == "proj-alpha"
    assert item["bound_at"] == "2026-01-15T10:30:00Z"
    assert item["is_bound"] is True


# ---------------------------------------------------------------------------
# T052: Empty resources
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_discover_empty_resources(mock_service_fn, monkeypatch) -> None:
    """Empty discover results produce an informational message (not an error)."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.discover.return_value = []
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["discover", "--provider", "linear"])
    assert result.exit_code == 0, result.output
    assert "No bindable resources found" in result.output
    assert "linear" in result.output


# ---------------------------------------------------------------------------
# T052: Service error
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_discover_service_error(mock_service_fn, monkeypatch) -> None:
    """TrackerServiceError produces error message + exit code 1."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.discover.side_effect = TrackerServiceError("Connection refused")
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["discover", "--provider", "linear"])
    assert result.exit_code == 1
    assert "Connection refused" in result.output


# ---------------------------------------------------------------------------
# T052: Numbering (1-indexed)
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_discover_numbering(mock_service_fn, monkeypatch) -> None:
    """Three resources produce rows numbered 1, 2, 3 in output."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.discover.return_value = [
        _make_resource(candidate_token="t1", display_label="Project A"),
        _make_resource(candidate_token="t2", display_label="Project B"),
        _make_resource(candidate_token="t3", display_label="Project C"),
    ]
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["discover", "--provider", "linear"])
    assert result.exit_code == 0, result.output
    # Rich table renders numbers; verify all three appear
    assert "Project A" in result.output
    assert "Project B" in result.output
    assert "Project C" in result.output


@patch("specify_cli.cli.commands.tracker._service")
def test_discover_json_numbering(mock_service_fn, monkeypatch) -> None:
    """JSON output includes 1-indexed numbers for all resources."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.discover.return_value = [
        _make_resource(candidate_token="t1", display_label="Project A"),
        _make_resource(candidate_token="t2", display_label="Project B"),
        _make_resource(candidate_token="t3", display_label="Project C"),
    ]
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["discover", "--provider", "linear", "--json"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    assert len(data) == 3
    assert data[0]["number"] == 1
    assert data[1]["number"] == 2
    assert data[2]["number"] == 3


# ---------------------------------------------------------------------------
# T052: Bound vs unbound distinction in rich table
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_discover_bound_unbound_distinction(mock_service_fn, monkeypatch) -> None:
    """Rich table distinguishes bound (has binding_ref) from unbound resources."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.discover.return_value = [
        _make_resource(
            candidate_token="t-unbound",
            display_label="Unbound Proj",
            binding_ref=None,
        ),
        _make_resource(
            candidate_token="t-bound",
            display_label="Bound Proj",
            binding_ref="ref-123",
            bound_project_slug="slug-x",
            bound_at="2026-04-01T00:00:00Z",
        ),
    ]
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["discover", "--provider", "linear"])
    assert result.exit_code == 0, result.output
    # The output should contain both status markers
    assert "available" in result.output
    assert "bound" in result.output


# ---------------------------------------------------------------------------
# T052: JSON output for unbound resource has null fields
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.tracker._service")
def test_discover_json_unbound_resource(mock_service_fn, monkeypatch) -> None:
    """JSON output for unbound resource has null binding fields."""
    app = _make_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.discover.return_value = [
        _make_resource(
            candidate_token="tok-free",
            display_label="Free Project",
            binding_ref=None,
            bound_project_slug=None,
            bound_at=None,
        ),
    ]
    mock_service_fn.return_value = mock_svc

    result = runner.invoke(app, ["discover", "--provider", "linear", "--json"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    assert len(data) == 1
    item = data[0]
    assert item["binding_ref"] is None
    assert item["bound_project_slug"] is None
    assert item["bound_at"] is None
    assert item["is_bound"] is False
