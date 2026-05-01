"""Contract tests: mission-level SaaS events use mission_id as aggregate identity (WP06).

FR-024: Every outbound mission-lifecycle event envelope must carry
  ``aggregate_id = mission_id`` (a ULID) so the SaaS side can join events
  without relying on mutable slug strings.

Payload shape contract (T031):
  - ``mission_id``     (str, ULID)   — new primary key / aggregate identity
  - ``mission_slug``   (str)         — human display; never used as identity
  - ``mission_number`` (int | None)  — numeric display; None for pre-merge missions

T032 — aggregate identity assertions for every mission-level emitter.
T033 — mission_number type/null assertions (int or null in JSON, never string).
"""

from __future__ import annotations

import json
import re

import pytest

from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.queue import OfflineQueue

pytestmark = pytest.mark.fast

# ULID regex: 26 chars from Crockford Base32 alphabet
_ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

# A valid ULID for tests (26 chars, valid Crockford Base32)
_MISSION_ID = "01JWPQRS0V8ZXMNK3V5BYMCAEF"
_MISSION_SLUG = "083-mission-id-canonical"
_MISSION_NUMBER_INT = 83
_MISSION_NUMBER_NONE = None


# ---------------------------------------------------------------------------
# T032 — emit_mission_created: aggregate_id == mission_id
# ---------------------------------------------------------------------------


