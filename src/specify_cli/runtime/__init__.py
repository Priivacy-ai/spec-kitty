"""Global runtime management for spec-kitty.

This subpackage manages the user-global ~/.kittify/ directory,
including path resolution, asset discovery, and runtime bootstrapping.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MODULES = {
    "AssetDisposition": "specify_cli.runtime.migrate",
    "MigrationReport": "specify_cli.runtime.migrate",
    "OriginEntry": "specify_cli.runtime.show_origin",
    "ResolutionResult": "specify_cli.runtime.resolver",
    "ResolutionTier": "specify_cli.runtime.resolver",
    "check_version_pin": "specify_cli.runtime.bootstrap",
    "classify_asset": "specify_cli.runtime.migrate",
    "collect_origins": "specify_cli.runtime.show_origin",
    "ensure_runtime": "specify_cli.runtime.bootstrap",
    "execute_migration": "specify_cli.runtime.migrate",
    "get_kittify_home": "specify_cli.runtime.home",
    "get_package_asset_root": "specify_cli.runtime.home",
    "resolve_command": "specify_cli.runtime.resolver",
    "resolve_mission": "specify_cli.runtime.resolver",
    "resolve_template": "specify_cli.runtime.resolver",
}


def __getattr__(name: str) -> Any:
    """Lazily resolve package re-exports without importing all runtime helpers."""
    try:
        module_name = _EXPORT_MODULES[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value

__all__ = [
    "AssetDisposition",
    "MigrationReport",
    "OriginEntry",
    "ResolutionResult",
    "ResolutionTier",
    "check_version_pin",
    "classify_asset",
    "collect_origins",
    "ensure_runtime",
    "execute_migration",
    "get_kittify_home",
    "get_package_asset_root",
    "resolve_command",
    "resolve_mission",
    "resolve_template",
]
