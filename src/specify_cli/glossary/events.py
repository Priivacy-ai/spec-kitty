"""Event emission adapters (WP08).

This module provides stub implementations for event emission.
Full implementation will be completed in WP08 (orchestrator integration).

WP07 adds:
- emit_step_checkpointed(): Persist checkpoint state before generation gate blocks.
"""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, List

if TYPE_CHECKING:
    from .checkpoint import StepCheckpoint
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


def emit_step_checkpointed(
    checkpoint: "StepCheckpoint",
    project_root: Path | None = None,
) -> None:
    """Emit StepCheckpointed event to event log.

    Persists checkpoint state before the generation gate blocks execution.
    This is a stub for WP07. Full event infrastructure in WP08 via
    spec-kitty-events.

    The checkpoint is serialized to JSONL and appended to the glossary
    checkpoint event log at .kittify/events/glossary/checkpoints.jsonl.

    Args:
        checkpoint: Checkpoint state to persist
        project_root: Repository root for event log storage. If None,
                      only logs (useful for testing without filesystem).

    Note:
        When WP08 is complete, this will emit a proper event with:
        - event_type: "StepCheckpointed"
        - checkpoint payload (mission/run/step IDs, hash, cursor, etc.)
        - timestamp: event timestamp
    """
    from .checkpoint import checkpoint_to_dict

    payload = checkpoint_to_dict(checkpoint)

    logger.info(
        "Checkpoint emitted: step=%s, cursor=%s, hash=%s...",
        checkpoint.step_id,
        checkpoint.cursor,
        checkpoint.input_hash[:8],
    )

    if project_root is not None:
        events_dir = project_root / ".kittify" / "events" / "glossary"
        events_dir.mkdir(parents=True, exist_ok=True)
        events_file = events_dir / "checkpoints.jsonl"

        with events_file.open("a") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")