class TestEmitMissionCreatedAggregateId:
    """emit_mission_created must use mission_id as aggregate identity."""

    def test_aggregate_id_is_mission_id(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """aggregate_id on emitted event equals the provided mission_id ULID."""
        event = emitter.emit_mission_created(
            mission_slug=_MISSION_SLUG,
            mission_number=_MISSION_NUMBER_INT,
            target_branch="main",
            wp_count=6,
            mission_id=_MISSION_ID,
        )
        assert event is not None, "emit_mission_created returned None"
        assert event["aggregate_id"] == _MISSION_ID, (
            f"Expected aggregate_id={_MISSION_ID!r}, got {event['aggregate_id']!r}"
        )

    def test_aggregate_id_is_ulid_shaped(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """aggregate_id matches the ULID character pattern."""
        event = emitter.emit_mission_created(
            mission_slug=_MISSION_SLUG,
            mission_number=_MISSION_NUMBER_INT,
            target_branch="main",
            wp_count=6,
            mission_id=_MISSION_ID,
        )
        assert event is not None
        assert _ULID_RE.match(event["aggregate_id"]), (
            f"aggregate_id {event['aggregate_id']!r} is not a valid ULID"
        )

    def test_payload_contains_mission_id(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """Payload includes mission_id field equal to meta.json mission_id."""
        event = emitter.emit_mission_created(
            mission_slug=_MISSION_SLUG,
            mission_number=_MISSION_NUMBER_INT,
            target_branch="main",
            wp_count=6,
            mission_id=_MISSION_ID,
        )
        assert event is not None
        assert "mission_id" in event["payload"], "mission_id missing from payload"
        assert event["payload"]["mission_id"] == _MISSION_ID

    def test_payload_contains_mission_slug(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """Payload retains mission_slug as display metadata."""
        event = emitter.emit_mission_created(
            mission_slug=_MISSION_SLUG,
            mission_number=_MISSION_NUMBER_INT,
            target_branch="main",
            wp_count=6,
            mission_id=_MISSION_ID,
        )
        assert event is not None
        assert event["payload"]["mission_slug"] == _MISSION_SLUG

    def test_payload_contains_mission_number(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """Payload retains mission_number as display metadata (int)."""
        event = emitter.emit_mission_created(
            mission_slug=_MISSION_SLUG,
            mission_number=_MISSION_NUMBER_INT,
            target_branch="main",
            wp_count=6,
            mission_id=_MISSION_ID,
        )
        assert event is not None
        assert event["payload"]["mission_number"] == _MISSION_NUMBER_INT

    def test_aggregate_id_is_not_mission_slug(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """Regression guard: aggregate_id must not equal mission_slug."""
        event = emitter.emit_mission_created(
            mission_slug=_MISSION_SLUG,
            mission_number=_MISSION_NUMBER_INT,
            target_branch="main",
            wp_count=6,
            mission_id=_MISSION_ID,
        )
        assert event is not None
        assert event["aggregate_id"] != _MISSION_SLUG, (
            "aggregate_id must be mission_id (ULID), not mission_slug"
        )


# ---------------------------------------------------------------------------
# T032 — emit_mission_closed: aggregate_id == mission_id
# ---------------------------------------------------------------------------


class TestEmitMissionClosedAggregateId:
    """emit_mission_closed must use mission_id as aggregate identity."""

    def test_aggregate_id_is_mission_id(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """aggregate_id on emitted event equals the provided mission_id ULID."""
        event = emitter.emit_mission_closed(
            mission_slug=_MISSION_SLUG,
            total_wps=6,
            mission_id=_MISSION_ID,
        )
        assert event is not None, "emit_mission_closed returned None"
        assert event["aggregate_id"] == _MISSION_ID, (
            f"Expected aggregate_id={_MISSION_ID!r}, got {event['aggregate_id']!r}"
        )

    def test_aggregate_id_is_ulid_shaped(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """aggregate_id matches the ULID character pattern."""
        event = emitter.emit_mission_closed(
            mission_slug=_MISSION_SLUG,
            total_wps=6,
            mission_id=_MISSION_ID,
        )
        assert event is not None
        assert _ULID_RE.match(event["aggregate_id"])

    def test_payload_contains_mission_id(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """Payload includes mission_id field."""
        event = emitter.emit_mission_closed(
            mission_slug=_MISSION_SLUG,
            total_wps=6,
            mission_id=_MISSION_ID,
        )
        assert event is not None
        assert event["payload"]["mission_id"] == _MISSION_ID

    def test_payload_contains_mission_slug(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """Payload retains mission_slug as display metadata."""
        event = emitter.emit_mission_closed(
            mission_slug=_MISSION_SLUG,
            total_wps=6,
            mission_id=_MISSION_ID,
        )
        assert event is not None
        assert event["payload"]["mission_slug"] == _MISSION_SLUG

    def test_aggregate_id_is_not_mission_slug(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """Regression guard: aggregate_id must not equal mission_slug."""
        event = emitter.emit_mission_closed(
            mission_slug=_MISSION_SLUG,
            total_wps=6,
            mission_id=_MISSION_ID,
        )
        assert event is not None
        assert event["aggregate_id"] != _MISSION_SLUG


# ---------------------------------------------------------------------------
# T032 — emit_mission_origin_bound: aggregate_id == mission_id
# ---------------------------------------------------------------------------


class TestEmitMissionOriginBoundAggregateId:
    """emit_mission_origin_bound must use mission_id as aggregate identity."""

    def test_aggregate_id_is_mission_id(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """aggregate_id on emitted event equals the provided mission_id ULID."""
        event = emitter.emit_mission_origin_bound(
            mission_slug=_MISSION_SLUG,
            provider="jira",
            external_issue_id="12345",
            external_issue_key="SK-42",
            external_issue_url="https://jira.example.com/browse/SK-42",
            title="Test origin binding",
            mission_id=_MISSION_ID,
        )
        assert event is not None, "emit_mission_origin_bound returned None"
        assert event["aggregate_id"] == _MISSION_ID, (
            f"Expected aggregate_id={_MISSION_ID!r}, got {event['aggregate_id']!r}"
        )

    def test_aggregate_id_is_ulid_shaped(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """aggregate_id matches the ULID character pattern."""
        event = emitter.emit_mission_origin_bound(
            mission_slug=_MISSION_SLUG,
            provider="linear",
            external_issue_id="LIN-99",
            external_issue_key="LIN-99",
            external_issue_url="https://linear.app/team/issue/LIN-99",
            title="Linear issue",
            mission_id=_MISSION_ID,
        )
        assert event is not None
        assert _ULID_RE.match(event["aggregate_id"])

    def test_payload_contains_mission_id(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """Payload includes mission_id field."""
        event = emitter.emit_mission_origin_bound(
            mission_slug=_MISSION_SLUG,
            provider="jira",
            external_issue_id="12345",
            external_issue_key="SK-42",
            external_issue_url="https://jira.example.com/browse/SK-42",
            title="Test origin binding",
            mission_id=_MISSION_ID,
        )
        assert event is not None
        assert event["payload"]["mission_id"] == _MISSION_ID

    def test_payload_contains_mission_slug(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """Payload retains mission_slug as display metadata."""
        event = emitter.emit_mission_origin_bound(
            mission_slug=_MISSION_SLUG,
            provider="jira",
            external_issue_id="12345",
            external_issue_key="SK-42",
            external_issue_url="https://jira.example.com/browse/SK-42",
            title="Test origin binding",
            mission_id=_MISSION_ID,
        )
        assert event is not None
        assert event["payload"]["mission_slug"] == _MISSION_SLUG

    def test_aggregate_id_is_not_mission_slug(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """Regression guard: aggregate_id must not equal mission_slug."""
        event = emitter.emit_mission_origin_bound(
            mission_slug=_MISSION_SLUG,
            provider="jira",
            external_issue_id="12345",
            external_issue_key="SK-42",
            external_issue_url="https://jira.example.com/browse/SK-42",
            title="Test origin binding",
            mission_id=_MISSION_ID,
        )
        assert event is not None
        assert event["aggregate_id"] != _MISSION_SLUG


# ---------------------------------------------------------------------------
# T033 — mission_number type in payload (int | null, never string)
# ---------------------------------------------------------------------------


class TestMissionNumberTypeInPayload:
    """mission_number must serialize as int or null, never as a string."""

    def test_pre_merge_mission_number_is_json_null(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """Pre-merge mission: mission_number=None serializes as JSON null."""
        event = emitter.emit_mission_created(
            mission_slug=_MISSION_SLUG,
            mission_number=None,
            target_branch="main",
            wp_count=0,
            mission_id=_MISSION_ID,
        )
        assert event is not None
        payload_json = json.dumps(event["payload"])
        parsed = json.loads(payload_json)
        # Must be null (None in Python), not "", not "pending", not absent
        assert "mission_number" in parsed, "mission_number key missing from payload"
        assert parsed["mission_number"] is None, (
            f"Expected null, got {parsed['mission_number']!r}"
        )
        # Paranoia: raw JSON string must contain the null literal
        assert '"mission_number": null' in payload_json or '"mission_number":null' in payload_json

    def test_post_merge_mission_number_is_json_integer(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """Post-merge mission: mission_number=42 serializes as JSON integer 42."""
        event = emitter.emit_mission_created(
            mission_slug="042-my-feature",
            mission_number=42,
            target_branch="main",
            wp_count=3,
            mission_id=_MISSION_ID,
        )
        assert event is not None
        payload_json = json.dumps(event["payload"])
        parsed = json.loads(payload_json)
        assert parsed["mission_number"] == 42
        assert isinstance(parsed["mission_number"], int), (
            f"Expected int, got {type(parsed['mission_number'])}"
        )
        # Must not be a string like "42" or "042"
        assert '"mission_number": 42' in payload_json or '"mission_number":42' in payload_json

    def test_mission_number_never_empty_string(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """mission_number must not be an empty string in the payload JSON."""
        # This test catches regression where "" was emitted instead of null
        event = emitter.emit_mission_created(
            mission_slug=_MISSION_SLUG,
            mission_number=None,
            target_branch="main",
            wp_count=0,
            mission_id=_MISSION_ID,
        )
        assert event is not None
        payload_json = json.dumps(event["payload"])
        # Ensure we don't see the legacy empty-string sentinel
        assert '"mission_number": ""' not in payload_json
        assert '"mission_number":""' not in payload_json

    def test_mission_number_type_coercion_guard(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
    ) -> None:
        """mission_number=83 (int) round-trips as integer 83 through JSON."""
        event = emitter.emit_mission_created(
            mission_slug="083-mission-id",
            mission_number=83,
            target_branch="main",
            wp_count=14,
            mission_id=_MISSION_ID,
        )
        assert event is not None
        parsed = json.loads(json.dumps(event["payload"]))
        assert parsed["mission_number"] == 83
        assert not isinstance(parsed["mission_number"], str)
