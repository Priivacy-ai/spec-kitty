"""Global runtime home directory and package asset discovery.

Provides the canonical functions for locating:
- The user-global ~/.kittify/ directory (cross-platform)
- The package-bundled mission assets (for ensure_runtime to copy from)
"""

from __future__ import annotations

import importlib.resources
import os
from pathlib import Path


def _is_windows() -> bool:
    """Return True when running on Windows."""
    return os.name == "nt"


def get_kittify_home() -> Path:
    """Return the path to the user-global ~/.kittify/ directory.

    Resolution order:
    1. SPEC_KITTY_HOME environment variable (all platforms)
    2. ~/.kittify/ on macOS/Linux (Path.home() / ".kittify")
    3. %LOCALAPPDATA%\\kittify\\ on Windows (via platformdirs)

    Returns:
        Path: Absolute path to the global runtime directory.

    Raises:
        RuntimeError: If the home directory cannot be determined.
    """
    if env_home := os.environ.get("SPEC_KITTY_HOME"):
        return Path(env_home)

    if _is_windows():
        from platformdirs import user_data_dir

        return Path(user_data_dir("kittify"))

    return Path.home() / ".kittify"


def get_package_asset_root() -> Path:
    """Return the path to the package's bundled mission assets.

    Resolution order:
    1. SPEC_KITTY_TEMPLATE_ROOT environment variable (CI/testing)
    2. importlib.resources.files("doctrine") / "missions" (installed package)
    3. Path(__file__).parent.parent / "doctrine" / "missions" (development layout)

    Returns:
        Path: Absolute path to the missions directory in the package.

    Raises:
        FileNotFoundError: If no valid asset root can be found.
    """
    # CI/testing override
    if env_root := os.environ.get("SPEC_KITTY_TEMPLATE_ROOT"):
        root = Path(env_root)
        if root.is_dir():
            return root
        raise FileNotFoundError(f"SPEC_KITTY_TEMPLATE_ROOT path does not exist: {env_root}")

    # Installed package - try doctrine package first
    try:
        pkg_root = importlib.resources.files("doctrine")
        missions_dir = Path(str(pkg_root)) / "missions"
        if missions_dir.is_dir():
            return missions_dir
    except (TypeError, ModuleNotFoundError):
        pass

    # Development layout - look for src/doctrine/missions
    dev_root = Path(__file__).parent.parent.parent / "doctrine" / "missions"
    if dev_root.is_dir():
        return dev_root

    raise FileNotFoundError(
        "Cannot locate package mission assets. Set SPEC_KITTY_TEMPLATE_ROOT or reinstall spec-kitty-cli."
    )
