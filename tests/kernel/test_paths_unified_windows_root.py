"""Windows runtime-root consistency tests.

Auth session storage is intentionally excluded from the shared runtime root:
it lives under ``%USERPROFILE%\\.spec-kitty\\auth`` while tracker/sync/daemon
state continues to use the runtime-root helpers.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.windows_ci
def test_runtime_consumers_share_single_windows_root_except_auth() -> None:
    """Tracker/sync/daemon/kernel runtime state resolves under RuntimeRoot.base."""
    from specify_cli.paths import get_runtime_root

    root = get_runtime_root()
    assert root.platform == "win32", (
        f"This test must run on Windows; platform={root.platform}"
    )
    base_str = str(root.base).lower()

    # Tracker
    from specify_cli.tracker import credentials

    tracker_root = credentials._tracker_root()
    assert base_str in str(tracker_root).lower(), (
        f"Tracker root {tracker_root} is not under unified root {root.base}"
    )

    # Sync
    from specify_cli.sync import daemon

    sync_root = daemon._sync_root()
    assert base_str in str(sync_root).lower(), (
        f"Sync root {sync_root} is not under unified root {root.base}"
    )

    # Daemon
    daemon_root = daemon._daemon_root()
    assert base_str in str(daemon_root).lower(), (
        f"Daemon root {daemon_root} is not under unified root {root.base}"
    )

    # kernel.paths — get_kittify_home() Windows branch uses the same
    # platformdirs call (app="spec-kitty", roaming=False) as get_runtime_root(),
    # so both must resolve to the same %LOCALAPPDATA%\spec-kitty base.
    from kernel import paths as kernel_paths

    kittify_home = kernel_paths.get_kittify_home()
    assert base_str in str(kittify_home).lower(), (
        f"kernel.paths.get_kittify_home() resolves to {kittify_home}, "
        f"outside the unified Windows root {root.base}"
    )


@pytest.mark.windows_ci
def test_auth_store_uses_user_home_root_on_windows() -> None:
    """Auth storage now lives under %USERPROFILE%\\.spec-kitty\\auth."""
    from specify_cli.auth.secure_storage import WindowsFileStorage

    auth = WindowsFileStorage()
    assert auth.store_path == Path.home() / ".spec-kitty" / "auth"


@pytest.mark.windows_ci
def test_runtime_root_platform_field_is_win32() -> None:
    """RuntimeRoot.platform is 'win32' when running on Windows."""
    from specify_cli.paths import get_runtime_root

    root = get_runtime_root()
    assert root.platform == "win32"


@pytest.mark.windows_ci
def test_runtime_root_base_is_absolute() -> None:
    """RuntimeRoot.base is an absolute path."""
    from specify_cli.paths import get_runtime_root

    root = get_runtime_root()
    assert root.base.is_absolute(), f"Expected absolute base path, got: {root.base}"
