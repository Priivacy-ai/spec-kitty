"""Tests for binding_ref routing logic on SaaSTrackerClient endpoints.

Validates that ``_routing_params()`` correctly dispatches ``binding_ref``
vs ``project_slug`` and that each public endpoint threads the routing
key through to the HTTP layer.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from specify_cli.tracker.saas_client import (
    SaaSTrackerClient,
    SaaSTrackerClientError,
)

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    status_code: int = 200,
    json_body: dict[str, Any] | None = None,
) -> httpx.Response:
    """Build a fake httpx.Response with the given status and JSON body."""
    resp = httpx.Response(
        status_code=status_code,
        request=httpx.Request("GET", "https://example.com"),
    )
    if json_body is not None:
        import json as _json

        resp._content = _json.dumps(json_body).encode()
        resp.headers["content-type"] = "application/json"
    else:
        resp._content = b""
    return resp


@pytest.fixture()
def mock_sync_config() -> MagicMock:
    config = MagicMock()
    config.get_server_url.return_value = "https://saas.example.com"
    return config


@pytest.fixture()
def client(mock_sync_config: MagicMock, monkeypatch) -> SaaSTrackerClient:
    monkeypatch.setattr("specify_cli.tracker.saas_client._fetch_access_token_sync", lambda: "test-access-token")
    monkeypatch.setattr("specify_cli.tracker.saas_client._current_team_slug_sync", lambda: "team-acme")
    return SaaSTrackerClient(sync_config=mock_sync_config, timeout=5.0)


# ---------------------------------------------------------------------------
# _routing_params unit tests
# ---------------------------------------------------------------------------


class TestRoutingParams:
    """Direct unit tests for the _routing_params helper."""

    def test_binding_ref_only(self, client: SaaSTrackerClient) -> None:
        params = client._routing_params("jira", None, "bind-abc")
        assert params == {"provider": "jira", "binding_ref": "bind-abc"}

    def test_project_slug_only(self, client: SaaSTrackerClient) -> None:
        params = client._routing_params("jira", "my-proj", None)
        assert params == {"provider": "jira", "project_slug": "my-proj"}

    def test_binding_ref_takes_precedence(self, client: SaaSTrackerClient) -> None:
        """When both are supplied, binding_ref wins and project_slug is excluded."""
        params = client._routing_params("jira", "my-proj", "bind-abc")
        assert params == {"provider": "jira", "binding_ref": "bind-abc"}
        assert "project_slug" not in params

    def test_missing_both_raises(self, client: SaaSTrackerClient) -> None:
        with pytest.raises(SaaSTrackerClientError, match="Either project_slug or binding_ref") as exc_info:
            client._routing_params("jira", None, None)
        assert exc_info.value.error_code == "missing_routing_key"

    def test_provider_always_present(self, client: SaaSTrackerClient) -> None:
        params = client._routing_params("linear", None, "ref-1")
        assert params["provider"] == "linear"


# ---------------------------------------------------------------------------
# status() routing integration
# ---------------------------------------------------------------------------


class TestStatusRouting:
    """Verify status() threads routing params to HTTP query params."""

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_status_with_binding_ref(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"connected": True})

        result = client.status("jira", binding_ref="bind-xyz")

        assert result == {"connected": True}
        _, kwargs = mock_http.request.call_args
        assert kwargs["params"]["binding_ref"] == "bind-xyz"
        assert kwargs["params"]["provider"] == "jira"
        assert "project_slug" not in kwargs["params"]

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_status_with_project_slug(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"connected": True})

        result = client.status("jira", "my-project")

        assert result == {"connected": True}
        _, kwargs = mock_http.request.call_args
        assert kwargs["params"]["project_slug"] == "my-project"
        assert kwargs["params"]["provider"] == "jira"
        assert "binding_ref" not in kwargs["params"]

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_status_binding_ref_precedence(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        """When both project_slug and binding_ref supplied, only binding_ref is sent."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"connected": True})

        client.status("jira", "my-project", binding_ref="bind-xyz")

        _, kwargs = mock_http.request.call_args
        assert kwargs["params"]["binding_ref"] == "bind-xyz"
        assert "project_slug" not in kwargs["params"]

    def test_status_missing_both_raises(self, client: SaaSTrackerClient) -> None:
        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client.status("jira")
        assert exc_info.value.error_code == "missing_routing_key"


# ---------------------------------------------------------------------------
# mappings() routing integration
# ---------------------------------------------------------------------------


