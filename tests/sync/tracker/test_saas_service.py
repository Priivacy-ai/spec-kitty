"""Tests for SaaSTrackerService -- SaaS-backed tracker service layer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.tracker.config import (
    TrackerProjectConfig,
    load_tracker_config,
)
from specify_cli.tracker.saas_client import SaaSTrackerClientError
from specify_cli.tracker.saas_service import SaaSTrackerService
from specify_cli.tracker.service import StaleBindingError, TrackerServiceError


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
    """Return a mock SaaSTrackerClient with canned responses."""
    client = MagicMock()
    client.status.return_value = {
        "provider": "linear",
        "project_slug": "my-proj",
        "connected": True,
    }
    client.pull.return_value = {
        "items": [{"id": "LIN-1", "title": "Task 1"}],
        "cursor": "abc123",
    }
    client.push.return_value = {
        "pushed": 0,
        "errors": [],
    }
    client.run.return_value = {
        "pulled": 1,
        "pushed": 0,
        "errors": [],
    }
    client.mappings.return_value = {
        "mappings": [
            {"wp_id": "WP01", "external_id": "LIN-1"},
            {"wp_id": "WP02", "external_id": "LIN-2"},
        ],
    }
    client.search_issues.return_value = {
        "candidates": [
            {
                "identifier": "PRI-17",
                "external_issue_id": "linear-issue-17",
                "title": "Wire hosted tracker reads",
                "url": "https://linear.app/priivacy/issue/PRI-17",
                "state": {"name": "todo"},
                "team": {"key": "PRI"},
                "assignee": None,
                "created_at": "2026-04-18T10:00:00+00:00",
                "updated_at": "2026-04-18T11:00:00+00:00",
                "body": "body",
            }
        ]
    }
    client.list_tickets.return_value = {
        "tickets": [
            {
                "identifier": "PRI-1",
                "external_issue_id": "linear-issue-1",
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
    }
    return client


@pytest.fixture()
def config() -> TrackerProjectConfig:
    """Return a pre-configured SaaS tracker config."""
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
    """Return a SaaSTrackerService wired to mocks."""
    return SaaSTrackerService(repo_root, config, client=mock_client)


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


class TestProperties:
    def test_provider_returns_config_provider(self, service: SaaSTrackerService) -> None:
        assert service.provider == "linear"

    def test_project_slug_returns_config_slug(self, service: SaaSTrackerService) -> None:
        assert service.project_slug == "my-proj"

    def test_provider_asserts_when_none(self, repo_root: Path, mock_client: MagicMock) -> None:
        empty_config = TrackerProjectConfig()
        svc = SaaSTrackerService(repo_root, empty_config, client=mock_client)
        with pytest.raises(AssertionError):
            _ = svc.provider

    def test_project_slug_none_for_binding_ref_only(self, repo_root: Path, mock_client: MagicMock) -> None:
        config = TrackerProjectConfig(provider="linear", binding_ref="ref-1")
        svc = SaaSTrackerService(repo_root, config, client=mock_client)
        assert svc.project_slug is None


# ---------------------------------------------------------------------------
# Routing resolution (T030)
# ---------------------------------------------------------------------------


class TestResolveRoutingParams:
    def test_resolve_routing_binding_ref_first(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Config with both binding_ref and project_slug returns binding_ref."""
        cfg = TrackerProjectConfig(
            provider="linear",
            binding_ref="bind-abc-123",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)
        result = svc._resolve_routing_params()
        assert result == {"binding_ref": "bind-abc-123"}
        assert "project_slug" not in result

    def test_resolve_routing_project_slug_fallback(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Config with only project_slug returns project_slug."""
        cfg = TrackerProjectConfig(
            provider="linear",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)
        result = svc._resolve_routing_params()
        assert result == {"project_slug": "my-proj"}
        assert "binding_ref" not in result

    def test_resolve_routing_neither_raises(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Config with neither binding_ref nor project_slug raises."""
        cfg = TrackerProjectConfig(provider="linear")
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)
        with pytest.raises(TrackerServiceError, match="No tracker binding configured"):
            svc._resolve_routing_params()

    def test_resolve_routing_binding_ref_only(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Config with only binding_ref (no project_slug) returns binding_ref."""
        cfg = TrackerProjectConfig(
            provider="linear",
            binding_ref="bind-xyz-456",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)
        result = svc._resolve_routing_params()
        assert result == {"binding_ref": "bind-xyz-456"}


# ---------------------------------------------------------------------------
# Delegated methods use routing (T031)
# ---------------------------------------------------------------------------


class TestDelegatedMethodsUseRouting:
    """Verify that all 5 delegated methods pass routing params to the client."""

    def test_status_uses_binding_ref(self, repo_root: Path, mock_client: MagicMock) -> None:
        cfg = TrackerProjectConfig(
            provider="linear",
            binding_ref="bind-abc",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)
        svc.status()
        mock_client.status.assert_called_once_with(
            "linear",
            binding_ref="bind-abc",
        )

    def test_status_uses_project_slug_fallback(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        service.status()
        mock_client.status.assert_called_once_with(
            "linear",
            project_slug="my-proj",
        )

    def test_sync_pull_uses_binding_ref(self, repo_root: Path, mock_client: MagicMock) -> None:
        cfg = TrackerProjectConfig(
            provider="linear",
            binding_ref="bind-abc",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)
        svc.sync_pull(limit=50)
        mock_client.pull.assert_called_once_with(
            "linear",
            limit=50,
            binding_ref="bind-abc",
        )

    def test_sync_push_uses_binding_ref(self, repo_root: Path, mock_client: MagicMock) -> None:
        cfg = TrackerProjectConfig(
            provider="linear",
            binding_ref="bind-abc",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)
        svc.sync_push()
        mock_client.push.assert_called_once_with(
            "linear",
            items=[],
            binding_ref="bind-abc",
        )

    def test_sync_run_uses_binding_ref(self, repo_root: Path, mock_client: MagicMock) -> None:
        cfg = TrackerProjectConfig(
            provider="linear",
            binding_ref="bind-abc",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)
        svc.sync_run(limit=200)
        mock_client.run.assert_called_once_with(
            "linear",
            limit=200,
            binding_ref="bind-abc",
        )

    def test_map_list_uses_binding_ref(self, repo_root: Path, mock_client: MagicMock) -> None:
        cfg = TrackerProjectConfig(
            provider="linear",
            binding_ref="bind-abc",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)
        svc.map_list()
        mock_client.mappings.assert_called_once_with(
            "linear",
            binding_ref="bind-abc",
        )


# ---------------------------------------------------------------------------
# Opportunistic upgrade (T032, T033)
# ---------------------------------------------------------------------------


class TestMaybeUpgradeBindingRef:
    def test_upgrade_writes_binding_ref(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Response with binding_ref persists to config."""
        cfg = TrackerProjectConfig(
            provider="linear",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.status.return_value = {
            "connected": True,
            "binding_ref": "bind-new-abc",
            "display_label": "My Project (Linear)",
            "provider_context": {"org": "acme"},
        }
        svc.status()

        # Verify config updated in memory (atomic: svc._config is a NEW object)
        assert svc._config.binding_ref == "bind-new-abc"
        assert svc._config.display_label == "My Project (Linear)"
        assert svc._config.provider_context == {"org": "acme"}

        # Verify persisted to disk
        loaded = load_tracker_config(repo_root)
        assert loaded.binding_ref == "bind-new-abc"
        assert loaded.display_label == "My Project (Linear)"

    def test_upgrade_no_binding_ref_noop(self, service: SaaSTrackerService, repo_root: Path, mock_client: MagicMock) -> None:
        """Response without binding_ref does not modify config."""
        mock_client.status.return_value = {"connected": True}
        service.status()

        loaded = load_tracker_config(repo_root)
        assert loaded.binding_ref is None

    def test_upgrade_already_current_noop(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Same binding_ref in response does not trigger save."""
        cfg = TrackerProjectConfig(
            provider="linear",
            binding_ref="bind-abc",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.status.return_value = {
            "connected": True,
            "binding_ref": "bind-abc",  # Same as config
        }

        with patch("specify_cli.tracker.saas_service.save_tracker_config") as mock_save:
            svc.status()
            mock_save.assert_not_called()

    def test_upgrade_failure_silent(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Save failure does not propagate; call still returns normally."""
        cfg = TrackerProjectConfig(
            provider="linear",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.status.return_value = {
            "connected": True,
            "binding_ref": "bind-new",
        }

        with patch(
            "specify_cli.tracker.saas_service.save_tracker_config",
            side_effect=OSError("disk full"),
        ):
            # Should NOT raise
            result = svc.status()
            assert result["connected"] is True

    def test_maybe_upgrade_save_failure_preserves_config(self, repo_root: Path, mock_client: MagicMock) -> None:
        """When save_tracker_config raises, self._config must NOT be mutated."""
        cfg = TrackerProjectConfig(
            provider="linear",
            binding_ref="old-bind-ref",
            project_slug="my-proj",
            display_label="Old Label",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.status.return_value = {
            "connected": True,
            "binding_ref": "new-bind-ref",
            "display_label": "New Label",
            "provider_context": {"org": "acme"},
        }

        with patch(
            "specify_cli.tracker.saas_service.save_tracker_config",
            side_effect=OSError("disk full"),
        ):
            result = svc.status()
            assert result["connected"] is True

        # The critical assertion: in-memory config must still have the OLD values
        assert svc._config.binding_ref == "old-bind-ref"
        assert svc._config.display_label == "Old Label"
        assert svc._config.provider_context is None

    def test_upgrade_partial_response_display_label_only(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Response with binding_ref and display_label but no provider_context."""
        cfg = TrackerProjectConfig(
            provider="linear",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.status.return_value = {
            "connected": True,
            "binding_ref": "bind-new",
            "display_label": "Label Only",
        }
        svc.status()

        assert svc._config.binding_ref == "bind-new"
        assert svc._config.display_label == "Label Only"
        assert svc._config.provider_context is None

    def test_upgrade_called_after_sync_pull(self, repo_root: Path, mock_client: MagicMock) -> None:
        """sync_pull also triggers opportunistic upgrade."""
        cfg = TrackerProjectConfig(
            provider="linear",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.pull.return_value = {
            "items": [],
            "binding_ref": "bind-from-pull",
        }
        svc.sync_pull()

        assert svc._config.binding_ref == "bind-from-pull"

    def test_upgrade_called_after_sync_push(self, repo_root: Path, mock_client: MagicMock) -> None:
        """sync_push also triggers opportunistic upgrade."""
        cfg = TrackerProjectConfig(
            provider="linear",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.push.return_value = {
            "pushed": 0,
            "binding_ref": "bind-from-push",
        }
        svc.sync_push()

        assert svc._config.binding_ref == "bind-from-push"

    def test_upgrade_called_after_sync_run(self, repo_root: Path, mock_client: MagicMock) -> None:
        """sync_run also triggers opportunistic upgrade."""
        cfg = TrackerProjectConfig(
            provider="linear",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.run.return_value = {
            "pulled": 0,
            "pushed": 0,
            "binding_ref": "bind-from-run",
        }
        svc.sync_run()

        assert svc._config.binding_ref == "bind-from-run"

    def test_upgrade_called_after_map_list(self, repo_root: Path, mock_client: MagicMock) -> None:
        """map_list also triggers opportunistic upgrade."""
        cfg = TrackerProjectConfig(
            provider="linear",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.mappings.return_value = {
            "mappings": [],
            "binding_ref": "bind-from-mappings",
        }
        svc.map_list()

        assert svc._config.binding_ref == "bind-from-mappings"

    def test_maybe_upgrade_preserves_extra_fields(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Unknown config fields survive opportunistic upgrade (forward-compat)."""
        cfg = TrackerProjectConfig(
            provider="linear",
            project_slug="my-proj",
            _extra={"future_flag": True, "beta_feature": "enabled"},
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.status.return_value = {
            "connected": True,
            "binding_ref": "bind-new-abc",
        }
        svc.status()

        # Core assertion: _extra must survive the upgrade rebuild
        assert svc._config._extra == {"future_flag": True, "beta_feature": "enabled"}
        assert svc._config.binding_ref == "bind-new-abc"


# ---------------------------------------------------------------------------
# Stale binding detection (T034)
# ---------------------------------------------------------------------------


class TestStaleBindingDetection:
    def test_stale_binding_detection_binding_not_found(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Client error with binding_not_found raises StaleBindingError."""
        cfg = TrackerProjectConfig(
            provider="linear",
            binding_ref="bind-stale",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.status.side_effect = SaaSTrackerClientError(
            "Binding not found",
            error_code="binding_not_found",
            status_code=404,
        )

        with pytest.raises(StaleBindingError) as exc_info:
            svc.status()

        assert exc_info.value.binding_ref == "bind-stale"
        assert exc_info.value.error_code == "binding_not_found"
        assert "stale" in str(exc_info.value).lower()
        assert "rebind" in str(exc_info.value).lower()

    def test_stale_binding_detection_mapping_disabled(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Client error with mapping_disabled raises StaleBindingError."""
        cfg = TrackerProjectConfig(
            provider="linear",
            binding_ref="bind-disabled",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.pull.side_effect = SaaSTrackerClientError(
            "Mapping disabled",
            error_code="mapping_disabled",
            status_code=403,
        )

        with pytest.raises(StaleBindingError) as exc_info:
            svc.sync_pull()

        assert exc_info.value.error_code == "mapping_disabled"

    def test_stale_binding_detection_project_mismatch(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Client error with project_mismatch raises StaleBindingError."""
        cfg = TrackerProjectConfig(
            provider="linear",
            binding_ref="bind-mismatched",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.run.side_effect = SaaSTrackerClientError(
            "Project mismatch",
            error_code="project_mismatch",
            status_code=409,
        )

        with pytest.raises(StaleBindingError) as exc_info:
            svc.sync_run()

        assert exc_info.value.error_code == "project_mismatch"

    def test_stale_binding_no_false_positive(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Client error with non-stale error_code propagates as-is."""
        cfg = TrackerProjectConfig(
            provider="linear",
            binding_ref="bind-abc",
            project_slug="my-proj",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.status.side_effect = SaaSTrackerClientError(
            "Rate limited",
            error_code="rate_limited",
            status_code=429,
        )

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            svc.status()

        # Should be the original error, NOT StaleBindingError
        assert not isinstance(exc_info.value, StaleBindingError)
        assert exc_info.value.error_code == "rate_limited"

    def test_stale_binding_only_when_routing_by_binding_ref(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Stale error codes don't trigger StaleBindingError when routing by project_slug."""
        cfg = TrackerProjectConfig(
            provider="linear",
            project_slug="my-proj",
            # binding_ref is None
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.status.side_effect = SaaSTrackerClientError(
            "Binding not found",
            error_code="binding_not_found",
            status_code=404,
        )

        # Should raise the original error, NOT StaleBindingError
        with pytest.raises(SaaSTrackerClientError) as exc_info:
            svc.status()

        assert not isinstance(exc_info.value, StaleBindingError)

    def test_stale_binding_no_error_code_passthrough(self, repo_root: Path, mock_client: MagicMock) -> None:
        """Client error without error_code passes through unchanged."""
        cfg = TrackerProjectConfig(
            provider="linear",
            binding_ref="bind-abc",
        )
        svc = SaaSTrackerService(repo_root, cfg, client=mock_client)

        mock_client.status.side_effect = SaaSTrackerClientError(
            "Generic error",
        )

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            svc.status()

        assert not isinstance(exc_info.value, StaleBindingError)


# ---------------------------------------------------------------------------
# bind / unbind
# ---------------------------------------------------------------------------


class TestBind:
    def test_bind_stores_project_slug(self, service: SaaSTrackerService, repo_root: Path) -> None:
        result = service.bind(provider="linear", project_slug="new-proj")

        assert result.provider == "linear"
        assert result.project_slug == "new-proj"
        assert result.workspace is None  # No workspace for SaaS

        # Verify persisted to disk
        loaded = load_tracker_config(repo_root)
        assert loaded.provider == "linear"
        assert loaded.project_slug == "new-proj"

    def test_bind_updates_internal_config(self, service: SaaSTrackerService) -> None:
        service.bind(provider="jira", project_slug="jira-proj")
        assert service.provider == "jira"
        assert service.project_slug == "jira-proj"

    def test_bind_stores_no_credentials(self, service: SaaSTrackerService, repo_root: Path) -> None:
        """Verify that bind does not create any credential artifacts."""
        service.bind(provider="github", project_slug="gh-proj")

        loaded = load_tracker_config(repo_root)
        # doctrine defaults are present but no credential-related fields
        cfg_dict = loaded.to_dict()
        assert "credentials" not in cfg_dict
        assert loaded.provider == "github"
        assert loaded.project_slug == "gh-proj"


class TestUnbind:
    def test_unbind_clears_config(self, service: SaaSTrackerService, repo_root: Path) -> None:
        # First bind so there's something to clear
        service.bind(provider="linear", project_slug="my-proj")
        loaded = load_tracker_config(repo_root)
        assert loaded.provider == "linear"

        # Now unbind
        service.unbind()

        loaded = load_tracker_config(repo_root)
        assert loaded.provider is None
        assert loaded.project_slug is None

    def test_unbind_resets_internal_config(self, service: SaaSTrackerService) -> None:
        service.unbind()
        # Internal config should be empty -- provider/project_slug are None
        with pytest.raises(AssertionError):
            _ = service.provider


# ---------------------------------------------------------------------------
# Operations that delegate to SaaSTrackerClient
# ---------------------------------------------------------------------------


class TestStatus:
    def test_status_delegates_to_client(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        result = service.status()

        mock_client.status.assert_called_once_with("linear", project_slug="my-proj")
        assert result["connected"] is True
        assert result["provider"] == "linear"


class TestSyncPull:
    def test_pull_delegates_to_client(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        result = service.sync_pull(limit=50)

        mock_client.pull.assert_called_once_with("linear", limit=50, project_slug="my-proj")
        assert result["items"][0]["id"] == "LIN-1"

    def test_pull_default_limit(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        service.sync_pull()
        mock_client.pull.assert_called_once_with("linear", limit=100, project_slug="my-proj")


class TestSyncPush:
    def test_push_delegates_to_client(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        result = service.sync_push()

        mock_client.push.assert_called_once_with("linear", items=[], project_slug="my-proj")
        assert result["pushed"] == 0

    def test_push_forwards_items(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        """Verify caller-supplied items are forwarded to the SaaS client."""
        items = [{"ref": {"system": "linear", "id": "LIN-1", "workspace": "team"}, "action": "update"}]
        service.sync_push(items=items)
        mock_client.push.assert_called_once_with("linear", items=items, project_slug="my-proj")

    def test_push_defaults_to_empty_items(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        """When no items provided, sends empty list."""
        service.sync_push()
        mock_client.push.assert_called_once_with("linear", items=[], project_slug="my-proj")


class TestSyncRun:
    def test_run_delegates_to_client(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        result = service.sync_run(limit=200)

        mock_client.run.assert_called_once_with("linear", limit=200, project_slug="my-proj")
        assert result["pulled"] == 1

    def test_run_default_limit(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        service.sync_run()
        mock_client.run.assert_called_once_with("linear", limit=100, project_slug="my-proj")


class TestMapList:
    def test_map_list_delegates_to_client(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        result = service.map_list()

        mock_client.mappings.assert_called_once_with("linear", project_slug="my-proj")
        assert len(result) == 2
        assert result[0]["wp_id"] == "WP01"

    def test_map_list_returns_empty_when_no_mappings(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        mock_client.mappings.return_value = {}
        result = service.map_list()
        assert result == []

    def test_map_list_with_provider_uses_installation_scope(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        service.map_list(provider="linear")
        mock_client.mappings.assert_called_once_with("linear")


class TestIssueSearch:
    def test_issue_search_uses_bound_routing_when_available(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        result = service.issue_search(provider="linear", query="PRI-17")

        mock_client.search_issues.assert_called_once_with(
            "linear",
            project_slug="my-proj",
            query_text="PRI-17",
            query_key="PRI-17",
            limit=20,
        )
        assert result[0]["identifier"] == "PRI-17"
        assert result[0]["external_issue_id"] == "linear-issue-17"
        assert result[0]["team"]["key"] == "PRI"

    def test_issue_search_without_matching_bound_provider_uses_provider_only(self, repo_root: Path, mock_client: MagicMock) -> None:
        service = SaaSTrackerService(repo_root, TrackerProjectConfig(provider="jira"), client=mock_client)
        service.issue_search(provider="linear", query="bug")

        mock_client.search_issues.assert_called_once_with(
            "linear",
            query_text="bug",
            query_key=None,
            limit=20,
        )


class TestListTickets:
    def test_list_tickets_uses_bound_routing_when_available(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        result = service.list_tickets(provider="linear", limit=15)

        mock_client.list_tickets.assert_called_once_with(
            "linear",
            project_slug="my-proj",
            limit=15,
        )
        assert result[0]["identifier"] == "PRI-1"
        assert result[0]["external_issue_id"] == "linear-issue-1"

    def test_list_tickets_without_matching_bound_provider_uses_provider_only(self, repo_root: Path, mock_client: MagicMock) -> None:
        service = SaaSTrackerService(repo_root, TrackerProjectConfig(provider="jira"), client=mock_client)
        service.list_tickets(provider="linear", limit=20)

        mock_client.list_tickets.assert_called_once_with("linear", limit=20)


# ---------------------------------------------------------------------------
# Hard-fails
# ---------------------------------------------------------------------------


class TestMapAddHardFail:
    def test_map_add_raises_tracker_service_error(self, service: SaaSTrackerService) -> None:
        with pytest.raises(
            TrackerServiceError,
            match="managed in the Spec Kitty dashboard",
        ):
            service.map_add(wp_id="WP01", external_id="LIN-123")

    def test_map_add_fails_with_no_args(self, service: SaaSTrackerService) -> None:
        with pytest.raises(TrackerServiceError):
            service.map_add()

    def test_map_add_mentions_web_interface(self, service: SaaSTrackerService) -> None:
        with pytest.raises(TrackerServiceError, match="web interface"):
            service.map_add()


class TestSyncPublishHardFail:
    def test_sync_publish_raises_tracker_service_error(self, service: SaaSTrackerService) -> None:
        with pytest.raises(
            TrackerServiceError,
            match="not supported for SaaS-backed",
        ):
            service.sync_publish(server_url="https://example.com")

    def test_sync_publish_fails_with_no_args(self, service: SaaSTrackerService) -> None:
        with pytest.raises(TrackerServiceError):
            service.sync_publish()

    def test_sync_publish_mentions_push_alternative(self, service: SaaSTrackerService) -> None:
        with pytest.raises(
            TrackerServiceError,
            match="spec-kitty tracker sync push",
        ):
            service.sync_publish()


# ---------------------------------------------------------------------------
# Client is NOT called for hard-fail operations
# ---------------------------------------------------------------------------


class TestNoClientCallsForHardFails:
    def test_map_add_does_not_call_client(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        with pytest.raises(TrackerServiceError):
            service.map_add(wp_id="WP01", external_id="LIN-1")

        # Verify zero client calls
        mock_client.assert_not_called()

    def test_sync_publish_does_not_call_client(self, service: SaaSTrackerService, mock_client: MagicMock) -> None:
        # Reset mock to clear any prior calls from fixture setup
        mock_client.reset_mock()

        with pytest.raises(TrackerServiceError):
            service.sync_publish(server_url="https://example.com")

        mock_client.assert_not_called()
