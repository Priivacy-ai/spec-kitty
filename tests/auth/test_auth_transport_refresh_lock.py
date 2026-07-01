from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from specify_cli.auth.errors import TokenRefreshError
from specify_cli.auth.refresh_transaction import RefreshLockTimeoutError
from specify_cli.auth.transport import (
    AsyncAuthenticatedClient,
    AuthRefreshFailed,
    AuthenticatedClient,
    reset_user_facing_dedup,
)

# Pure-logic transport tests (httpx mocks, asyncio); no subprocess/filesystem.
pytestmark = [pytest.mark.unit, pytest.mark.fast]


LOCK_MESSAGE = (
    "Another spec-kitty process is refreshing the auth session; retry in a moment."
)


class _LockingTokenManager:
    is_authenticated = True

    def __init__(
        self,
        *,
        lock_on_refresh: bool = False,
        refresh_succeeds: bool = False,
        lock_after_refresh: bool = False,
    ) -> None:
        self.lock_on_refresh = lock_on_refresh
        self.refresh_succeeds = refresh_succeeds
        self.lock_after_refresh = lock_after_refresh
        self.refresh_calls = 0
        self.session = SimpleNamespace(access_token_expires_at=None)

    async def get_access_token(self) -> str:
        if self.lock_on_refresh and not (
            self.lock_after_refresh and self.refresh_calls
        ):
            return "access-v1"
        raise RefreshLockTimeoutError(LOCK_MESSAGE)

    async def refresh_if_needed(self) -> bool:
        self.refresh_calls += 1
        if self.refresh_succeeds:
            return True
        raise RefreshLockTimeoutError(LOCK_MESSAGE)

    def get_current_session(self) -> SimpleNamespace:
        return self.session


@pytest.fixture(autouse=True)
def _reset_dedup() -> None:
    reset_user_facing_dedup()
    yield
    reset_user_facing_dedup()


def test_sync_transport_maps_initial_refresh_lock_timeout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from specify_cli.auth import transport as transport_mod

    monkeypatch.setattr(
        transport_mod,
        "get_token_manager",
        lambda: _LockingTokenManager(),
    )

    def _should_not_send(request: httpx.Request) -> httpx.Response:
        raise AssertionError("request should not be sent without an access token")

    client = AuthenticatedClient(
        client=httpx.Client(transport=httpx.MockTransport(_should_not_send))
    )

    with pytest.raises(AuthRefreshFailed) as exc_info:
        client.get("https://api.example.test/v1/resource")

    assert exc_info.value.error_code == "refresh_lock_timeout"
    assert LOCK_MESSAGE in str(exc_info.value)
    captured = capsys.readouterr()
    assert LOCK_MESSAGE in captured.err
    assert "Authentication expired" not in captured.err


def test_sync_transport_maps_401_forced_refresh_lock_timeout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from specify_cli.auth import transport as transport_mod

    monkeypatch.setattr(
        transport_mod,
        "get_token_manager",
        lambda: _LockingTokenManager(lock_on_refresh=True),
    )
    attempts = 0

    def _unauthorized(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(401, request=request)

    client = AuthenticatedClient(
        client=httpx.Client(transport=httpx.MockTransport(_unauthorized))
    )

    with pytest.raises(AuthRefreshFailed) as exc_info:
        client.get("https://api.example.test/v1/resource")

    assert attempts == 1
    assert exc_info.value.error_code == "refresh_lock_timeout"
    assert LOCK_MESSAGE in str(exc_info.value)
    captured = capsys.readouterr()
    assert LOCK_MESSAGE in captured.err
    assert "Authentication expired" not in captured.err


def test_sync_transport_maps_post_refresh_token_fetch_lock_timeout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from specify_cli.auth import transport as transport_mod

    token_manager = _LockingTokenManager(
        lock_on_refresh=True,
        refresh_succeeds=True,
        lock_after_refresh=True,
    )
    monkeypatch.setattr(
        transport_mod,
        "get_token_manager",
        lambda: token_manager,
    )
    attempts = 0

    def _unauthorized(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(401, request=request)

    client = AuthenticatedClient(
        client=httpx.Client(transport=httpx.MockTransport(_unauthorized))
    )

    with pytest.raises(AuthRefreshFailed) as exc_info:
        client.get("https://api.example.test/v1/resource")

    assert attempts == 1
    assert token_manager.refresh_calls == 1
    assert exc_info.value.error_code == "refresh_lock_timeout"
    assert LOCK_MESSAGE in str(exc_info.value)
    captured = capsys.readouterr()
    assert LOCK_MESSAGE in captured.err
    assert "Authentication expired" not in captured.err


@pytest.mark.asyncio
async def test_oauth_http_transport_maps_initial_refresh_lock_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from specify_cli.auth.http import transport as http_transport_mod

    monkeypatch.setattr(
        http_transport_mod,
        "get_token_manager",
        lambda: _LockingTokenManager(),
    )

    async def _should_not_send(request: httpx.Request) -> httpx.Response:
        raise AssertionError("request should not be sent without an access token")

    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(_should_not_send)) as raw_client,
        http_transport_mod.OAuthHttpClient(client=raw_client) as client,
    ):
        with pytest.raises(TokenRefreshError) as exc_info:
            await client.get("https://api.example.test/v1/resource")

    assert LOCK_MESSAGE in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, RefreshLockTimeoutError)


@pytest.mark.asyncio
async def test_async_authenticated_client_preserves_refresh_lock_hint(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from specify_cli.auth.http import transport as http_transport_mod

    monkeypatch.setattr(
        http_transport_mod,
        "get_token_manager",
        lambda: _LockingTokenManager(),
    )

    async def _should_not_send(request: httpx.Request) -> httpx.Response:
        raise AssertionError("request should not be sent without an access token")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(_should_not_send)
    ) as raw_client:
        client = AsyncAuthenticatedClient(client=raw_client)
        with pytest.raises(AuthRefreshFailed) as exc_info:
            await client.get("https://api.example.test/v1/resource")

    assert exc_info.value.error_code == "refresh_lock_timeout"
    assert LOCK_MESSAGE in str(exc_info.value)
    captured = capsys.readouterr()
    assert LOCK_MESSAGE in captured.err
    assert "Authentication expired" not in captured.err


@pytest.mark.asyncio
async def test_oauth_http_transport_maps_401_forced_refresh_lock_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from specify_cli.auth.http import transport as http_transport_mod

    monkeypatch.setattr(
        http_transport_mod,
        "get_token_manager",
        lambda: _LockingTokenManager(lock_on_refresh=True),
    )
    attempts = 0

    async def _unauthorized(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(401, request=request)

    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(_unauthorized)) as raw_client,
        http_transport_mod.OAuthHttpClient(client=raw_client) as client,
    ):
        with pytest.raises(TokenRefreshError) as exc_info:
            await client.get("https://api.example.test/v1/resource")

    assert attempts == 1
    assert LOCK_MESSAGE in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, RefreshLockTimeoutError)
