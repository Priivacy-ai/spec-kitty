"""Event emission adapters (WP08).

This module provides stub implementations for event emission.
Full implementation will be completed in WP08 (orchestrator integration).

WP06 adds: GlossaryClarificationRequested, GlossaryClarificationResolved,
GlossarySenseUpdated event stubs.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .models import SemanticConflict, TermSense
    from .strictness import Strictness

logger = logging.getLogger(__name__)


def emit_generation_blocked_event(
    step_id: str,
    mission_id: str,
    conflicts: List["SemanticConflict"],
    strictness_mode: "Strictness",
) -> None:
    """Emit GenerationBlockedBySemanticConflict event.

    This is a stub for WP05. Full implementation in WP08.

    Args:
        step_id: ID of the step being executed
        mission_id: ID of the mission containing the step
        conflicts: List of conflicts that caused blocking
        strictness_mode: The effective strictness mode
    """
    logger.info(
        "Generation blocked: %d conflicts, strictness=%s, step=%s, mission=%s",
        len(conflicts),
        strictness_mode,
        step_id,
        mission_id,
    )


def emit_clarification_requested(
    conflict_id: str,
    question: str,
    term: str,
    options: List[str],
    urgency: str,
    step_id: str,
    mission_id: str,
    run_id: str,
    timestamp: datetime,
) -> None:
    """Emit GlossaryClarificationRequested event (stub for WP06).

    Emitted when a conflict is deferred to async resolution.
    Full implementation in WP08.

    Args:
        conflict_id: Unique conflict identifier
        question: The clarification question
        term: The ambiguous term
        options: Ranked candidate definitions
        urgency: Severity/urgency of the conflict
        step_id: Step that triggered the conflict
        mission_id: Mission containing the step
        run_id: Current run identifier
        timestamp: Event timestamp
    """
    logger.info(
        "Clarification requested: term=%s, urgency=%s, options=%d",
        term,
        urgency,
        len(options),
    )


def emit_clarification_resolved(
    conflict_id: str,
    term_surface: str,
    selected_sense: "TermSense",
    actor_id: str,
    timestamp: datetime,
    resolution_mode: str,
) -> None:
    """Emit GlossaryClarificationResolved event (stub for WP06).

    Emitted when a user selects a candidate sense to resolve a conflict.
    Full implementation in WP08.

    Args:
        conflict_id: Unique conflict identifier
        term_surface: The resolved term's surface text
        selected_sense: The TermSense selected by the user
        actor_id: Who resolved it (e.g. "user:alice")
        timestamp: Event timestamp
        resolution_mode: "interactive" or "async"
    """
    logger.info(
        "Clarification resolved: term=%s, mode=%s",
        term_surface,
        resolution_mode,
    )


def emit_sense_updated(
    term_surface: str,
    scope: str,
    new_sense: "TermSense",
    actor_id: str,
    timestamp: datetime,
    update_type: str,
) -> None:
    """Emit GlossarySenseUpdated event (stub for WP06).

    Emitted when a user provides a custom sense definition.
    Full implementation in WP08.

    Args:
        term_surface: The term's surface text
        scope: Glossary scope (e.g. "team_domain")
        new_sense: The newly created TermSense
        actor_id: Who created it
        timestamp: Event timestamp
        update_type: "create" or "update"
    """
    logger.info(
        "Sense updated: term=%s, scope=%s, type=%s",
        term_surface,
        scope,
        update_type,
    )
