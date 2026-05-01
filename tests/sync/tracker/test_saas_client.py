"""Comprehensive tests for SaaSTrackerClient.

Covers auth injection, synchronous endpoints, async endpoints (push/run with
202 polling), polling timeout, 401 refresh, 429 rate-limit, error envelope
parsing, and network errors.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock, patch

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
                "error_code": "missing_installation",
                "category": "identity_resolution",
                "message": "No installation found",
                "retryable": False,
                "user_action_required": True,
                "source": "jira",
                "retry_after_seconds": None,
            },
        )
        envelope = _parse_error_envelope(resp)
        assert envelope["error_code"] == "missing_installation"
        assert envelope["category"] == "identity_resolution"
        assert envelope["message"] == "No installation found"
        assert envelope["retryable"] is False
        assert envelope["user_action_required"] is True
        assert envelope["source"] == "jira"

    def test_handles_malformed_json(self) -> None:
        resp = _make_response(500, text="Internal Server Error")
        envelope = _parse_error_envelope(resp)
        assert envelope["error_code"] is None
        assert envelope["category"] is None
        assert envelope["message"] == "HTTP 500"

    def test_handles_partial_envelope(self) -> None:
        resp = _make_response(400, {"message": "Bad request"})
        envelope = _parse_error_envelope(resp)
        assert envelope["message"] == "Bad request"
        assert envelope["error_code"] is None
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
        client._credential_store.get_access_token.return_value = "new-token"  # type: ignore[attr-defined]
        client._request("GET", "/api/v1/tracker/status")

        calls = mock_http.request.call_args_list
        assert calls[0][1]["headers"]["Authorization"] == "Bearer test-access-token"
        assert calls[1][1]["headers"]["Authorization"] == "Bearer new-token"

    def test_no_token_raises(self, client: SaaSTrackerClient) -> None:
        client._credential_store.get_access_token.return_value = None  # type: ignore[attr-defined]
        with pytest.raises(SaaSTrackerClientError, match="No valid access token"):
            client._request("GET", "/api/v1/tracker/status")

    def test_missing_team_slug_raises_error(self, client: SaaSTrackerClient) -> None:
        """FR-015: Missing X-Team-Slug must raise, not silently omit the header."""
        client._credential_store.get_team_slug.return_value = None  # type: ignore[attr-defined]
        with pytest.raises(SaaSTrackerClientError, match="No team context available"):
            client._request("GET", "/api/v1/tracker/status")

    def test_empty_team_slug_raises_error(self, client: SaaSTrackerClient) -> None:
        """FR-015: Empty string team slug must also raise."""
        client._credential_store.get_team_slug.return_value = ""  # type: ignore[attr-defined]
        with pytest.raises(SaaSTrackerClientError, match="No team context available"):
            client._request("GET", "/api/v1/tracker/status")


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
        assert args[1].endswith("/api/v1/tracker/pull/")


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
        assert args[1].endswith("/api/v1/tracker/status/")
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
        assert args[1].endswith("/api/v1/tracker/mappings/")


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
    @patch(
        "specify_cli.tracker.saas_client.secrets.randbelow",
        side_effect=[1000, 2000, 3000],  # basis points → jitter factors 0.9, 1.0, 1.1
    )
    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_exponential_backoff_intervals(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        mock_randbelow: MagicMock,
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

        result = client._poll_operation("op-backoff")
        assert result == {"done": True}

        # Verify sleep was called with increasing delays (with jitter)
        # jitter_factor = 0.8 + (basis_points / 10000)
        # 1000 bp → 0.9, 2000 bp → 1.0, 3000 bp → 1.1
        sleep_calls = mock_sleep.call_args_list
        assert len(sleep_calls) == 3
        delays = [c.args[0] for c in sleep_calls]
        assert delays == [0.9, 2.0, 4.4]
        assert mock_randbelow.call_count == 3

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
    @patch("specify_cli.tracker.saas_client._force_refresh_sync")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_401_refresh_retry_success(
        self,
        mock_cls: MagicMock,
        mock_force_refresh: MagicMock,
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
        result = client._request_with_retry("GET", "/api/v1/tracker/status")
        assert result.status_code == 200
        mock_force_refresh.assert_called_once()

    @patch("specify_cli.tracker.saas_client._force_refresh_sync")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_401_double_failure_halts(
        self,
        mock_cls: MagicMock,
        mock_force_refresh: MagicMock,
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
        with pytest.raises(SaaSTrackerClientError, match="Session expired"):
            client._request_with_retry("GET", "/api/v1/tracker/status")

    @patch("specify_cli.tracker.saas_client._force_refresh_sync")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_401_refresh_itself_fails(
        self,
        mock_cls: MagicMock,
        mock_force_refresh: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(401, {"message": "Unauthorized"})
        mock_force_refresh.side_effect = RuntimeError("refresh failed")

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
                "error_code": "missing_installation",
                "category": "identity_resolution",
                "message": "Jira app not installed",
                "user_action_required": True,
            },
        )

        with pytest.raises(
            SaaSTrackerClientError, match="Jira app not installed"
        ) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")
        assert "action required" in str(exc_info.value)

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_5xx_error_envelope_parsed(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            500, {"error_code": "internal_error", "message": "Something broke"}
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
    @pytest.mark.skip(
        reason=(
            "Obsolete after WP08 HTTP transport rewire: SaaSTrackerClient no "
            "longer instantiates CredentialStore directly. Tokens are fetched "
            "lazily via the process-wide TokenManager, so the default-path "
            "construction no longer touches CredentialStore at all."
        )
    )
    def test_defaults_when_none(self) -> None:
        pass

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


# ---------------------------------------------------------------------------
# Regression tests for Codex review cycle 1 fixes
# ---------------------------------------------------------------------------


class TestAsyncErrorEnvelopeParsing:
    """Fix 1 (FR-017/NFR-002): Failed async operations must parse the error
    envelope dict, not dump it as a raw string."""

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_failed_operation_parses_error_envelope_dict(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        """When the 'error' field is an ErrorEnvelope dict, the raised exception
        must contain the human-readable 'message' and 'user_action_required',
        not a repr of the dict."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        error_envelope = {
            "error_code": "provider_auth_expired",
            "category": "auth",
            "message": "Jira OAuth token has expired",
            "user_action_required": True,
        }
        mock_http.request.side_effect = [
            _make_response(202, {"operation_id": "op-err-envelope"}),
            _make_response(200, {"status": "failed", "error": error_envelope}),
        ]
        mock_monotonic.side_effect = [0.0, 1.0]

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client.push("jira", "proj-1", [{"title": "Bug"}])

        error_text = str(exc_info.value)
        # Must contain the readable message
        assert "Jira OAuth token has expired" in error_text
        # user_action_required is boolean True → generic guidance appended
        assert "action required" in error_text
        # Must NOT contain raw dict syntax
        assert "{'error_code'" not in error_text
        assert "provider_auth_expired" not in error_text

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_failed_operation_with_string_error_still_works(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        """When the 'error' field is a plain string, it should still work."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(202, {"operation_id": "op-str-err"}),
            _make_response(200, {"status": "failed", "error": "Something went wrong"}),
        ]
        mock_monotonic.side_effect = [0.0, 1.0]

        with pytest.raises(SaaSTrackerClientError, match="Something went wrong"):
            client.push("jira", "proj-1", [{"title": "Bug"}])

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.time.monotonic")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_failed_operation_with_no_error_field(
        self,
        mock_cls: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        """When the 'error' field is missing, a fallback message is used."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(202, {"operation_id": "op-no-err"}),
            _make_response(200, {"status": "failed"}),
        ]
        mock_monotonic.side_effect = [0.0, 1.0]

        with pytest.raises(SaaSTrackerClientError, match="Operation failed"):
            client.push("jira", "proj-1", [{"title": "Bug"}])


