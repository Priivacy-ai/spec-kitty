"""Tests for the JSONL event store (status.events.jsonl)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import (
    EVENTS_FILENAME,
    EventPersistenceError,
    _SlugResolver,
    StoreError,
    append_event,
    append_event_verified,
    append_events_atomic,
    append_events_atomic_verified,
    read_events,
    read_events_raw,
    verify_event_readback,
)

pytestmark = pytest.mark.fast


def _make_event(
    *,
    event_id: str = "01HXYZ0123456789ABCDEFGHJK",
    mission_slug: str = "034-feature-name",
    mission_id: str | None = None,
    wp_id: str = "WP01",
    from_lane: Lane = Lane.PLANNED,
    to_lane: Lane = Lane.CLAIMED,
) -> StatusEvent:
    """Helper to build a minimal StatusEvent for testing."""
    return StatusEvent(
        event_id=event_id,
        mission_slug=mission_slug,
        wp_id=wp_id,
        from_lane=from_lane,
        to_lane=to_lane,
        at="2026-02-08T12:00:00Z",
        actor="claude-opus",
        force=False,
        execution_mode="worktree",
        mission_id=mission_id,
    )


# --- round-trip ---


def test_append_and_read_round_trip(tmp_path: Path) -> None:
    """Append a single event then read it back; fields must match."""
    event = _make_event()
    append_event(tmp_path, event)

    events = read_events(tmp_path)
    assert len(events) == 1
    assert events[0] == event


def test_append_event_verified_fails_when_readback_misses_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verified append requires durable readback of the exact transition."""
    event = _make_event(to_lane=Lane.IN_PROGRESS)

    import specify_cli.status.store as status_store

    monkeypatch.setattr(status_store, "append_event", lambda _feature_dir, _event: None)

    with pytest.raises(EventPersistenceError) as exc_info:
        append_event_verified(tmp_path, event)

    message = str(exc_info.value)
    assert "expected event missing after append" in message
    assert "mission_slug=034-feature-name" in message
    assert "wp_id=WP01" in message
    assert "target_lane=in_progress" in message
    assert str(tmp_path / EVENTS_FILENAME) in message
    diagnostic = exc_info.value.to_diagnostic()
    assert diagnostic["diagnostic_code"] == "STATUS_EVENT_PERSISTENCE_VERIFICATION_FAILED"
    assert diagnostic["violated_invariant"] == "STA-002"
    assert diagnostic["work_package_id"] == "WP01"
    assert diagnostic["to_lane"] == "in_progress"
    assert diagnostic["status_events_path"] == str(tmp_path / EVENTS_FILENAME)


