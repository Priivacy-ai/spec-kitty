"""Global runtime management for spec-kitty.

This subpackage manages the user-global ~/.kittify/ directory,
including path resolution, asset discovery, and runtime bootstrapping.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_BOOTSTRAP_MODULE = "specify_cli.runtime.bootstrap"
_HOME_MODULE = "specify_cli.runtime.home"
_MIGRATE_MODULE = "specify_cli.runtime.migrate"
_RESOLVER_MODULE = "specify_cli.runtime.resolver"
_SHOW_ORIGIN_MODULE = "specify_cli.runtime.show_origin"

_EXPORT_MODULES = {
    "AssetDisposition": _MIGRATE_MODULE,
    "MigrationReport": _MIGRATE_MODULE,
    "OriginEntry": _SHOW_ORIGIN_MODULE,
    "ResolutionResult": _RESOLVER_MODULE,
    "ResolutionTier": _RESOLVER_MODULE,
    "check_version_pin": _BOOTSTRAP_MODULE,
    "classify_asset": _MIGRATE_MODULE,
    "collect_origins": _SHOW_ORIGIN_MODULE,
    "ensure_runtime": _BOOTSTRAP_MODULE,
    "execute_migration": _MIGRATE_MODULE,
    "get_kittify_home": _HOME_MODULE,
    "get_package_asset_root": _HOME_MODULE,
    "resolve_command": _RESOLVER_MODULE,
    "resolve_mission": _RESOLVER_MODULE,
    "resolve_template": _RESOLVER_MODULE,
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
