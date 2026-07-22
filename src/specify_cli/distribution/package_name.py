"""Resolve the installed CLI distribution package name.

Precedence (never controlled by a runtime env var for the distribution name):

1. ``spec_kitty.cli_package`` entry point (string, zero-arg callable → str, or
   object with ``package_name`` / ``name``)
2. Distribution owning the ``specify_cli`` import package via
   ``packages_distributions``
3. Default ``spec-kitty-cli``
"""

from __future__ import annotations

from importlib.metadata import EntryPoint, entry_points, packages_distributions

__all__ = [
    "CLI_PACKAGE_GROUP",
    "DEFAULT_CLI_PACKAGE_NAME",
    "IMPORT_PACKAGE_NAME",
    "clear_cli_package_name_cache",
    "resolve_cli_package_name",
]

CLI_PACKAGE_GROUP = "spec_kitty.cli_package"
DEFAULT_CLI_PACKAGE_NAME = "spec-kitty-cli"
IMPORT_PACKAGE_NAME = "specify_cli"

_cached_name: str | None = None


def clear_cli_package_name_cache() -> None:
    """Clear the process-level memo (tests only)."""
    global _cached_name
    _cached_name = None


def resolve_cli_package_name() -> str:
    """Return the CLI distribution name. Never raises."""
    global _cached_name
    if _cached_name is not None:
        return _cached_name
    resolved = _resolve_cli_package_name_uncached()
    _cached_name = resolved
    return resolved


def _resolve_cli_package_name_uncached() -> str:
    try:
        discovered = list(entry_points(group=CLI_PACKAGE_GROUP))
    except Exception:
        discovered = []

    selected = _select_entry_point(discovered)
    if selected is not None:
        name = _name_from_entry_point(selected)
        if name:
            return name

    owning = _name_from_packages_distributions()
    if owning:
        return owning

    return DEFAULT_CLI_PACKAGE_NAME


def _select_entry_point(discovered: list[EntryPoint]) -> EntryPoint | None:
    if not discovered:
        return None
    if len(discovered) == 1:
        return discovered[0]
    return sorted(discovered, key=lambda entry: entry.name)[0]


def _name_from_entry_point(entry: EntryPoint) -> str | None:
    try:
        loaded = entry.load()
    except Exception:
        return None

    try:
        if isinstance(loaded, str):
            return loaded.strip() or None
        if callable(loaded) and not isinstance(loaded, type):
            value = loaded()
            if isinstance(value, str) and value.strip():
                return value.strip()
        if isinstance(loaded, type):
            instance = loaded()
            return _name_from_object(instance)
        return _name_from_object(loaded)
    except Exception:
        return None


def _name_from_object(obj: object) -> str | None:
    for attr in ("package_name", "name"):
        value = getattr(obj, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _name_from_packages_distributions() -> str | None:
    try:
        mapping = packages_distributions()
    except Exception:
        return None
    names = mapping.get(IMPORT_PACKAGE_NAME) or []
    for name in names:
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None
