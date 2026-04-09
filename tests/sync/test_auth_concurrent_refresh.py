"""Regression tests for the concurrent refresh race fix (FR-401–FR-404).

T5.1 — Lock is held for the full transaction (including the HTTP POST).
T5.2 — Stale 401 does NOT clear credentials.
T5.3 — Real (non-stale) 401 DOES clear credentials.
T5.4 — Reentrancy: inner load()/save() inside the lock do not deadlock.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch

import filelock
import pytest

from specify_cli.sync.auth import AuthClient, AuthenticationError

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _save_creds(auth_client: AuthClient, refresh_token: str = "original-refresh") -> None:
    """Save a full set of credentials into the auth_client's credential store."""
    auth_client.credential_store.save(
        access_token="access-token",
        refresh_token=refresh_token,
        access_expires_at=datetime.now(UTC) - timedelta(minutes=1),  # already expired
        refresh_expires_at=datetime.now(UTC) + timedelta(days=7),
        username="user@example.com",
        server_url="https://test.example.com",
    )


def _make_response(status_code: int, body: dict | None = None) -> Mock:
    """Create a minimal mock httpx response."""
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = body or {}
    return resp


# ---------------------------------------------------------------------------
# Fixture: isolated AuthClient
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_client(tmp_path):
    """AuthClient wired to an isolated, temporary credential store."""
    client = AuthClient()
    cred_dir = tmp_path / ".spec-kitty"
    cred_dir.mkdir()
    client.credential_store.credentials_path = cred_dir / "credentials"
    client.credential_store.lock_path = cred_dir / "credentials.lock"
    client.config.get_server_url = lambda: "https://test.example.com"
    return client


# ---------------------------------------------------------------------------
# T5.1 — Lock is held while the HTTP POST is in flight
# ---------------------------------------------------------------------------

class TestLockHeldDuringNetworkCall:
    """T5.1: FileLock is held across the entire refresh_tokens() transaction."""

    def test_lock_held_during_http_post(self, auth_client):
        """Another thread must NOT be able to acquire the lock while HTTP POST is in flight."""
        _save_creds(auth_client)

        lock_acquired_during_call = threading.Event()
        lock_was_held = threading.Event()

        def mock_post(*args, **kwargs):
            """Simulate a slow network call; check lock contention from another thread."""
            contender_acquired = threading.Event()

            def try_acquire_lock():
                # Use timeout=0 so the attempt is non-blocking; if it succeeds the lock
                # was NOT held, which would be a bug.
                try:
                    lock = auth_client.credential_store._acquire_lock()
                    # FileLock with timeout=0 raises Timeout if already held
                    lock_instance = filelock.FileLock(
                        str(auth_client.credential_store.lock_path), timeout=0
                    )
                    with lock_instance:
                        lock_acquired_during_call.set()  # BAD: should not reach here
                except filelock.Timeout:
                    lock_was_held.set()  # GOOD: lock is held as expected
                finally:
                    contender_acquired.set()

            t = threading.Thread(target=try_acquire_lock, daemon=True)
            t.start()
            contender_acquired.wait(timeout=2.0)
            t.join(timeout=2.0)

            return _make_response(200, {"access": "new-access", "refresh": "new-refresh"})

        with patch.object(auth_client, "_get_http_client") as mock_get_client:
            mock_get_client.return_value.post.side_effect = mock_post
            auth_client.refresh_tokens()

        assert not lock_acquired_during_call.is_set(), (
            "Another thread acquired the lock while HTTP POST was in flight — lock scope too narrow"
        )
        assert lock_was_held.is_set(), (
            "The contender thread never ran — test setup issue"
        )


# ---------------------------------------------------------------------------
# T5.2 — Stale 401 does NOT clear credentials
# ---------------------------------------------------------------------------

class TestStale401DoesNotClearCredentials:
    """T5.2: A 401 that arrives after another process has already rotated the token
    must exit cleanly without clearing credentials."""

    def test_stale_401_leaves_rotated_credentials_intact(self, auth_client):
        """When on-disk refresh token differs from entry token → stale 401 → no clear."""
        _save_creds(auth_client, refresh_token="original-refresh")

        # We simulate the race by patching get_refresh_token() to return the *old* token
        # (as if we read it before the other process rotated) while the on-disk state
        # already has the new token (set by a concurrent successful refresh).

        original_get_refresh = auth_client.credential_store.get_refresh_token

        call_count = 0

        def patched_get_refresh_token():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call (inside refresh_tokens entry) — return the old token
                return "original-refresh"
            # Subsequent calls go to the real implementation
            return original_get_refresh()

        # Rotate the on-disk credentials to simulate another process winning the race
        auth_client.credential_store.save(
            access_token="new-access",
            refresh_token="rotated-refresh",
            access_expires_at=datetime.now(UTC) + timedelta(minutes=15),
            refresh_expires_at=datetime.now(UTC) + timedelta(days=7),
            username="user@example.com",
            server_url="https://test.example.com",
        )

        def mock_post(*args, **kwargs):
            # Server rejects the old refresh token
            return _make_response(401)

        with (
            patch.object(auth_client.credential_store, "get_refresh_token", side_effect=patched_get_refresh_token),
            patch.object(auth_client, "_get_http_client") as mock_get_client,
        ):
            mock_get_client.return_value.post.side_effect = mock_post
            # Should NOT raise — stale 401 exits cleanly
            result = auth_client.refresh_tokens()

        assert result is True, "refresh_tokens() should return True on stale 401"

        # Credentials must NOT be cleared — the rotated token must remain
        current = auth_client.credential_store.load()
        assert current is not None, "Credentials were cleared by a stale 401 — this is the race bug!"
        assert current["tokens"]["refresh"] == "rotated-refresh", (
            "Rotated refresh token was overwritten or cleared"
        )


