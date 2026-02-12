"""5-tier asset resolution: override > legacy > global-mission > global > package default.

Resolution tiers (checked in order):
1. OVERRIDE        -- .kittify/overrides/{templates,command-templates}/
2. LEGACY          -- .kittify/{templates,command-templates}/ (deprecated; emits warning)
3. GLOBAL_MISSION  -- ~/.kittify/missions/{mission}/{templates,command-templates}/
4. GLOBAL          -- ~/.kittify/{templates,command-templates}/
5. PACKAGE         -- src/specify_cli/missions/{mission}/{templates,command-templates}/

After ``spec-kitty migrate`` has been run (i.e. ``~/.kittify/`` is
populated), legacy-tier warnings are suppressed.  Pre-migration projects
receive a single "run ``spec-kitty migrate``" nudge per CLI invocation.
"""

from __future__ import annotations

import logging
import sys
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
    GLOBAL_MISSION = "global_mission"
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

def _is_global_runtime_configured() -> bool:
    """Return True if ``~/.kittify/`` has been populated by ``ensure_runtime``.

    The presence of ``cache/version.lock`` is the authoritative indicator
    that the global runtime has been bootstrapped at least once.  This
    avoids false positives from an empty ``~/.kittify/`` directory.
    """
    try:
        home = get_kittify_home()
        return (home / "cache" / "version.lock").is_file()
    except RuntimeError:
        return False


# Module-level flag: ensures the migrate nudge is emitted at most once per
# CLI invocation (not per resolution call).
_migrate_nudge_shown = False


def _warn_legacy_asset(path: Path) -> None:
    """Emit a deprecation warning for a legacy-tier asset hit.

    When the global runtime is already configured (``~/.kittify/`` has
    ``cache/version.lock``), the warning is suppressed because the user
    simply hasn't run ``spec-kitty migrate`` for this *project* yet.
    Instead, a one-time stderr nudge is printed.
    """
    if _is_global_runtime_configured():
        # Global runtime exists — suppress noisy DeprecationWarning, emit
        # a single one-time nudge to stderr instead.
        _emit_migrate_nudge()
        return

    msg = (
        f"Legacy asset resolved: {path} — run 'spec-kitty migrate' to clean up. "
        f"Legacy resolution will be removed in the next major version."
    )
    logger.warning(msg)
    warnings.warn(msg, DeprecationWarning, stacklevel=3)


def _emit_migrate_nudge() -> None:
    """Print a one-time "run ``spec-kitty migrate``" message to stderr.

    Uses a module-level flag so the nudge appears at most once per CLI
    invocation regardless of how many assets are resolved.  Output goes
    to stderr so it never interferes with ``--json`` output on stdout.
    """
    global _migrate_nudge_shown  # noqa: PLW0603
    if _migrate_nudge_shown:
        return
    _migrate_nudge_shown = True
    print(
        "Note: Run `spec-kitty migrate` to clean up legacy project files "
        "and use the global runtime (~/.kittify/).",
        file=sys.stderr,
    )


def _reset_migrate_nudge() -> None:
    """Reset the one-time nudge flag (for testing only)."""
    global _migrate_nudge_shown  # noqa: PLW0603
    _migrate_nudge_shown = False


def _resolve_asset(
    name: str,
    subdir: str,
    project_dir: Path,
    mission: str = "software-dev",
) -> ResolutionResult:
    """Core 5-tier resolution logic shared by public helpers.

    Args:
        name: Filename to resolve (e.g. ``"plan.md"``).
        subdir: Subdirectory within each tier (``"templates"`` or
                ``"command-templates"``).
        project_dir: Root of the user project that contains ``.kittify/``.
        mission: Mission key used for tiers 3-5.

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

    # Tier 3 -- global mission-specific (~/.kittify/missions/{mission}/...)
    try:
        global_home = get_kittify_home()

        global_mission_path = global_home / "missions" / mission / subdir / name
        if global_mission_path.is_file():
            return ResolutionResult(
                path=global_mission_path, tier=ResolutionTier.GLOBAL_MISSION, mission=mission,
            )

        # Tier 4 -- global non-mission (~/.kittify/{subdir}/{name})
        global_path = global_home / subdir / name
        if global_path.is_file():
            return ResolutionResult(path=global_path, tier=ResolutionTier.GLOBAL, mission=mission)
    except RuntimeError:
        # Cannot determine home directory -- skip tiers 3 and 4
        pass

    # Tier 5 -- package default
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
    """Resolve a template file through the 5-tier precedence chain.

    Checks (in order):
    1. .kittify/overrides/templates/{name}
    2. .kittify/templates/{name}  (legacy -- emits warning/nudge)
    3. ~/.kittify/missions/{mission}/templates/{name}
    4. ~/.kittify/templates/{name}
    5. <package>/missions/{mission}/templates/{name}

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
    """Resolve a command template through the 5-tier precedence chain.

    Checks (in order):
    1. .kittify/overrides/command-templates/{name}
    2. .kittify/command-templates/{name}  (legacy -- emits warning/nudge)
    3. ~/.kittify/missions/{mission}/command-templates/{name}
    4. ~/.kittify/command-templates/{name}
    5. <package>/missions/{mission}/command-templates/{name}

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
    """Resolve a mission.yaml through the precedence chain.

    Checks (in order):
    1. .kittify/overrides/missions/{name}/mission.yaml
    2. .kittify/missions/{name}/mission.yaml  (legacy -- emits warning/nudge)
    3. ~/.kittify/missions/{name}/mission.yaml
    4. <package>/missions/{name}/mission.yaml

    Note: missions are inherently mission-scoped, so there is no separate
    "global non-mission" tier for mission configs.

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

    # Tier 3 -- global (missions are inherently mission-scoped)
    try:
        global_home = get_kittify_home()
        global_path = global_home / "missions" / name / filename
        if global_path.is_file():
            return ResolutionResult(path=global_path, tier=ResolutionTier.GLOBAL_MISSION, mission=name)
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