def test_append_event_verified_wraps_append_failures_in_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Append failures surface the same structured persistence diagnostic."""
    event = _make_event(to_lane=Lane.IN_PROGRESS)

    import specify_cli.status.store as status_store

    def _raise_append(_feature_dir: Path, _event: StatusEvent) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(status_store, "append_event", _raise_append)

    with pytest.raises(EventPersistenceError) as exc_info:
        append_event_verified(tmp_path, event)

    assert "append failed: disk full" in str(exc_info.value)
    diagnostic = exc_info.value.to_diagnostic()
    assert diagnostic["diagnostic_code"] == "STATUS_EVENT_PERSISTENCE_VERIFICATION_FAILED"
    assert diagnostic["work_package_id"] == "WP01"
    assert diagnostic["to_lane"] == "in_progress"
    assert diagnostic["status_events_path"] == str(tmp_path / EVENTS_FILENAME)


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


def test_append_events_atomic_persists_full_batch(tmp_path: Path) -> None:
    e1 = _make_event(event_id="01AAAA0000000000000000001A", wp_id="WP01")
    e2 = _make_event(
        event_id="01BBBB0000000000000000002B",
        wp_id="WP01",
        from_lane=Lane.CLAIMED,
        to_lane=Lane.IN_PROGRESS,
    )

    append_events_atomic(tmp_path, [e1, e2])

    events = read_events(tmp_path)
    assert [(event.from_lane, event.to_lane) for event in events] == [
        (Lane.PLANNED, Lane.CLAIMED),
        (Lane.CLAIMED, Lane.IN_PROGRESS),
    ]


def test_append_events_atomic_verified_fails_when_batch_readback_misses_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    e1 = _make_event(event_id="01AAAA0000000000000000001A", wp_id="WP01")
    e2 = _make_event(
        event_id="01BBBB0000000000000000002B",
        wp_id="WP01",
        from_lane=Lane.CLAIMED,
        to_lane=Lane.IN_PROGRESS,
    )

    import specify_cli.status.store as status_store

    monkeypatch.setattr(status_store, "append_events_atomic", lambda _feature_dir, _events: None)

    with pytest.raises(EventPersistenceError) as exc_info:
        append_events_atomic_verified(tmp_path, [e1, e2])

    assert "expected event missing after append" in str(exc_info.value)
    assert "event_id=01AAAA0000000000000000001A" in str(exc_info.value)


def test_verify_event_readback_rejects_wrong_mission_slug(tmp_path: Path) -> None:
    expected = _make_event()
    append_event(tmp_path, replace(expected, mission_slug="999-other-mission"))

    with pytest.raises(EventPersistenceError) as exc_info:
        verify_event_readback(tmp_path, expected)

    assert "expected event missing after append" in str(exc_info.value)


def test_verify_event_readback_rejects_wrong_mission_id(tmp_path: Path) -> None:
    expected = _make_event(mission_id="01HQ0000000000000000000001")
    append_event(tmp_path, replace(expected, mission_id="01HQ0000000000000000000002"))

    with pytest.raises(EventPersistenceError) as exc_info:
        verify_event_readback(tmp_path, expected)

    assert "expected event missing after append" in str(exc_info.value)


def test_verify_event_readback_wraps_read_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _make_event()

    import specify_cli.status.store as status_store

    def _raise_read(_feature_dir: Path) -> list[StatusEvent]:
        raise ValueError("bad json")

    monkeypatch.setattr(status_store, "read_events", _raise_read)

    with pytest.raises(EventPersistenceError) as exc_info:
        verify_event_readback(tmp_path, event)

    assert "readback failed: bad json" in str(exc_info.value)


def test_append_events_atomic_empty_batch_is_noop(tmp_path: Path) -> None:
    append_events_atomic(tmp_path, [])

    assert not (tmp_path / EVENTS_FILENAME).exists()


def test_append_events_atomic_verified_empty_batch_is_noop(tmp_path: Path) -> None:
    append_events_atomic_verified(tmp_path, [])

    assert not (tmp_path / EVENTS_FILENAME).exists()


def test_append_events_atomic_verified_wraps_append_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _make_event()

    import specify_cli.status.store as status_store

    def _raise_append(_feature_dir: Path, _events: list[StatusEvent]) -> None:
        raise OSError("readonly")

    monkeypatch.setattr(status_store, "append_events_atomic", _raise_append)

    with pytest.raises(EventPersistenceError) as exc_info:
        append_events_atomic_verified(tmp_path, [event])

    assert "append failed: readonly" in str(exc_info.value)


def test_append_events_atomic_repairs_missing_trailing_newline(tmp_path: Path) -> None:
    first = _make_event(event_id="01AAAA0000000000000000001A", wp_id="WP01")
    second = _make_event(event_id="01BBBB0000000000000000002B", wp_id="WP02")
    events_path = tmp_path / EVENTS_FILENAME
    events_path.write_text(json.dumps(first.to_dict(), sort_keys=True), encoding="utf-8")

    append_events_atomic(tmp_path, [second])

    assert [event.wp_id for event in read_events(tmp_path)] == ["WP01", "WP02"]


def test_append_events_atomic_replace_failure_leaves_original(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = _make_event(event_id="01AAAA0000000000000000001A", wp_id="WP01")
    append_event(tmp_path, original)

    def _raise_replace(_src: Path, _dst: Path) -> None:
        raise OSError("replace failed")

    import specify_cli.status.store as status_store

    monkeypatch.setattr(status_store.os, "replace", _raise_replace)

    with pytest.raises(OSError, match="replace failed"):
        append_events_atomic(
            tmp_path,
            [
                _make_event(
                    event_id="01BBBB0000000000000000002B",
                    wp_id="WP01",
                    from_lane=Lane.CLAIMED,
                    to_lane=Lane.IN_PROGRESS,
                )
            ],
        )

    events = read_events(tmp_path)
    assert events == [original]


def test_read_events_skips_retrospective_events(tmp_path: Path) -> None:
    event = _make_event()
    events_file = tmp_path / EVENTS_FILENAME
    events_file.write_text(
        "\n".join(
            [
                json.dumps(event.to_dict(), sort_keys=True),
                json.dumps(
                    {
                        "event_id": "01RETRO000000000000000000",
                        "event_name": "retrospective.completed",
                        "payload": {"record_path": "/retro.yaml"},
                    },
                    sort_keys=True,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    events = read_events(tmp_path)

    assert len(events) == 1
    assert events[0].wp_id == "WP01"


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


def test_slug_resolver_finds_kitty_specs_two_levels_up(tmp_path: Path) -> None:
    """Nested feature dirs still resolve via a kitty-specs root two levels up."""
    mission_dir = tmp_path / "kitty-specs" / "034-feature-name"
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(
        json.dumps({"mission_id": "01KNXQS9ATWWFXS3K5ZJ9E5008"}),
        encoding="utf-8",
    )
    nested_feature_dir = mission_dir / "status"
    nested_feature_dir.mkdir()

    resolver = _SlugResolver(nested_feature_dir)

    assert resolver.resolve("034-feature-name") == "01KNXQS9ATWWFXS3K5ZJ9E5008"


def test_slug_resolver_returns_none_for_malformed_meta(tmp_path: Path) -> None:
    """Malformed legacy meta.json leaves mission_id unresolved instead of crashing."""
    mission_dir = tmp_path / "kitty-specs" / "034-feature-name"
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text("{bad json", encoding="utf-8")

    resolver = _SlugResolver(mission_dir)

    assert resolver.resolve("034-feature-name") is None
