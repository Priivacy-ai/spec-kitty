"""Test ULID monotonic generation and datetime serialization."""

import pytest
from datetime import datetime
from specify_cli.events.ulid_utils import generate_event_id


def test_ulid_monotonic_ordering():
    """Test that rapidly generated ULIDs maintain strict ordering."""
    # Generate ULIDs rapidly (simulate concurrent event generation)
    ulids = [generate_event_id() for _ in range(100)]

    # Verify all ULIDs are unique
    assert len(ulids) == len(set(ulids)), "ULIDs must be unique"

    # Verify ULIDs are in strictly increasing lexicographic order
    sorted_ulids = sorted(ulids)
    assert ulids == sorted_ulids, "ULIDs must be monotonically increasing"

    # Verify each ULID is strictly greater than the previous
    for i in range(1, len(ulids)):
        assert ulids[i] > ulids[i-1], f"ULID at index {i} not greater than previous"


def test_ulid_format():
    """Test that generated ULIDs have correct format."""
    ulid = generate_event_id()

    # Verify length
    assert len(ulid) == 26, f"ULID must be 26 characters, got {len(ulid)}"

    # Verify all characters are valid (Crockford Base32)
    valid_chars = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    assert all(c in valid_chars for c in ulid.upper()), "ULID contains invalid characters"


def test_datetime_serialization_in_event_model():
    """Test that Event models with datetime fields serialize correctly to JSON."""
    # This test verifies the fix for model_dump() -> model_dump(mode="json")
    from specify_cli.spec_kitty_events.models import Event

    # Create an event with a datetime field
    event = Event(
        event_id="01H0X123456789ABCDEFGHJKMN",
        event_type="agent_joined",
        timestamp=datetime.now(),
        mission_id="test-mission",
        aggregate_id="test-aggregate",
        node_id="test-node",
        lamport_clock=1,
        causation_id=None,
        actor_id="test-actor",
        payload={}
    )

    # Verify model_dump(mode="json") works (doesn't raise TypeError)
    event_dict = event.model_dump(mode="json")

    # Verify timestamp is serialized to string (ISO format)
    assert isinstance(event_dict["timestamp"], str), "Timestamp should be serialized to string"

    # Verify the string is a valid ISO format
    datetime.fromisoformat(event_dict["timestamp"].replace("Z", "+00:00"))
