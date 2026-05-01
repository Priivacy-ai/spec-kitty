"""Tests for specify_cli.saas_client.

Full integration tests using ``respx`` are deferred to WP10.  This module
contains smoke-level unit tests to verify the import surface, error hierarchy,
and basic client construction — all without network access.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from specify_cli.saas_client import (
    AuthContext,
    SaasAuthError,
    SaasClient,
    SaasClientError,
    SaasNotFoundError,
    SaasTimeoutError,
    load_auth_context,
)


# ---------------------------------------------------------------------------
# Import smoke tests
# ---------------------------------------------------------------------------


def test_public_api_imports() -> None:
    """All public names are importable from the package root."""
    assert SaasClient is not None
    assert SaasClientError is not None
    assert SaasTimeoutError is not None
    assert SaasAuthError is not None
    assert SaasNotFoundError is not None
    assert AuthContext is not None
    assert load_auth_context is not None


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


def test_error_hierarchy() -> None:
    """Subclasses are proper subclasses of SaasClientError."""
    assert issubclass(SaasTimeoutError, SaasClientError)
    assert issubclass(SaasAuthError, SaasClientError)
    assert issubclass(SaasNotFoundError, SaasClientError)


def test_saas_client_error_carries_status_code() -> None:
    err = SaasClientError("oops", status_code=500)
    assert err.status_code == 500
    assert str(err) == "oops"


def test_saas_client_error_status_code_optional() -> None:
    err = SaasClientError("no code")
    assert err.status_code is None


# ---------------------------------------------------------------------------
# SaasClient construction
# ---------------------------------------------------------------------------


def test_client_constructs_with_explicit_http() -> None:
    """SaasClient accepts an injected httpx.Client without raising."""
    mock_http = MagicMock(spec=httpx.Client)
    client = SaasClient("http://localhost:8000", "tok", _http=mock_http)
    assert client._base_url == "http://localhost:8000"
    assert client._token == "tok"


def test_client_strips_trailing_slash_from_base_url() -> None:
    mock_http = MagicMock(spec=httpx.Client)
    client = SaasClient("http://localhost:8000/", "tok", _http=mock_http)
    assert client._base_url == "http://localhost:8000"


def test_has_token_true_when_token_present() -> None:
    """has_token property returns True for a non-empty token."""
    mock_http = MagicMock(spec=httpx.Client)
    client = SaasClient("http://localhost:8000", "my-token", _http=mock_http)
    assert client.has_token is True


def test_has_token_false_when_token_empty() -> None:
    """has_token property returns False when token is an empty string."""
    mock_http = MagicMock(spec=httpx.Client)
    client = SaasClient("http://localhost:8000", "", _http=mock_http)
    assert client.has_token is False


# ---------------------------------------------------------------------------
# auth.load_auth_context
# ---------------------------------------------------------------------------


def test_load_auth_context_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_SAAS_TOKEN", "test-token")
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://example.com")
    monkeypatch.setenv("SPEC_KITTY_TEAM_SLUG", "my-team")
    ctx = load_auth_context()
    assert ctx.token == "test-token"
    assert ctx.saas_url == "https://example.com"
    assert ctx.team_slug == "my-team"


def test_load_auth_context_default_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_SAAS_TOKEN", "test-token")
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    ctx = load_auth_context()
    assert ctx.saas_url == "https://api.spec-kitty.io"


def test_load_auth_context_from_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPEC_KITTY_SAAS_TOKEN", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    auth_dir = tmp_path / ".kittify"
    auth_dir.mkdir()
    (auth_dir / "saas-auth.json").write_text(json.dumps({"token": "file-token", "saas_url": "https://file-url.example"}))
    ctx = load_auth_context(repo_root=tmp_path)
    assert ctx.token == "file-token"
    assert ctx.saas_url == "https://file-url.example"


def test_load_auth_context_raises_when_no_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPEC_KITTY_SAAS_TOKEN", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    with pytest.raises(SaasAuthError, match="SPEC_KITTY_SAAS_TOKEN"):
        load_auth_context(repo_root=tmp_path)


# ---------------------------------------------------------------------------
# SaasClient endpoint method signatures (dependency-injected mock)
# ---------------------------------------------------------------------------


def _make_client(response_data: object, status_code: int = 200) -> SaasClient:
    """Build a SaasClient backed by a mock httpx.Client returning fixed data."""
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = status_code
    mock_resp.is_success = 200 <= status_code < 300
    mock_resp.json.return_value = response_data
    mock_resp.text = json.dumps(response_data) if isinstance(response_data, (dict, list)) else str(response_data)

    mock_http = MagicMock(spec=httpx.Client)
    mock_http.get.return_value = mock_resp
    mock_http.post.return_value = mock_resp
    return SaasClient("http://test", "tok", team_slug="my-team", _http=mock_http)


def test_get_audience_default_returns_list() -> None:
    client = _make_client({"members": [{"user_id": 1, "display_name": "Alice"}]})
    result = client.get_audience_default("mission-123")
    assert result == [{"user_id": 1, "display_name": "Alice"}]


def test_get_audience_default_accepts_bare_list() -> None:
    client = _make_client(["Alice", "Bob"])
    result = client.get_audience_default("mission-123")
    assert result == [{"display_name": "Alice"}, {"display_name": "Bob"}]


def test_post_widen_returns_widen_response() -> None:
    client = _make_client(
        {
            "decision_id": "dec-1",
            "widened_at": "2026-04-23T10:00:00Z",
            "slack_thread_url": "https://slack.com/x",
            "invited_count": 2,
        }
    )
    result = client.post_widen("dec-1", [1, 2])
    assert result["decision_id"] == "dec-1"
    assert result["invited_count"] == 2


def test_get_team_integrations_returns_list() -> None:
    client = _make_client({"integrations": ["slack"]})
    result = client.get_team_integrations("my-team")
    assert result == ["slack"]


def test_health_probe_returns_true_on_200() -> None:
    client = _make_client({"status": "ok"})
    assert client.health_probe() is True


def test_health_probe_returns_false_on_error() -> None:
    """health_probe never raises — returns False on any error."""
    mock_http = MagicMock(spec=httpx.Client)
    mock_http.get.side_effect = httpx.TimeoutException("timeout")
    client = SaasClient("http://test", "tok", team_slug="my-team", _http=mock_http)
    assert client.health_probe() is False


def test_fetch_discussion_returns_discussion_data() -> None:
    client = _make_client(
        {
            "decision_id": "dec-1",
            "participants": ["Alice", "Bob"],
            "messages": [{"author": "Alice", "text": "Hello", "timestamp": None}],
            "thread_url": "https://slack.com/y",
            "message_count": 1,
        }
    )
    result = client.fetch_discussion("dec-1")
    assert result["decision_id"] == "dec-1"
    assert result["participants"] == ["Alice", "Bob"]
    assert len(result["messages"]) == 1


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


def test_timeout_exception_maps_to_saas_timeout_error() -> None:
    mock_http = MagicMock(spec=httpx.Client)
    mock_http.get.side_effect = httpx.TimeoutException("timed out")
    client = SaasClient("http://test", "tok", team_slug="my-team", _http=mock_http)
    with pytest.raises(SaasTimeoutError):
        client.get_audience_default("m-1")


def test_401_maps_to_saas_auth_error() -> None:
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 401
    mock_resp.is_success = False
    mock_resp.text = "Unauthorized"
    mock_http = MagicMock(spec=httpx.Client)
    mock_http.get.return_value = mock_resp
    client = SaasClient("http://test", "tok", team_slug="my-team", _http=mock_http)
    with pytest.raises(SaasAuthError) as exc_info:
        client.get_audience_default("m-1")
    assert exc_info.value.status_code == 401


def test_404_maps_to_saas_not_found_error() -> None:
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 404
    mock_resp.is_success = False
    mock_resp.text = "Not Found"
    mock_http = MagicMock(spec=httpx.Client)
    mock_http.get.return_value = mock_resp
    client = SaasClient("http://test", "tok", team_slug="my-team", _http=mock_http)
    with pytest.raises(SaasNotFoundError) as exc_info:
        client.get_audience_default("m-1")
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# respx integration tests — WP10 (T050)
# ---------------------------------------------------------------------------


class TestRespxIntegration:
    """Full HTTP-level tests using respx to mock httpx transports (WP10)."""

    BASE = "http://saas-test"

    def _client(self, http_client: httpx.Client) -> SaasClient:
        return SaasClient(self.BASE, "test-token", team_slug="my-team", _http=http_client)

    def test_get_audience_default_success_respx(self) -> None:
        """respx: GET /audience-default returns list from {'members': [...]}."""
        import respx

        with respx.mock:
            respx.get(f"{self.BASE}/a/my-team/collaboration/missions/M1/audience-default").respond(200, json={"members": [{"user_id": 1, "display_name": "Alice"}]})
            client = self._client(httpx.Client())
            result = client.get_audience_default("M1")
        assert result == [{"user_id": 1, "display_name": "Alice"}]

    def test_get_audience_default_bare_list_respx(self) -> None:
        """respx: GET /audience-default also accepts a bare JSON list."""
        import respx

        with respx.mock:
            respx.get(f"{self.BASE}/a/my-team/collaboration/missions/M2/audience-default").respond(200, json=["Carol", "Dana"])
            client = self._client(httpx.Client())
            result = client.get_audience_default("M2")
        assert result == [{"display_name": "Carol"}, {"display_name": "Dana"}]

    def test_post_widen_returns_widen_response_respx(self) -> None:
        """respx: POST /widen parses WidenResponse fields (TypedDict)."""
        import respx

        with respx.mock:
            respx.post(f"{self.BASE}/a/my-team/collaboration/decision-points/D1/widen").respond(
                200,
                json={
                    "decision_id": "D1",
                    "widened_at": "2026-04-23T12:00:00Z",
                    "slack_thread_url": "https://slack.com/thread/1",
                    "invited_count": 2,
                },
            )
            client = self._client(httpx.Client())
            result = client.post_widen("D1", [1, 2])
        # WidenResponse is a TypedDict — use dict-style access
        assert result["decision_id"] == "D1"
        assert result["invited_count"] == 2
        assert result["slack_thread_url"] == "https://slack.com/thread/1"

    def test_post_widen_sends_invited_list_respx(self) -> None:
        """respx: POST /widen sends the correct request body."""
        import respx

        route = None
        with respx.mock as mock:
            route = mock.post(f"{self.BASE}/a/my-team/collaboration/decision-points/D2/widen").respond(
                200,
                json={
                    "decision_id": "D2",
                    "widened_at": "2026-04-23T12:00:00Z",
                    "slack_thread_url": None,
                    "invited_count": 1,
                },
            )
            client = self._client(httpx.Client())
            client.post_widen("D2", [3])

        assert route.called
        req_body = json.loads(route.calls[0].request.content)
        assert req_body["invited_user_ids"] == [3]

    def test_health_probe_true_on_200_respx(self) -> None:
        """respx: health_probe() returns True when GET /health returns 200."""
        import respx

        with respx.mock:
            respx.get(f"{self.BASE}/api/v1/health").respond(200, json={"status": "ok"})
            client = self._client(httpx.Client())
            assert client.health_probe() is True

    def test_health_probe_false_on_timeout_respx(self) -> None:
        """respx: health_probe() returns False when httpx raises TimeoutException."""
        import respx

        with respx.mock:
            respx.get(f"{self.BASE}/api/v1/health").mock(side_effect=httpx.TimeoutException("timed out"))
            client = self._client(httpx.Client())
            assert client.health_probe() is False

    def test_get_team_integrations_respx(self) -> None:
        """respx: GET /integrations returns parsed list."""
        import respx

        with respx.mock:
            respx.get(f"{self.BASE}/a/my-team/collaboration/integrations/").respond(200, json={"integrations": ["slack", "github"]})
            client = self._client(httpx.Client())
            result = client.get_team_integrations("my-team")
        assert "slack" in result
        assert "github" in result

    def test_401_maps_to_saas_auth_error_respx(self) -> None:
        """respx: 401 response raises SaasAuthError."""
        import respx

        with respx.mock:
            respx.get(f"{self.BASE}/a/my-team/collaboration/missions/M3/audience-default").respond(401, text="Unauthorized")
            client = self._client(httpx.Client())
            with pytest.raises(SaasAuthError) as exc_info:
                client.get_audience_default("M3")
        assert exc_info.value.status_code == 401

    def test_fetch_discussion_respx(self) -> None:
        """respx: GET /discussion returns parsed DiscussionData (TypedDict)."""
        import respx

        with respx.mock:
            respx.get(f"{self.BASE}/a/my-team/collaboration/decision-points/D3/discussion/").respond(
                200,
                json={
                    "decision_id": "D3",
                    "participants": [{"display_name": "Alice"}, {"display_name": "Bob"}],
                    "messages": [
                        {"author_display_name": "Alice", "text": "Use Postgres", "ts": "1.0"},
                        {"author_display_name": "Bob", "text": "Agreed", "ts": "2.0"},
                    ],
                    "thread_url": "https://slack.com/t3",
                    "message_count": 2,
                },
            )
            client = self._client(httpx.Client())
            result = client.fetch_discussion("D3")

        # DiscussionData is a TypedDict — use dict-style access
        assert result["decision_id"] == "D3"
        assert result["participants"] == ["Alice", "Bob"]
        assert result["message_count"] == 2
        assert result["thread_url"] == "https://slack.com/t3"
        assert len(result["messages"]) == 2
