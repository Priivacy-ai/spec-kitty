"""Event emission adapters (WP08).

This module provides stub implementations for event emission.
Full implementation will be completed in WP08 (orchestrator integration).
"""

import logging
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .models import SemanticConflict
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

    Note:
        When WP08 is complete, this will emit a proper event with:
        - event_type: "GenerationBlockedBySemanticConflict"
        - step_id: step identifier
        - mission_id: mission identifier
        - conflicts: serialized conflict details
        - strictness_mode: effective strictness setting
        - timestamp: event timestamp
    """
    # TODO (WP08): Import from spec_kitty_events.glossary.events
    # For now, just log
    logger.info(
        f"Generation blocked: {len(conflicts)} conflicts, "
        f"strictness={strictness_mode}, step={step_id}, mission={mission_id}"
    )
