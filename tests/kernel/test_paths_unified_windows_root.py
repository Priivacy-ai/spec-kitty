"""Cross-module single-root consistency test (T030).

Asserts C-002 / FR-005: on Windows, auth / tracker / sync / daemon /
kernel.paths all resolve under the same ``RuntimeRoot.base``.

Marked ``windows_ci`` — runs on ``windows-latest`` only.  Collects cleanly on
POSIX so that CI configuration errors surface immediately.
"""
from __future__ import annotations

import pytest


@pytest.mark.windows_ci
def test_all_consumers_share_single_windows_root() -> None:
    """Every runtime-state consumer resolves under the same RuntimeRoot.base."""
    from specify_cli.paths import get_runtime_root

    root = get_runtime_root()
    assert root.platform == "win32", (
        f"This test must run on Windows; platform={root.platform}"
    )
    base_str = str(root.base).lower()

    # Auth — WP03 WindowsFileStorage
    from specify_cli.auth.secure_storage import WindowsFileStorage

    auth = WindowsFileStorage()
    assert base_str in str(auth.store_path).lower(), (
        f"Auth store_path {auth.store_path} is not under unified root {root.base}"
    )

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
