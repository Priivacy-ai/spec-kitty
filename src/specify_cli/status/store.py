"""JSONL event store for status events.

Provides append-only persistence of StatusEvent records to a JSONL file
(status.events.jsonl). Each line is a JSON object with deterministic
(sorted) key ordering.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import StatusEvent

EVENTS_FILENAME = "status.events.jsonl"


class StoreError(Exception):
    """Raised when the event store encounters corruption or I/O errors."""


def _events_path(feature_dir: Path) -> Path:
    """Return the canonical path to the events JSONL file."""
    return feature_dir / EVENTS_FILENAME


def append_event(feature_dir: Path, event: StatusEvent) -> None:
    """Atomically append a StatusEvent as a single JSON line.

    Creates parent directories and the file if they do not exist.
    Uses ``sort_keys=True`` for deterministic key ordering.
    """
    path = _events_path(feature_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event.to_dict(), sort_keys=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def read_events_raw(feature_dir: Path) -> list[dict]:
    """Read raw JSON dicts from the events file.

    Returns an empty list when the file does not exist.
    Blank lines are silently skipped.
    Raises :class:`StoreError` on invalid JSON, including the 1-based
    line number in the message.
    """
    path = _events_path(feature_dir)
    if not path.exists():
        return []

    results: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_number, raw_line in enumerate(fh, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise StoreError(
                    f"Invalid JSON on line {line_number}: {exc}"
                ) from exc
            results.append(obj)
    return results


def read_events(feature_dir: Path) -> list[StatusEvent]:
    """Read and deserialize StatusEvent objects from the events file.

    Returns an empty list when the file does not exist.
    Blank lines are silently skipped.
    Raises :class:`StoreError` on invalid JSON **or** invalid event
    structure, including the 1-based line number in the message.
    """
    path = _events_path(feature_dir)
    if not path.exists():
        return []

    results: list[StatusEvent] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_number, raw_line in enumerate(fh, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise StoreError(
                    f"Invalid JSON on line {line_number}: {exc}"
                ) from exc
            try:
                event = StatusEvent.from_dict(obj)
            except (KeyError, ValueError, TypeError) as exc:
                raise StoreError(
                    f"Invalid event structure on line {line_number}: {exc}"
                ) from exc
            results.append(event)
    return results