# ---------------------------------------------------------------------------
# T5.3 — Real 401 DOES clear credentials
# ---------------------------------------------------------------------------

class TestReal401ClearsCredentials:
    """T5.3: When the on-disk token is unchanged and the server returns 401,
    credentials must be cleared and AuthenticationError raised."""

    def test_real_401_clears_credentials_and_raises(self, auth_client):
        """Non-stale 401: on-disk token unchanged → clear credentials → raise."""
        _save_creds(auth_client, refresh_token="my-refresh")

        def mock_post(*args, **kwargs):
            # Server returns 401; disk still has "my-refresh" (no concurrent rotation)
            return _make_response(401)

        with patch.object(auth_client, "_get_http_client") as mock_get_client:
            mock_get_client.return_value.post.side_effect = mock_post

            with pytest.raises(AuthenticationError) as exc_info:
                auth_client.refresh_tokens()

        assert "Session expired" in str(exc_info.value)
        assert auth_client.credential_store.load() is None, (
            "Credentials should be cleared after a real 401"
        )

    def test_real_401_with_no_creds_on_disk_raises(self, auth_client):
        """Edge case: on-disk credentials are None after 401 → treat as real 401."""
        _save_creds(auth_client, refresh_token="my-refresh")

        def mock_post(*args, **kwargs):
            return _make_response(401)

        # Simulate: credentials were deleted between entry and 401 (very rare edge case).
        # current_creds will be None → falls through to real-401 path.
        original_get_refresh = auth_client.credential_store.get_refresh_token
        original_load = auth_client.credential_store.load

        call_count = {"get_refresh": 0, "load": 0}

        def patched_get_refresh():
            call_count["get_refresh"] += 1
            return original_get_refresh()

        def patched_load():
            call_count["load"] += 1
            if call_count["load"] >= 2:
                # Second load() call (inside the 401 handler) returns None
                return None
            return original_load()

        with (
            patch.object(auth_client.credential_store, "get_refresh_token", side_effect=patched_get_refresh),
            patch.object(auth_client.credential_store, "load", side_effect=patched_load),
            patch.object(auth_client, "_get_http_client") as mock_get_client,
        ):
            mock_get_client.return_value.post.side_effect = mock_post

            with pytest.raises(AuthenticationError) as exc_info:
                auth_client.refresh_tokens()

        assert "Session expired" in str(exc_info.value)


# ---------------------------------------------------------------------------
# T5.4 — Reentrancy: inner load()/save() don't deadlock
# ---------------------------------------------------------------------------

class TestInnerLockReacquisitionIsNoOp:
    """T5.4: load()/save()/clear() inside the locked refresh_tokens() must not deadlock."""

    def test_successful_refresh_completes_without_deadlock(self, auth_client):
        """Happy path: inner save() inside the lock does not deadlock."""
        _save_creds(auth_client, refresh_token="good-refresh")

        def mock_post(*args, **kwargs):
            return _make_response(200, {"access": "new-access", "refresh": "new-refresh"})

        with patch.object(auth_client, "_get_http_client") as mock_get_client:
            mock_get_client.return_value.post.side_effect = mock_post
            # Should complete without hanging
            result = auth_client.refresh_tokens()

        assert result is True

        creds = auth_client.credential_store.load()
        assert creds is not None
        assert creds["tokens"]["access"] == "new-access"
        assert creds["tokens"]["refresh"] == "new-refresh"

    def test_failed_refresh_completes_without_deadlock(self, auth_client):
        """Failure path: inner clear() inside the lock on real 401 does not deadlock."""
        _save_creds(auth_client, refresh_token="bad-refresh")

        def mock_post(*args, **kwargs):
            return _make_response(401)

        with patch.object(auth_client, "_get_http_client") as mock_get_client:
            mock_get_client.return_value.post.side_effect = mock_post

            # Must raise but not hang
            with pytest.raises(AuthenticationError):
                auth_client.refresh_tokens()

        # Credentials should be cleared (not deadlocked)
        assert auth_client.credential_store.load() is None

    def test_multiple_inner_loads_do_not_deadlock(self, auth_client):
        """Multiple inner load() calls (get_refresh_token, get_username, etc.) don't deadlock."""
        _save_creds(auth_client, refresh_token="multi-read-refresh")

        inner_load_count = [0]
        original_load = auth_client.credential_store.load

        def counted_load():
            inner_load_count[0] += 1
            return original_load()

        def mock_post(*args, **kwargs):
            return _make_response(200, {"access": "a2", "refresh": "r2"})

        with (
            patch.object(auth_client.credential_store, "load", side_effect=counted_load),
            patch.object(auth_client, "_get_http_client") as mock_get_client,
        ):
            mock_get_client.return_value.post.side_effect = mock_post
            result = auth_client.refresh_tokens()

        assert result is True
        # Multiple load() calls happened (get_refresh_token, get_username, get_server_url,
        # get_team_slug all call load()) — none of them deadlocked
        assert inner_load_count[0] > 1, "Expected multiple inner load() calls"
