"""Integration and acceptance tests for tracker discovery binding flows."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.sync.project_identity import ProjectIdentity, atomic_write_config
from specify_cli.tracker.config import (
    TrackerProjectConfig,
    load_tracker_config,
    save_tracker_config,
)
from specify_cli.tracker.discovery import BindableResource
from specify_cli.tracker.saas_client import SaaSTrackerClient, SaaSTrackerClientError
from specify_cli.tracker.service import StaleBindingError, TrackerService, TrackerServiceError

pytestmark = pytest.mark.fast

cli_runner = CliRunner()


@pytest.fixture()
def identity() -> ProjectIdentity:
    return ProjectIdentity(
        project_uuid=UUID("11111111-1111-4111-8111-111111111111"),
        project_slug="spec-kitty",
        node_id="0123456789ab",
        repo_slug="acme/spec-kitty",
    )


@pytest.fixture()
def project_identity(identity: ProjectIdentity) -> dict[str, object]:
    return identity.to_dict()


@pytest.fixture()
def repo_root(tmp_path: Path, identity: ProjectIdentity) -> Path:
    atomic_write_config(tmp_path / ".kittify" / "config.yaml", identity)
    return tmp_path


@pytest.fixture()
def mock_client() -> MagicMock:
    return MagicMock(spec=SaaSTrackerClient)


def test_scenario_1_auto_bind_single_match_persists_binding_config(
    repo_root: Path,
    project_identity: dict[str, object],
    mock_client: MagicMock,
) -> None:
    mock_client.bind_resolve.return_value = {
        "match_type": "exact",
        "binding_ref": "bind-linear-eng",
        "display_label": "Engineering Tracker",
        "provider_context": {
            "team_name": "Engineering",
            "workspace_name": "Acme Corp",
        },
        "candidates": [],
    }

    with patch("specify_cli.tracker.saas_service.SaaSTrackerClient", return_value=mock_client):
        result = TrackerService(repo_root).bind(
            provider="linear",
            project_identity=project_identity,
        )

    mock_client.bind_resolve.assert_called_once_with("linear", project_identity)
    mock_client.bind_confirm.assert_not_called()
    assert result.binding_ref == "bind-linear-eng"
    assert result.provider_context == {
        "team_name": "Engineering",
        "workspace_name": "Acme Corp",
    }

    config = load_tracker_config(repo_root)
    assert config.provider == "linear"
    assert config.binding_ref == "bind-linear-eng"
    assert config.display_label == "Engineering Tracker"
    assert config.provider_context == {
        "team_name": "Engineering",
        "workspace_name": "Acme Corp",
    }
    assert config.project_slug is None


def test_scenario_2_ambiguous_selection_uses_requested_candidate_position(
    repo_root: Path,
    project_identity: dict[str, object],
    mock_client: MagicMock,
) -> None:
    mock_client.bind_resolve.return_value = {
        "match_type": "candidates",
        "candidates": [
            {
                "candidate_token": "candidate-third",
                "display_label": "Third",
                "confidence": "low",
                "match_reason": "fuzzy",
                "sort_position": 2,
            },
            {
                "candidate_token": "candidate-first",
                "display_label": "First",
                "confidence": "high",
                "match_reason": "slug",
                "sort_position": 0,
            },
            {
                "candidate_token": "candidate-second",
                "display_label": "Second",
                "confidence": "medium",
                "match_reason": "repo",
                "sort_position": 1,
            },
        ],
    }
    mock_client.bind_confirm.return_value = {
        "binding_ref": "bind-candidate-second",
        "display_label": "Second",
        "provider": "linear",
        "provider_context": {"team_name": "Platform"},
        "bound_at": "2026-04-04T12:00:00Z",
    }

    with patch("specify_cli.tracker.saas_service.SaaSTrackerClient", return_value=mock_client):
        result = TrackerService(repo_root).bind(
            provider="linear",
            project_identity=project_identity,
            select_n=2,
        )

    mock_client.bind_confirm.assert_called_once_with(
        "linear",
        "candidate-second",
        project_identity,
    )
    assert result.binding_ref == "bind-candidate-second"

    config = load_tracker_config(repo_root)
    assert config.binding_ref == "bind-candidate-second"
    assert config.display_label == "Second"
    assert config.provider_context == {"team_name": "Platform"}


def test_scenario_3_no_candidates_raises_without_changing_config(
    repo_root: Path,
    project_identity: dict[str, object],
    mock_client: MagicMock,
) -> None:
    mock_client.bind_resolve.return_value = {
        "match_type": "none",
        "candidates": [],
    }

    with (
        patch("specify_cli.tracker.saas_service.SaaSTrackerClient", return_value=mock_client),
        pytest.raises(TrackerServiceError) as exc_info,
    ):
        TrackerService(repo_root).bind(
            provider="linear",
            project_identity=project_identity,
        )

    assert "No bindable resources found" in str(exc_info.value)
    assert "raw metadata" not in str(exc_info.value).lower()
    _assert_tracker_binding_empty(repo_root)


def test_scenario_7b_host_unavailable_propagates_without_changing_config(
    repo_root: Path,
    project_identity: dict[str, object],
    mock_client: MagicMock,
) -> None:
    mock_client.bind_resolve.side_effect = SaaSTrackerClientError(
        "Cannot connect to Spec Kitty SaaS at https://saas.example.com.",
    )

    with (
        patch("specify_cli.tracker.saas_service.SaaSTrackerClient", return_value=mock_client),
        pytest.raises(SaaSTrackerClientError, match="Cannot connect"),
    ):
        TrackerService(repo_root).bind(
            provider="linear",
            project_identity=project_identity,
        )

    _assert_tracker_binding_empty(repo_root)


def test_scenario_4_valid_bind_ref_persists_validated_binding(
    repo_root: Path,
    project_identity: dict[str, object],
    mock_client: MagicMock,
) -> None:
    mock_client.bind_validate.return_value = {
        "valid": True,
        "binding_ref": "bind-known",
        "display_label": "Known Binding",
        "provider": "linear",
        "provider_context": {"team_name": "Platform"},
    }

    with patch("specify_cli.tracker.saas_service.SaaSTrackerClient", return_value=mock_client):
        result = TrackerService(repo_root).bind(
            provider="linear",
            bind_ref="bind-known",
            project_identity=project_identity,
        )

    mock_client.bind_validate.assert_called_once_with(
        "linear",
        "bind-known",
        project_identity,
    )
    assert result.binding_ref == "bind-known"

    config = load_tracker_config(repo_root)
    assert config.provider == "linear"
    assert config.binding_ref == "bind-known"
    assert config.display_label == "Known Binding"
    assert config.provider_context == {"team_name": "Platform"}


def test_scenario_4_invalid_bind_ref_raises_without_changing_config(
    repo_root: Path,
    project_identity: dict[str, object],
    mock_client: MagicMock,
) -> None:
    mock_client.bind_validate.return_value = {
        "valid": False,
        "binding_ref": "bind-bad",
        "reason": "binding expired",
        "guidance": "Run `spec-kitty tracker bind --provider linear` to rebind.",
    }

    with (
        patch("specify_cli.tracker.saas_service.SaaSTrackerClient", return_value=mock_client),
        pytest.raises(TrackerServiceError) as exc_info,
    ):
        TrackerService(repo_root).bind(
            provider="linear",
            bind_ref="bind-bad",
            project_identity=project_identity,
        )

    assert "binding expired" in str(exc_info.value)
    assert "rebind" in str(exc_info.value)
    _assert_tracker_binding_empty(repo_root)


def test_scenario_5_select_n_one_picks_first_ranked_candidate(
    repo_root: Path,
    project_identity: dict[str, object],
    mock_client: MagicMock,
) -> None:
    mock_client.bind_resolve.return_value = {
        "match_type": "candidates",
        "candidates": [
            {
                "candidate_token": "candidate-second",
                "display_label": "Second",
                "confidence": "medium",
                "match_reason": "repo",
                "sort_position": 1,
            },
            {
                "candidate_token": "candidate-first",
                "display_label": "First",
                "confidence": "high",
                "match_reason": "slug",
                "sort_position": 0,
            },
        ],
    }
    mock_client.bind_confirm.return_value = {
        "binding_ref": "bind-candidate-first",
        "display_label": "First",
        "provider": "linear",
        "provider_context": {"team_name": "Engineering"},
        "bound_at": "2026-04-04T12:01:00Z",
    }

    with patch("specify_cli.tracker.saas_service.SaaSTrackerClient", return_value=mock_client):
        result = TrackerService(repo_root).bind(
            provider="linear",
            project_identity=project_identity,
            select_n=1,
        )

    mock_client.bind_confirm.assert_called_once_with(
        "linear",
        "candidate-first",
        project_identity,
    )
    assert result.binding_ref == "bind-candidate-first"
    assert load_tracker_config(repo_root).binding_ref == "bind-candidate-first"


def test_scenario_6_legacy_project_slug_status_opportunistically_upgrades_binding_ref(
    repo_root: Path,
    mock_client: MagicMock,
) -> None:
    save_tracker_config(
        repo_root,
        TrackerProjectConfig(provider="linear", project_slug="legacy-proj"),
    )
    mock_client.status.return_value = {
        "provider": "linear",
        "project_slug": "legacy-proj",
        "connected": True,
        "binding_ref": "bind-upgraded",
        "display_label": "Legacy Project",
        "provider_context": {"team_name": "Engineering"},
    }

    with patch("specify_cli.tracker.saas_service.SaaSTrackerClient", return_value=mock_client):
        result = TrackerService(repo_root).status()

    assert result["binding_ref"] == "bind-upgraded"
    mock_client.status.assert_called_once_with("linear", project_slug="legacy-proj")

    config = load_tracker_config(repo_root)
    assert config.project_slug == "legacy-proj"
    assert config.binding_ref == "bind-upgraded"
    assert config.display_label == "Legacy Project"
    assert config.provider_context == {"team_name": "Engineering"}


def test_scenario_7a_legacy_project_slug_status_without_upgrade_metadata_leaves_config_unchanged(
    repo_root: Path,
    mock_client: MagicMock,
) -> None:
    save_tracker_config(
        repo_root,
        TrackerProjectConfig(provider="linear", project_slug="legacy-proj"),
    )
    mock_client.status.return_value = {
        "provider": "linear",
        "project_slug": "legacy-proj",
        "connected": True,
    }

    with patch("specify_cli.tracker.saas_service.SaaSTrackerClient", return_value=mock_client):
        result = TrackerService(repo_root).status()

    assert result["connected"] is True
    mock_client.status.assert_called_once_with("linear", project_slug="legacy-proj")

    config = load_tracker_config(repo_root)
    assert config.project_slug == "legacy-proj"
    assert config.binding_ref is None
    assert config.display_label is None
    assert config.provider_context is None


def test_scenario_11_stale_binding_raises_actionable_error_without_clearing_config(
    repo_root: Path,
    mock_client: MagicMock,
) -> None:
    save_tracker_config(
        repo_root,
        TrackerProjectConfig(provider="linear", binding_ref="bind-stale"),
    )
    mock_client.status.side_effect = SaaSTrackerClientError(
        "binding_not_found",
        error_code="binding_not_found",
    )

    with (
        patch("specify_cli.tracker.saas_service.SaaSTrackerClient", return_value=mock_client),
        pytest.raises(StaleBindingError) as exc_info,
    ):
        TrackerService(repo_root).status()

    mock_client.status.assert_called_once_with("linear", binding_ref="bind-stale")
    message = str(exc_info.value)
    assert "bind-stale" in message
    assert "spec-kitty tracker bind --provider linear" in message
    assert exc_info.value.binding_ref == "bind-stale"

    config = load_tracker_config(repo_root)
    assert config.binding_ref == "bind-stale"
    assert config.project_slug is None


def test_scenario_12_stale_binding_with_legacy_slug_does_not_fallback_to_project_slug(
    repo_root: Path,
    mock_client: MagicMock,
) -> None:
    save_tracker_config(
        repo_root,
        TrackerProjectConfig(
            provider="linear",
            binding_ref="bind-stale",
            project_slug="legacy-proj",
        ),
    )
    mock_client.status.side_effect = SaaSTrackerClientError(
        "binding_not_found",
        error_code="binding_not_found",
    )

    with (
        patch("specify_cli.tracker.saas_service.SaaSTrackerClient", return_value=mock_client),
        pytest.raises(StaleBindingError, match="bind-stale"),
    ):
        TrackerService(repo_root).status()

    mock_client.status.assert_called_once_with("linear", binding_ref="bind-stale")
    config = load_tracker_config(repo_root)
    assert config.binding_ref == "bind-stale"
    assert config.project_slug == "legacy-proj"


def _assert_tracker_binding_empty(repo_root: Path) -> None:
    config = load_tracker_config(repo_root)
    assert config.provider is None
    assert config.binding_ref is None
    assert config.project_slug is None
    assert config.display_label is None
    assert config.provider_context is None


# ---------------------------------------------------------------------------
# Scenario 8: Installation-Wide Discovery
# ---------------------------------------------------------------------------


def test_scenario_8_discover_returns_all_bindable_resources_with_bound_flag(
    repo_root: Path,
    mock_client: MagicMock,
) -> None:
    """``tracker discover --provider linear`` lists all bindable resources.

    Verifies that 3 resources (2 unbound, 1 already bound) are returned
    as ``BindableResource`` objects and that ``is_bound`` reflects the
    presence of a ``binding_ref``.
    """
    mock_client.resources.return_value = {
        "resources": [
            {
                "candidate_token": "ct-eng",
                "display_label": "Engineering",
                "provider": "linear",
                "provider_context": {"team_name": "Engineering"},
            },
            {
                "candidate_token": "ct-design",
                "display_label": "Design",
                "provider": "linear",
                "provider_context": {"team_name": "Design"},
            },
            {
                "candidate_token": "ct-ops",
                "display_label": "Operations",
                "provider": "linear",
                "provider_context": {"team_name": "Operations"},
                "binding_ref": "bind-ops-existing",
                "bound_project_slug": "ops-project",
                "bound_at": "2026-03-15T10:00:00Z",
            },
        ],
    }

    with patch(
        "specify_cli.tracker.saas_service.SaaSTrackerClient",
        return_value=mock_client,
    ):
        resources = TrackerService(repo_root).discover(provider="linear")

    mock_client.resources.assert_called_once_with("linear")
    assert len(resources) == 3

    # All returned items are BindableResource instances
    for r in resources:
        assert isinstance(r, BindableResource)

    # Unbound resources
    eng, design, ops = resources
    assert eng.display_label == "Engineering"
    assert eng.is_bound is False
    assert eng.binding_ref is None

    assert design.display_label == "Design"
    assert design.is_bound is False

    # Bound resource
    assert ops.display_label == "Operations"
    assert ops.is_bound is True
    assert ops.binding_ref == "bind-ops-existing"
    assert ops.bound_project_slug == "ops-project"


# ---------------------------------------------------------------------------
# Scenario 9: Installation-Wide Status
# ---------------------------------------------------------------------------


def test_scenario_9_status_all_returns_installation_level_data(
    repo_root: Path,
    mock_client: MagicMock,
) -> None:
    """``tracker status --all`` shows multi-project summary (SaaS-only).

    Calls ``client.status(provider)`` **without** project_slug or binding_ref,
    and verifies the returned dict contains installation-level data.
    """
    # Pre-configure a SaaS binding so _resolve_backend works
    save_tracker_config(
        repo_root,
        TrackerProjectConfig(provider="linear", binding_ref="bind-eng"),
    )

    mock_client.status.return_value = {
        "provider": "linear",
        "installation_id": "inst-12345",
        "total_bindings": 4,
        "active_bindings": 3,
        "projects": [
            {"project_slug": "alpha", "connected": True},
            {"project_slug": "beta", "connected": True},
            {"project_slug": "gamma", "connected": True},
            {"project_slug": "delta", "connected": False},
        ],
    }

    with patch(
        "specify_cli.tracker.saas_service.SaaSTrackerClient",
        return_value=mock_client,
    ):
        result = TrackerService(repo_root).status(all=True)

    # status(all=True) calls client.status(provider) without routing keys
    mock_client.status.assert_called_once_with("linear")
    assert isinstance(result, dict)
    assert result["total_bindings"] == 4
    assert result["active_bindings"] == 3
    assert len(result["projects"]) == 4


# ---------------------------------------------------------------------------
# Scenario 10: Re-Bind (replace existing binding)
# ---------------------------------------------------------------------------


def test_scenario_10_rebind_replaces_existing_binding_in_config(
    repo_root: Path,
    project_identity: dict[str, object],
    mock_client: MagicMock,
) -> None:
    """Developer with existing binding runs ``tracker bind`` and new binding replaces old.

    Pre-populates config with an old binding_ref, calls ``resolve_and_bind()``,
    and verifies the new binding completely replaces the old one in config.
    """
    # Pre-existing binding
    save_tracker_config(
        repo_root,
        TrackerProjectConfig(
            provider="linear",
            binding_ref="bind-old-team",
            display_label="Old Team",
            provider_context={"team_name": "Old"},
        ),
    )
    config_before = load_tracker_config(repo_root)
    assert config_before.binding_ref == "bind-old-team"

    # New bind resolves to a different exact match
    mock_client.bind_resolve.return_value = {
        "match_type": "exact",
        "binding_ref": "bind-new-team",
        "display_label": "New Team",
        "provider_context": {
            "team_name": "New",
            "workspace_name": "Acme Corp v2",
        },
        "candidates": [],
    }

    with patch(
        "specify_cli.tracker.saas_service.SaaSTrackerClient",
        return_value=mock_client,
    ):
        result = TrackerService(repo_root).bind(
            provider="linear",
            project_identity=project_identity,
        )

    assert result.binding_ref == "bind-new-team"

    # Verify config on disk is updated
    config_after = load_tracker_config(repo_root)
    assert config_after.provider == "linear"
    assert config_after.binding_ref == "bind-new-team"
    assert config_after.display_label == "New Team"
    assert config_after.provider_context == {
        "team_name": "New",
        "workspace_name": "Acme Corp v2",
    }
    # Old binding is fully replaced
    assert config_after.binding_ref != "bind-old-team"


# ===========================================================================
# CLI-level integration tests
# ===========================================================================


def _make_tracker_app(monkeypatch) -> typer.Typer:
    """Return the tracker app with the SaaS sync feature flag enabled."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    from specify_cli.cli.commands import tracker as tracker_module

    return tracker_module.app


