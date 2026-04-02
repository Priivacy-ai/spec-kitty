"""Tests for SaaSTrackerClient origin-binding transport extensions.

Covers search_issues() and bind_mission_origin() methods: success paths,
error semantics (401, 404, 409, 422, 429), auth header injection, and
idempotency key handling.
"""

from __future__ import annotations

import json as _json
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
    *,
    text: str = "",
) -> httpx.Response:
    """Build a fake httpx.Response with the given status and JSON body."""
    resp = httpx.Response(
        status_code=status_code,
        request=httpx.Request("GET", "https://example.com"),
    )
    if json_body is not None:
        resp._content = _json.dumps(json_body).encode()
        resp.headers["content-type"] = "application/json"
    elif text:
        resp._content = text.encode()
    else:
        resp._content = b""
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_credential_store() -> MagicMock:
    store = MagicMock()
    store.get_access_token.return_value = "test-access-token"
    store.get_team_slug.return_value = "team-acme"
    store.get_refresh_token.return_value = "test-refresh-token"
    return store


@pytest.fixture()
def mock_sync_config() -> MagicMock:
    config = MagicMock()
    config.get_server_url.return_value = "https://saas.example.com"
    return config


@pytest.fixture()
def client(mock_credential_store: MagicMock, mock_sync_config: MagicMock) -> SaaSTrackerClient:
    return SaaSTrackerClient(
        credential_store=mock_credential_store,
        sync_config=mock_sync_config,
        timeout=5.0,
    )


# ---------------------------------------------------------------------------
# search_issues() tests
# ---------------------------------------------------------------------------


