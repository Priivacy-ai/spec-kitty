"""T017 — Windows-native round-trip tests for WindowsFileStorage.

These tests are marked @pytest.mark.windows_ci and run only on the
native windows-latest CI job (WP07). They test the actual store → load →
delete cycle using a real filesystem path under %LOCALAPPDATA%.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from specify_cli.auth.secure_storage import WindowsFileStorage
from specify_cli.auth.session import StoredSession, Team


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
def test_windows_file_store_default_path_under_localappdata():
    """Default store_path is rooted under %LOCALAPPDATA%\\spec-kitty\\auth."""
    from specify_cli.paths import get_runtime_root

    root = get_runtime_root()
    assert root.platform == "win32", (
        "This test only makes sense on windows-latest where sys.platform == 'win32'"
    )
    path_str = str(root.auth_dir).upper()
    assert "APPDATA" in path_str or "LOCALAPPDATA" in path_str, (
        f"Expected Windows AppData path, got: {root.auth_dir}"
    )
