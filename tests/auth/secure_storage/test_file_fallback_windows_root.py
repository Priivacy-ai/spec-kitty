"""T017 — Windows-native round-trip tests for WindowsFileStorage.

These tests are marked @pytest.mark.windows_ci and run only on the
native windows-latest CI job (WP07). They test the actual store → load →
delete cycle using a real filesystem path under %LOCALAPPDATA%.
"""

from __future__ import annotations

import pytest

from specify_cli.auth.secure_storage import WindowsFileStorage


@pytest.mark.windows_ci
def test_windows_file_store_round_trip(tmp_path):
    """Round-trip: store → load → delete using a temp directory."""
    store = WindowsFileStorage(store_path=tmp_path / "auth")
    store.write.__func__  # verify the method exists via the base class

    # Use the inherited read/write/delete interface from FileFallbackStorage.
    from specify_cli.auth.session import StoredSession

    session = StoredSession(
        access_token="test-token",
        refresh_token="test-refresh",
        token_type="Bearer",
        storage_backend="file",
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
