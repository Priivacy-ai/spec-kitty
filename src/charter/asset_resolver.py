"""Charter-level asset resolver gateway (4-tier chain with injected providers).

Delegates path-helper sourcing to caller-supplied `home_provider` and
`asset_root_provider` callables so downstream consumers (e.g. `runtime.discovery`)
can keep their own monkeypatch-targetable helpers without charter caching any
path at import time.

Re-exports `ResolutionTier` and `ResolutionResult` from `doctrine.resolver` —
same class identities — so `isinstance` and `==` checks work across modules.

Tier order (checked highest-precedence first):

1. OVERRIDE        -- {project_dir}/.kittify/overrides/{subdir}/{name}
2. LEGACY          -- {project_dir}/.kittify/{subdir}/{name}
3. GLOBAL_MISSION  -- {home_provider()}/missions/{mission}/{subdir}/{name}
4. GLOBAL          -- {home_provider()}/{subdir}/{name}    (templates/command-templates only)
5. PACKAGE_DEFAULT -- {asset_root_provider()}/{mission}/{subdir}/{name}

Mission-config resolution (`resolve_mission`) has no GLOBAL tier — missions
are inherently mission-scoped.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from doctrine.resolver import ResolutionResult, ResolutionTier

__all__ = [
    "ResolutionResult",
    "ResolutionTier",
    "resolve_command",
    "resolve_mission",
    "resolve_template",
]

HomeProvider = Callable[[], Path]
AssetRootProvider = Callable[[], Path]
LegacyWarnHook = Callable[[Path], None]


def _resolve_asset(
    name: str,
    subdir: str,
    project_dir: Path,
    mission: str,
    *,
    home_provider: HomeProvider,
    asset_root_provider: AssetRootProvider,
    legacy_warn_hook: LegacyWarnHook | None = None,
) -> ResolutionResult:
    """Resolve a template/command-template asset through the 5-tier chain."""
    kittify = project_dir / ".kittify"

    override = kittify / "overrides" / subdir / name
    if override.is_file():
        return ResolutionResult(path=override, tier=ResolutionTier.OVERRIDE, mission=mission)

    legacy = kittify / subdir / name
    if legacy.is_file():
        if legacy_warn_hook is not None:
            legacy_warn_hook(legacy)
        return ResolutionResult(path=legacy, tier=ResolutionTier.LEGACY, mission=mission)

    try:
        home = home_provider()
        global_mission = home / "missions" / mission / subdir / name
        if global_mission.is_file():
            return ResolutionResult(
                path=global_mission, tier=ResolutionTier.GLOBAL_MISSION, mission=mission
            )
        global_path = home / subdir / name
        if global_path.is_file():
            return ResolutionResult(path=global_path, tier=ResolutionTier.GLOBAL, mission=mission)
    except RuntimeError:
        pass

    try:
        asset_root = asset_root_provider()
        pkg_path = asset_root / mission / subdir / name
        if pkg_path.is_file():
            return ResolutionResult(
                path=pkg_path, tier=ResolutionTier.PACKAGE_DEFAULT, mission=mission
            )
    except FileNotFoundError:
        pass

    raise FileNotFoundError(
        f"Asset {name!r} not found in any resolution tier "
        f"(subdir={subdir!r}, mission={mission!r}, project={project_dir})"
    )


def resolve_template(
    name: str,
    project_dir: Path,
    mission: str = "software-dev",
    *,
    home_provider: HomeProvider,
    asset_root_provider: AssetRootProvider,
    legacy_warn_hook: LegacyWarnHook | None = None,
) -> ResolutionResult:
    """Resolve a template file through the 5-tier chain."""
    return _resolve_asset(
        name, "templates", project_dir, mission,
        home_provider=home_provider,
        asset_root_provider=asset_root_provider,
        legacy_warn_hook=legacy_warn_hook,
    )


def resolve_command(
    name: str,
    project_dir: Path,
    mission: str = "software-dev",
    *,
    home_provider: HomeProvider,
    asset_root_provider: AssetRootProvider,
    legacy_warn_hook: LegacyWarnHook | None = None,
) -> ResolutionResult:
    """Resolve a command template file through the 5-tier chain."""
    return _resolve_asset(
        name, "command-templates", project_dir, mission,
        home_provider=home_provider,
        asset_root_provider=asset_root_provider,
        legacy_warn_hook=legacy_warn_hook,
    )


def resolve_mission(
    name: str,
    project_dir: Path,
    *,
    home_provider: HomeProvider,
    asset_root_provider: AssetRootProvider,
    legacy_warn_hook: LegacyWarnHook | None = None,
) -> ResolutionResult:
    """Resolve a mission.yaml through the 4-tier chain (no non-mission GLOBAL tier)."""
    kittify = project_dir / ".kittify"
    filename = "mission.yaml"

    override = kittify / "overrides" / "missions" / name / filename
    if override.is_file():
        return ResolutionResult(path=override, tier=ResolutionTier.OVERRIDE, mission=name)

    legacy = kittify / "missions" / name / filename
    if legacy.is_file():
        if legacy_warn_hook is not None:
            legacy_warn_hook(legacy)
        return ResolutionResult(path=legacy, tier=ResolutionTier.LEGACY, mission=name)

    try:
        home = home_provider()
        global_path = home / "missions" / name / filename
        if global_path.is_file():
            return ResolutionResult(
                path=global_path, tier=ResolutionTier.GLOBAL_MISSION, mission=name
            )
    except RuntimeError:
        pass

    try:
        asset_root = asset_root_provider()
        pkg_path = asset_root / name / filename
        if pkg_path.is_file():
            return ResolutionResult(
                path=pkg_path, tier=ResolutionTier.PACKAGE_DEFAULT, mission=name
            )
    except FileNotFoundError:
        pass

    raise FileNotFoundError(
        f"Mission {name!r} config not found in any resolution tier (project={project_dir})"
    )
