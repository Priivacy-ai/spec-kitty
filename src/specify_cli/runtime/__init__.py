"""Global runtime management for spec-kitty.

This subpackage manages the user-global ~/.kittify/ directory,
including path resolution, asset discovery, and runtime bootstrapping.
"""

from specify_cli.runtime.home import get_kittify_home, get_package_asset_root
from specify_cli.runtime.resolver import (
    ResolutionResult,
    ResolutionTier,
    resolve_command,
    resolve_mission,
    resolve_template,
)

__all__ = [
    "ResolutionResult",
    "ResolutionTier",
    "get_kittify_home",
    "get_package_asset_root",
    "resolve_command",
    "resolve_mission",
    "resolve_template",
]
