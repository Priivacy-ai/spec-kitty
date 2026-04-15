"""CliRunner-driven integration test for FR-009: expired-access-token refresh
through the live HTTP transport stack.

This test exercises the full chain:

1. :class:`typer.testing.CliRunner` invokes the real ``sync status --check``
   Typer command.
2. The command calls ``get_token_manager().get_access_token()`` which detects
   the access token is expired and calls ``refresh_if_needed()``.
3. ``refresh_if_needed`` acquires the single-flight lock, invokes the
   (fake) refresh flow, persists the refreshed session.
4. The refreshed access token is used to probe the health endpoint.

Coverage: FR-009 (auto-refresh before expiry), FR-010 (single-flight lock),
FR-016 (TokenManager is the sole credential source), FR-017 (no direct
keystore reads outside auth/).

The sync infrastructure (config, queue, daemon, feature flags) is stubbed —
only the auth pipeline runs for real. No endpoint shapes are changed.
"""

from __future__ import annotations

import sys
import types
from datetime import datetime, timedelta, UTC
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from typer.testing import CliRunner

from specify_cli.auth import get_token_manager, reset_token_manager
from specify_cli.auth.secure_storage.abstract import SecureStorage
from specify_cli.auth.session import StoredSession, Team

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


def _make_expired_session() -> StoredSession:
    """Session with an access token that expired 10 minutes ago."""
    now = _now()
    return StoredSession(
        user_id="u_refresh_test",
        email="refresh@test.example",
        name="Refresh Tester",
        teams=[Team(id="tm_test", name="TestTeam", role="admin")],
        default_team_id="tm_test",
        access_token="stale_access_token",
        refresh_token="valid_refresh_token",
        session_id="sess_refresh_test",
        issued_at=now - timedelta(hours=2),
        access_token_expires_at=now - timedelta(minutes=10),  # EXPIRED
        refresh_token_expires_at=now + timedelta(days=89),
        scope="offline_access",
        storage_backend="file",
        last_used_at=now - timedelta(hours=1),
        auth_method="authorization_code",
    )


class FakeStorage(SecureStorage):
    """In-memory secure storage seeded with an expired session."""

    def __init__(self, session: StoredSession | None = None) -> None:
        self._session = session
        self.writes: list[StoredSession] = []
        self.deletes = 0

    def read(self) -> StoredSession | None:
        return self._session

    def write(self, session: StoredSession) -> None:
        self._session = session
        self.writes.append(session)

    def delete(self) -> None:
        self._session = None
        self.deletes += 1

    @property
    def backend_name(self) -> str:
        return "file"


