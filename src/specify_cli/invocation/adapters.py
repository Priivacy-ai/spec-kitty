"""Invocation adapter registry for the SaaS-client seam.

Provides a decoupled factory boundary so that invocation/propagator.py does
not need to depend on any concrete transport. The dispatch function is
non-raising, and its degradation is safe by construction: :func:`get_saas_client`
degrades to ``None``, which means "no transport" — nothing can leave, so
absence is safe.

(The former egress-consent seam here retired with the sync transport,
issue #5: its only production registrant was the deleted consent chain.)

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


def register_saas_client_factory(
    fn: Callable[[Path], Any | None],
) -> None:
    """Register the SaaS-client factory (idempotent by qualified name).

    Nothing registers a factory today (#3030 FR-032) — the seam exists but
    is never called in production. See :func:`propagator._get_saas_client`
    for the canonical record of why this stays empty and the ``request_text``
    hazard a future registration would open. (No line range: the symbol is the
    durable anchor. An earlier draft cited ``propagator.py:70-83``, but the
    function begins at ``:58`` and nothing pins those numbers.)
    **Re-registration replaces the existing factory unconditionally.** Not "when
    the qualified name matches" — that was this docstring's last remaining false
    sentence, and FR-018 is precisely about not leaving one here. Both arms of the
    ``existing_key == new_key`` branch below assign ``fn``, so the comparison
    changes nothing but the control flow taken to reach the same assignment; a
    callable with a *different* ``__qualname__`` replaces the entry just as
    completely. The invariant that does hold is the one that matters: at most one
    factory is ever registered, so reloading ``specify_cli.sync`` cannot stack
    several.

    The dead comparison itself is left in place: it is pre-existing, identical in
    the sibling registrar above, and removing it from both is a behaviour-preserving
    simplification outside this mission's scope. Filed rather than folded — see the
    mission's follow-up record.
    """
    global _saas_client_factory  # noqa: PLW0603
    new_key = _callable_key(fn)
    if _saas_client_factory is not None:
        existing_key = _callable_key(_saas_client_factory)
        if existing_key == new_key:
            _saas_client_factory = fn
            return
    _saas_client_factory = fn


def get_saas_client(path: Path) -> Any | None:
    """Dispatch to the registered SaaS-client factory.

    Returns the factory's result, or ``None`` when:
    - no factory has been registered (safe-degrade on missing sync package), or
    - the registered factory raises any exception.

    Never raises.

    **No production code registers a factory today** (#3030 FR-032), so in a real
    process this is the first branch, every time. The ``sync`` package used to
    register one whose entire body read ``token_manager._ws_client`` — an attribute
    nothing in ``src/`` assigns — making it a ``None``-returning phantom; it was
    deleted rather than wired up, because wiring it would have turned three egress
    paths live at once in the middle of a confidentiality incident. The slot survives
    as the seam a real transport would be registered into; whoever does that owns
    proving the consent gate above each consumer holds.
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
    """Clear the registered slot (test-only utility).

    Call only from test teardown to prevent state bleed between tests.
    Production code must never call this.
    """
    global _saas_client_factory  # noqa: PLW0603
    _saas_client_factory = None
