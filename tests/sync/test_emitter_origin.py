"""Tests for MissionOriginBound event registration (WP02, Feature 061).

Covers:
- T011: Payload validation (valid, missing fields, invalid values)
- T012: Event routing, aggregate metadata, causation_id passthrough
"""

from __future__ import annotations

import pytest

from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.queue import OfflineQueue

pytestmark = pytest.mark.fast


# ── T011: Payload validation ──────────────────────────────────────


class TestMissionOriginBoundValidPayload:
    """Valid payloads pass validation and produce events."""

    def test_valid_payload_produces_event(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """A complete, valid payload produces a non-None event."""
        event = emitter.emit_mission_origin_bound(
            feature_slug="061-ticket-first-mission-origin-binding",
            provider="jira",
            external_issue_id="10042",
            external_issue_key="PROJ-123",
            external_issue_url="https://myorg.atlassian.net/browse/PROJ-123",
            title="Implement origin binding",
        )
        assert event is not None
        assert event["event_type"] == "MissionOriginBound"
        assert event["payload"]["feature_slug"] == "061-ticket-first-mission-origin-binding"
        assert event["payload"]["provider"] == "jira"
        assert event["payload"]["external_issue_id"] == "10042"
        assert event["payload"]["external_issue_key"] == "PROJ-123"
        assert event["payload"]["external_issue_url"] == "https://myorg.atlassian.net/browse/PROJ-123"
        assert event["payload"]["title"] == "Implement origin binding"

    def test_linear_provider_accepted(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Provider 'linear' is accepted."""
        event = emitter.emit_mission_origin_bound(
            feature_slug="061-ticket-first-mission-origin-binding",
            provider="linear",
            external_issue_id="abc-123",
            external_issue_key="ENG-42",
            external_issue_url="https://linear.app/myorg/issue/ENG-42",
            title="Linear issue",
        )
        assert event is not None
        assert event["payload"]["provider"] == "linear"


class TestMissionOriginBoundMissingFields:
    """Missing required fields are rejected."""

    def test_missing_provider_rejected(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Omitting provider causes validation failure (returns None)."""
        # Call _emit directly to bypass the method's explicit signature
        payload = {
            "feature_slug": "061-ticket-first-mission-origin-binding",
            # "provider" intentionally missing
            "external_issue_id": "10042",
            "external_issue_key": "PROJ-123",
            "external_issue_url": "https://example.com/PROJ-123",
            "title": "Test",
        }
        event = emitter._emit(
            event_type="MissionOriginBound",
            aggregate_id="061-ticket-first-mission-origin-binding",
            aggregate_type="Feature",
            payload=payload,
        )
        assert event is None
        assert temp_queue.size() == 0

    def test_missing_title_rejected(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Omitting title causes validation failure."""
        payload = {
            "feature_slug": "061-ticket-first-mission-origin-binding",
            "provider": "jira",
            "external_issue_id": "10042",
            "external_issue_key": "PROJ-123",
            "external_issue_url": "https://example.com/PROJ-123",
            # "title" intentionally missing
        }
        event = emitter._emit(
            event_type="MissionOriginBound",
            aggregate_id="061-ticket-first-mission-origin-binding",
            aggregate_type="Feature",
            payload=payload,
        )
        assert event is None

    def test_missing_external_issue_id_rejected(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Omitting external_issue_id causes validation failure."""
        payload = {
            "feature_slug": "061-ticket-first-mission-origin-binding",
            "provider": "jira",
            # "external_issue_id" intentionally missing
            "external_issue_key": "PROJ-123",
            "external_issue_url": "https://example.com/PROJ-123",
            "title": "Test",
        }
        event = emitter._emit(
            event_type="MissionOriginBound",
            aggregate_id="061-ticket-first-mission-origin-binding",
            aggregate_type="Feature",
            payload=payload,
        )
        assert event is None


class TestMissionOriginBoundInvalidValues:
    """Invalid field values are rejected by validators."""

    def test_invalid_feature_slug_rejected(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        r"""feature_slug not matching ^\d{3}-[a-z0-9-]+$ is rejected."""
        event = emitter.emit_mission_origin_bound(
            feature_slug="bad-slug",  # Missing 3-digit prefix
            provider="jira",
            external_issue_id="10042",
            external_issue_key="PROJ-123",
            external_issue_url="https://example.com/PROJ-123",
            title="Test",
        )
        assert event is None
        assert temp_queue.size() == 0

    def test_invalid_provider_rejected(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Provider 'github' is not in the allowed set {jira, linear}."""
        event = emitter.emit_mission_origin_bound(
            feature_slug="061-ticket-first-mission-origin-binding",
            provider="github",
            external_issue_id="10042",
            external_issue_key="PROJ-123",
            external_issue_url="https://example.com/PROJ-123",
            title="Test",
        )
        assert event is None
        assert temp_queue.size() == 0

    def test_empty_title_rejected(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Empty string title fails len(v) >= 1 validator."""
        event = emitter.emit_mission_origin_bound(
            feature_slug="061-ticket-first-mission-origin-binding",
            provider="jira",
            external_issue_id="10042",
            external_issue_key="PROJ-123",
            external_issue_url="https://example.com/PROJ-123",
            title="",
        )
        assert event is None
        assert temp_queue.size() == 0

    def test_empty_external_issue_key_rejected(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Empty external_issue_key is rejected."""
        event = emitter.emit_mission_origin_bound(
            feature_slug="061-ticket-first-mission-origin-binding",
            provider="jira",
            external_issue_id="10042",
            external_issue_key="",
            external_issue_url="https://example.com/PROJ-123",
            title="Test",
        )
        assert event is None
        assert temp_queue.size() == 0


# ── T012: Event routing and metadata ─────────────────────────────


class TestMissionOriginBoundEventRouting:
    """Event is queued offline, has correct aggregate metadata, and passes causation_id."""

    def test_event_queued_in_offline_queue(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """With no WebSocket, event is queued in offline queue."""
        event = emitter.emit_mission_origin_bound(
            feature_slug="061-ticket-first-mission-origin-binding",
            provider="jira",
            external_issue_id="10042",
            external_issue_key="PROJ-123",
            external_issue_url="https://example.com/PROJ-123",
            title="Test",
        )
        assert event is not None
        assert temp_queue.size() == 1

    def test_aggregate_type_is_feature(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """aggregate_type must be 'Feature'."""
        event = emitter.emit_mission_origin_bound(
            feature_slug="061-ticket-first-mission-origin-binding",
            provider="jira",
            external_issue_id="10042",
            external_issue_key="PROJ-123",
            external_issue_url="https://example.com/PROJ-123",
            title="Test",
        )
        assert event is not None
        assert event["aggregate_type"] == "Feature"

    def test_aggregate_id_is_feature_slug(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """aggregate_id must be the feature_slug value."""
        slug = "061-ticket-first-mission-origin-binding"
        event = emitter.emit_mission_origin_bound(
            feature_slug=slug,
            provider="jira",
            external_issue_id="10042",
            external_issue_key="PROJ-123",
            external_issue_url="https://example.com/PROJ-123",
            title="Test",
        )
        assert event is not None
        assert event["aggregate_id"] == slug

    def test_causation_id_passed_through(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """causation_id provided to the method appears in the event."""
        causation = emitter.generate_causation_id()
        event = emitter.emit_mission_origin_bound(
            feature_slug="061-ticket-first-mission-origin-binding",
            provider="linear",
            external_issue_id="abc-123",
            external_issue_key="ENG-42",
            external_issue_url="https://linear.app/myorg/issue/ENG-42",
            title="Test with causation",
            causation_id=causation,
        )
        assert event is not None
        assert event["causation_id"] == causation

    def test_causation_id_none_by_default(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Without causation_id, the field is None."""
        event = emitter.emit_mission_origin_bound(
            feature_slug="061-ticket-first-mission-origin-binding",
            provider="jira",
            external_issue_id="10042",
            external_issue_key="PROJ-123",
            external_issue_url="https://example.com/PROJ-123",
            title="Test",
        )
        assert event is not None
        assert event["causation_id"] is None

    def test_emission_is_fire_and_forget(self, temp_queue: OfflineQueue):
        """Even with a broken clock, emit never raises -- returns None."""
        from unittest.mock import MagicMock

        clock = MagicMock()
        clock.tick.side_effect = RuntimeError("Clock corrupted")
        auth = MagicMock()
        config = MagicMock()

        em = EventEmitter(clock=clock, config=config, queue=temp_queue, _auth=auth, ws_client=None)
        event = em.emit_mission_origin_bound(
            feature_slug="061-ticket-first-mission-origin-binding",
            provider="jira",
            external_issue_id="10042",
            external_issue_key="PROJ-123",
            external_issue_url="https://example.com/PROJ-123",
            title="Test",
        )
        assert event is None
        # Critically: no exception raised
