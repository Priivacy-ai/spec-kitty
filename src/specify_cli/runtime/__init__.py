"""Global runtime management for spec-kitty.

This subpackage manages the user-global ~/.kittify/ directory,
including path resolution, asset discovery, and runtime bootstrapping.
"""

from specify_cli.runtime.bootstrap import check_version_pin
from specify_cli.runtime.home import get_kittify_home, get_package_asset_root
from specify_cli.runtime.resolver import (
    ResolutionResult,
    ResolutionTier,
    resolve_command,
    resolve_mission,
    resolve_template,
)
from specify_cli.runtime.show_origin import OriginEntry, collect_origins

__all__ = [
    "OriginEntry",
    "ResolutionResult",
    "ResolutionTier",
    "check_version_pin",
    "collect_origins",
    "get_kittify_home",
    "get_package_asset_root",
    "resolve_command",
    "resolve_mission",
    "resolve_template",
]
