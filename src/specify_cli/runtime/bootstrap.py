"""Runtime bootstrap: ensure_runtime() and related functions.

On every CLI startup, ``ensure_runtime()`` guarantees that
``~/.kittify/`` contains up-to-date package assets. It uses a
version.lock file for fast-path detection and file locking for
concurrency safety across parallel CLI invocations.

Also provides version pin detection and warning for projects that set
``runtime.pin_version`` in their ``.kittify/config.yaml``.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
import warnings
from pathlib import Path
from typing import IO

import yaml

from specify_cli.runtime.home import get_kittify_home, get_package_asset_root
from specify_cli.runtime.merge import merge_package_assets

logger = logging.getLogger(__name__)


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


def _cleanup_orphaned_update_dirs(parent: Path) -> None:
    """Remove stale ``.kittify_update_*`` directories left by crashed processes.

    After an abnormal termination, orphaned staging directories may remain.
    This function scans *parent* for any matching directories and removes
    them unconditionally.  It is called **under the exclusive file lock**
    so that it never deletes another process's active staging directory.

    Errors during removal are silently ignored (best-effort cleanup).
    """
    if not parent.is_dir():
        return
    for entry in parent.iterdir():
        if entry.is_dir() and entry.name.startswith(".kittify_update_"):
            try:
                shutil.rmtree(entry)
            except OSError:
                pass  # best-effort cleanup


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

        # Clean up orphaned staging dirs from crashed processes.
        # Done under the lock so we never delete another process's
        # active staging directory.
        _cleanup_orphaned_update_dirs(home.parent)

        # Double-check after lock acquired (another process may have finished)
        if version_file.exists():
            stored = version_file.read_text().strip()
            if stored == cli_version:
                return

        # Build new asset tree in a unique temp directory
        tmp_dir = Path(
            tempfile.mkdtemp(prefix=".kittify_update_", dir=home.parent)
        )
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


def check_version_pin(project_dir: Path) -> None:
    """Check for runtime.pin_version in project config and warn if present.

    Version pinning is not yet supported.  When a pin is detected the
    function emits both a ``logging.warning`` and a ``UserWarning`` so
    that CI pipelines and interactive users alike are notified.  The
    pinned version is **never** silently honored -- the latest global
    assets are always used.

    Args:
        project_dir: Project root containing ``.kittify/``.
    """
    config_path = project_dir / ".kittify" / "config.yaml"
    if not config_path.exists():
        return

    try:
        config = yaml.safe_load(config_path.read_text())
    except Exception:
        # Config parsing failure handled elsewhere
        return

    if not config or not isinstance(config, dict):
        return

    runtime = config.get("runtime", {})
    if not isinstance(runtime, dict):
        return

    if "pin_version" not in runtime:
        return

    pin = runtime["pin_version"]
    msg = (
        f"runtime.pin_version={pin} found in .kittify/config.yaml. "
        f"Version pinning is not yet supported. Using latest global assets. "
        f"The pin will NOT be silently honored."
    )
    logger.warning(msg)
    warnings.warn(msg, UserWarning, stacklevel=2)