class TestAuthClientUsesCorrectConfig:
    """Fix 2 (FR-020): historically, SaaSTrackerClient used to reach into
    AuthClient and rewire its credential_store + config on every 401 refresh.

    After the WP08 HTTP-transport rewire, refresh is driven through the
    process-wide ``TokenManager`` single-flight, which always uses the same
    backing storage and config surface by construction. There is no longer a
    per-call AuthClient instance to inspect. The concern FR-020 raised is
    still satisfied — the TokenManager resolves its server URL through
    ``get_saas_base_url()`` — but the legacy attribute-level assertion is
    no longer meaningful.
    """

    @pytest.mark.skip(
        reason=(
            "Obsolete after WP08 HTTP transport rewire: refresh is now a "
            "TokenManager single-flight call, not a per-request AuthClient "
            "instance whose attributes can be inspected from outside."
        )
    )
    def test_401_refresh_uses_client_sync_config(self) -> None:
        pass


# ---------------------------------------------------------------------------
# WP03: Enriched error attributes (T013 + T014)
# ---------------------------------------------------------------------------


class TestErrorEnrichmentAttributes:
    """T013: Verify enriched SaaSTrackerClientError attributes from PRI-12 envelope."""

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_error_enrichment_preserves_error_code(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """error_code is extracted from the envelope 'error_code' field."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            400,
            {
                "error_code": "binding_not_found",
                "message": "No binding exists for this mission",
            },
        )

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")

        assert exc_info.value.error_code == "binding_not_found"

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_error_enrichment_preserves_status_code(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """status_code is the HTTP status from the response."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            400,
            {"error_code": "binding_not_found", "message": "Not found"},
        )

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")

        assert exc_info.value.status_code == 400

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_error_enrichment_preserves_details(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """details dict is the full parsed envelope."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            422,
            {
                "error_code": "mapping_disabled",
                "category": "configuration",
                "message": "Mapping is disabled",
                "retryable": False,
                "user_action_required": False,
                "source": "jira",
                "retry_after_seconds": None,
            },
        )

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")

        details = exc_info.value.details
        assert isinstance(details, dict)
        assert details["error_code"] == "mapping_disabled"
        assert details["category"] == "configuration"
        assert details["source"] == "jira"

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_error_enrichment_user_action_required(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """user_action_required is True when envelope says so."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            422,
            {
                "error_code": "missing_installation",
                "message": "App not installed",
                "user_action_required": True,
            },
        )

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")

        assert exc_info.value.user_action_required is True

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_error_enrichment_backward_compat_str(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """str(e) still returns the human-readable message."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            400,
            {"error_code": "binding_not_found", "message": "No binding found"},
        )

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")

        assert str(exc_info.value) == "No binding found"

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_error_enrichment_missing_envelope(
        self, mock_cls: MagicMock, client: SaaSTrackerClient
    ) -> None:
        """Empty/malformed body: error_code=None, status_code preserved."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.return_value = _make_response(
            400, text="Bad Request"
        )

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")

        assert exc_info.value.error_code is None
        assert exc_info.value.status_code == 400
        assert str(exc_info.value) == "HTTP 400"

    @patch("specify_cli.tracker.saas_client.time.sleep")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_429_enrichment_has_error_code_and_status(
        self,
        mock_cls: MagicMock,
        mock_sleep: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        """Double 429 raises with error_code='rate_limited' and status_code=429."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(429, {"message": "Rate limited", "retry_after_seconds": 1}),
            _make_response(429, {"message": "Still rate limited"}),
        ]

        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")

        assert exc_info.value.error_code == "rate_limited"
        assert exc_info.value.status_code == 429

    @patch("specify_cli.tracker.saas_client._force_refresh_sync")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_401_enrichment_has_error_code_and_status(
        self,
        mock_cls: MagicMock,
        mock_force_refresh: MagicMock,
        client: SaaSTrackerClient,
    ) -> None:
        """Double 401 raises with error_code='session_expired' and status_code=401."""
        mock_http = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_http.request.side_effect = [
            _make_response(401, {"message": "Unauthorized"}),
            _make_response(401, {"message": "Unauthorized"}),
        ]
        with pytest.raises(SaaSTrackerClientError) as exc_info:
            client._request_with_retry("GET", "/api/v1/tracker/status")

        assert exc_info.value.error_code == "session_expired"
        assert exc_info.value.status_code == 401
        assert exc_info.value.user_action_required is True


class TestErrorEnrichmentRegression:
    """T014: Regression — existing callers constructing SaaSTrackerClientError('msg') still work."""

    def test_existing_str_pattern(self) -> None:
        """Plain string construction with no kwargs must still work."""
        err = SaaSTrackerClientError("Something failed")
        assert str(err) == "Something failed"
        assert err.error_code is None
        assert err.status_code is None
        assert err.details == {}
        assert err.user_action_required is False

    def test_isinstance_runtime_error(self) -> None:
        """SaaSTrackerClientError is still a RuntimeError subclass."""
        err = SaaSTrackerClientError("boom")
        assert isinstance(err, RuntimeError)

    def test_enriched_construction(self) -> None:
        """Full kwarg construction exposes all attributes."""
        err = SaaSTrackerClientError(
            "Binding not found",
            error_code="binding_not_found",
            status_code=404,
            details={"error_code": "binding_not_found", "source": "jira"},
            user_action_required=True,
        )
        assert str(err) == "Binding not found"
        assert err.error_code == "binding_not_found"
        assert err.status_code == 404
        assert err.details == {"error_code": "binding_not_found", "source": "jira"}
        assert err.user_action_required is True

    def test_catch_as_exception(self) -> None:
        """Can be caught as generic Exception (callers that do except Exception)."""
        with pytest.raises(Exception):
            raise SaaSTrackerClientError("test")

    def test_catch_as_runtime_error(self) -> None:
        """Can be caught as RuntimeError (existing callers)."""
        with pytest.raises(RuntimeError):
            raise SaaSTrackerClientError("test")
