"""Tests for SaaSTrackerService discovery and bind flow (WP08).

Covers: discover(), resolve_and_bind(), _persist_binding(),
_confirm_and_persist(), exact match, candidates, none, token retry.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specify_cli.tracker.config import (
    TrackerProjectConfig,
    load_tracker_config,
)
from specify_cli.tracker.discovery import (
    BindResult,
    BindableResource,
    ResolutionResult,
)
from specify_cli.tracker.saas_client import SaaSTrackerClientError
from specify_cli.tracker.saas_service import SaaSTrackerService
from specify_cli.tracker.service import TrackerServiceError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo_root(tmp_path: Path) -> Path:
    """Create a minimal .kittify directory so config save/load works."""
    (tmp_path / ".kittify").mkdir()
    return tmp_path


@pytest.fixture()
def mock_client() -> MagicMock:
    """Return a mock SaaSTrackerClient."""
    return MagicMock()


@pytest.fixture()
def config() -> TrackerProjectConfig:
    return TrackerProjectConfig(
        provider="linear",
        project_slug="my-proj",
    )


@pytest.fixture()
def service(
    repo_root: Path,
    config: TrackerProjectConfig,
    mock_client: MagicMock,
) -> SaaSTrackerService:
    return SaaSTrackerService(repo_root, config, client=mock_client)


# ---------------------------------------------------------------------------
# discover()
# ---------------------------------------------------------------------------


class TestDiscover:
    def test_discover_parses_resources(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        """discover() delegates to client.resources() and parses into BindableResource."""
        mock_client.resources.return_value = {
            "resources": [
                {
                    "candidate_token": "tok-1",
                    "display_label": "Project Alpha",
                    "provider": "linear",
                    "provider_context": {"team": "eng"},
                    "binding_ref": "ref-1",
                    "bound_project_slug": "alpha",
                    "bound_at": "2026-01-01T00:00:00Z",
                },
                {
                    "candidate_token": "tok-2",
                    "display_label": "Project Beta",
                    "provider": "linear",
                    "provider_context": {},
                },
            ],
        }

        result = service.discover("linear")

        mock_client.resources.assert_called_once_with("linear")
        assert len(result) == 2
        assert isinstance(result[0], BindableResource)
        assert result[0].candidate_token == "tok-1"
        assert result[0].display_label == "Project Alpha"
        assert result[0].is_bound is True
        assert result[1].candidate_token == "tok-2"
        assert result[1].is_bound is False

    def test_discover_empty(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        """discover() with empty resources returns empty list."""
        mock_client.resources.return_value = {"resources": []}

        result = service.discover("linear")

        assert result == []

    def test_discover_missing_resources_key(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        """discover() with missing 'resources' key returns empty list."""
        mock_client.resources.return_value = {}

        result = service.discover("linear")

        assert result == []


# ---------------------------------------------------------------------------
# resolve_and_bind() -- exact match with binding_ref
# ---------------------------------------------------------------------------


class TestResolveAndBindExactWithRef:
    def test_exact_with_binding_ref_auto_binds(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Exact match with binding_ref skips confirm, persists directly."""
        cfg = TrackerProjectConfig(provider="linear", project_slug="my-proj")
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.bind_resolve.return_value = {
            "match_type": "exact",
            "binding_ref": "ref-abc",
            "display_label": "Project Alpha",
            "candidate_token": None,
            "candidates": [],
        }

        identity = {"repo_name": "my-repo", "remote_url": "git@github.com:org/repo"}
        result = svc.resolve_and_bind(
            provider="linear",
            project_identity=identity,
        )

        assert isinstance(result, BindResult)
        assert result.binding_ref == "ref-abc"
        assert result.display_label == "Project Alpha"

        # Verify config persisted
        loaded = load_tracker_config(repo_root)
        assert loaded.binding_ref == "ref-abc"
        assert loaded.display_label == "Project Alpha"
        assert loaded.provider == "linear"
        assert loaded.project_slug == "my-proj"  # preserved

        # bind_confirm should NOT have been called
        mock_client.bind_confirm.assert_not_called()


# ---------------------------------------------------------------------------
# resolve_and_bind() -- exact match without binding_ref
# ---------------------------------------------------------------------------


