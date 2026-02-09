"""Provisional emit_event interface for mission event logging.

This is a Phase 1B provisional interface. Phase 2 will replace the JSONL
backend with a proper event store. Events are written to
``<feature_dir>/mission-events.jsonl``, one JSON object per line.

Key design constraints:
- emit_event failures log a warning but NEVER raise or block.
- Single-process CLI -- no file locking needed, use append mode.
- Keep interface minimal; do not add features Phase 2 won't need.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

MISSION_EVENTS_FILE = "mission-events.jsonl"


def emit_event(
    event_type: str,
    payload: dict,
    mission_name: str = "",
    feature_dir: Path | None = None,
) -> None:
    """Emit a mission event to the local JSONL log.

    This is a provisional interface for Phase 1B. Phase 2 will replace
    the backend with a proper event store.

    Args:
        event_type: Event type (e.g., "phase_entered", "guard_failed").
        payload: Event-specific data.
        mission_name: Name of the mission.
        feature_dir: Feature directory for the JSONL file location.
            If ``None``, the event is not persisted (debug-logged only).
    """
    event = {
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mission": mission_name,
        "payload": payload,
    }

    if feature_dir is None:
        logger.debug("No feature_dir -- event not persisted: %s", event_type)
        return

    try:
        _write_event(feature_dir, event)
    except Exception:
        logger.warning("Failed to emit event: %s", event_type, exc_info=True)


def _write_event(feature_dir: Path, event: dict) -> None:
    """Append event as a JSON line to the mission events log."""
    events_file = feature_dir / MISSION_EVENTS_FILE
    line = json.dumps(event, sort_keys=True) + "\n"
    with open(events_file, "a", encoding="utf-8") as f:
        f.write(line)


def read_events(feature_dir: Path) -> list[dict]:
    """Read all events from the mission events log.

    Returns empty list if the log does not exist.

    Args:
        feature_dir: Feature directory containing the JSONL file.

    Returns:
        List of event dicts parsed from each JSONL line.
    """
    events_file = feature_dir / MISSION_EVENTS_FILE
    if not events_file.exists():
        return []

    events: list[dict] = []
    with open(events_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("Corrupt event line: %s", line[:100])
    return events
