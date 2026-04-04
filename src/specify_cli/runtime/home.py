"""Global runtime home directory and package asset discovery.

This module preserves the historical ``specify_cli.runtime.home`` API surface,
including monkeypatch seams used by the existing test suite.  The matching
kernel-level helpers remain available for other packages, but this shim keeps
the older development-layout fallback behavior intact inside ``specify_cli``.
"""

from __future__ import annotations

import importlib.resources
import os
from pathlib import Path


def _is_windows() -> bool:
    """Return True when running on Windows."""
    return os.name == "nt"


def get_kittify_home() -> Path:
    """Return the path to the user-global ~/.kittify/ directory."""
    if env_home := os.environ.get("SPEC_KITTY_HOME"):
        return Path(env_home)

    if _is_windows():
        from platformdirs import user_data_dir

        return Path(user_data_dir("kittify"))

    return Path.home() / ".kittify"


def get_package_asset_root() -> Path:
    """Return the path to the package's bundled mission assets."""
    if env_root := os.environ.get("SPEC_KITTY_TEMPLATE_ROOT"):
        root = Path(env_root)
        if root.is_dir():
            return root
        raise FileNotFoundError(f"SPEC_KITTY_TEMPLATE_ROOT path does not exist: {env_root}")

    try:
        pkg_root = importlib.resources.files("specify_cli")
        missions_dir = Path(str(pkg_root)) / "missions"
        if missions_dir.is_dir():
            return missions_dir
    except (TypeError, ModuleNotFoundError):
        pass

    dev_root = Path(__file__).parent.parent / "missions"
    if dev_root.is_dir():
        return dev_root

    raise FileNotFoundError(
        "Cannot locate package mission assets. Set SPEC_KITTY_TEMPLATE_ROOT or reinstall spec-kitty-cli."
    )


__all__ = ["_is_windows", "get_kittify_home", "get_package_asset_root"]
