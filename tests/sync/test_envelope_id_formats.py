"""Tests for mixed ULID/UUID envelope ID acceptance in the sync emitter.

Verifies that the CLI accepts ULID, UUID-hyphenated, and UUID-bare
envelope IDs after the cross-repo ID-format alignment with
spec-kitty-events 2.2.0.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from specify_cli.sync.emitter import EventEmitter


def _make_full_event(
    emitter: EventEmitter,
    *,
    event_id: str | None = None,
    causation_id: str | None = None,
    correlation_id: str | None = None,
) -> dict:
    """Build a well-formed event dict for _validate_event testing."""
    event = {
        "event_id": event_id if event_id is not None else emitter.generate_causation_id(),
        "event_type": "WPStatusChanged",
        "aggregate_id": "WP01",
        "aggregate_type": "WorkPackage",
        "payload": {
            "wp_id": "WP01",
            "from_lane": "planned",
            "to_lane": "in_progress",
            "actor": "user",
            "feature_slug": None,
        },
        "node_id": "test-node-id",
        "lamport_clock": 1,
        "causation_id": causation_id,
        "timestamp": "2026-02-17T12:00:00+00:00",
        "team_slug": "test-team",
    }
    if correlation_id is not None:
        event["correlation_id"] = correlation_id
    return event


# ── event_id acceptance ──────────────────────────────────────────────


class TestEventIdAcceptance:
    """Verify _validate_event accepts ULID, UUID-hyphenated, and UUID-bare."""

    def test_ulid_event_id_accepted(self, emitter: EventEmitter, temp_queue):
        ulid_id = emitter.generate_causation_id()
        event = _make_full_event(emitter, event_id=ulid_id)
        assert emitter._validate_event(event) is True

    def test_uuid_hyphenated_event_id_accepted(self, emitter: EventEmitter, temp_queue):
        event = _make_full_event(
            emitter, event_id="550e8400-e29b-41d4-a716-446655440000"
        )
        assert emitter._validate_event(event) is True

    def test_uuid_bare_event_id_accepted_and_normalized(
        self, emitter: EventEmitter, temp_queue
    ):
        event = _make_full_event(
            emitter, event_id="550e8400e29b41d4a716446655440000"
        )
        assert emitter._validate_event(event) is True

    def test_uuid_bare_event_id_stored_as_hyphenated_lowercase(
        self, emitter: EventEmitter, temp_queue
    ):
        bare = "550E8400E29B41D4A716446655440000"
        event = _make_full_event(emitter, event_id=bare)
        emitter._validate_event(event)
        assert event["event_id"] == "550e8400-e29b-41d4-a716-446655440000"

    def test_lowercase_ulid_event_id_uppercased(self, emitter: EventEmitter, temp_queue):
        """Lowercase Crockford base32 ULID is normalized to uppercase."""
        lower_ulid = "01hxyz0123456789abcdefghjk"
        event = _make_full_event(emitter, event_id=lower_ulid)
        assert emitter._validate_event(event) is True
        assert event["event_id"] == "01HXYZ0123456789ABCDEFGHJK"

    def test_non_crockford_26_char_rejected(self, emitter: EventEmitter, temp_queue):
        """26-char string with non-Crockford chars (e.g. @) is rejected."""
        event = _make_full_event(emitter, event_id="@@@@@@@@@@@@@@@@@@@@@@@@@@")
        assert emitter._validate_event(event) is False

    def test_ulid_with_excluded_chars_rejected(self, emitter: EventEmitter, temp_queue):
        """ULID with I, L, O, U (excluded from Crockford base32) is rejected."""
        # 'I' is excluded from Crockford base32
        event = _make_full_event(emitter, event_id="01IIOO0123456789LLUUUUGHJK")
        assert emitter._validate_event(event) is False


# ── causation_id acceptance ──────────────────────────────────────────


class TestCausationIdAcceptance:
    def test_ulid_causation_id_accepted(self, emitter: EventEmitter, temp_queue):
        cid = emitter.generate_causation_id()
        event = _make_full_event(emitter, causation_id=cid)
        assert emitter._validate_event(event) is True

    def test_uuid_hyphenated_causation_id_accepted(
        self, emitter: EventEmitter, temp_queue
    ):
        event = _make_full_event(
            emitter, causation_id="550e8400-e29b-41d4-a716-446655440000"
        )
        assert emitter._validate_event(event) is True

    def test_uuid_bare_causation_id_normalized(
        self, emitter: EventEmitter, temp_queue
    ):
        bare = "AABBCCDD11223344AABBCCDD11223344"
        event = _make_full_event(emitter, causation_id=bare)
        assert emitter._validate_event(event) is True
        assert event["causation_id"] == "aabbccdd-1122-3344-aabb-ccdd11223344"


# ── correlation_id acceptance (future-proof) ─────────────────────────


class TestCorrelationIdAcceptance:
    def test_correlation_id_uuid_accepted_if_present(
        self, emitter: EventEmitter, temp_queue
    ):
        event = _make_full_event(
            emitter, correlation_id="550e8400-e29b-41d4-a716-446655440000"
        )
        assert emitter._validate_event(event) is True


# ── rejection ────────────────────────────────────────────────────────


class TestEnvelopeIdRejection:
    def test_empty_string_event_id_rejected(self, emitter: EventEmitter, temp_queue):
        event = _make_full_event(emitter, event_id="")
        assert emitter._validate_event(event) is False

    def test_short_string_event_id_rejected(self, emitter: EventEmitter, temp_queue):
        event = _make_full_event(emitter, event_id="short")
        assert emitter._validate_event(event) is False

    def test_integer_event_id_rejected(self, emitter: EventEmitter, temp_queue):
        event = _make_full_event(emitter)
        event["event_id"] = 12345
        assert emitter._validate_event(event) is False

    def test_35_char_string_rejected(self, emitter: EventEmitter, temp_queue):
        """35-char string is not ULID (26), not UUID bare (32), not UUID hyphenated (36)."""
        event = _make_full_event(emitter, event_id="a" * 35)
        assert emitter._validate_event(event) is False


# ── regression: UUID events NOT dropped ──────────────────────────────


class TestUuidEventsNotDropped:
    @patch("specify_cli.sync.emitter._generate_ulid", return_value="550e8400-e29b-41d4-a716-446655440000")
    def test_uuid_event_queued_not_dropped(self, _mock_ulid, emitter: EventEmitter, temp_queue):
        """UUID-format event_id events must reach the queue, not be silently dropped.

        Patches _generate_ulid to return a UUID, proving the full _emit path
        accepts UUID event_ids (not just ULID ones).
        """
        event = emitter._emit(
            event_type="WPStatusChanged",
            aggregate_id="WP01",
            aggregate_type="WorkPackage",
            payload={
                "wp_id": "WP01",
                "from_lane": "planned",
                "to_lane": "in_progress",
                "actor": "user",
                "feature_slug": None,
            },
        )
        assert event is not None
        # Confirm it's the UUID we injected (normalized to lowercase)
        assert event["event_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert temp_queue.size() >= 1

    def test_uuid_event_survives_validate_and_route(
        self, emitter: EventEmitter, temp_queue
    ):
        """An event with a UUID-format causation_id must pass validation and be routed."""
        uuid_cid = "550e8400-e29b-41d4-a716-446655440000"
        event = emitter.emit_wp_status_changed(
            "WP01", "planned", "in_progress", causation_id=uuid_cid
        )
        assert event is not None
        assert event["causation_id"] == "550e8400-e29b-41d4-a716-446655440000"
