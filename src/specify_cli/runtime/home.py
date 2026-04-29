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
    """Return the path to the user-global runtime directory.

    On Windows this resolves to the unified ``%LOCALAPPDATA%\\spec-kitty\\``
    root (via ``specify_cli.paths.get_runtime_root()``) so that every consumer
    in ``specify_cli`` sees the same Windows runtime root per Q3=C of the
    Windows Compatibility Hardening mission.  POSIX behavior is unchanged
    (returns ``~/.kittify`` for back-compat with existing installs).

    The ``SPEC_KITTY_HOME`` environment variable always wins regardless of
    platform.
    """
    if env_home := os.environ.get("SPEC_KITTY_HOME"):
        return Path(env_home)

    if _is_windows():
        from specify_cli.paths import get_runtime_root  # noqa: PLC0415

        return get_runtime_root().base

    return Path.home() / ".kittify"


def _looks_like_missions_root(path: Path) -> bool:
    """Return True when ``path`` can serve as a mission asset root."""
    if path.name == "missions":
        return True
    for mission_name in ("software-dev", "documentation", "research", "plan"):
        mission_dir = path / mission_name
        if (mission_dir / "mission.yaml").is_file() or (mission_dir / "mission-runtime.yaml").is_file():
            return True
        if (mission_dir / "command-templates").is_dir():
            return True
    return False


def _resolve_env_package_asset_root(root: Path) -> Path:
    """Normalize SPEC_KITTY_TEMPLATE_ROOT to the bundled missions directory.

    Development docs and tests point ``SPEC_KITTY_TEMPLATE_ROOT`` at the
    checkout root. Runtime asset resolution needs the missions directory under
    that checkout, not the checkout root itself.
    """
    candidates = (
        root,
        root / "missions",
        root / "src" / "specify_cli" / "missions",
        root / "src" / "doctrine" / "missions",
    )
    for candidate in candidates:
        if candidate.is_dir() and _looks_like_missions_root(candidate):
            return candidate
    raise FileNotFoundError(f"SPEC_KITTY_TEMPLATE_ROOT does not contain mission assets: {root}. Expected a missions directory or a Spec Kitty checkout root.")


def get_package_asset_root() -> Path:
    """Return the path to the package's bundled mission assets."""
    if env_root := os.environ.get("SPEC_KITTY_TEMPLATE_ROOT"):
        root = Path(env_root)
        if root.is_dir():
            return _resolve_env_package_asset_root(root)
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

    raise FileNotFoundError("Cannot locate package mission assets. Set SPEC_KITTY_TEMPLATE_ROOT or reinstall spec-kitty-cli.")


__all__ = ["_is_windows", "get_kittify_home", "get_package_asset_root"]
