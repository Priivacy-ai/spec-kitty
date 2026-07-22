"""Resolve the active ``LatestVersionProvider`` via packager entry points.

Downstream packagers register under ``spec_kitty.upgrade_provider``. Stock
installs with no registrations use :class:`PyPIProvider`.

Resolution rules (every failure falls back to the built-in default; never
raises):

1. Discover entry points in the ``spec_kitty.upgrade_provider`` group.
2. If none are registered, return :class:`PyPIProvider`.
3. If exactly one is registered, load and return it.
4. If several are registered, select by ``SPEC_KITTY_UPGRADE_PROVIDER=<name>``;
   otherwise pick the first name alphabetically (deterministic).
"""

from __future__ import annotations

import os
from importlib.metadata import EntryPoint, entry_points
from typing import cast

from specify_cli.compat.provider import LatestVersionProvider, PyPIProvider

__all__ = [
    "PROVIDER_SELECT_ENV_VAR",
    "UPGRADE_PROVIDER_GROUP",
    "clear_upgrade_provider_cache",
    "resolve_upgrade_provider",
]

UPGRADE_PROVIDER_GROUP = "spec_kitty.upgrade_provider"
PROVIDER_SELECT_ENV_VAR = "SPEC_KITTY_UPGRADE_PROVIDER"

_cached_provider: LatestVersionProvider | None = None


def clear_upgrade_provider_cache() -> None:
    """Clear the process-level memo (tests only)."""
    global _cached_provider
    _cached_provider = None


def _default_provider() -> LatestVersionProvider:
    return PyPIProvider()


def _select_entry_point(discovered: list[EntryPoint]) -> EntryPoint | None:
    if not discovered:
        return None
    if len(discovered) == 1:
        return discovered[0]

    requested = (os.environ.get(PROVIDER_SELECT_ENV_VAR) or "").strip()
    if requested:
        for entry in discovered:
            if entry.name == requested:
                return entry

    return sorted(discovered, key=lambda entry: entry.name)[0]


def resolve_upgrade_provider() -> LatestVersionProvider:
    """Return the active upgrade-source provider. Never raises."""
    global _cached_provider
    if _cached_provider is not None:
        return _cached_provider
    provider = _resolve_upgrade_provider_uncached()
    _cached_provider = provider
    return provider


def _resolve_upgrade_provider_uncached() -> LatestVersionProvider:
    try:
        discovered = list(entry_points(group=UPGRADE_PROVIDER_GROUP))
    except Exception:
        return _default_provider()

    selected = _select_entry_point(discovered)
    if selected is None:
        return _default_provider()

    try:
        loaded = selected.load()
        provider = loaded() if callable(loaded) else loaded
    except Exception:
        return _default_provider()

    if not hasattr(provider, "get_latest"):
        return _default_provider()

    return cast(LatestVersionProvider, provider)