class TestResolveAndBindExactWithoutRef:
    def test_exact_without_ref_calls_confirm(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Exact match without binding_ref calls bind_confirm."""
        cfg = TrackerProjectConfig(provider="linear", project_slug="my-proj")
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.bind_resolve.return_value = {
            "match_type": "exact",
            "binding_ref": None,
            "candidate_token": "tok-exact",
            "display_label": "Project Alpha",
            "candidates": [],
        }
        mock_client.bind_confirm.return_value = {
            "binding_ref": "ref-confirmed",
            "display_label": "Project Alpha (confirmed)",
            "provider": "linear",
            "provider_context": {"org": "acme"},
            "bound_at": "2026-04-04T12:00:00Z",
        }

        identity = {"repo_name": "my-repo"}
        result = svc.resolve_and_bind(
            provider="linear",
            project_identity=identity,
        )

        assert isinstance(result, BindResult)
        assert result.binding_ref == "ref-confirmed"
        mock_client.bind_confirm.assert_called_once_with(
            "linear",
            "tok-exact",
            identity,
        )

        # Verify config persisted
        loaded = load_tracker_config(repo_root)
        assert loaded.binding_ref == "ref-confirmed"
        assert loaded.display_label == "Project Alpha (confirmed)"
        assert loaded.provider_context == {"org": "acme"}


# ---------------------------------------------------------------------------
# resolve_and_bind() -- candidates (return for CLI selection)
# ---------------------------------------------------------------------------


class TestResolveAndBindCandidates:
    def test_candidates_returns_resolution_result(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Candidates without select_n returns ResolutionResult for CLI."""
        cfg = TrackerProjectConfig(provider="linear", project_slug="my-proj")
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.bind_resolve.return_value = {
            "match_type": "candidates",
            "candidates": [
                {
                    "candidate_token": "tok-a",
                    "display_label": "Alpha",
                    "confidence": "high",
                    "match_reason": "name match",
                    "sort_position": 0,
                },
                {
                    "candidate_token": "tok-b",
                    "display_label": "Beta",
                    "confidence": "medium",
                    "match_reason": "partial match",
                    "sort_position": 1,
                },
            ],
        }

        identity = {"repo_name": "my-repo"}
        result = svc.resolve_and_bind(
            provider="linear",
            project_identity=identity,
        )

        assert isinstance(result, ResolutionResult)
        assert result.match_type == "candidates"
        assert len(result.candidates) == 2
        assert result.candidates[0].display_label == "Alpha"

        # No config change, no confirm call
        mock_client.bind_confirm.assert_not_called()

    def test_candidates_select_n_auto_selects(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Candidates with select_n=2 auto-selects the second candidate."""
        cfg = TrackerProjectConfig(provider="linear", project_slug="my-proj")
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.bind_resolve.return_value = {
            "match_type": "candidates",
            "candidates": [
                {
                    "candidate_token": "tok-a",
                    "display_label": "Alpha",
                    "confidence": "high",
                    "match_reason": "name match",
                    "sort_position": 0,
                },
                {
                    "candidate_token": "tok-b",
                    "display_label": "Beta",
                    "confidence": "medium",
                    "match_reason": "partial match",
                    "sort_position": 1,
                },
            ],
        }
        mock_client.bind_confirm.return_value = {
            "binding_ref": "ref-beta",
            "display_label": "Beta (confirmed)",
            "provider": "linear",
            "provider_context": {},
            "bound_at": "2026-04-04T12:00:00Z",
        }

        identity = {"repo_name": "my-repo"}
        result = svc.resolve_and_bind(
            provider="linear",
            project_identity=identity,
            select_n=2,
        )

        assert isinstance(result, BindResult)
        assert result.binding_ref == "ref-beta"
        mock_client.bind_confirm.assert_called_once_with(
            "linear",
            "tok-b",
            identity,
        )

        # Config persisted
        loaded = load_tracker_config(repo_root)
        assert loaded.binding_ref == "ref-beta"

    def test_candidates_select_out_of_range(self, repo_root: Path, mock_client: MagicMock) -> None:
        """select_n out of range raises TrackerServiceError."""
        cfg = TrackerProjectConfig(provider="linear", project_slug="my-proj")
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.bind_resolve.return_value = {
            "match_type": "candidates",
            "candidates": [
                {
                    "candidate_token": "tok-a",
                    "display_label": "Alpha",
                    "confidence": "high",
                    "match_reason": "name match",
                    "sort_position": 0,
                },
            ],
        }

        identity = {"repo_name": "my-repo"}
        with pytest.raises(TrackerServiceError, match="out of range"):
            svc.resolve_and_bind(
                provider="linear",
                project_identity=identity,
                select_n=99,
            )


# ---------------------------------------------------------------------------
# resolve_and_bind() -- none match
# ---------------------------------------------------------------------------


class TestResolveAndBindNone:
    def test_none_match_raises(self, repo_root: Path, mock_client: MagicMock) -> None:
        """match_type=none raises TrackerServiceError."""
        cfg = TrackerProjectConfig(provider="linear", project_slug="my-proj")
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.bind_resolve.return_value = {
            "match_type": "none",
            "candidates": [],
        }

        identity = {"repo_name": "my-repo"}
        with pytest.raises(TrackerServiceError, match="No bindable resources found"):
            svc.resolve_and_bind(
                provider="linear",
                project_identity=identity,
            )


# ---------------------------------------------------------------------------
# Candidate token retry (T040)
# ---------------------------------------------------------------------------


class TestCandidateTokenRetry:
    def test_confirm_token_rejected_retries_resolution_once(self, repo_root: Path, mock_client: MagicMock) -> None:
        """invalid_candidate_token retries bind-resolve once and then confirms."""
        cfg = TrackerProjectConfig(provider="linear", project_slug="my-proj")
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.bind_resolve.side_effect = [
            {
                "match_type": "exact",
                "binding_ref": None,
                "candidate_token": "tok-expired",
                "display_label": "Stale Project",
                "candidates": [],
            },
            {
                "match_type": "exact",
                "binding_ref": None,
                "candidate_token": "tok-fresh",
                "display_label": "Fresh Project",
                "candidates": [],
            },
        ]
        mock_client.bind_confirm.side_effect = [
            SaaSTrackerClientError(
                "Token expired",
                error_code="invalid_candidate_token",
                status_code=422,
            ),
            {
                "binding_ref": "ref-fresh",
                "display_label": "Fresh Project",
                "provider": "linear",
                "provider_context": {"org": "acme"},
                "bound_at": "2026-04-04T12:00:00Z",
            },
        ]

        identity = {"repo_name": "my-repo"}
        result = svc.resolve_and_bind(
            provider="linear",
            project_identity=identity,
        )

        assert isinstance(result, BindResult)
        assert result.binding_ref == "ref-fresh"
        assert mock_client.bind_resolve.call_count == 2
        assert mock_client.bind_confirm.call_count == 2
        loaded = load_tracker_config(repo_root)
        assert loaded.binding_ref == "ref-fresh"
        assert loaded.provider_context == {"org": "acme"}

    def test_candidate_selection_retry_reuses_requested_position(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Retry after token expiry re-resolves and reuses the same select_n value."""
        cfg = TrackerProjectConfig(provider="linear", project_slug="my-proj")
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.bind_resolve.side_effect = [
            {
                "match_type": "candidates",
                "candidates": [
                    {
                        "candidate_token": "tok-a1",
                        "display_label": "Alpha",
                        "confidence": "high",
                        "match_reason": "name match",
                        "sort_position": 0,
                    },
                    {
                        "candidate_token": "tok-b1",
                        "display_label": "Beta",
                        "confidence": "medium",
                        "match_reason": "partial match",
                        "sort_position": 1,
                    },
                ],
            },
            {
                "match_type": "candidates",
                "candidates": [
                    {
                        "candidate_token": "tok-a2",
                        "display_label": "Alpha",
                        "confidence": "high",
                        "match_reason": "name match",
                        "sort_position": 0,
                    },
                    {
                        "candidate_token": "tok-b2",
                        "display_label": "Beta",
                        "confidence": "medium",
                        "match_reason": "partial match",
                        "sort_position": 1,
                    },
                ],
            },
        ]
        mock_client.bind_confirm.side_effect = [
            SaaSTrackerClientError(
                "Token expired",
                error_code="invalid_candidate_token",
                status_code=422,
            ),
            {
                "binding_ref": "ref-beta",
                "display_label": "Beta (confirmed)",
                "provider": "linear",
                "provider_context": {},
                "bound_at": "2026-04-04T12:00:00Z",
            },
        ]

        identity = {"repo_name": "my-repo"}
        result = svc.resolve_and_bind(
            provider="linear",
            project_identity=identity,
            select_n=2,
        )

        assert isinstance(result, BindResult)
        assert result.binding_ref == "ref-beta"
        assert mock_client.bind_resolve.call_count == 2
        assert mock_client.bind_confirm.call_args_list[0].args == (
            "linear",
            "tok-b1",
            identity,
        )
        assert mock_client.bind_confirm.call_args_list[1].args == (
            "linear",
            "tok-b2",
            identity,
        )

    def test_confirm_token_rejected_twice_raises_clear_error(self, repo_root: Path, mock_client: MagicMock) -> None:
        """A second invalid_candidate_token after retry surfaces a clear error."""
        cfg = TrackerProjectConfig(provider="linear", project_slug="my-proj")
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.bind_resolve.side_effect = [
            {
                "match_type": "exact",
                "binding_ref": None,
                "candidate_token": "tok-expired",
                "display_label": "Stale Project",
                "candidates": [],
            },
            {
                "match_type": "exact",
                "binding_ref": None,
                "candidate_token": "tok-expired-again",
                "display_label": "Still Stale",
                "candidates": [],
            },
        ]
        mock_client.bind_confirm.side_effect = [
            SaaSTrackerClientError(
                "Token expired",
                error_code="invalid_candidate_token",
                status_code=422,
            ),
            SaaSTrackerClientError(
                "Token expired again",
                error_code="invalid_candidate_token",
                status_code=422,
            ),
        ]

        identity = {"repo_name": "my-repo"}
        with pytest.raises(TrackerServiceError, match="Candidate token expired"):
            svc.resolve_and_bind(
                provider="linear",
                project_identity=identity,
            )

        assert mock_client.bind_resolve.call_count == 2
        assert mock_client.bind_confirm.call_count == 2

    def test_confirm_other_error_propagates(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Non-token-rejection errors from bind_confirm propagate as SaaSTrackerClientError."""
        cfg = TrackerProjectConfig(provider="linear", project_slug="my-proj")
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.bind_resolve.return_value = {
            "match_type": "exact",
            "binding_ref": None,
            "candidate_token": "tok-valid",
            "display_label": "Some Project",
            "candidates": [],
        }
        mock_client.bind_confirm.side_effect = SaaSTrackerClientError(
            "Server error",
            error_code="internal_error",
            status_code=500,
        )

        identity = {"repo_name": "my-repo"}
        with pytest.raises(SaaSTrackerClientError, match="Server error"):
            svc.resolve_and_bind(
                provider="linear",
                project_identity=identity,
            )


# ---------------------------------------------------------------------------
# _persist_binding preserves project_slug (backward compat)
# ---------------------------------------------------------------------------


class TestPersistBinding:
    def test_persist_binding_preserves_project_slug(self, repo_root: Path, mock_client: MagicMock) -> None:
        """_persist_binding keeps existing project_slug for backward compat."""
        cfg = TrackerProjectConfig(
            provider="linear",
            project_slug="legacy-slug",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.bind_resolve.return_value = {
            "match_type": "exact",
            "binding_ref": "ref-new",
            "display_label": "New Binding",
            "candidate_token": None,
            "candidates": [],
        }

        identity = {"repo_name": "my-repo"}
        svc.resolve_and_bind(provider="linear", project_identity=identity)

        loaded = load_tracker_config(repo_root)
        assert loaded.binding_ref == "ref-new"
        assert loaded.project_slug == "legacy-slug"  # Preserved!

    def test_persist_binding_with_provider_context(self, repo_root: Path, mock_client: MagicMock) -> None:
        """_persist_binding stores provider_context from confirm result."""
        cfg = TrackerProjectConfig(provider="linear", project_slug="my-proj")
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.bind_resolve.return_value = {
            "match_type": "exact",
            "binding_ref": None,
            "candidate_token": "tok-x",
            "display_label": "X",
            "candidates": [],
        }
        mock_client.bind_confirm.return_value = {
            "binding_ref": "ref-x",
            "display_label": "X Confirmed",
            "provider": "linear",
            "provider_context": {"workspace_id": "ws-123", "org_slug": "acme"},
            "bound_at": "2026-04-04T12:00:00Z",
        }

        identity = {"repo_name": "my-repo"}
        result = svc.resolve_and_bind(provider="linear", project_identity=identity)

        assert isinstance(result, BindResult)
        loaded = load_tracker_config(repo_root)
        assert loaded.provider_context == {"workspace_id": "ws-123", "org_slug": "acme"}

    def test_persist_binding_preserves_extra_fields(self, repo_root: Path, mock_client: MagicMock) -> None:
        """_persist_binding preserves forward-compatible unknown tracker fields."""
        cfg = TrackerProjectConfig(
            provider="linear",
            project_slug="legacy-slug",
            _extra={"future_field": {"enabled": True}},
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.bind_resolve.return_value = {
            "match_type": "exact",
            "binding_ref": "ref-new",
            "display_label": "New Binding",
            "candidate_token": None,
            "candidates": [],
        }

        identity = {"repo_name": "my-repo"}
        svc.resolve_and_bind(provider="linear", project_identity=identity)

        loaded = load_tracker_config(repo_root)
        assert loaded.binding_ref == "ref-new"
        assert loaded.project_slug == "legacy-slug"
        assert loaded.to_dict()["future_field"] == {"enabled": True}
