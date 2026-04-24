"""Runtime asset resolver — thin delegation to charter.asset_resolver.

Routes resolve_template/resolve_command/resolve_mission through the charter
gateway while keeping ``get_kittify_home`` and ``get_package_asset_root``
bound as module-local attributes. Tests that ``patch`` those names against
this module continue to intercept every call because the resolve functions
read the attributes from the local module namespace at each invocation.

Re-exports ``ResolutionResult`` and ``ResolutionTier`` for callers that
import them from this module.
"""

from __future__ import annotations

import logging
import sys
import warnings
from pathlib import Path

from charter.asset_resolver import (
    ResolutionResult,
    ResolutionTier,
    resolve_command as _charter_resolve_command,
    resolve_mission as _charter_resolve_mission,
    resolve_template as _charter_resolve_template,
)
from runtime.discovery.home import get_kittify_home, get_package_asset_root

logger = logging.getLogger(__name__)

__all__ = [
    "ResolutionResult",
    "ResolutionTier",
    "get_kittify_home",
    "get_package_asset_root",
    "resolve_command",
    "resolve_mission",
    "resolve_template",
]

# Module-level flag: ensures the migrate nudge is emitted at most once per
# CLI invocation (not per resolution call).
_migrate_nudge_shown = False


def _is_global_runtime_configured() -> bool:
    """Return True if ``~/.kittify/`` has been populated by ``ensure_runtime``."""
    try:
        home = get_kittify_home()
        return (home / "cache" / "version.lock").is_file()
    except RuntimeError:
        return False


def _emit_migrate_nudge() -> None:
    """Print a one-time stderr nudge suggesting ``spec-kitty migrate``."""
    global _migrate_nudge_shown  # noqa: PLW0603
    if _migrate_nudge_shown:
        return
    _migrate_nudge_shown = True
    from kernel.paths import render_runtime_path

    runtime_display = render_runtime_path(get_kittify_home())
    print(
        "Note: Run `spec-kitty migrate` to clean up legacy project files and use the "
        f"global runtime ({runtime_display}).",
        file=sys.stderr,
    )


def _reset_migrate_nudge() -> None:
    """Reset the one-time nudge flag (tests only)."""
    global _migrate_nudge_shown  # noqa: PLW0603
    _migrate_nudge_shown = False


def _warn_legacy_asset(path: Path) -> None:
    """Emit a deprecation warning for a LEGACY-tier asset hit."""
    if _is_global_runtime_configured():
        _emit_migrate_nudge()
        return
    msg = (
        f"Legacy asset resolved: {path} — run 'spec-kitty migrate' to clean up. "
        "Legacy resolution will be removed in the next major version."
    )
    logger.warning(msg)
    # stacklevel=5 accounts for the charter-delegation chain:
    # 5: caller code
    # 4: runtime.discovery.resolver.resolve_{template,command,mission}
    # 3: charter.asset_resolver.resolve_{template,command,mission}
    # 2: charter.asset_resolver._resolve_asset  (invokes legacy_warn_hook)
    # 1: this function
    warnings.warn(msg, DeprecationWarning, stacklevel=5)


def resolve_template(
    name: str,
    project_dir: Path,
    mission: str = "software-dev",
) -> ResolutionResult:
    """Resolve a template file through the 5-tier precedence chain."""
    return _charter_resolve_template(
        name, project_dir, mission,
        home_provider=get_kittify_home,
        asset_root_provider=get_package_asset_root,
        legacy_warn_hook=_warn_legacy_asset,
    )


def resolve_command(
    name: str,
    project_dir: Path,
    mission: str = "software-dev",
) -> ResolutionResult:
    """Resolve a command template through the 5-tier precedence chain."""
    return _charter_resolve_command(
        name, project_dir, mission,
        home_provider=get_kittify_home,
        asset_root_provider=get_package_asset_root,
        legacy_warn_hook=_warn_legacy_asset,
    )


def resolve_mission(
    name: str,
    project_dir: Path,
) -> ResolutionResult:
    """Resolve a mission.yaml through the 4-tier precedence chain."""
    return _charter_resolve_mission(
        name, project_dir,
        home_provider=get_kittify_home,
        asset_root_provider=get_package_asset_root,
        legacy_warn_hook=_warn_legacy_asset,
    )
