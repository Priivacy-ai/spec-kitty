"""Fan-out adapter registry for status events.

Provides a decoupled callback boundary so that status/emit.py does not
need to depend on the sync package. The sync package registers its
handlers at startup; sync -> status.adapters is the clean dependency
direction.

All fire_* functions are non-raising: exceptions from individual
handlers are caught and logged, never re-raised to the caller. An empty
registry is a no-op.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Callback signature: (feature_dir, mission_slug, repo_root) -> None
DossierSyncHandler = Callable[[Path, str, Path], None]

# Callback signature: keyword-only, mirrors emit_wp_status_changed
SaasFanOutHandler = Callable[..., None]

_dossier_handlers: list[DossierSyncHandler] = []
_saas_handlers: list[SaasFanOutHandler] = []


def register_dossier_sync_handler(cb: DossierSyncHandler) -> None:
    """Register a dossier-sync callback.

    Called once at sync package startup. Not thread-safe by design
    (registration runs before concurrent access begins).
    """
    _dossier_handlers.append(cb)


def register_saas_fanout_handler(cb: SaasFanOutHandler) -> None:
    """Register a SaaS fan-out callback.

    Called once at sync package startup.
    """
    _saas_handlers.append(cb)


def reset_handlers() -> None:
    """Clear all registered handlers (test-only utility)."""
    _dossier_handlers.clear()
    _saas_handlers.clear()


def fire_dossier_sync(
    feature_dir: Path,
    mission_slug: str,
    repo_root: Path,
) -> None:
    """Call all registered dossier-sync handlers.

    Guarantees:
    - Handlers called in registration order.
    - Exceptions are caught per handler, logged at DEBUG level, and
      never propagate to the caller.
    - If no handlers are registered, this is a no-op.
    """
    for handler in _dossier_handlers:
        try:
            handler(feature_dir, mission_slug, repo_root)
        except Exception:
            logger.debug(
                "Dossier sync handler failed; never blocks status transitions",
                exc_info=True,
            )


def fire_saas_fanout(**kwargs: Any) -> None:
    """Call all registered SaaS fan-out handlers with **kwargs.

    Guarantees:
    - Handlers called in registration order.
    - Exceptions are caught per handler, logged at WARNING level, and
      never propagate to the caller.
    - If no handlers are registered, this is a no-op.
    """
    for handler in _saas_handlers:
        try:
            handler(**kwargs)
        except Exception:
            logger.warning(
                "SaaS fan-out handler failed; canonical status log unaffected",
                exc_info=True,
            )
