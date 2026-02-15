"""Integration test for feature 006 event schemas."""

from spec_kitty_events.models import Event
from specify_cli.events.ulid_utils import validate_ulid_format
import uuid


def test_event_envelope_ulid_format():
    """Test event_id and causation_id are ULIDs."""
    event = Event(
        event_id="01HQRS8ZMBE6XYZABC0123DEFG",
        event_type="ParticipantJoined",
        aggregate_id="mission/mission-123",
        correlation_id="01HQRS8ZMBE6XYZABC0123AAAA",
        payload={
            "participant_id": "01HQRS",
            "mission_id": "mission-123",
            "participant_identity": {
                "participant_id": "01HQRS",
                "participant_type": "human",
            },
        },
        timestamp="2026-02-15T10:00:00Z",
        node_id="cli-local",
        lamport_clock=1,
        causation_id="01HQRS8ZMBE6XYZABC0123ABCD",
        project_uuid=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        project_slug="mission-123",
        schema_version="1.0.0",
        data_tier=0,
    )

    assert validate_ulid_format(event.event_id)
    assert validate_ulid_format(event.causation_id)


def test_participant_joined_payload_schema():
    """Test ParticipantJoined payload structure."""
    event = Event(
        event_id="01HQRS8ZMBE6XYZABC0123DEFG",
        event_type="ParticipantJoined",
        aggregate_id="mission/mission-123",
        correlation_id="01HQRS8ZMBE6XYZABC0123AAAA",
        payload={
            "participant_id": "01HQRS8ZMBE6XYZABC0123ZZZZ",
            "mission_id": "mission-123",
            "participant_identity": {
                "participant_id": "01HQRS8ZMBE6XYZABC0123ZZZZ",
                "participant_type": "human",
            },
        },
        timestamp="2026-02-15T10:00:00Z",
        node_id="cli-local",
        lamport_clock=1,
        causation_id=None,
        project_uuid=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        project_slug="mission-123",
        schema_version="1.0.0",
        data_tier=0,
    )

    assert event.payload["participant_id"] == "01HQRS8ZMBE6XYZABC0123ZZZZ"
    assert event.payload["participant_identity"]["participant_type"] == "human"


def test_focus_changed_payload_schema():
    """Test FocusChanged payload structure."""
    event = Event(
        event_id="01HQRS8ZMBE6XYZABC0123DEFG",
        event_type="FocusChanged",
        aggregate_id="mission/mission-123",
        correlation_id="01HQRS8ZMBE6XYZABC0123AAAA",
        payload={
            "participant_id": "01HQRS8ZMBE6XYZABC0123ZZZZ",
            "mission_id": "mission-123",
            "focus_target": {
                "target_type": "work_package",
                "target_id": "WP01",
            },
            "previous_focus_target": None,
        },
        timestamp="2026-02-15T10:00:00Z",
        node_id="cli-local",
        lamport_clock=2,
        causation_id=None,
        project_uuid=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        project_slug="mission-123",
        schema_version="1.0.0",
        data_tier=0,
    )

    assert event.payload["focus_target"]["target_type"] == "work_package"
    assert event.payload["focus_target"]["target_id"] == "WP01"


def test_drive_intent_set_payload_schema():
    """Test DriveIntentSet payload structure."""
    event = Event(
        event_id="01HQRS8ZMBE6XYZABC0123DEFG",
        event_type="DriveIntentSet",
        aggregate_id="mission/mission-123",
        correlation_id="01HQRS8ZMBE6XYZABC0123AAAA",
        payload={
            "participant_id": "01HQRS8ZMBE6XYZABC0123ZZZZ",
            "mission_id": "mission-123",
            "intent": "active",
        },
        timestamp="2026-02-15T10:00:00Z",
        node_id="cli-local",
        lamport_clock=3,
        causation_id=None,
        project_uuid=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        project_slug="mission-123",
        schema_version="1.0.0",
        data_tier=0,
    )

    assert event.payload["intent"] == "active"
    assert event.payload["mission_id"] == "mission-123"
