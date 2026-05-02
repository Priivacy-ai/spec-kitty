"""Classifier for handoff/events.jsonl mission artifacts."""

from __future__ import annotations

from pathlib import Path

from ..models import MissionFinding
from .mission_events import _classify_jsonl_file


def classify_handoff_events_jsonl(mission_dir: Path) -> list[MissionFinding]:
    """Classify handoff/events.jsonl for legacy keys, forbidden keys, and corruption.

    Args:
        mission_dir: Path to the mission directory.

    Returns:
        A list of :class:`~specify_cli.audit.models.MissionFinding` objects.
        Returns ``[]`` when the file is absent.
    """
    path = mission_dir / "handoff" / "events.jsonl"
    return _classify_jsonl_file(path, "handoff/events.jsonl", "handoff_event_row")
