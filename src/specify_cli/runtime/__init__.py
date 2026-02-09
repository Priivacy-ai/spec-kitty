"""Global runtime management for spec-kitty.

This subpackage manages the user-global ~/.kittify/ directory,
including path resolution, asset discovery, and runtime bootstrapping.
"""

from specify_cli.runtime.bootstrap import ensure_runtime
from specify_cli.runtime.home import get_kittify_home, get_package_asset_root
from specify_cli.runtime.resolver import (
    ResolutionResult,
    ResolutionTier,
    resolve_command,
    resolve_mission,
    resolve_template,
)
from specify_cli.runtime.migrate import (
    AssetDisposition,
    MigrationReport,
    classify_asset,
    execute_migration,
)

__all__ = [
    "AssetDisposition",
    "MigrationReport",
    "ResolutionResult",
    "ResolutionTier",
    "classify_asset",
    "ensure_runtime",
    "execute_migration",
    "get_kittify_home",
    "get_package_asset_root",
    "resolve_command",
    "resolve_mission",
    "resolve_template",
]
