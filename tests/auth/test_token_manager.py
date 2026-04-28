"""Tests for ``specify_cli.auth.token_manager`` (feature 080, WP01 T007).

The headline test is ``test_concurrent_get_access_token_is_single_flight``:
10 concurrent callers with an expired session must result in **exactly one**
refresh call. This is the central guarantee WP08 and every subsequent WP
depends on.

TokenManager's refresh path imports ``auth.flows.refresh.TokenRefreshFlow``
lazily — that module doesn't exist yet (WP04 creates it). These tests
inject a fake ``flows.refresh`` module into ``sys.modules`` so the lazy
import picks up our mock.
"""

from __future__ import annotations

import asyncio
import sys
import types
from datetime import datetime, timedelta, UTC

import pytest

from specify_cli.auth.errors import (
    NotAuthenticatedError,
    RefreshTokenExpiredError,
    SessionInvalidError,
)
from specify_cli.auth.secure_storage import SecureStorage
from specify_cli.auth.session import StoredSession, Team
from specify_cli.auth.token_manager import TokenManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


def _make_session(
    *,
    access_expires_in: int = 900,
    refresh_token_expires_at: datetime | None = None,
    refresh_token: str = "refresh-v1",
    access_token: str = "access-v1",
) -> StoredSession:
    now = _now()
    return StoredSession(
        user_id="user-1",
        email="a@b.com",
        name="A B",
        teams=[Team(id="t1", name="T1", role="owner")],
        default_team_id="t1",
        access_token=access_token,
        refresh_token=refresh_token,
        session_id="sess",
        issued_at=now,
        access_token_expires_at=now + timedelta(seconds=access_expires_in),
        refresh_token_expires_at=refresh_token_expires_at,
        scope="openid",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


class FakeStorage(SecureStorage):
    """Minimal in-memory :class:`SecureStorage` for TokenManager tests."""

    def __init__(self) -> None:
        self._session: StoredSession | None = None
        self.writes = 0
        self.deletes = 0

    def read(self) -> StoredSession | None:
        return self._session

    def write(self, session: StoredSession) -> None:
        self._session = session
        self.writes += 1

    def delete(self) -> None:
        self._session = None
        self.deletes += 1

    @property
    def backend_name(self) -> str:
        return "file"


class FakeRefreshFlow:
    """Counts how many times ``refresh`` is invoked and returns a fresh token."""

    call_count = 0
    delay_seconds: float = 0.05
    raise_session_invalid: bool = False
    raise_refresh_expired: bool = False

    def __init__(self) -> None:
        # Instance counter so each test starts clean.
        pass

    async def refresh(self, session: StoredSession) -> StoredSession:
        FakeRefreshFlow.call_count += 1
        await asyncio.sleep(FakeRefreshFlow.delay_seconds)
        if FakeRefreshFlow.raise_refresh_expired:
            raise RefreshTokenExpiredError("refresh token invalid")
        if FakeRefreshFlow.raise_session_invalid:
            raise SessionInvalidError("server says no")
        # Return a brand-new session with a fresh access token and a non-expired window.
        return StoredSession(
            user_id=session.user_id,
            email=session.email,
            name=session.name,
            teams=list(session.teams),
            default_team_id=session.default_team_id,
            access_token=f"access-v{FakeRefreshFlow.call_count + 1}",
            refresh_token=session.refresh_token,
            session_id=session.session_id,
            issued_at=_now(),
            access_token_expires_at=_now() + timedelta(seconds=900),
            refresh_token_expires_at=session.refresh_token_expires_at,
            scope=session.scope,
            storage_backend=session.storage_backend,
            last_used_at=_now(),
            auth_method=session.auth_method,
        )


@pytest.fixture
def install_fake_refresh_flow(monkeypatch):
    """Install ``specify_cli.auth.flows.refresh`` as a fake module in sys.modules."""
    FakeRefreshFlow.call_count = 0
    FakeRefreshFlow.raise_session_invalid = False
    FakeRefreshFlow.raise_refresh_expired = False
    FakeRefreshFlow.delay_seconds = 0.05

    flows_pkg = types.ModuleType("specify_cli.auth.flows")
    flows_pkg.__path__ = []  # mark as a package
    refresh_module = types.ModuleType("specify_cli.auth.flows.refresh")
    refresh_module.TokenRefreshFlow = FakeRefreshFlow

    monkeypatch.setitem(sys.modules, "specify_cli.auth.flows", flows_pkg)
    monkeypatch.setitem(sys.modules, "specify_cli.auth.flows.refresh", refresh_module)
    yield FakeRefreshFlow


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_current_session_none_by_default():
    tm = TokenManager(FakeStorage())
    assert tm.get_current_session() is None
    assert tm.is_authenticated is False


def test_load_from_storage_sync_populates_session():
    storage = FakeStorage()
    session = _make_session()
    storage._session = session
    tm = TokenManager(storage)
    tm.load_from_storage_sync()
    assert tm.get_current_session() == session
    assert tm.is_authenticated is True


def test_load_from_storage_sync_handles_storage_errors():
    class BrokenStorage(FakeStorage):
        def read(self):
            raise RuntimeError("disk on fire")

    tm = TokenManager(BrokenStorage())
    tm.load_from_storage_sync()  # must not raise
    assert tm.get_current_session() is None
    assert tm.is_authenticated is False


def test_set_session_writes_to_storage():
    storage = FakeStorage()
    tm = TokenManager(storage)
    s = _make_session()
    tm.set_session(s)
    assert tm.get_current_session() == s
    assert storage.writes == 1
    assert storage._session == s


def test_clear_session_deletes_from_storage():
    storage = FakeStorage()
    tm = TokenManager(storage)
    tm.set_session(_make_session())
    tm.clear_session()
    assert tm.get_current_session() is None
    assert storage._session is None
    assert storage.deletes == 1


def test_clear_session_swallows_delete_errors():
    class DeleteFailsStorage(FakeStorage):
        def delete(self):
            raise RuntimeError("nope")

    tm = TokenManager(DeleteFailsStorage())
    tm.set_session(_make_session())
    tm.clear_session()  # must not raise
    assert tm.get_current_session() is None


def test_is_authenticated_false_when_refresh_expired():
    tm = TokenManager(FakeStorage())
    tm.set_session(_make_session(refresh_token_expires_at=_now() - timedelta(days=1)))
    assert tm.is_authenticated is False


def test_is_authenticated_true_when_refresh_expiry_is_none():
    """D-9: no hardcoded client-side refresh TTL."""
    tm = TokenManager(FakeStorage())
    tm.set_session(_make_session(refresh_token_expires_at=None))
    assert tm.is_authenticated is True


@pytest.mark.asyncio
async def test_get_access_token_without_session_raises():
    tm = TokenManager(FakeStorage())
    with pytest.raises(NotAuthenticatedError):
        await tm.get_access_token()


@pytest.mark.asyncio
async def test_get_access_token_returns_current_when_not_expired():
    tm = TokenManager(FakeStorage())
    tm.set_session(_make_session(access_expires_in=900, access_token="still-valid"))
    token = await tm.get_access_token()
    assert token == "still-valid"


@pytest.mark.asyncio
async def test_get_access_token_refreshes_when_expired(install_fake_refresh_flow):
    storage = FakeStorage()
    tm = TokenManager(storage)
    tm.set_session(_make_session(access_expires_in=-1, access_token="stale"))
    token = await tm.get_access_token()
    assert token != "stale"
    assert install_fake_refresh_flow.call_count == 1
    # The refresh result should also have been persisted.
    assert storage.writes >= 2  # initial set_session + refresh write


@pytest.mark.asyncio
async def test_get_access_token_refreshes_within_buffer_window(install_fake_refresh_flow):
    """The 5-second buffer must trigger refresh for near-expiry tokens."""
    tm = TokenManager(FakeStorage())
    tm.set_session(_make_session(access_expires_in=2, access_token="near-expiry"))
    token = await tm.get_access_token()
    assert token != "near-expiry"
    assert install_fake_refresh_flow.call_count == 1


@pytest.mark.asyncio
async def test_refresh_if_needed_raises_when_refresh_token_expired(
    install_fake_refresh_flow,
):
    storage = FakeStorage()
    tm = TokenManager(storage)
    tm.set_session(
        _make_session(
            access_expires_in=-1,
            refresh_token_expires_at=_now() - timedelta(days=1),
        )
    )
    with pytest.raises(RefreshTokenExpiredError):
        await tm.refresh_if_needed()
    # No network call was made.
    assert install_fake_refresh_flow.call_count == 0
    # Locally-known expiry is not stale state; keep the session loaded so
    # status commands can still explain why re-login is required.
    assert tm.get_current_session() is not None
    assert storage.deletes == 0


@pytest.mark.asyncio
async def test_refresh_if_needed_clears_session_on_server_invalid_grant(
    install_fake_refresh_flow,
):
    install_fake_refresh_flow.raise_refresh_expired = True
    storage = FakeStorage()
    tm = TokenManager(storage)
    tm.set_session(_make_session(access_expires_in=-1))
    with pytest.raises(RefreshTokenExpiredError):
        await tm.refresh_if_needed()
    assert tm.get_current_session() is None
    assert storage.deletes >= 1


@pytest.mark.asyncio
async def test_refresh_if_needed_clears_session_on_session_invalid(
    install_fake_refresh_flow,
):
    install_fake_refresh_flow.raise_session_invalid = True
    storage = FakeStorage()
    tm = TokenManager(storage)
    tm.set_session(_make_session(access_expires_in=-1))
    with pytest.raises(SessionInvalidError):
        await tm.refresh_if_needed()
    assert tm.get_current_session() is None
    assert storage.deletes >= 1


@pytest.mark.asyncio
async def test_refresh_if_needed_returns_false_when_not_needed(
    install_fake_refresh_flow,
):
    tm = TokenManager(FakeStorage())
    tm.set_session(_make_session(access_expires_in=900))
    refreshed = await tm.refresh_if_needed()
    assert refreshed is False
    assert install_fake_refresh_flow.call_count == 0


@pytest.mark.asyncio
async def test_refresh_if_needed_raises_without_session():
    tm = TokenManager(FakeStorage())
    with pytest.raises(NotAuthenticatedError):
        await tm.refresh_if_needed()


@pytest.mark.asyncio
async def test_concurrent_get_access_token_is_single_flight(install_fake_refresh_flow):
    """10 concurrent callers with an expired session → exactly one refresh."""
    install_fake_refresh_flow.delay_seconds = 0.1  # ensure overlap
    tm = TokenManager(FakeStorage())
    tm.set_session(_make_session(access_expires_in=-1, access_token="stale"))

    tasks = [asyncio.create_task(tm.get_access_token()) for _ in range(10)]
    results = await asyncio.gather(*tasks)

    assert install_fake_refresh_flow.call_count == 1, f"Expected 1 refresh, got {install_fake_refresh_flow.call_count}"
    assert len(set(results)) == 1  # all callers see the same fresh token
    assert all(r != "stale" for r in results)


@pytest.mark.asyncio
async def test_second_burst_after_refresh_does_not_re_refresh(
    install_fake_refresh_flow,
):
    """Once a fresh token is in place, subsequent calls must not refresh again."""
    install_fake_refresh_flow.delay_seconds = 0.01
    tm = TokenManager(FakeStorage())
    tm.set_session(_make_session(access_expires_in=-1))

    # First burst: triggers one refresh.
    await asyncio.gather(*[tm.get_access_token() for _ in range(5)])
    assert install_fake_refresh_flow.call_count == 1

    # Second burst: token is fresh now, no further refreshes.
    await asyncio.gather(*[tm.get_access_token() for _ in range(5)])
    assert install_fake_refresh_flow.call_count == 1
