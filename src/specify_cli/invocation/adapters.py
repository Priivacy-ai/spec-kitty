"""Invocation adapter registry for sync-routing and SaaS-client seams.

Provides a decoupled resolver boundary so that invocation/propagator.py
does not need to depend on the sync package.  The sync package registers
its concrete implementations at startup; sync -> invocation.adapters is
the clean dependency direction.

All dispatch functions are non-raising: when no implementation is
registered, or when a registered implementation raises, the function
returns ``None`` (safe-degrade).  An unregistered registry is a no-op.

Mirrors the ``status/adapters.py`` idiom (C-007, FR-008).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Single-slot registries — the sync package registers one concrete
# implementation per slot at startup.  Using ``None`` as the sentinel
# means "no implementation registered" which is the correct initial
# state for CORE modules that are loaded before INTEGRATION packages.
_sync_routing_resolver: Callable[[Path], bool | None] | None = None
_saas_client_factory: Callable[[Path], Any | None] | None = None


def _callable_key(fn: Callable[..., Any]) -> str:
    """Return a stable identity key for a registered callable.

    Uses ``__module__`` + ``__qualname__`` (falling back to ``__name__``)
    so that the same logical callable is treated as identical across
    module reloads that produce fresh function objects.
    """
    module = getattr(fn, "__module__", None)
    qualname = getattr(fn, "__qualname__", None)
    name = qualname if isinstance(qualname, str) else getattr(fn, "__name__", None)
    if isinstance(module, str) and isinstance(name, str):
        return f"{module}.{name}"
    if isinstance(name, str):
        return name
    return repr(fn)


def register_sync_routing_resolver(
    fn: Callable[[Path], bool | None],
) -> None:
    """Register the sync-routing resolver (idempotent by qualified name).

    Called once at sync package startup.  Re-registration of a callable
    with the same ``__qualname__`` replaces the existing entry, so that
    re-importing or reloading ``specify_cli.sync`` (e.g. in test
    processes) is safe and does not stack multiple resolvers.
    Not thread-safe by design (registration runs before concurrent
    access begins).
    """
    global _sync_routing_resolver  # noqa: PLW0603
    new_key = _callable_key(fn)
    if _sync_routing_resolver is not None:
        existing_key = _callable_key(_sync_routing_resolver)
        if existing_key == new_key:
            _sync_routing_resolver = fn
            return
    _sync_routing_resolver = fn


def register_saas_client_factory(
    fn: Callable[[Path], Any | None],
) -> None:
    """Register the SaaS-client factory (idempotent by qualified name).

    Called once at sync package startup.  Re-registration replaces the
    existing factory when the qualified name matches.
    """
    global _saas_client_factory  # noqa: PLW0603
    new_key = _callable_key(fn)
    if _saas_client_factory is not None:
        existing_key = _callable_key(_saas_client_factory)
        if existing_key == new_key:
            _saas_client_factory = fn
            return
    _saas_client_factory = fn


def resolve_sync_routing(path: Path) -> bool | None:
    """Dispatch to the registered sync-routing resolver.

    Returns the resolver's result, or ``None`` when:
    - no resolver has been registered (safe-degrade on missing sync package), or
    - the registered resolver raises any exception.

    Never raises.
    """
    if _sync_routing_resolver is None:
        return None
    try:
        return _sync_routing_resolver(path)
    except Exception:  # noqa: BLE001
        logger.debug(
            "sync-routing resolver raised; safe-degrading to None",
            exc_info=True,
        )
        return None


def get_saas_client(path: Path) -> Any | None:
    """Dispatch to the registered SaaS-client factory.

    Returns the factory's result, or ``None`` when:
    - no factory has been registered (safe-degrade on missing sync package), or
    - the registered factory raises any exception.

    Never raises.
    """
    if _saas_client_factory is None:
        return None
    try:
        return _saas_client_factory(path)
    except Exception:  # noqa: BLE001
        logger.debug(
            "SaaS-client factory raised; safe-degrading to None",
            exc_info=True,
        )
        return None


def reset_adapters() -> None:
    """Clear both registered slots (test-only utility).

    Call only from test teardown to prevent state bleed between tests.
    Production code must never call this.
    """
    global _sync_routing_resolver, _saas_client_factory  # noqa: PLW0603
    _sync_routing_resolver = None
    _saas_client_factory = None