class TestMappingsRouting:
    """Verify mappings() threads routing params to HTTP query params."""

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_mappings_with_binding_ref(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"fields": []})

        result = client.mappings("jira", binding_ref="bind-m1")

        assert result == {"fields": []}
        _, kwargs = mock_http.request.call_args
        assert kwargs["params"]["binding_ref"] == "bind-m1"
        assert "project_slug" not in kwargs["params"]

    def test_mappings_missing_both_raises(self, client: SaaSTrackerClient) -> None:
        with patch("specify_cli.tracker.saas_client.httpx.Client") as mock_cls:
            mock_http = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_http.request.return_value = _make_response(200, {"fields": []})

            result = client.mappings("jira")

        assert result == {"fields": []}


class TestListTicketsRouting:
    """Verify list_tickets() threads optional routing params into the POST body."""

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_list_tickets_with_binding_ref(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"tickets": []})

        client.list_tickets("linear", binding_ref="bind-123", limit=20)

        _, kwargs = mock_http.request.call_args
        assert kwargs["json"]["binding_ref"] == "bind-123"
        assert kwargs["json"]["provider"] == "linear"
        assert kwargs["json"]["limit"] == 20
        assert "project_slug" not in kwargs["json"]

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_list_tickets_provider_only(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"tickets": []})

        client.list_tickets("linear", limit=20)

        _, kwargs = mock_http.request.call_args
        assert kwargs["json"] == {"provider": "linear", "limit": 20}


# ---------------------------------------------------------------------------
# pull() routing integration (POST method)
# ---------------------------------------------------------------------------


class TestPullRouting:
    """Verify pull() threads routing params into the JSON body."""

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_pull_with_binding_ref(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"items": [], "cursor": None})

        result = client.pull("jira", binding_ref="bind-pull1")

        assert result == {"items": [], "cursor": None}
        _, kwargs = mock_http.request.call_args
        assert kwargs["json"]["binding_ref"] == "bind-pull1"
        assert kwargs["json"]["provider"] == "jira"
        assert "project_slug" not in kwargs["json"]

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_pull_with_project_slug(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"items": []})

        client.pull("jira", "proj-slug")

        _, kwargs = mock_http.request.call_args
        assert kwargs["json"]["project_slug"] == "proj-slug"
        assert "binding_ref" not in kwargs["json"]

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_pull_binding_ref_precedence(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"items": []})

        client.pull("jira", "proj-slug", binding_ref="bind-wins")

        _, kwargs = mock_http.request.call_args
        assert kwargs["json"]["binding_ref"] == "bind-wins"
        assert "project_slug" not in kwargs["json"]

    def test_pull_missing_both_raises(self, client: SaaSTrackerClient) -> None:
        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client.pull("jira")
        assert exc_info.value.error_code == "missing_routing_key"


# ---------------------------------------------------------------------------
# push() routing integration (POST, async-capable)
# ---------------------------------------------------------------------------


class TestPushRouting:
    """Verify push() threads routing params into the JSON body."""

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_push_with_binding_ref(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"pushed": 0})

        result = client.push("jira", binding_ref="bind-push1", items=[])

        assert result == {"pushed": 0}
        _, kwargs = mock_http.request.call_args
        assert kwargs["json"]["binding_ref"] == "bind-push1"
        assert "project_slug" not in kwargs["json"]

    def test_push_missing_both_raises(self, client: SaaSTrackerClient) -> None:
        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client.push("jira")
        assert exc_info.value.error_code == "missing_routing_key"


# ---------------------------------------------------------------------------
# run() routing integration (POST, async-capable)
# ---------------------------------------------------------------------------


class TestRunRouting:
    """Verify run() threads routing params into the JSON body."""

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_run_with_binding_ref(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"synced": 5})

        result = client.run("jira", binding_ref="bind-run1")

        assert result == {"synced": 5}
        _, kwargs = mock_http.request.call_args
        assert kwargs["json"]["binding_ref"] == "bind-run1"
        assert kwargs["json"]["provider"] == "jira"
        assert "project_slug" not in kwargs["json"]

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_run_with_project_slug(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"synced": 0})

        client.run("jira", "my-proj")

        _, kwargs = mock_http.request.call_args
        assert kwargs["json"]["project_slug"] == "my-proj"
        assert "binding_ref" not in kwargs["json"]

    def test_run_missing_both_raises(self, client: SaaSTrackerClient) -> None:
        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client.run("jira")
        assert exc_info.value.error_code == "missing_routing_key"