class FakeRefreshFlow:
    """Fake refresh flow that mints a fresh session and tracks call count."""

    call_count = 0

    def __init__(self) -> None:
        pass

    async def refresh(self, session: StoredSession) -> StoredSession:
        FakeRefreshFlow.call_count += 1
        now = _now()
        return StoredSession(
            user_id=session.user_id,
            email=session.email,
            name=session.name,
            teams=list(session.teams),
            default_team_id=session.default_team_id,
            access_token="refreshed_access_token",
            refresh_token=session.refresh_token,
            session_id=session.session_id,
            issued_at=now,
            access_token_expires_at=now + timedelta(hours=1),
            refresh_token_expires_at=session.refresh_token_expires_at,
            scope=session.scope,
            storage_backend=session.storage_backend,
            last_used_at=now,
            auth_method=session.auth_method,
        )


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Clean auth and sync env for each test."""
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")
    reset_token_manager()
    yield
    reset_token_manager()


@pytest.fixture
def install_fake_refresh(monkeypatch: pytest.MonkeyPatch) -> FakeRefreshFlow:
    """Inject a fake refresh module so TokenManager.refresh_if_needed uses it."""
    FakeRefreshFlow.call_count = 0

    flows_pkg = types.ModuleType("specify_cli.auth.flows")
    flows_pkg.__path__ = []
    refresh_mod = types.ModuleType("specify_cli.auth.flows.refresh")
    refresh_mod.TokenRefreshFlow = FakeRefreshFlow  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "specify_cli.auth.flows", flows_pkg)
    monkeypatch.setitem(sys.modules, "specify_cli.auth.flows.refresh", refresh_mod)
    return FakeRefreshFlow()


@pytest.fixture
def seeded_tm(monkeypatch: pytest.MonkeyPatch, install_fake_refresh: FakeRefreshFlow) -> FakeStorage:
    """Seed the process-wide TokenManager with an expired-access-token session."""
    import specify_cli.auth as auth_pkg
    from specify_cli.auth.token_manager import TokenManager

    storage = FakeStorage(session=_make_expired_session())
    tm = TokenManager(storage)
    tm.load_from_storage_sync()

    monkeypatch.setattr(auth_pkg, "_tm", tm, raising=False)
    return storage


# ---------------------------------------------------------------------------
# Stub helpers for sync infrastructure
# ---------------------------------------------------------------------------

def _stub_sync_deps():
    """Return a context manager that stubs all non-auth sync dependencies.

    ``SyncConfig``, ``OfflineQueue``, and ``get_sync_daemon_status`` are
    lazy-imported inside the ``status`` function body, so we patch them at
    their source modules rather than on the ``sync`` command module.
    """
    # SyncConfig stub
    mock_config = MagicMock()
    mock_config.get_server_url.return_value = "https://saas.test"
    mock_config.config_file = "/tmp/test-sync-config.toml"

    # OfflineQueue stub
    mock_queue = MagicMock()
    mock_queue.size.return_value = 0
    mock_queue.get_queue_stats.return_value = MagicMock(total_queued=0)

    # DaemonStatus stub
    mock_daemon_status = MagicMock()
    mock_daemon_status.healthy = False
    mock_daemon_status.url = None
    mock_daemon_status.sync_running = False
    mock_daemon_status.websocket_status = "Disconnected"
    mock_daemon_status.last_sync = None
    mock_daemon_status.consecutive_failures = 0

    from contextlib import ExitStack

    stack = ExitStack()
    # Patch at source modules (lazy imports inside the function body)
    stack.enter_context(
        patch("specify_cli.sync.config.SyncConfig", return_value=mock_config)
    )
    stack.enter_context(
        patch("specify_cli.sync.queue.OfflineQueue", return_value=mock_queue)
    )
    stack.enter_context(
        patch(
            "specify_cli.sync.feature_flags.is_saas_sync_enabled",
            return_value=True,
        )
    )
    stack.enter_context(
        patch(
            "specify_cli.sync.daemon.get_sync_daemon_status",
            return_value=mock_daemon_status,
        )
    )
    return stack


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


class TestRefreshThroughTransport:
    """FR-009: expired access token triggers automatic refresh through the
    live ``get_access_token()`` path inside a real CliRunner-invoked command.
    """

    def test_expired_token_refreshes_before_health_probe(
        self,
        seeded_tm: FakeStorage,
        install_fake_refresh: FakeRefreshFlow,
    ) -> None:
        """CliRunner → sync status --check → get_access_token() → refresh →
        health probe with refreshed token → "Connected".

        The access token was expired when the command started. The command
        calls ``get_token_manager().get_access_token()`` which detects expiry,
        acquires the single-flight lock, calls the (fake) refresh flow, and
        returns the fresh token. The health probe then uses that fresh token.
        """
        from specify_cli.cli.commands.sync import app as sync_app

        captured_auth_headers: list[str] = []

        def _fake_request(
            method: str, url: str, *, headers: dict | None = None, **kw: Any
        ) -> httpx.Response:
            # Commit 533e47d2 routes sync health probes through
            # request_with_fallback_sync, which calls httpx.Client.request(...)
            # rather than .get(...). Capture headers on every request.
            if headers:
                captured_auth_headers.append(headers.get("Authorization", ""))
            return httpx.Response(200, json={"status": "ok"})

        mock_http_client = MagicMock(spec=httpx.Client)
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.request = _fake_request
        mock_http_client.get = _fake_request  # Legacy compat, same behavior.
        mock_http_client.post = MagicMock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )

        with _stub_sync_deps() as stack:
            stack.enter_context(
                patch("httpx.Client", return_value=mock_http_client)
            )
            result = runner.invoke(sync_app, ["status", "--check"])

        # Command completed successfully.
        assert result.exit_code == 0, (
            f"exit_code={result.exit_code}\n"
            f"stdout={result.stdout}\n"
            f"exception={result.exception!r}"
        )

        # The refresh flow was called exactly once (FR-009 + FR-010).
        assert install_fake_refresh.call_count == 1, (
            f"Expected exactly 1 refresh call, got {install_fake_refresh.call_count}"
        )

        # The health probe used the REFRESHED token, not the stale one.
        assert len(captured_auth_headers) >= 1, "No health probe was made"
        assert captured_auth_headers[0] == "Bearer refreshed_access_token", (
            f"Expected refreshed token in Authorization header, "
            f"got: {captured_auth_headers[0]!r}"
        )
        assert "stale_access_token" not in result.stdout

        # The refreshed session was persisted to storage.
        assert len(seeded_tm.writes) == 1
        assert seeded_tm.writes[0].access_token == "refreshed_access_token"

        # Output confirms the connection probe succeeded.
        assert "Connected" in result.stdout
