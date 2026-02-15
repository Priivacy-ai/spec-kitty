"""Integration test for SaaS replay API with mocking."""

import pytest
import httpx
import respx
from datetime import datetime

from specify_cli.events.replay import replay_pending_events
from specify_cli.events.store import append_event, read_pending_events
from specify_cli.events.ulid_utils import generate_event_id
from spec_kitty_events.models import Event


@pytest.mark.respx(base_url="https://api.example.com")
def test_replay_pending_events(respx_mock: respx.MockRouter, clean_queue):
    """Test event replay with mocked SaaS batch endpoint."""
    event_id1 = "01HQRS8ZMBE6XYZABC0123AAA1"
    event_id2 = "01HQRS8ZMBE6XYZABC0123AAA2"

    respx_mock.post("/api/v1/events/batch/").mock(
        return_value=httpx.Response(
            200, json={"accepted": [event_id1, event_id2], "rejected": []}
        )
    )

    # Queue events
    event1 = Event(
        event_id=event_id1,
        event_type="FocusChanged",
        aggregate_id="mission/mission-123",
        correlation_id="01HQRS8ZMBE6XYZABC0123AAAA",
        payload={"participant_id": "01HQRS8ZMBE6XYZABC0123ZZZZ", "mission_id": "mission-123", "focus_target": None},
        timestamp=datetime.now().isoformat(),
        node_id="cli-local",
        lamport_clock=1,
        causation_id=None,
    )
    event2 = Event(
        event_id=event_id2,
        event_type="DriveIntentSet",
        aggregate_id="mission/mission-123",
        correlation_id="01HQRS8ZMBE6XYZABC0123AAAA",
        payload={"participant_id": "01HQRS8ZMBE6XYZABC0123ZZZZ", "mission_id": "mission-123", "intent": "active"},
        timestamp=datetime.now().isoformat(),
        node_id="cli-local",
        lamport_clock=2,
        causation_id=None,
    )

    append_event("mission-123", event1, "pending")
    append_event("mission-123", event2, "pending")

    # Replay
    result = replay_pending_events("mission-123", "https://api.example.com", "token")

    assert result["accepted"] == [event_id1, event_id2]
    assert result["rejected"] == []


@pytest.mark.respx(base_url="https://api.example.com")
def test_replay_partial_failure(respx_mock: respx.MockRouter, clean_queue):
    """Test replay handles partial rejection."""
    event_id1 = "01HQRS8ZMBE6XYZABC0123AAA1"
    event_id2 = "01HQRS8ZMBE6XYZABC0123AAA2"

    respx_mock.post("/api/v1/events/batch/").mock(
        return_value=httpx.Response(
            200,
            json={
                "accepted": [event_id1],
                "rejected": [event_id2],  # Simplified format (just IDs)
            },
        )
    )

    # Queue events
    event1 = Event(
        event_id=event_id1,
        event_type="FocusChanged",
        aggregate_id="mission/mission-123",
        correlation_id="01HQRS8ZMBE6XYZABC0123AAAA",
        payload={"participant_id": "01HQRS8ZMBE6XYZABC0123ZZZZ", "mission_id": "mission-123", "focus_target": None},
        timestamp=datetime.now().isoformat(),
        node_id="cli-local",
        lamport_clock=1,
        causation_id=None,
    )
    event2 = Event(
        event_id=event_id2,
        event_type="DriveIntentSet",
        aggregate_id="mission/mission-123",
        correlation_id="01HQRS8ZMBE6XYZABC0123AAAA",
        payload={"participant_id": "01HQRS8ZMBE6XYZABC0123ZZZZ", "mission_id": "mission-123", "intent": "active"},
        timestamp=datetime.now().isoformat(),
        node_id="cli-local",
        lamport_clock=2,
        causation_id=None,
    )

    append_event("mission-123", event1, "pending")
    append_event("mission-123", event2, "pending")

    result = replay_pending_events("mission-123", "https://api.example.com", "token")

    assert result["accepted"] == [event_id1]
    assert len(result["rejected"]) == 1


@pytest.mark.respx(base_url="https://api.example.com")
def test_replay_empty_queue(respx_mock: respx.MockRouter, clean_queue):
    """Test replay with empty queue."""
    # No mock needed - should not make any API calls

    result = replay_pending_events("mission-123", "https://api.example.com", "token")

    assert result["accepted"] == []
    assert result["rejected"] == []


@pytest.mark.respx(base_url="https://api.example.com")
def test_replay_network_error(respx_mock: respx.MockRouter, clean_queue):
    """Test replay handles network errors."""
    event_id = "01HQRS8ZMBE6XYZABC0123AAA1"

    respx_mock.post("/api/v1/events/batch/").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )

    # Queue event
    event = Event(
        event_id=event_id,
        event_type="FocusChanged",
        aggregate_id="mission/mission-123",
        correlation_id="01HQRS8ZMBE6XYZABC0123AAAA",
        payload={"participant_id": "01HQRS8ZMBE6XYZABC0123ZZZZ", "mission_id": "mission-123", "focus_target": None},
        timestamp=datetime.now().isoformat(),
        node_id="cli-local",
        lamport_clock=1,
        causation_id=None,
    )

    append_event("mission-123", event, "pending")

    result = replay_pending_events("mission-123", "https://api.example.com", "token", max_retries=1)

    # Network error should result in rejection
    assert result["accepted"] == []
    assert result["rejected"] == [event_id]
