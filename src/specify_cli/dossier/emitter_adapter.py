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
        project_context: ProjectSyncContext,
        project_unit: ProjectUnitOfWork,
        project_layout: LayoutGenerationAuthority,
    ) -> dict[str, Any]

Registration is expected to happen once at sync package init. Calling
register_dossier_emitter again replaces the existing callable
(idempotent re-registration).

Production wiring of the registration lives in WP02 (sync init).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from specify_cli.sync.layout_generation import LayoutGenerationAuthority
    from specify_cli.sync.project_context import ProjectSyncContext
    from specify_cli.sync.project_store import ProjectUnitOfWork

logger = logging.getLogger(__name__)


class DossierEmitterCallable(Protocol):
    """Explicit-context local dossier capture seam registered by sync."""

    def __call__(
        self,
        *,
        event_type: str,
        aggregate_id: str,
        aggregate_type: str,
        payload: dict[str, Any],
        project_context: ProjectSyncContext,
        project_unit: ProjectUnitOfWork,
        project_layout: LayoutGenerationAuthority,
    ) -> dict[str, Any]: ...


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
    project_context: ProjectSyncContext | None = None,
    project_unit: ProjectUnitOfWork | None = None,
    project_layout: LayoutGenerationAuthority | None = None,
) -> dict[str, Any] | None:
    """Emit a dossier event via the registered emitter.

    Returns the event dict on success. Returns None when no emitter is
    registered, no valid explicit context is supplied, or the emitter raises
    (the latter two are logged at WARNING). Never re-raises to the caller.
    """
    if project_context is None or project_unit is None or project_layout is None:
        logger.warning(
            "Dossier event %s withheld: no explicit same-UoW project authority was supplied",
            event_type,
        )
        return None
    from specify_cli.sync.project_context import (
        validate_project_sync_context_authority,
    )

    try:
        validate_project_sync_context_authority(project_context)
        if project_unit.store_identity is not project_context.store_identity:
            raise ValueError("dossier project unit does not match the explicit project context")
    except (TypeError, ValueError):
        logger.warning(
            "Dossier event %s withheld: project context authority is invalid",
            event_type,
            exc_info=True,
        )
        return None
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
            project_context=project_context,
            project_unit=project_unit,
            project_layout=project_layout,
        )
    except Exception:
        logger.warning(
            "Registered dossier emitter raised for %s; event dropped",
            event_type,
            exc_info=True,
        )
        return None
