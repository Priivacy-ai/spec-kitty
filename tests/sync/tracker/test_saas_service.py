"""Tests for SaaSTrackerService -- SaaS-backed tracker service layer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specify_cli.tracker.config import (
    TrackerProjectConfig,
    load_tracker_config,
)
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

    def test_project_slug_asserts_when_none(self, repo_root: Path, mock_client: MagicMock) -> None:
        empty_config = TrackerProjectConfig(provider="linear")
        svc = SaaSTrackerService(repo_root, empty_config, client=mock_client)
        with pytest.raises(AssertionError):
            _ = svc.project_slug


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
    def test_status_delegates_to_client(
        self, service: SaaSTrackerService, mock_client: MagicMock
    ) -> None:
        result = service.status()

        mock_client.status.assert_called_once_with("linear", "my-proj")
        assert result["connected"] is True
        assert result["provider"] == "linear"


class TestSyncPull:
    def test_pull_delegates_to_client(
        self, service: SaaSTrackerService, mock_client: MagicMock
    ) -> None:
        result = service.sync_pull(limit=50)

        mock_client.pull.assert_called_once_with("linear", "my-proj", limit=50)
        assert result["items"][0]["id"] == "LIN-1"

    def test_pull_default_limit(
        self, service: SaaSTrackerService, mock_client: MagicMock
    ) -> None:
        service.sync_pull()
        mock_client.pull.assert_called_once_with("linear", "my-proj", limit=100)


class TestSyncPush:
    def test_push_delegates_to_client(
        self, service: SaaSTrackerService, mock_client: MagicMock
    ) -> None:
        result = service.sync_push()

        mock_client.push.assert_called_once_with("linear", "my-proj", items=[])
        assert result["pushed"] == 0

    def test_push_sends_empty_items(
        self, service: SaaSTrackerService, mock_client: MagicMock
    ) -> None:
        """Verify items=[] is always sent (SaaS owns payload construction)."""
        service.sync_push()
        _, _, kwargs = mock_client.push.mock_calls[0]
        assert kwargs["items"] == []


class TestSyncRun:
    def test_run_delegates_to_client(
        self, service: SaaSTrackerService, mock_client: MagicMock
    ) -> None:
        result = service.sync_run(limit=200)

        mock_client.run.assert_called_once_with("linear", "my-proj", limit=200)
        assert result["pulled"] == 1

    def test_run_default_limit(
        self, service: SaaSTrackerService, mock_client: MagicMock
    ) -> None:
        service.sync_run()
        mock_client.run.assert_called_once_with("linear", "my-proj", limit=100)


class TestMapList:
    def test_map_list_delegates_to_client(
        self, service: SaaSTrackerService, mock_client: MagicMock
    ) -> None:
        result = service.map_list()

        mock_client.mappings.assert_called_once_with("linear", "my-proj")
        assert len(result) == 2
        assert result[0]["wp_id"] == "WP01"

    def test_map_list_returns_empty_when_no_mappings(
        self, service: SaaSTrackerService, mock_client: MagicMock
    ) -> None:
        mock_client.mappings.return_value = {}
        result = service.map_list()
        assert result == []


# ---------------------------------------------------------------------------
# Hard-fails
# ---------------------------------------------------------------------------


class TestMapAddHardFail:
    def test_map_add_raises_tracker_service_error(
        self, service: SaaSTrackerService
    ) -> None:
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
    def test_sync_publish_raises_tracker_service_error(
        self, service: SaaSTrackerService
    ) -> None:
        with pytest.raises(
            TrackerServiceError,
            match="not supported for SaaS-backed",
        ):
            service.sync_publish(server_url="https://example.com")

    def test_sync_publish_fails_with_no_args(self, service: SaaSTrackerService) -> None:
        with pytest.raises(TrackerServiceError):
            service.sync_publish()

    def test_sync_publish_mentions_push_alternative(
        self, service: SaaSTrackerService
    ) -> None:
        with pytest.raises(
            TrackerServiceError,
            match="spec-kitty tracker sync push",
        ):
            service.sync_publish()


# ---------------------------------------------------------------------------
# Client is NOT called for hard-fail operations
# ---------------------------------------------------------------------------


class TestNoClientCallsForHardFails:
    def test_map_add_does_not_call_client(
        self, service: SaaSTrackerService, mock_client: MagicMock
    ) -> None:
        with pytest.raises(TrackerServiceError):
            service.map_add(wp_id="WP01", external_id="LIN-1")

        # Verify zero client calls
        mock_client.assert_not_called()

    def test_sync_publish_does_not_call_client(
        self, service: SaaSTrackerService, mock_client: MagicMock
    ) -> None:
        # Reset mock to clear any prior calls from fixture setup
        mock_client.reset_mock()

        with pytest.raises(TrackerServiceError):
            service.sync_publish(server_url="https://example.com")

        mock_client.assert_not_called()
