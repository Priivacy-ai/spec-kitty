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
    # Single-source the built-in mission-type names (#2669). Not circular: the
    # accessor resolves the INSTALLED doctrine package via importlib.resources,
    # independent of this candidate-``path`` template probe.
    from doctrine.missions.mission_type_repository import builtin_mission_type_ids  # noqa: PLC0415

    for mission_name in builtin_mission_type_ids():
        mission_dir = path / mission_name
        has_content_templates = any((mission_dir / "templates").glob("*.md"))
        has_legacy_commands = any((mission_dir / "command-templates").glob("*.md"))
        has_step_prompts = any((path / "mission-steps" / mission_name).glob("*/prompt.md"))
        if has_content_templates or has_legacy_commands or has_step_prompts:
            return True
    return False


def _resolve_env_package_asset_root(root: Path) -> Path:
    """Normalize ``SPEC_KITTY_TEMPLATE_ROOT`` to the bundled missions directory.

    Development docs and tests point ``SPEC_KITTY_TEMPLATE_ROOT`` at the
    checkout root. Runtime asset resolution needs the canonical doctrine
    missions directory under that checkout, not the checkout root itself.
    """
    candidates = (
        root / "missions",
        root / "src" / "doctrine" / "missions",
        root.parent.parent / "doctrine" / "missions",
        root,
        root / "src" / "specify_cli" / "missions",
    )
    for candidate in candidates:
        if candidate.is_dir() and _looks_like_missions_root(candidate):
            return candidate
    raise FileNotFoundError(
        "SPEC_KITTY_TEMPLATE_ROOT does not contain mission assets: "
        f"{root}. Expected a missions directory or a Spec Kitty checkout root."
    )


def get_package_asset_root() -> Path:
    """Return the path to the package's bundled mission assets.

    The canonical package asset root is ``doctrine/missions``. The
    ``specify_cli/missions`` fallback remains only for older editable layouts
    and tests that intentionally provide a legacy asset root.
    """
    if env_root := os.environ.get("SPEC_KITTY_TEMPLATE_ROOT"):
        root = Path(env_root)
        if root.is_dir():
            return _resolve_env_package_asset_root(root)
        raise FileNotFoundError(f"SPEC_KITTY_TEMPLATE_ROOT path does not exist: {env_root}")

    for package in ("doctrine", "specify_cli"):
        try:
            pkg_root = importlib.resources.files(package)
            missions_dir = Path(str(pkg_root)) / "missions"
            if missions_dir.is_dir():
                return missions_dir
        except (TypeError, ModuleNotFoundError):
            pass

    dev_roots = (
        Path(__file__).parents[2] / "doctrine" / "missions",
        Path(__file__).parent.parent / "missions",
    )
    for dev_root in dev_roots:
        if dev_root.is_dir():
            return dev_root

    raise FileNotFoundError(
        "Cannot locate package mission assets. Set SPEC_KITTY_TEMPLATE_ROOT or reinstall spec-kitty-cli."
    )


__all__ = ["_is_windows", "get_kittify_home", "get_package_asset_root"]
