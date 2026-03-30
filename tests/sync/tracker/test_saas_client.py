"""Comprehensive tests for SaaSTrackerClient.

Covers auth injection, synchronous endpoints, async endpoints (push/run with
202 polling), polling timeout, 401 refresh, 429 rate-limit, error envelope
parsing, and network errors.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock, patch, call

import httpx
import pytest

from specify_cli.tracker.saas_client import (
    SaaSTrackerClient,
    SaaSTrackerClientError,
    _parse_error_envelope,
)

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Fixtures
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
        import json as _json

        resp._content = _json.dumps(json_body).encode()
        resp.headers["content-type"] = "application/json"
    elif text:
        resp._content = text.encode()
    else:
        resp._content = b""
    return resp


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
# Error envelope parsing
# ---------------------------------------------------------------------------


class TestParseErrorEnvelope:
    def test_parses_full_envelope(self) -> None:
        resp = _make_response(
            422,
            {
                "code": "missing_installation",
                "category": "identity_resolution",
                "message": "No installation found",
                "retryable": False,
                "user_action_required": "Install the app",
                "source": "jira",
                "retry_after_seconds": None,
            },
        )
        envelope = _parse_error_envelope(resp)
        assert envelope["code"] == "missing_installation"
        assert envelope["category"] == "identity_resolution"
        assert envelope["message"] == "No installation found"
        assert envelope["retryable"] is False
        assert envelope["user_action_required"] == "Install the app"
        assert envelope["source"] == "jira"

    def test_handles_malformed_json(self) -> None:
        resp = _make_response(500, text="Internal Server Error")
        envelope = _parse_error_envelope(resp)
        assert envelope["code"] is None
        assert envelope["category"] is None
        assert envelope["message"] == "HTTP 500"

    def test_handles_partial_envelope(self) -> None:
        resp = _make_response(400, {"message": "Bad request"})
        envelope = _parse_error_envelope(resp)
        assert envelope["message"] == "Bad request"
        assert envelope["code"] is None
        assert envelope["category"] is None
        assert envelope["retryable"] is False


# ---------------------------------------------------------------------------
# Auth injection
# ---------------------------------------------------------------------------


class TestAuthInjection:
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_bearer_token_on_every_request(
        self, mock_httpx_client_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_httpx_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_httpx_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"ok": True})

        client._request("GET", "/api/v1/tracker/status")

        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer test-access-token"

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_team_slug_header_on_every_request(
        self, mock_httpx_client_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_httpx_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_httpx_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"ok": True})

        client._request("GET", "/api/v1/tracker/status")

        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-Team-Slug"] == "team-acme"

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_token_fetched_at_request_time(
        self, mock_httpx_client_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """Token is read on each call, not cached at construction."""
        mock_http = MagicMock()
        mock_httpx_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_httpx_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"ok": True})

        # First request uses the original token
        client._request("GET", "/api/v1/tracker/status")

        # Change token
        client._credential_store.get_access_token.return_value = "new-token"
        client._request("GET", "/api/v1/tracker/status")

        calls = mock_http.request.call_args_list
        assert calls[0][1]["headers"]["Authorization"] == "Bearer test-access-token"
        assert calls[1][1]["headers"]["Authorization"] == "Bearer new-token"

    def test_no_token_raises(self, client: SaaSTrackerClient) -> None:
        client._credential_store.get_access_token.return_value = None
        with pytest.raises(SaaSTrackerClientError, match="No valid access token"):
            client._request("GET", "/api/v1/tracker/status")

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_no_team_slug_omits_header(
        self, mock_httpx_client_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_httpx_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_httpx_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"ok": True})

        client._credential_store.get_team_slug.return_value = None
        client._request("GET", "/api/v1/tracker/status")

        _, kwargs = mock_http.request.call_args
        assert "X-Team-Slug" not in kwargs["headers"]


# ---------------------------------------------------------------------------
# Synchronous endpoints
# ---------------------------------------------------------------------------


class TestPull:
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_pull_200(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"items": [{"id": "1"}], "cursor": "abc"}
        )

        result = client.pull("jira", "proj-1")

        assert result == {"items": [{"id": "1"}], "cursor": "abc"}
        _, kwargs = mock_http.request.call_args
        assert kwargs["json"]["provider"] == "jira"
        assert kwargs["json"]["project_slug"] == "proj-1"
        assert kwargs["json"]["limit"] == 100

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_pull_with_cursor_and_filters(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"items": []})

        client.pull(
            "jira", "proj-1", limit=50, cursor="xyz", filters={"status": ["open"]}
        )

        _, kwargs = mock_http.request.call_args
        assert kwargs["json"]["cursor"] == "xyz"
        assert kwargs["json"]["filters"] == {"status": ["open"]}
        assert kwargs["json"]["limit"] == 50

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_pull_uses_post_method(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"items": []})

        client.pull("jira", "proj-1")

        args, kwargs = mock_http.request.call_args
        assert args[0] == "POST"
        assert "/api/v1/tracker/pull" in args[1]


class TestStatus:
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_status_200(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"connected": True, "last_sync": "2026-01-01"}
        )

        result = client.status("jira", "proj-1")

        assert result["connected"] is True
        args, kwargs = mock_http.request.call_args
        assert args[0] == "GET"
        assert "/api/v1/tracker/status" in args[1]
        assert kwargs["params"]["provider"] == "jira"
        assert kwargs["params"]["project_slug"] == "proj-1"


class TestMappings:
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_mappings_200(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"fields": [{"src": "title", "dst": "summary"}]}
        )

        result = client.mappings("jira", "proj-1")

        assert result["fields"][0]["src"] == "title"
        args, kwargs = mock_http.request.call_args
        assert args[0] == "GET"
        assert "/api/v1/tracker/mappings" in args[1]


# ---------------------------------------------------------------------------
# Async-capable endpoints (push, run)
# ---------------------------------------------------------------------------


class TestPush:
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_push_200_sync(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"pushed": 3, "errors": []}
        )

        result = client.push("jira", "proj-1", [{"title": "Bug"}])
        assert result == {"pushed": 3, "errors": []}

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_push_has_idempotency_key(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"pushed": 1})

        client.push("jira", "proj-1", [])

        _, kwargs = mock_http.request.call_args
        idem_key = kwargs["headers"]["Idempotency-Key"]
        # Must be a valid UUID
        uuid.UUID(idem_key)

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_push_custom_idempotency_key(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"pushed": 1})

        client.push("jira", "proj-1", [], idempotency_key="my-key-123")

        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["Idempotency-Key"] == "my-key-123"

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_push_202_polls_until_completed(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        # First call: POST push -> 202
        # Second call: GET operation -> pending
        # Third call: GET operation -> completed
        mock_http.request.side_effect = [
            _make_response(202, {"operation_id": "op-1"}),
            _make_response(200, {"status": "pending"}),
            _make_response(200, {"status": "completed", "result": {"pushed": 2}}),
        ]
        mock_monotonic.side_effect = [0.0, 1.0, 3.0]

        result = client.push("jira", "proj-1", [{"title": "X"}])
        assert result == {"pushed": 2}

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_push_202_polls_failed_raises(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(202, {"operation_id": "op-2"}),
            _make_response(200, {"status": "failed", "error": "Provider rejected"}),
        ]
        mock_monotonic.side_effect = [0.0, 1.0]

        with pytest.raises(SaaSTrackerClientError, match="Provider rejected"):
            client.push("jira", "proj-1", [{"title": "Y"}])


class TestRun:
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_run_200_sync(self, mock_cls: MagicMock, client: SaaSTrackerClient) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(
            200, {"pulled": 5, "pushed": 3}
        )

        result = client.run("jira", "proj-1")
        assert result == {"pulled": 5, "pushed": 3}
        _, kwargs = mock_http.request.call_args
        assert kwargs["json"]["pull_first"] is True
        assert kwargs["json"]["limit"] == 100

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_run_has_idempotency_key(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.request.return_value = _make_response(200, {"ok": True})

        client.run("jira", "proj-1")

        _, kwargs = mock_http.request.call_args
        idem_key = kwargs["headers"]["Idempotency-Key"]
        uuid.UUID(idem_key)  # validates UUID format

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_run_202_polls_until_completed(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(202, {"operation_id": "op-run"}),
            _make_response(200, {"status": "running"}),
            _make_response(200, {"status": "completed", "result": {"synced": 10}}),
        ]
        mock_monotonic.side_effect = [0.0, 1.0, 3.0]

        result = client.run("jira", "proj-1")
        assert result == {"synced": 10}


# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------


class TestPolling:
    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_exponential_backoff_intervals(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        # pending, pending, pending, completed
        mock_http.request.side_effect = [
            _make_response(200, {"status": "pending"}),
            _make_response(200, {"status": "pending"}),
            _make_response(200, {"status": "pending"}),
            _make_response(200, {"status": "completed", "result": {"done": True}}),
        ]
        # Provide enough time values: start, check1, check2, check3, check4
        mock_monotonic.side_effect = [0.0, 1.0, 3.0, 7.0, 15.0]

        # Seed random for deterministic jitter
        import random
        random.seed(42)

        result = client._poll_operation("op-backoff")
        assert result == {"done": True}

        # Verify sleep was called with increasing delays (with jitter)
        sleep_calls = mock_sleep.call_args_list
        assert len(sleep_calls) == 3
        # delay starts at 1, doubles each iteration
        # jitter: delay * (0.8 + 0.4 * random())
        delays = [c.args[0] for c in sleep_calls]
        # First delay based on 1.0, second on 2.0, third on 4.0
        assert 0.8 <= delays[0] <= 1.2
        assert 1.6 <= delays[1] <= 2.4
        assert 3.2 <= delays[2] <= 4.8

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_timeout_after_5_minutes(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        # monotonic returns 301 on first check, exceeding 300 timeout
        mock_monotonic.side_effect = [0.0, 301.0]

        with pytest.raises(SaaSTrackerClientError, match="timed out after 5 minutes"):
            client._poll_operation("op-timeout")

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_pending_then_running_then_completed(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(200, {"status": "pending"}),
            _make_response(200, {"status": "running"}),
            _make_response(200, {"status": "completed", "result": {"items": 5}}),
        ]
        mock_monotonic.side_effect = [0.0, 1.0, 3.0, 7.0]

        result = client._poll_operation("op-progress")
        assert result == {"items": 5}


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestRetryBehaviors:
    @patch("specify_cli.tracker.saas_client.AuthClient")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_401_refresh_retry_success(
        self,
        mock_cls: MagicMock,
        mock_auth_cls: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        # First: 401, after refresh: 200
        mock_http.request.side_effect = [
            _make_response(401, {"message": "Unauthorized"}),
            _make_response(200, {"ok": True}),
        ]
        mock_auth_instance = MagicMock()
        mock_auth_cls.return_value = mock_auth_instance

        result = client._request_with_retry("GET", "/api/v1/tracker/status")
        assert result.status_code == 200
        mock_auth_instance.refresh_tokens.assert_called_once()

    @patch("specify_cli.tracker.saas_client.AuthClient")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_401_double_failure_halts(
        self,
        mock_cls: MagicMock,
        mock_auth_cls: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        # 401 both times
        mock_http.request.side_effect = [
            _make_response(401, {"message": "Unauthorized"}),
            _make_response(401, {"message": "Unauthorized"}),
        ]
        mock_auth_instance = MagicMock()
        mock_auth_cls.return_value = mock_auth_instance

        with pytest.raises(SaaSTrackerClientError, match="Session expired"):
            client._request_with_retry("GET", "/api/v1/tracker/status")

    @patch("specify_cli.tracker.saas_client.AuthClient")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_401_refresh_itself_fails(
        self,
        mock_cls: MagicMock,
        mock_auth_cls: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(401, {"message": "Unauthorized"})
        mock_auth_instance = MagicMock()
        mock_auth_instance.refresh_tokens.side_effect = RuntimeError("refresh failed")
        mock_auth_cls.return_value = mock_auth_instance

        with pytest.raises(SaaSTrackerClientError, match="Session expired"):
            client._request_with_retry("GET", "/api/v1/tracker/status")

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_429_respects_retry_after(
        self,
        mock_cls: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(429, {"message": "Rate limited", "retry_after_seconds": 3}),
            _make_response(200, {"ok": True}),
        ]

        result = client._request_with_retry("GET", "/api/v1/tracker/status")
        assert result.status_code == 200
        mock_sleep.assert_called_once_with(3.0)

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_429_defaults_to_5s_when_missing(
        self,
        mock_cls: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(429, {"message": "Rate limited"}),
            _make_response(200, {"ok": True}),
        ]

        client._request_with_retry("GET", "/api/v1/tracker/status")
        mock_sleep.assert_called_once_with(5.0)

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_429_double_failure_raises(
        self,
        mock_cls: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(429, {"message": "Rate limited", "retry_after_seconds": 1}),
            _make_response(429, {"message": "Still rate limited"}),
        ]

        with pytest.raises(SaaSTrackerClientError, match="Still rate limited"):
            client._request_with_retry("GET", "/api/v1/tracker/status")

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_4xx_error_envelope_parsed(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            422,
            {
                "code": "missing_installation",
                "category": "identity_resolution",
                "message": "Jira app not installed",
                "user_action_required": "Install the Spec Kitty app in Jira",
            },
        )

        with pytest.raises(
            SaaSTrackerClientError, match="Jira app not installed"
        ) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")
        assert "Install the Spec Kitty app" in str(exc_info.value)

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_5xx_error_envelope_parsed(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            500, {"code": "internal_error", "message": "Something broke"}
        )

        with pytest.raises(SaaSTrackerClientError, match="Something broke"):
            client._request_with_retry("GET", "/api/v1/tracker/status")

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_malformed_error_response(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(500, text="Internal Server Error")

        with pytest.raises(SaaSTrackerClientError, match="HTTP 500"):
            client._request_with_retry("GET", "/api/v1/tracker/status")


class TestNetworkErrors:
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_connect_error(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(SaaSTrackerClientError, match="Cannot connect"):
            client._request("GET", "/api/v1/tracker/status")

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_timeout_error(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = httpx.ReadTimeout("Read timed out")

        with pytest.raises(SaaSTrackerClientError, match="Cannot connect"):
            client._request("GET", "/api/v1/tracker/status")


# ---------------------------------------------------------------------------
# Constructor defaults
# ---------------------------------------------------------------------------


class TestConstructorDefaults:
    @patch("specify_cli.tracker.saas_client.SyncConfig")
    @patch("specify_cli.tracker.saas_client.CredentialStore")
    def test_defaults_when_none(
        self, mock_cred_cls: MagicMock, mock_config_cls: MagicMock
    ) -> None:
        mock_config_cls.return_value.get_server_url.return_value = "https://default.dev"
        c = SaaSTrackerClient()
        assert c._base_url == "https://default.dev"
        mock_cred_cls.assert_called_once()
        mock_config_cls.assert_called_once()

    def test_custom_instances_used(
        self, mock_credential_store: MagicMock, mock_sync_config: MagicMock
    ) -> None:
        c = SaaSTrackerClient(
            credential_store=mock_credential_store,
            sync_config=mock_sync_config,
        )
        assert c._credential_store is mock_credential_store
        assert c._sync_config is mock_sync_config
        assert c._base_url == "https://saas.example.com"
