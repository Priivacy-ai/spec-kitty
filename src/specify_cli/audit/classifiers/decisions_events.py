"""Classifier for decisions/events.jsonl mission artifacts."""

from __future__ import annotations

from pathlib import Path

from ..models import MissionFinding
from .mission_events import _classify_jsonl_file


def classify_decisions_events_jsonl(mission_dir: Path) -> list[MissionFinding]:
    """Classify decisions/events.jsonl for legacy keys, forbidden keys, and corruption.

    Args:
        mission_dir: Path to the mission directory.

    Returns:
        A list of :class:`~specify_cli.audit.models.MissionFinding` objects.
        Returns ``[]`` when the file is absent.
    """
    path = mission_dir / "decisions" / "events.jsonl"
    return _classify_jsonl_file(path, "decisions/events.jsonl", "decision_event_row")
