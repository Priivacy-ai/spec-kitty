"""Helpers for semantically merging append-only status event logs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class EventLogMergeError(Exception):
    """Raised when an event-log merge cannot be completed safely."""


def read_event_log_text(text: str, *, source: str = "<memory>") -> list[dict[str, Any]]:
    """Read status.events.jsonl-style content from an in-memory string."""
    events: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise EventLogMergeError(
                f"{source}: invalid JSON on line {line_number}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise EventLogMergeError(
                f"{source}: line {line_number} is not a JSON object"
            )
        event_id = payload.get("event_id")
        if not isinstance(event_id, str) or not event_id.strip():
            raise EventLogMergeError(
                f"{source}: line {line_number} is missing a valid event_id"
            )
        # Non-status event types (e.g. tracker events) may lack 'at' or
        # 'timestamp'; accept them and sort them first via empty-string key.
        events.append(payload)
    return events


def _read_event_file(path: Path) -> list[dict[str, Any]]:
    """Read a status.events.jsonl-style file from an arbitrary path."""
    if not path.exists():
        return []
    return read_event_log_text(path.read_text(encoding="utf-8"), source=str(path))


def merge_event_payloads(*event_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Union event payloads, dedupe by event_id, sort by timestamp."""
    merged: dict[str, dict[str, Any]] = {}
    for group in event_groups:
        for event in group:
            event_id = event["event_id"]
            existing = merged.get(event_id)
            if existing is not None and existing != event:
                raise EventLogMergeError(
                    f"Conflicting payloads found for event_id {event_id!r}"
                )
            merged[event_id] = event

    return sorted(
        merged.values(),
        key=lambda payload: (
            str(payload.get("at") or payload.get("timestamp", "")),
            str(payload["event_id"]),
        ),
    )


def merge_event_log_texts(*texts: str) -> str:
    """Union JSONL event-log texts and serialize deterministic JSONL."""
    merged = merge_event_payloads(
        *[
            read_event_log_text(text, source=f"<merge-stage-{idx}>")
            for idx, text in enumerate(texts, start=1)
        ]
    )
    return "".join(json.dumps(event, sort_keys=True) + "\n" for event in merged)


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
