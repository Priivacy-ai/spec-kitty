"""Platform-aware runtime state path resolution for spec-kitty.

This module is a leaf — it must not import from specify_cli.auth,
specify_cli.tracker, specify_cli.sync, or any kernel subpackage.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import platformdirs


@dataclass(frozen=True)
class RuntimeRoot:
    """Immutable descriptor of the runtime state root for the current platform.

    Fields
    ------
    platform:
        The normalised platform string: "win32", "darwin", or "linux".
    base:
        Absolute path to the top-level runtime state directory.  Subdirs are
        derived properties so callers never construct paths by hand.

    Notes
    -----
    This dataclass is frozen so it can safely be cached at module or function
    level by callers.  It performs no I/O and creates no directories.
    """

    platform: Literal["win32", "darwin", "linux"]
    base: Path

    @property
    def auth_dir(self) -> Path:
        return self.base / "auth"

    @property
    def tracker_dir(self) -> Path:
        return self.base / "tracker"

    @property
    def sync_dir(self) -> Path:
        return self.base / "sync"

    @property
    def daemon_dir(self) -> Path:
        return self.base / "daemon"

    @property
    def cache_dir(self) -> Path:
        return self.base / "cache"


def get_runtime_root() -> RuntimeRoot:
    """Return the canonical runtime state root for the current platform.

    On Windows: uses ``platformdirs.user_data_dir`` (non-roaming LocalAppData).
    On POSIX  : returns ``~/.spec-kitty`` unchanged.

    This function is **pure** — it performs no I/O and creates no directories.
    Directory creation is the caller's responsibility.
    """
    platform = _current_platform()
    base = Path(platformdirs.user_data_dir("spec-kitty", appauthor=False, roaming=False)) if platform == "win32" else Path.home() / ".spec-kitty"
    return RuntimeRoot(platform=platform, base=base)


def render_runtime_path(path: Path, *, for_user: bool = True) -> str:
    """Render a runtime-state path for user-facing output.

    On Windows: returns the real absolute path
    (e.g. ``C:\\Users\\alice\\AppData\\Local\\spec-kitty\\auth``).

    On POSIX: returns a tilde-compressed form (``~/...``) when the path is
    under ``$HOME`` and *for_user* is ``True``, otherwise returns the absolute
    path as a string.

    Parameters
    ----------
    path:
        The path to render.  May be relative or not yet exist on disk.
    for_user:
        When ``False`` always return the absolute path regardless of platform.
    """
    abs_path = Path(path).resolve(strict=False)
    if not for_user:
        return str(abs_path)
    if _current_platform() == "win32":
        return str(abs_path)
    # POSIX tilde compression
    try:
        home = Path.home().resolve(strict=False)
        rel = abs_path.relative_to(home)
        return "~/" + str(rel).replace("\\", "/")
    except ValueError:
        return str(abs_path)


def _current_platform() -> Literal["win32", "darwin", "linux"]:
    """Return the normalised platform string for the current runtime."""
    if sys.platform.startswith("win"):
        return "win32"
    if sys.platform == "darwin":
        return "darwin"
    return "linux"