class TestSearchIssues:
    """Tests for SaaSTrackerClient.search_issues()."""

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_200_with_candidates(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200,
            {
                "candidates": [
                    {"id": "PROJ-42", "key": "PROJ-42", "title": "Fix login bug"},
                    {"id": "PROJ-43", "key": "PROJ-43", "title": "Add search"},
                ],
                "resource_type": "project",
                "resource_id": "proj-1",
            },
        )

        result = client.search_issues("jira", "proj-1", query_text="login")

        assert len(result["candidates"]) == 2
        assert result["candidates"][0]["key"] == "PROJ-42"
        assert result["resource_type"] == "project"

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_200_empty_candidates(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200,
            {"candidates": [], "resource_type": "project", "resource_id": "proj-1"},
        )

        result = client.search_issues("jira", "proj-1", query_text="nonexistent")

        assert result["candidates"] == []

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_query_key_and_query_text_both_in_payload(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"candidates": []}
        )

        client.search_issues(
            "jira", "proj-1", query_key="PROJ-42", query_text="login bug"
        )

        _, kwargs = mock_http.request.call_args
        payload = kwargs["json"]
        assert payload["query_key"] == "PROJ-42"
        assert payload["query_text"] == "login bug"
        assert payload["provider"] == "jira"
        assert payload["project_slug"] == "proj-1"
        assert payload["limit"] == 10

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_401_raises_after_refresh(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """401 user_action_required: raises SaaSTrackerClientError after refresh attempt."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        # First call: 401, refresh attempt, second call: still 401
        mock_http.request.side_effect = [
            _make_response(
                401,
                {"message": "Unauthorized", "user_action_required": True},
            ),
            _make_response(
                401,
                {"message": "Unauthorized", "user_action_required": True},
            ),
        ]

        with patch("specify_cli.tracker.saas_client.AuthClient") as mock_auth_cls:
            mock_auth = MagicMock()
            mock_auth_cls.return_value = mock_auth

            with pytest.raises(SaaSTrackerClientError, match="Session expired"):
                client.search_issues("jira", "proj-1", query_text="test")

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_404_raises(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            404,
            {"message": "No mapping found for provider", "code": "no_mapping"},
        )

        with pytest.raises(SaaSTrackerClientError, match="No mapping found"):
            client.search_issues("jira", "proj-1", query_text="test")

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_422_raises(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            422,
            {"message": "Invalid query parameters", "code": "validation_error"},
        )

        with pytest.raises(SaaSTrackerClientError, match="Invalid query parameters"):
            client.search_issues("jira", "proj-1", query_text="")

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_429_retries_then_raises(
        self, mock_cls: MagicMock, mock_sleep: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        # First request: 429, retry, second request: still 429
        mock_http.request.side_effect = [
            _make_response(
                429,
                {
                    "message": "Rate limited",
                    "retry_after_seconds": 2,
                    "retryable": True,
                },
            ),
            _make_response(
                429,
                {
                    "message": "Rate limited",
                    "retry_after_seconds": 2,
                    "retryable": True,
                },
            ),
        ]

        with pytest.raises(SaaSTrackerClientError, match="Rate limited"):
            client.search_issues("jira", "proj-1", query_text="test")

        mock_sleep.assert_called_once_with(2.0)

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_auth_headers_sent(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"candidates": []}
        )

        client.search_issues("jira", "proj-1", query_text="test")

        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer test-access-token"
        assert kwargs["headers"]["X-Team-Slug"] == "team-acme"

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_uses_post_method_to_search_path(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"candidates": []}
        )

        client.search_issues("jira", "proj-1")

        args, _ = mock_http.request.call_args
        assert args[0] == "POST"
        assert args[1].endswith("/api/v1/tracker/issue-search/")


# ---------------------------------------------------------------------------
# bind_mission_origin() tests
# ---------------------------------------------------------------------------


class TestBindMissionOrigin:
    """Tests for SaaSTrackerClient.bind_mission_origin()."""

    _BIND_KWARGS: dict[str, Any] = {
        "feature_slug": "061-ticket-first",
        "external_issue_id": "12345",
        "external_issue_key": "PROJ-42",
        "external_issue_url": "https://jira.example.com/browse/PROJ-42",
        "title": "Fix login bug",
    }

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_200_success(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200,
            {
                "origin_link_id": "link-abc-123",
                "bound_at": "2026-04-01T12:00:00Z",
                "feature_slug": "061-ticket-first",
            },
        )

        result = client.bind_mission_origin("jira", "proj-1", **self._BIND_KWARGS)

        assert result["origin_link_id"] == "link-abc-123"
        assert result["bound_at"] == "2026-04-01T12:00:00Z"

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_200_same_origin_noop(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """Re-binding same origin returns success (idempotent no-op)."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200,
            {
                "origin_link_id": "link-abc-123",
                "bound_at": "2026-04-01T10:00:00Z",
                "already_bound": True,
            },
        )

        result = client.bind_mission_origin("jira", "proj-1", **self._BIND_KWARGS)

        assert result["origin_link_id"] == "link-abc-123"
        assert result["already_bound"] is True

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_409_different_origin_raises(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            409,
            {
                "message": "Feature already bound to a different issue",
                "code": "origin_conflict",
            },
        )

        with pytest.raises(
            SaaSTrackerClientError, match="already bound to a different issue"
        ):
            client.bind_mission_origin("jira", "proj-1", **self._BIND_KWARGS)

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_401_raises_after_refresh(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(401, {"message": "Unauthorized"}),
            _make_response(401, {"message": "Unauthorized"}),
        ]

        with patch("specify_cli.tracker.saas_client.AuthClient") as mock_auth_cls:
            mock_auth = MagicMock()
            mock_auth_cls.return_value = mock_auth

            with pytest.raises(SaaSTrackerClientError, match="Session expired"):
                client.bind_mission_origin("jira", "proj-1", **self._BIND_KWARGS)

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_idempotency_key_auto_generated(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """When no idempotency_key provided, one is auto-generated and sent as header."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"origin_link_id": "link-abc-123"}
        )

        client.bind_mission_origin("jira", "proj-1", **self._BIND_KWARGS)

        _, kwargs = mock_http.request.call_args
        # Idempotency-Key header must be present (auto-generated UUID)
        assert "Idempotency-Key" in kwargs["headers"]
        key_value = kwargs["headers"]["Idempotency-Key"]
        assert len(key_value) > 0

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_idempotency_key_provided(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """When idempotency_key is explicitly provided, it is forwarded as-is."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"origin_link_id": "link-abc-123"}
        )

        client.bind_mission_origin(
            "jira",
            "proj-1",
            **self._BIND_KWARGS,
            idempotency_key="my-custom-key-123",
        )

        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["Idempotency-Key"] == "my-custom-key-123"

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_uses_post_method_to_bind_path(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"origin_link_id": "link-abc-123"}
        )

        client.bind_mission_origin("jira", "proj-1", **self._BIND_KWARGS)

        args, _ = mock_http.request.call_args
        assert args[0] == "POST"
        assert args[1].endswith("/api/v1/tracker/mission-origin/bind/")

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_payload_contains_all_fields(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"origin_link_id": "link-abc-123"}
        )

        client.bind_mission_origin("jira", "proj-1", **self._BIND_KWARGS)

        _, kwargs = mock_http.request.call_args
        payload = kwargs["json"]
        assert payload["provider"] == "jira"
        assert payload["project_slug"] == "proj-1"
        assert payload["mission_id"] == "061-ticket-first"
        assert payload["external_issue_id"] == "12345"
        assert payload["external_issue_key"] == "PROJ-42"
        assert payload["external_issue_url"] == "https://jira.example.com/browse/PROJ-42"
        assert payload["external_title"] == "Fix login bug"
        assert payload["external_status"] == ""
