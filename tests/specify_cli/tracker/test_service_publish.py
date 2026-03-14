"""Tests for resource routing in TrackerService.sync_publish()."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.tracker.config import TrackerProjectConfig
from specify_cli.tracker.service import RESOURCE_ROUTING_MAP, TrackerService


# ---------------------------------------------------------------------------
# T004 — Unit tests for _resolve_resource_routing()
# ---------------------------------------------------------------------------


class TestResolveResourceRouting:
    """Unit tests for TrackerService._resolve_resource_routing()."""

    def test_jira_happy_path(self):
        result = TrackerService._resolve_resource_routing(
            "jira", {"project_key": "ACME", "base_url": "https://x.atlassian.net"}
        )
        assert result == ("jira_project", "ACME")

    def test_linear_happy_path(self):
        result = TrackerService._resolve_resource_routing("linear", {"team_id": "abc-123", "api_key": "tok"})
        assert result == ("linear_team", "abc-123")

    def test_jira_missing_project_key(self):
        result = TrackerService._resolve_resource_routing("jira", {"base_url": "https://x.atlassian.net"})
        assert result == (None, None)

    def test_linear_missing_team_id(self):
        result = TrackerService._resolve_resource_routing("linear", {"api_key": "tok"})
        assert result == (None, None)

    def test_jira_empty_string_project_key(self):
        result = TrackerService._resolve_resource_routing("jira", {"project_key": ""})
        assert result == (None, None)

    def test_jira_whitespace_only_project_key(self):
        result = TrackerService._resolve_resource_routing("jira", {"project_key": "   "})
        assert result == (None, None)

    def test_unsupported_provider(self):
        result = TrackerService._resolve_resource_routing("beads", {"command": "bd"})
        assert result == (None, None)

    def test_unknown_provider(self):
        result = TrackerService._resolve_resource_routing("notion", {"api_key": "tok"})
        assert result == (None, None)

    def test_jira_creds_present_but_no_routing_key(self):
        """Credentials dict is non-empty but lacks project_key."""
        result = TrackerService._resolve_resource_routing(
            "jira",
            {"base_url": "https://x.atlassian.net", "email": "a@b.com", "api_token": "tok"},
        )
        assert result == (None, None)


class TestResourceRoutingMap:
    """Verify canonical wire values are stable."""

    def test_jira_wire_value(self):
        assert RESOURCE_ROUTING_MAP["jira"] == ("jira_project", "project_key")

    def test_linear_wire_value(self):
        assert RESOURCE_ROUTING_MAP["linear"] == ("linear_team", "team_id")

    def test_only_jira_and_linear(self):
        assert set(RESOURCE_ROUTING_MAP.keys()) == {"jira", "linear"}


# ---------------------------------------------------------------------------
# T005 — Integration tests for sync_publish() payload
# ---------------------------------------------------------------------------


def _make_mock_store():
    """Create a mock store with the async list_issues interface."""
    store = MagicMock()
    store.list_mappings.return_value = []
    store.get_checkpoint.return_value = None

    async def _list_issues(system=None):
        return []

    store.list_issues = _list_issues
    return store


def _make_mock_http(mock_client_cls):
    """Wire up httpx.Client mock to capture outgoing POST payload."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.is_success = True
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"status": "ok"}

    mock_ctx = MagicMock()
    mock_ctx.post.return_value = mock_response
    mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
    mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
    return mock_ctx


