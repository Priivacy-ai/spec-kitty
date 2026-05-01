"""Unit tests for ``specify_cli.auth.http.me_fetch.fetch_me_payload`` (WP02 T008).

These tests intentionally hit no real network: ``respx.mock`` intercepts the
sync ``httpx.Client.request`` issued by ``request_with_fallback_sync``.

The helper is sync-only — there is no ``pytest.mark.asyncio`` here.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from specify_cli.auth.http.me_fetch import fetch_me_payload


@respx.mock
def test_fetch_me_payload_success() -> None:
    """Happy path: 200 + parsed teams payload returned verbatim to the caller."""
    respx.get("https://saas.example/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [{"id": "t1", "is_private_teamspace": True}],
            },
        )
    )

    payload = fetch_me_payload("https://saas.example", "tok")

    assert payload["email"] == "u@example.com"
    assert payload["teams"][0]["is_private_teamspace"] is True


@respx.mock
def test_fetch_me_payload_raises_on_401() -> None:
    """Non-2xx surfaces as ``HTTPStatusError`` — the caller decides recovery."""
    respx.get("https://saas.example/api/v1/me").mock(
        return_value=httpx.Response(401)
    )

    with pytest.raises(httpx.HTTPStatusError):
        fetch_me_payload("https://saas.example", "tok")


@respx.mock
def test_fetch_me_payload_passes_bearer_header() -> None:
    """The Bearer token must be sent verbatim in the ``Authorization`` header."""
    route = respx.get("https://saas.example/api/v1/me").mock(
        return_value=httpx.Response(200, json={"teams": []})
    )

    fetch_me_payload("https://saas.example", "my-tok")

    assert route.calls[0].request.headers["Authorization"] == "Bearer my-tok"


@respx.mock
def test_fetch_me_payload_strips_trailing_slash_from_base_url() -> None:
    """Defensive: callers may pass a base URL with a trailing slash."""
    route = respx.get("https://saas.example/api/v1/me").mock(
        return_value=httpx.Response(200, json={"teams": []})
    )

    fetch_me_payload("https://saas.example/", "tok")

    assert route.call_count == 1
