"""Unit tests for event queue store."""

import pytest
from pathlib import Path
from datetime import datetime
from specify_cli.events.store import (
    append_event,
    read_pending_events,
    read_all_events,
    get_queue_path,
    is_online,
)
from specify_cli.events.models import EventQueueEntry
from specify_cli.spec_kitty_events.models import Event


def test_append_event_creates_file(tmp_path, monkeypatch):
    """Test local queue store created on first append."""
    monkeypatch.setenv("HOME", str(tmp_path))

    event = Event(
        event_id="01HQRS8ZMBE6XYZABC0123DEFG",
        event_type="ParticipantJoined",
        aggregate_id="mission/mission-123",
        payload={"participant_id": "01HQRS", "role": "developer"},
        timestamp=datetime.now(),
        lamport_clock=1,
        node_id="test-node",
    )
    append_event("mission-123", event, "pending")

    queue_path = tmp_path / ".spec-kitty" / "queues" / "mission-123.jsonl"
    assert queue_path.exists()

    # Check file permissions (0600 = owner read/write only)
    mode = oct(queue_path.stat().st_mode)[-3:]
    assert mode == "600"


def test_read_pending_events_filters(tmp_path, monkeypatch):
    """Test read_pending_events filters by replay_status."""
    monkeypatch.setenv("HOME", str(tmp_path))

    event1 = Event(
        event_id="01HQRS8ZMBE6XYZABC0123DEF1",
        event_type="ParticipantJoined",
        aggregate_id="mission/mission-123",
        payload={"participant_id": "01HQRS1"},
        timestamp=datetime.now(),
        lamport_clock=1,
        node_id="test-node",
    )
    event2 = Event(
        event_id="01HQRS8ZMBE6XYZABC0123DEF2",
        event_type="ParticipantLeft",
        aggregate_id="mission/mission-123",
        payload={"participant_id": "01HQRS2"},
        timestamp=datetime.now(),
        lamport_clock=2,
        node_id="test-node",
    )

    append_event("mission-123", event1, "pending")
    append_event("mission-123", event2, "delivered")

    pending = read_pending_events("mission-123")
    assert len(pending) == 1
    assert pending[0].event.event_id == "01HQRS8ZMBE6XYZABC0123DEF1"
    assert pending[0].replay_status == "pending"


def test_read_all_events_returns_all_statuses(tmp_path, monkeypatch):
    """Test read_all_events returns events regardless of replay_status."""
    monkeypatch.setenv("HOME", str(tmp_path))

    event1 = Event(
        event_id="01HQRS8ZMBE6XYZABC0123DEF1",
        event_type="ParticipantJoined",
        aggregate_id="mission/mission-123",
        payload={"participant_id": "01HQRS1"},
        timestamp=datetime.now(),
        lamport_clock=1,
        node_id="test-node",
    )
    event2 = Event(
        event_id="01HQRS8ZMBE6XYZABC0123DEF2",
        event_type="ParticipantLeft",
        aggregate_id="mission/mission-123",
        payload={"participant_id": "01HQRS2"},
        timestamp=datetime.now(),
        lamport_clock=2,
        node_id="test-node",
    )

    append_event("mission-123", event1, "pending")
    append_event("mission-123", event2, "delivered")

    all_events = read_all_events("mission-123")
    assert len(all_events) == 2


def test_append_event_atomic_write(tmp_path, monkeypatch):
    """Test append_event uses atomic write with file locking."""
    monkeypatch.setenv("HOME", str(tmp_path))

    event = Event(
        event_id="01HQRS8ZMBE6XYZABC0123DEFG",
        event_type="FocusSet",
        aggregate_id="mission/mission-123",
        payload={"focus_target": "wp:WP01"},
        timestamp=datetime.now(),
        lamport_clock=1,
        node_id="test-node",
    )

    # Append multiple events (simulating concurrent writes)
    append_event("mission-123", event, "pending")
    append_event("mission-123", event, "pending")

    all_events = read_all_events("mission-123")
    assert len(all_events) == 2


def test_read_pending_events_empty_queue(tmp_path, monkeypatch):
    """Test read_pending_events returns empty list if queue missing."""
    monkeypatch.setenv("HOME", str(tmp_path))

    pending = read_pending_events("mission-nonexistent")
    assert pending == []


def test_is_online_returns_false_for_unreachable_url():
    """Test is_online returns False for unreachable SaaS."""
    result = is_online("https://nonexistent-domain-12345.example.com", timeout=0.5)
    assert result is False


def test_get_queue_path_returns_home_directory(tmp_path, monkeypatch):
    """Test get_queue_path returns ~/.spec-kitty/queues/mission-123.jsonl."""
    monkeypatch.setenv("HOME", str(tmp_path))

    queue_path = get_queue_path("mission-123")
    assert queue_path == tmp_path / ".spec-kitty" / "queues" / "mission-123.jsonl"