def test_cli_status_command_renders_output_and_exits_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI ``tracker status`` renders provider info and exits 0."""
    app = _make_tracker_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.status.return_value = {
        "configured": True,
        "provider": "linear",
        "identity_path": {"type": "saas", "provider": "linear"},
        "sync_state": "idle",
    }

    with patch("specify_cli.cli.commands.tracker._service", return_value=mock_svc):
        result = cli_runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "linear" in result.output
    assert "saas" in result.output


def test_cli_status_json_returns_valid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI ``tracker status --json`` returns parseable JSON with provider key."""
    app = _make_tracker_app(monkeypatch)
    mock_svc = MagicMock()
    mock_svc.status.return_value = {
        "configured": True,
        "provider": "linear",
        "binding_ref": "bind-eng",
        "display_label": "Engineering",
    }

    with patch("specify_cli.cli.commands.tracker._service", return_value=mock_svc):
        result = cli_runner.invoke(app, ["status", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["provider"] == "linear"
    assert data["binding_ref"] == "bind-eng"


def test_cli_bind_saas_with_project_slug_persists_and_renders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI ``tracker bind --provider linear --project-slug proj`` succeeds."""
    app = _make_tracker_app(monkeypatch)
    mock_svc = MagicMock()
    mock_config = MagicMock()
    mock_config.provider = "linear"
    mock_config.project_slug = "my-proj"
    mock_svc.bind.return_value = mock_config

    with patch("specify_cli.cli.commands.tracker._service", return_value=mock_svc):
        result = cli_runner.invoke(
            app, ["bind", "--provider", "linear", "--project-slug", "my-proj"]
        )

    assert result.exit_code == 0
    assert "Tracker binding saved" in result.output
    mock_svc.bind.assert_called_once_with(provider="linear", project_slug="my-proj")
