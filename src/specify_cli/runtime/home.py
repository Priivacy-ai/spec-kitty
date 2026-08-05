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


def _find_relocated_missions_ancestor(root: Path) -> Path | None:
    """Walk ``root`` and its ancestors for the real, post-relocation missions root.

    Mission ``doctrine-consumer-surface-missions-extraction-01KZ6G6H``
    (FR-005) moved the missions data from ``src/doctrine/missions`` to
    ``packs/built-in/missions``. ``SPEC_KITTY_TEMPLATE_ROOT`` may be set to
    any of several legacy shapes (the bare missions directory, a full
    checkout root, a stale ``specify_cli/missions`` leaf, ...), each sitting
    at a different depth relative to the real repository root, so this walks
    every ancestor (including ``root`` itself) rather than assuming a fixed
    number of ``.parent`` hops, finding the relocated data uniformly
    regardless of which legacy shape the caller supplied. Unlike the other
    candidates in :func:`_resolve_env_package_asset_root`, the
    ``packs/built-in/missions`` shape is unambiguous -- no unrelated tree can
    accidentally satisfy it -- so no content-sniff is needed once a candidate
    is found to exist.
    """
    for ancestor in (root, *root.parents):
        candidate = ancestor / "packs" / "built-in" / "missions"
        if candidate.is_dir():
            return candidate
    return None


def _resolve_env_package_asset_root(root: Path) -> Path:
    """Normalize ``SPEC_KITTY_TEMPLATE_ROOT`` to the bundled missions directory.

    Development docs and tests point ``SPEC_KITTY_TEMPLATE_ROOT`` at the
    checkout root. Runtime asset resolution needs the canonical doctrine
    missions directory under that checkout, not the checkout root itself.

    The relocated ``packs/built-in/missions`` location is tried first and
    unconditionally (see :func:`_find_relocated_missions_ancestor`): every
    candidate below predates mission #3091's move and would otherwise resolve
    into the now data-less ``src/doctrine/missions`` package directory or the
    unrelated ``specify_cli/missions`` legacy tree.
    """
    if (relocated := _find_relocated_missions_ancestor(root)) is not None:
        return relocated

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

    The canonical package asset root is ``packs/built-in/missions``. The
    ``specify_cli/missions`` fallback remains only for older editable layouts
    and tests that intentionally provide a legacy asset root.
    """
    if env_root := os.environ.get("SPEC_KITTY_TEMPLATE_ROOT"):
        root = Path(env_root)
        if root.is_dir():
            return _resolve_env_package_asset_root(root)
        raise FileNotFoundError(f"SPEC_KITTY_TEMPLATE_ROOT path does not exist: {env_root}")

    # Function-local import of a doctrine-layer class (matches the existing
    # pattern at :func:`_looks_like_missions_root` above) — FR-004/FR-005
    # retarget this probe onto the ONE promoted missions-root authority
    # instead of a raw ``importlib.resources.files("doctrine") / "missions"``
    # literal. Mission doctrine-consumer-surface-missions-extraction-01KZ6G6H
    # relocated the missions data to ``packs/built-in/missions`` -- the
    # "doctrine" package no longer carries it directly (only the 11 .py logic
    # modules remain under ``src/doctrine/missions``), so the retired raw
    # probe would silently resolve to that now data-less directory (it still
    # exists and still passes a bare ``.is_dir()`` check) instead of raising
    # or falling through. This shares the module docstring's #2986 blind
    # spot: a function-local import is invisible to import-time static
    # analysis that only checks module headers. Named here, not hidden.
    from doctrine.missions.repository import (  # noqa: PLC0415
        MissionsRootNotFound,
        MissionTemplateRepository,
    )

    try:
        doctrine_missions = MissionTemplateRepository.default_missions_root()
    except MissionsRootNotFound:
        doctrine_missions = None
    if doctrine_missions is not None and doctrine_missions.is_dir():
        return doctrine_missions

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
