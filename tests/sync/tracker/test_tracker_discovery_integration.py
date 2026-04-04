"""Integration and acceptance tests for tracker discovery binding flows."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from specify_cli.sync.project_identity import ProjectIdentity, atomic_write_config
from specify_cli.tracker.config import (
    TrackerProjectConfig,
    load_tracker_config,
    save_tracker_config,
)
from specify_cli.tracker.saas_client import SaaSTrackerClient, SaaSTrackerClientError
from specify_cli.tracker.service import StaleBindingError, TrackerService, TrackerServiceError

pytestmark = pytest.mark.fast


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
