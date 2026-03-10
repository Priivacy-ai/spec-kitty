"""Tests for the JSONL event store (status.events.jsonl)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import (
    EVENTS_FILENAME,
    StoreError,
    append_event,
    read_events,
    read_events_raw,
)


def _make_event(
    *,
    event_id: str = "01HXYZ0123456789ABCDEFGHJK",
    wp_id: str = "WP01",
    from_lane: Lane = Lane.PLANNED,
    to_lane: Lane = Lane.CLAIMED,
) -> StatusEvent:
    """Helper to build a minimal StatusEvent for testing."""
    return StatusEvent(
        event_id=event_id,
        feature_slug="034-feature-name",
        wp_id=wp_id,
        from_lane=from_lane,
        to_lane=to_lane,
        at="2026-02-08T12:00:00Z",
        actor="claude-opus",
        force=False,
        execution_mode="worktree",
    )


# --- round-trip ---


def test_append_and_read_round_trip(tmp_path: Path) -> None:
    """Append a single event then read it back; fields must match."""
    event = _make_event()
    append_event(tmp_path, event)

    events = read_events(tmp_path)
    assert len(events) == 1
    assert events[0] == event


def test_multiple_appends_preserve_order(tmp_path: Path) -> None:
    """Events appended in sequence are returned in the same order."""
    e1 = _make_event(event_id="01AAAA0000000000000000001A", wp_id="WP01")
    e2 = _make_event(event_id="01BBBB0000000000000000002B", wp_id="WP02")
    e3 = _make_event(event_id="01CCCC0000000000000000003C", wp_id="WP03")

    append_event(tmp_path, e1)
    append_event(tmp_path, e2)
    append_event(tmp_path, e3)

    events = read_events(tmp_path)
    assert len(events) == 3
    assert events[0].wp_id == "WP01"
    assert events[1].wp_id == "WP02"
    assert events[2].wp_id == "WP03"


# --- empty / nonexistent ---


def test_read_empty_file(tmp_path: Path) -> None:
    """An empty file returns an empty list (no crash)."""
    events_file = tmp_path / EVENTS_FILENAME
    events_file.write_text("", encoding="utf-8")

    assert read_events(tmp_path) == []


def test_read_nonexistent_file(tmp_path: Path) -> None:
    """Reading from a directory without events file returns empty list."""
    assert read_events(tmp_path) == []


# --- auto-creation ---


def test_file_created_on_first_event(tmp_path: Path) -> None:
    """The JSONL file is created automatically on the first append."""
    events_file = tmp_path / EVENTS_FILENAME
    assert not events_file.exists()

    append_event(tmp_path, _make_event())
    assert events_file.exists()


def test_directory_created_on_first_event(tmp_path: Path) -> None:
    """Parent directories are created if they do not exist."""
    nested = tmp_path / "deep" / "nested" / "feature"
    assert not nested.exists()

    append_event(nested, _make_event())
    assert (nested / EVENTS_FILENAME).exists()


# --- corruption / invalid JSON ---


def test_corruption_invalid_json(tmp_path: Path) -> None:
    """Invalid JSON raises StoreError mentioning the line number."""
    events_file = tmp_path / EVENTS_FILENAME
    events_file.write_text("not valid json\n", encoding="utf-8")

    with pytest.raises(StoreError, match="line 1"):
        read_events(tmp_path)


def test_corruption_reports_line_number(tmp_path: Path) -> None:
    """Corruption on a later line reports the correct line number."""
    event = _make_event()
    good_line = json.dumps(event.to_dict(), sort_keys=True)

    events_file = tmp_path / EVENTS_FILENAME
    events_file.write_text(f"{good_line}\n{good_line}\n{{bad json}}\n", encoding="utf-8")

    with pytest.raises(StoreError, match="line 3"):
        read_events(tmp_path)


def test_corruption_invalid_event_structure(tmp_path: Path) -> None:
    """Valid JSON but missing required fields raises StoreError."""
    events_file = tmp_path / EVENTS_FILENAME
    events_file.write_text('{"foo": "bar"}\n', encoding="utf-8")

    with pytest.raises(StoreError, match="line 1"):
        read_events(tmp_path)


# --- read_events_raw ---


def test_read_raw_returns_dicts(tmp_path: Path) -> None:
    """read_events_raw returns plain dicts, not StatusEvent objects."""
    event = _make_event()
    append_event(tmp_path, event)

    raw = read_events_raw(tmp_path)
    assert len(raw) == 1
    assert isinstance(raw[0], dict)
    assert raw[0]["wp_id"] == "WP01"


# --- deterministic ordering ---


def test_deterministic_key_ordering(tmp_path: Path) -> None:
    """JSON keys in the JSONL file are sorted alphabetically."""
    append_event(tmp_path, _make_event())

    events_file = tmp_path / EVENTS_FILENAME
    line = events_file.read_text(encoding="utf-8").strip()
    parsed = json.loads(line)
    keys = list(parsed.keys())
    assert keys == sorted(keys)


# --- blank lines ---


def test_blank_lines_skipped(tmp_path: Path) -> None:
    """Blank lines interspersed in the file are silently ignored."""
    event = _make_event()
    good_line = json.dumps(event.to_dict(), sort_keys=True)

    events_file = tmp_path / EVENTS_FILENAME
    events_file.write_text(f"\n{good_line}\n\n{good_line}\n\n", encoding="utf-8")

    events = read_events(tmp_path)
    assert len(events) == 2
