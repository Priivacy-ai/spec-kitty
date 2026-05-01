"""Helpers for semantically merging append-only status event logs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class EventLogMergeError(Exception):
    """Raised when an event-log merge cannot be completed safely."""


def _read_event_file(path: Path) -> list[dict[str, Any]]:
    """Read a status.events.jsonl-style file from an arbitrary path."""
    if not path.exists():
        return []

    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise EventLogMergeError(f"{path}: invalid JSON on line {line_number}: {exc}") from exc
            if not isinstance(payload, dict):
                raise EventLogMergeError(f"{path}: line {line_number} is not a JSON object")
            event_id = payload.get("event_id")
            at = payload.get("at")
            if not isinstance(event_id, str) or not event_id.strip():
                raise EventLogMergeError(f"{path}: line {line_number} is missing a valid event_id")
            if not isinstance(at, str) or not at.strip():
                raise EventLogMergeError(f"{path}: line {line_number} is missing a valid at timestamp")
            events.append(payload)
    return events


def merge_event_payloads(*event_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Union event payloads, dedupe by event_id, sort by timestamp."""
    merged: dict[str, dict[str, Any]] = {}
    for group in event_groups:
        for event in group:
            event_id = event["event_id"]
            existing = merged.get(event_id)
            if existing is not None and existing != event:
                raise EventLogMergeError(f"Conflicting payloads found for event_id {event_id!r}")
            merged[event_id] = event

    return sorted(
        merged.values(),
        key=lambda payload: (str(payload["at"]), str(payload["event_id"])),
    )


def merge_event_log_files(
    *,
    base_path: Path,
    ours_path: Path,
    theirs_path: Path,
    output_path: Path | None = None,
) -> None:
    """Merge three event logs into ``output_path`` (defaults to ``ours_path``)."""
    merged = merge_event_payloads(
        _read_event_file(base_path),
        _read_event_file(ours_path),
        _read_event_file(theirs_path),
    )
    target = output_path or ours_path
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for event in merged:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
