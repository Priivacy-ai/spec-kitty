"""4-tier asset resolution: override > legacy > global > package default.

Resolution tiers (checked in order):
1. OVERRIDE  -- .kittify/overrides/{templates,command-templates}/
2. LEGACY    -- .kittify/{templates,command-templates}/ (deprecated; emits warning)
3. GLOBAL    -- ~/.kittify/missions/{mission}/{templates,command-templates}/
4. PACKAGE   -- src/specify_cli/missions/{mission}/{templates,command-templates}/
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from specify_cli.runtime.home import get_kittify_home, get_package_asset_root

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------

class ResolutionTier(Enum):
    OVERRIDE = "override"
    LEGACY = "legacy"
    GLOBAL = "global"
    PACKAGE_DEFAULT = "package_default"


@dataclass(frozen=True)
class ResolutionResult:
    path: Path
    tier: ResolutionTier
    mission: str | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _warn_legacy_asset(path: Path) -> None:
    """Emit a deprecation warning for a legacy-tier asset hit."""
    msg = (
        f"Legacy asset resolved: {path} — run 'spec-kitty migrate' to clean up. "
        f"Legacy resolution will be removed in the next major version."
    )
    logger.warning(msg)
    warnings.warn(msg, DeprecationWarning, stacklevel=3)


def _resolve_asset(
    name: str,
    subdir: str,
    project_dir: Path,
    mission: str = "software-dev",
) -> ResolutionResult:
    """Core 4-tier resolution logic shared by public helpers.

    Args:
        name: Filename to resolve (e.g. ``"plan.md"``).
        subdir: Subdirectory within each tier (``"templates"`` or
                ``"command-templates"``).
        project_dir: Root of the user project that contains ``.kittify/``.
        mission: Mission key used for tiers 3 (global) and 4 (package).

    Returns:
        ResolutionResult with the winning path, tier and mission.

    Raises:
        FileNotFoundError: If no tier provides the requested asset.
    """
    kittify = project_dir / ".kittify"

    # Tier 1 -- override
    override = kittify / "overrides" / subdir / name
    if override.is_file():
        return ResolutionResult(path=override, tier=ResolutionTier.OVERRIDE, mission=mission)

    # Tier 2 -- legacy
    legacy = kittify / subdir / name
    if legacy.is_file():
        _warn_legacy_asset(legacy)
        return ResolutionResult(path=legacy, tier=ResolutionTier.LEGACY, mission=mission)

    # Tier 3 -- global (~/.kittify/missions/{mission}/...)
    try:
        global_home = get_kittify_home()
        global_path = global_home / "missions" / mission / subdir / name
        if global_path.is_file():
            return ResolutionResult(path=global_path, tier=ResolutionTier.GLOBAL, mission=mission)
    except RuntimeError:
        # Cannot determine home directory -- skip tier 3
        pass

    # Tier 4 -- package default
    try:
        pkg_missions = get_package_asset_root()
        pkg_path = pkg_missions / mission / subdir / name
        if pkg_path.is_file():
            return ResolutionResult(
                path=pkg_path, tier=ResolutionTier.PACKAGE_DEFAULT, mission=mission,
            )
    except FileNotFoundError:
        pass

    raise FileNotFoundError(
        f"Asset '{name}' not found in any resolution tier "
        f"(subdir={subdir!r}, mission={mission!r}, project={project_dir})"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_template(
    name: str,
    project_dir: Path,
    mission: str = "software-dev",
) -> ResolutionResult:
    """Resolve a template file through the 4-tier precedence chain.

    Checks (in order):
    1. .kittify/overrides/templates/{name}
    2. .kittify/templates/{name}  (legacy -- emits DeprecationWarning)
    3. ~/.kittify/missions/{mission}/templates/{name}
    4. <package>/missions/{mission}/templates/{name}

    Args:
        name: Template filename (e.g. ``"spec-template.md"``).
        project_dir: Project root containing ``.kittify/``.
        mission: Mission key (default ``"software-dev"``).

    Returns:
        ResolutionResult with the resolved path, tier, and mission.

    Raises:
        FileNotFoundError: If the template is not found at any tier.
    """
    return _resolve_asset(name, "templates", project_dir, mission)


def resolve_command(
    name: str,
    project_dir: Path,
    mission: str = "software-dev",
) -> ResolutionResult:
    """Resolve a command template through the 4-tier precedence chain.

    Checks (in order):
    1. .kittify/overrides/command-templates/{name}
    2. .kittify/command-templates/{name}  (legacy -- emits DeprecationWarning)
    3. ~/.kittify/missions/{mission}/command-templates/{name}
    4. <package>/missions/{mission}/command-templates/{name}

    Args:
        name: Command template filename (e.g. ``"plan.md"``).
        project_dir: Project root containing ``.kittify/``.
        mission: Mission key (default ``"software-dev"``).

    Returns:
        ResolutionResult with the resolved path, tier, and mission.

    Raises:
        FileNotFoundError: If the command template is not found at any tier.
    """
    return _resolve_asset(name, "command-templates", project_dir, mission)


def resolve_mission(
    name: str,
    project_dir: Path,
) -> ResolutionResult:
    """Resolve a mission.yaml through the 4-tier precedence chain.

    Checks (in order):
    1. .kittify/overrides/missions/{name}/mission.yaml
    2. .kittify/missions/{name}/mission.yaml  (legacy -- emits DeprecationWarning)
    3. ~/.kittify/missions/{name}/mission.yaml
    4. <package>/missions/{name}/mission.yaml

    Args:
        name: Mission key (e.g. ``"software-dev"``).
        project_dir: Project root containing ``.kittify/``.

    Returns:
        ResolutionResult with the resolved path, tier, and mission.

    Raises:
        FileNotFoundError: If the mission config is not found at any tier.
    """
    kittify = project_dir / ".kittify"
    filename = "mission.yaml"

    # Tier 1 -- override
    override = kittify / "overrides" / "missions" / name / filename
    if override.is_file():
        return ResolutionResult(path=override, tier=ResolutionTier.OVERRIDE, mission=name)

    # Tier 2 -- legacy
    legacy = kittify / "missions" / name / filename
    if legacy.is_file():
        _warn_legacy_asset(legacy)
        return ResolutionResult(path=legacy, tier=ResolutionTier.LEGACY, mission=name)

    # Tier 3 -- global
    try:
        global_home = get_kittify_home()
        global_path = global_home / "missions" / name / filename
        if global_path.is_file():
            return ResolutionResult(path=global_path, tier=ResolutionTier.GLOBAL, mission=name)
    except RuntimeError:
        pass

    # Tier 4 -- package default
    try:
        pkg_missions = get_package_asset_root()
        pkg_path = pkg_missions / name / filename
        if pkg_path.is_file():
            return ResolutionResult(path=pkg_path, tier=ResolutionTier.PACKAGE_DEFAULT, mission=name)
    except FileNotFoundError:
        pass

    raise FileNotFoundError(
        f"Mission '{name}' config not found in any resolution tier "
        f"(project={project_dir})"
    )
