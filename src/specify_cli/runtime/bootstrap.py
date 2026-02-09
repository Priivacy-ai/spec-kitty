"""Runtime bootstrap: ensure_runtime() and related functions.

On every CLI startup, ``ensure_runtime()`` guarantees that
``~/.kittify/`` contains up-to-date package assets. It uses a
version.lock file for fast-path detection and file locking for
concurrency safety across parallel CLI invocations.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import IO

from specify_cli.runtime.home import get_kittify_home, get_package_asset_root
from specify_cli.runtime.merge import merge_package_assets


def _get_cli_version() -> str:
    """Return the current CLI version string."""
    from specify_cli import __version__

    return __version__


def _lock_exclusive(fd: IO[str]) -> None:
    """Acquire an exclusive file lock, blocking if another process holds it.

    On Unix: uses ``fcntl.flock`` with a non-blocking attempt first.
    If another process holds the lock, falls back to a blocking wait.

    On Windows: uses ``msvcrt.locking`` with ``LK_LOCK`` (blocking).

    Args:
        fd: An open file object whose underlying descriptor will be locked.
    """
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(fd.fileno(), msvcrt.LK_LOCK, 1)
    else:
        import fcntl

        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            # Another process is updating -- wait for it
            fcntl.flock(fd, fcntl.LOCK_EX)


def populate_from_package(target: Path) -> None:
    """Copy all package-bundled assets to *target* directory.

    Creates a complete asset tree matching the ``~/.kittify/`` layout:

    - ``missions/`` -- copied from ``get_package_asset_root()``
    - ``scripts/``  -- copied from the package's ``scripts/`` directory
    - ``AGENTS.md`` -- copied from the package root

    Args:
        target: Destination directory (typically a temporary staging area).
    """
    asset_root = get_package_asset_root()
    target.mkdir(parents=True, exist_ok=True)

    # Copy all missions
    missions_src = asset_root
    missions_dst = target / "missions"
    if missions_src.is_dir():
        shutil.copytree(missions_src, missions_dst)

    # Copy scripts if they exist
    scripts_src = asset_root.parent / "scripts"
    if scripts_src.is_dir():
        shutil.copytree(scripts_src, target / "scripts")

    # Copy AGENTS.md if it exists
    agents_src = asset_root.parent / "AGENTS.md"
    if agents_src.is_file():
        shutil.copy2(agents_src, target / "AGENTS.md")


def ensure_runtime() -> None:
    """Ensure ``~/.kittify/`` global runtime is populated and current.

    **Fast path** (<100 ms): If ``cache/version.lock`` matches the CLI
    version, return immediately -- no lock acquired.

    **Slow path**: Acquire an exclusive file lock, double-check the
    version (another process may have finished the update while we
    waited), build a fresh asset tree in a temporary directory, merge
    managed assets into ``~/.kittify/``, and write ``version.lock``
    **last** so that incomplete updates are always detectable.

    The temporary staging directory is cleaned up in a ``finally``
    block, even if an exception occurs during the update.
    """
    home = get_kittify_home()
    home.mkdir(parents=True, exist_ok=True)

    cache_dir = home / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    version_file = cache_dir / "version.lock"
    cli_version = _get_cli_version()

    # Fast path: version matches -- no lock needed
    if version_file.exists():
        stored = version_file.read_text().strip()
        if stored == cli_version:
            return

    # Slow path: acquire exclusive file lock
    lock_path = cache_dir / ".update.lock"
    lock_fd = open(lock_path, "w")  # noqa: SIM115 -- need fd for flock
    try:
        _lock_exclusive(lock_fd)

        # Double-check after lock acquired (another process may have finished)
        if version_file.exists():
            stored = version_file.read_text().strip()
            if stored == cli_version:
                return

        # Build new asset tree in temp directory
        tmp_dir = home.parent / f".kittify_update_{os.getpid()}"
        try:
            populate_from_package(tmp_dir)
            merge_package_assets(source=tmp_dir, dest=home)
            # Write version.lock LAST -- incomplete updates won't have this
            version_file.write_text(cli_version)
        finally:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)
    finally:
        lock_fd.close()
