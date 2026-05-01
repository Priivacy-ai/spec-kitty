"""Adapter for emitting dossier events without importing the sync package.

Inverts the dossier→sync edge for emitter access. The sync package
registers an emitter callable at its own initialization time; dossier
calls fire_dossier_event(...) which routes through the registered
callable. If no callable is registered, fire_dossier_event returns
None (silent drop).

The registered callable must accept these keyword arguments and return
the constructed event dict::

    callable(
        event_type: str,
        aggregate_id: str,
        aggregate_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]

Registration is expected to happen once at sync package init. Calling
register_dossier_emitter again replaces the existing callable
(idempotent re-registration).

Production wiring of the registration lives in WP02 (sync init).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

DossierEmitterCallable = Callable[..., dict[str, Any]]

_emitter: DossierEmitterCallable | None = None


def register_dossier_emitter(emitter: DossierEmitterCallable) -> None:
    """Register the dossier event emitter callable.

    Called once at sync package startup. Subsequent calls replace the
    registered callable (idempotent re-registration).
    """
    global _emitter
    _emitter = emitter


def reset_dossier_emitter() -> None:
    """Clear the registered emitter (test-only utility)."""
    global _emitter
    _emitter = None


def fire_dossier_event(
    *,
    event_type: str,
    aggregate_id: str,
    aggregate_type: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    """Emit a dossier event via the registered emitter.

    Returns the event dict on success. Returns None when no emitter is
    registered or the emitter raises (the latter is logged at WARNING).
    Never re-raises to the caller.
    """
    if _emitter is None:
        logger.debug(
            "No dossier emitter registered; dossier event %s dropped",
            event_type,
        )
        return None
    try:
        return _emitter(
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            payload=payload,
        )
    except Exception:
        logger.warning(
            "Registered dossier emitter raised for %s; event dropped",
            event_type,
            exc_info=True,
        )
        return None