class TestSyncPublishPayload:
    """Integration test: sync_publish() sends routing fields in HTTP body."""

    def test_jira_publish_includes_routing_fields(self):
        config = TrackerProjectConfig(
            provider="jira",
            workspace="acme.atlassian.net",
            doctrine_mode="external_authoritative",
        )
        credentials = {
            "base_url": "https://acme.atlassian.net",
            "email": "a@b.com",
            "api_token": "tok",
            "project_key": "ACME",
        }
        store = _make_mock_store()
        service = TrackerService(Path("/tmp/fake-repo"))

        with (
            patch.object(TrackerService, "_load_runtime", return_value=(config, credentials, store)),
            patch.object(TrackerService, "_project_identity", return_value={"uuid": "test-uuid", "slug": "test-proj"}),
            patch("specify_cli.tracker.service.httpx.Client") as mock_client_cls,
        ):
            mock_ctx = _make_mock_http(mock_client_cls)
            service.sync_publish(server_url="https://example.com", auth_token="test-token")

            sent_payload = mock_ctx.post.call_args[1]["json"]
            assert sent_payload["external_resource_type"] == "jira_project"
            assert sent_payload["external_resource_id"] == "ACME"
            assert sent_payload["provider"] == "jira"
            assert sent_payload["workspace"] == "acme.atlassian.net"

    def test_linear_publish_includes_routing_fields(self):
        config = TrackerProjectConfig(
            provider="linear",
            workspace="my-linear-team",
            doctrine_mode="external_authoritative",
        )
        credentials = {"team_id": "abc-123", "api_key": "tok"}
        store = _make_mock_store()
        service = TrackerService(Path("/tmp/fake-repo"))

        with (
            patch.object(TrackerService, "_load_runtime", return_value=(config, credentials, store)),
            patch.object(TrackerService, "_project_identity", return_value={"uuid": None, "slug": None}),
            patch("specify_cli.tracker.service.httpx.Client") as mock_client_cls,
        ):
            mock_ctx = _make_mock_http(mock_client_cls)
            service.sync_publish(server_url="https://example.com", auth_token="test-token")

            sent_payload = mock_ctx.post.call_args[1]["json"]
            assert sent_payload["external_resource_type"] == "linear_team"
            assert sent_payload["external_resource_id"] == "abc-123"

    def test_unsupported_provider_publishes_null_routing(self):
        config = TrackerProjectConfig(
            provider="beads",
            workspace="my-workspace",
            doctrine_mode="external_authoritative",
        )
        credentials = {"command": "bd"}
        store = _make_mock_store()
        service = TrackerService(Path("/tmp/fake-repo"))

        with (
            patch.object(TrackerService, "_load_runtime", return_value=(config, credentials, store)),
            patch.object(TrackerService, "_project_identity", return_value={"uuid": None, "slug": None}),
            patch("specify_cli.tracker.service.httpx.Client") as mock_client_cls,
        ):
            mock_ctx = _make_mock_http(mock_client_cls)
            service.sync_publish(server_url="https://example.com", auth_token="test-token")

            sent_payload = mock_ctx.post.call_args[1]["json"]
            assert sent_payload["external_resource_type"] is None
            assert sent_payload["external_resource_id"] is None

    @pytest.mark.parametrize("raw_provider", ["Jira", "JIRA", "jIrA"])
    def test_unnormalized_provider_still_resolves_routing(self, raw_provider):
        """P3 regression: provider casing from config must be normalized before routing lookup."""
        config = TrackerProjectConfig(
            provider=raw_provider,
            workspace="acme.atlassian.net",
            doctrine_mode="external_authoritative",
        )
        credentials = {
            "base_url": "https://acme.atlassian.net",
            "email": "a@b.com",
            "api_token": "tok",
            "project_key": "ACME",
        }
        store = _make_mock_store()
        service = TrackerService(Path("/tmp/fake-repo"))

        with (
            patch.object(TrackerService, "_load_runtime", return_value=(config, credentials, store)),
            patch.object(TrackerService, "_project_identity", return_value={"uuid": "test-uuid", "slug": "test-proj"}),
            patch("specify_cli.tracker.service.httpx.Client") as mock_client_cls,
        ):
            mock_ctx = _make_mock_http(mock_client_cls)
            service.sync_publish(server_url="https://example.com", auth_token="test-token")

            sent_payload = mock_ctx.post.call_args[1]["json"]
            assert sent_payload["external_resource_type"] == "jira_project"
            assert sent_payload["external_resource_id"] == "ACME"
            assert sent_payload["provider"] == "jira"

    def test_idempotency_key_changes_on_rebind(self):
        """Rebinding to a different project_key must produce a different
        idempotency key, even when issue/mapping/cursor state is identical."""
        store = _make_mock_store()
        service = TrackerService(Path("/tmp/fake-repo"))
        keys: list[str] = []

        for project_key in ("ACME", "BETA"):
            config = TrackerProjectConfig(
                provider="jira",
                workspace="acme.atlassian.net",
                doctrine_mode="external_authoritative",
            )
            credentials = {
                "base_url": "https://acme.atlassian.net",
                "email": "a@b.com",
                "api_token": "tok",
                "project_key": project_key,
            }

            with (
                patch.object(TrackerService, "_load_runtime", return_value=(config, credentials, store)),
                patch.object(
                    TrackerService,
                    "_project_identity",
                    return_value={"uuid": "test-uuid", "slug": "test-proj"},
                ),
                patch("specify_cli.tracker.service.httpx.Client") as mock_client_cls,
            ):
                _make_mock_http(mock_client_cls)
                result = service.sync_publish(server_url="https://example.com", auth_token="test-token")
                keys.append(result["idempotency_key"])

        assert keys[0] != keys[1], "Rebind to different project_key must change idempotency key"
