"""Windows round-trip tests for the canonical file-backed auth store."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from specify_cli.auth.secure_storage import WindowsFileStorage
from specify_cli.auth.session import StoredSession, Team
from specify_cli.paths import get_runtime_root


pytestmark = [pytest.mark.integration]

@pytest.mark.windows_ci
def test_windows_file_store_round_trip(tmp_path):
    """Round-trip: store → load → delete using a temp directory."""
    store = WindowsFileStorage(store_path=tmp_path / "auth")

    now = datetime.now(UTC)
    session = StoredSession(
        user_id="user-1",
        email="user@example.com",
        name="Spec Kitty User",
        teams=[Team(id="team-1", name="Team One", role="owner")],
        default_team_id="team-1",
        access_token="test-token",
        refresh_token="test-refresh",
        session_id="session-1",
        issued_at=now,
        access_token_expires_at=now + timedelta(hours=1),
        refresh_token_expires_at=None,
        scope="openid profile email",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )

    store.write(session)
    loaded = store.read()
    assert loaded is not None
    assert loaded.access_token == "test-token"

    store.delete()
    assert store.read() is None


@pytest.mark.windows_ci
def test_windows_file_store_default_path_under_runtime_root():
    """Default store_path is the unified runtime root's ``auth`` dir.

    WP03 / DM-01KW1KDHVGWZ0QERDMV1CRJ15S: the Windows store was previously
    hardcoded to ``~/.spec-kitty/auth``. It now resolves through
    :func:`specify_cli.paths.get_runtime_root` — the platformdirs LocalAppData
    base on real Windows (``%LOCALAPPDATA%\\spec-kitty\\auth``), or
    ``$SPEC_KITTY_HOME/auth`` when that environment variable is set.
    """
    store = WindowsFileStorage()
    assert store.store_path == get_runtime_root().auth_dir
