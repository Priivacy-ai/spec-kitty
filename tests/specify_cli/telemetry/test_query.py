"""Unit tests for telemetry query layer.

Tests EventFilter matching logic and both feature-level
and project-level query functions.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from specify_cli.spec_kitty_events.models import Event
from specify_cli.telemetry.store import SimpleJsonStore
from specify_cli.telemetry.query import (
    EventFilter,
    query_execution_events,
    query_project_events,
    EXECUTION_EVENTS_FILE,
)


def create_event(
    event_id: str,
    event_type: str = "WPStarted",
    aggregate_id: str = "043-feature",
    lamport_clock: int = 1,
    node_id: str = "node1",
    **payload_kwargs: object,
) -> Event:
    """Helper to create test events with defaults."""
    return Event(
        event_id=event_id,
        event_type=event_type,
        aggregate_id=aggregate_id,
        timestamp=datetime.now(timezone.utc),
        node_id=node_id,
        lamport_clock=lamport_clock,
        causation_id=None,
        payload=dict(payload_kwargs),
    )


def test_query_no_filter(tmp_path: Path) -> None:
    """Query with no filter returns all events."""
    feature_dir = tmp_path / "kitty-specs" / "043-feature"
    feature_dir.mkdir(parents=True)

    store = SimpleJsonStore(feature_dir / EXECUTION_EVENTS_FILE)
    e1 = create_event("01" + "A" * 24, lamport_clock=1, wp_id="WP01")
    e2 = create_event("02" + "B" * 24, lamport_clock=2, wp_id="WP02")
    store.save_event(e1)
    store.save_event(e2)

    results = query_execution_events(feature_dir)
    assert len(results) == 2
    assert results[0].event_id == e1.event_id
    assert results[1].event_id == e2.event_id


def test_query_by_event_type(tmp_path: Path) -> None:
    """Filter by event_type field."""
    feature_dir = tmp_path / "kitty-specs" / "043-feature"
    feature_dir.mkdir(parents=True)

    store = SimpleJsonStore(feature_dir / EXECUTION_EVENTS_FILE)
    e1 = create_event("01" + "A" * 24, event_type="WPStarted", lamport_clock=1)
    e2 = create_event("02" + "B" * 24, event_type="WPCompleted", lamport_clock=2)
    e3 = create_event("03" + "C" * 24, event_type="WPStarted", lamport_clock=3)
    store.save_event(e1)
    store.save_event(e2)
    store.save_event(e3)

    filters = EventFilter(event_type="WPStarted")
    results = query_execution_events(feature_dir, filters)
    assert len(results) == 2
    assert all(e.event_type == "WPStarted" for e in results)


def test_query_by_wp_id(tmp_path: Path) -> None:
    """Filter by wp_id in payload."""
    feature_dir = tmp_path / "kitty-specs" / "043-feature"
    feature_dir.mkdir(parents=True)

    store = SimpleJsonStore(feature_dir / EXECUTION_EVENTS_FILE)
    e1 = create_event("01" + "A" * 24, lamport_clock=1, wp_id="WP01")
    e2 = create_event("02" + "B" * 24, lamport_clock=2, wp_id="WP02")
    e3 = create_event("03" + "C" * 24, lamport_clock=3, wp_id="WP01")
    store.save_event(e1)
    store.save_event(e2)
    store.save_event(e3)

    filters = EventFilter(wp_id="WP01")
    results = query_execution_events(feature_dir, filters)
    assert len(results) == 2
    assert all(e.payload.get("wp_id") == "WP01" for e in results)


def test_query_by_agent(tmp_path: Path) -> None:
    """Filter by agent in payload."""
    feature_dir = tmp_path / "kitty-specs" / "043-feature"
    feature_dir.mkdir(parents=True)

    store = SimpleJsonStore(feature_dir / EXECUTION_EVENTS_FILE)
    e1 = create_event("01" + "A" * 24, lamport_clock=1, agent="claude")
    e2 = create_event("02" + "B" * 24, lamport_clock=2, agent="codex")
    e3 = create_event("03" + "C" * 24, lamport_clock=3, agent="claude")
    store.save_event(e1)
    store.save_event(e2)
    store.save_event(e3)

    filters = EventFilter(agent="claude")
    results = query_execution_events(feature_dir, filters)
    assert len(results) == 2
    assert all(e.payload.get("agent") == "claude" for e in results)


def test_query_by_timeframe(tmp_path: Path) -> None:
    """Filter by since/until timestamps."""
    feature_dir = tmp_path / "kitty-specs" / "043-feature"
    feature_dir.mkdir(parents=True)

    store = SimpleJsonStore(feature_dir / EXECUTION_EVENTS_FILE)
    t1 = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    e1 = Event(
        event_id="01" + "A" * 24,
        event_type="WPStarted",
        aggregate_id="043-feature",
        timestamp=t1,
        node_id="node1",
        lamport_clock=1,
        causation_id=None,
        payload={},
    )
    e2 = Event(
        event_id="02" + "B" * 24,
        event_type="WPStarted",
        aggregate_id="043-feature",
        timestamp=t2,
        node_id="node1",
        lamport_clock=2,
        causation_id=None,
        payload={},
    )
    e3 = Event(
        event_id="03" + "C" * 24,
        event_type="WPStarted",
        aggregate_id="043-feature",
        timestamp=t3,
        node_id="node1",
        lamport_clock=3,
        causation_id=None,
        payload={},
    )
    store.save_event(e1)
    store.save_event(e2)
    store.save_event(e3)

    # Filter for events between 10:30 and 11:30
    filters = EventFilter(
        since=datetime(2025, 1, 1, 10, 30, 0, tzinfo=timezone.utc),
        until=datetime(2025, 1, 1, 11, 30, 0, tzinfo=timezone.utc),
    )
    results = query_execution_events(feature_dir, filters)
    assert len(results) == 1
    assert results[0].event_id == e2.event_id


def test_query_combined_filters(tmp_path: Path) -> None:
    """Multiple filters act as AND conditions."""
    feature_dir = tmp_path / "kitty-specs" / "043-feature"
    feature_dir.mkdir(parents=True)

    store = SimpleJsonStore(feature_dir / EXECUTION_EVENTS_FILE)
    e1 = create_event(
        "01" + "A" * 24,
        event_type="WPStarted",
        lamport_clock=1,
        wp_id="WP01",
        agent="claude",
    )
    e2 = create_event(
        "02" + "B" * 24,
        event_type="WPStarted",
        lamport_clock=2,
        wp_id="WP01",
        agent="codex",
    )
    e3 = create_event(
        "03" + "C" * 24,
        event_type="WPCompleted",
        lamport_clock=3,
        wp_id="WP01",
        agent="claude",
    )
    store.save_event(e1)
    store.save_event(e2)
    store.save_event(e3)

    # Only e1 matches all criteria
    filters = EventFilter(event_type="WPStarted", wp_id="WP01", agent="claude")
    results = query_execution_events(feature_dir, filters)
    assert len(results) == 1
    assert results[0].event_id == e1.event_id


def test_query_empty_file(tmp_path: Path) -> None:
    """Query on non-existent file returns empty list."""
    feature_dir = tmp_path / "kitty-specs" / "043-feature"
    feature_dir.mkdir(parents=True)

    results = query_execution_events(feature_dir)
    assert results == []


def test_query_project_events(tmp_path: Path) -> None:
    """Query across multiple features merges and sorts."""
    # Create 3 feature directories with events
    f1_dir = tmp_path / "kitty-specs" / "001-feature"
    f2_dir = tmp_path / "kitty-specs" / "002-feature"
    f3_dir = tmp_path / "kitty-specs" / "003-feature"
    f1_dir.mkdir(parents=True)
    f2_dir.mkdir(parents=True)
    f3_dir.mkdir(parents=True)

    # Feature 1: lamport 1, 3
    s1 = SimpleJsonStore(f1_dir / EXECUTION_EVENTS_FILE)
    e1 = create_event("01" + "A" * 24, lamport_clock=1, node_id="n1", wp_id="WP01")
    e2 = create_event("02" + "B" * 24, lamport_clock=3, node_id="n1", wp_id="WP02")
    s1.save_event(e1)
    s1.save_event(e2)

    # Feature 2: lamport 2, 4
    s2 = SimpleJsonStore(f2_dir / EXECUTION_EVENTS_FILE)
    e3 = create_event("03" + "C" * 24, lamport_clock=2, node_id="n1", wp_id="WP03")
    e4 = create_event("04" + "D" * 24, lamport_clock=4, node_id="n1", wp_id="WP04")
    s2.save_event(e3)
    s2.save_event(e4)

    # Feature 3: lamport 5
    s3 = SimpleJsonStore(f3_dir / EXECUTION_EVENTS_FILE)
    e5 = create_event("05" + "E" * 24, lamport_clock=5, node_id="n1", wp_id="WP05")
    s3.save_event(e5)

    # Query all
    results = query_project_events(tmp_path)
    assert len(results) == 5
    # Check sorted by lamport_clock
    assert [e.lamport_clock for e in results] == [1, 2, 3, 4, 5]

    # Query with filter
    filters = EventFilter(wp_id="WP02")
    filtered = query_project_events(tmp_path, filters)
    assert len(filtered) == 1
    assert filtered[0].event_id == e2.event_id


def test_query_project_missing_features(tmp_path: Path) -> None:
    """Query on project without kitty-specs returns empty list."""
    results = query_project_events(tmp_path)
    assert results == []


def test_eventfilter_matches_success_field(tmp_path: Path) -> None:
    """Filter by success boolean in payload."""
    feature_dir = tmp_path / "kitty-specs" / "043-feature"
    feature_dir.mkdir(parents=True)

    store = SimpleJsonStore(feature_dir / EXECUTION_EVENTS_FILE)
    e1 = create_event("01" + "A" * 24, lamport_clock=1, success=True)
    e2 = create_event("02" + "B" * 24, lamport_clock=2, success=False)
    e3 = create_event("03" + "C" * 24, lamport_clock=3, success=True)
    store.save_event(e1)
    store.save_event(e2)
    store.save_event(e3)

    filters = EventFilter(success=True)
    results = query_execution_events(feature_dir, filters)
    assert len(results) == 2
    assert all(e.payload.get("success") is True for e in results)


def test_eventfilter_matches_model_field(tmp_path: Path) -> None:
    """Filter by model in payload."""
    feature_dir = tmp_path / "kitty-specs" / "043-feature"
    feature_dir.mkdir(parents=True)

    store = SimpleJsonStore(feature_dir / EXECUTION_EVENTS_FILE)
    e1 = create_event("01" + "A" * 24, lamport_clock=1, model="sonnet-4.5")
    e2 = create_event("02" + "B" * 24, lamport_clock=2, model="haiku-4.5")
    e3 = create_event("03" + "C" * 24, lamport_clock=3, model="sonnet-4.5")
    store.save_event(e1)
    store.save_event(e2)
    store.save_event(e3)

    filters = EventFilter(model="sonnet-4.5")
    results = query_execution_events(feature_dir, filters)
    assert len(results) == 2
    assert all(e.payload.get("model") == "sonnet-4.5" for e in results)


def test_query_timeframe_with_naive_datetime(tmp_path: Path) -> None:
    """Timezone-naive filter datetimes should not crash when events are aware."""
    feature_dir = tmp_path / "kitty-specs" / "test-feature"
    feature_dir.mkdir(parents=True)
    store = SimpleJsonStore(feature_dir / EXECUTION_EVENTS_FILE)

    # Event with timezone-aware timestamp
    e = Event(
        event_id="01HX0000000000000000000001",
        event_type="ExecutionEvent",
        aggregate_id="test-feature",
        timestamp=datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        node_id="cli",
        lamport_clock=1,
        causation_id=None,
        payload={"agent": "claude"},
    )
    store.save_event(e)

    # Filter with naive datetime (no tzinfo)
    filters = EventFilter(since=datetime(2025, 6, 15, 11, 0, 0))
    results = query_execution_events(feature_dir, filters)
    assert len(results) == 1
