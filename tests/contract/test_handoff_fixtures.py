"""Contract tests: validate fixture data against Pydantic Event model.

These tests prove that the fixture data in contracts/batch-api-contract.md
and contracts/fixtures/ is valid according to the CLI's Pydantic Event model
and the payload validation rules defined in the EventEmitter.

Run: python -m pytest tests/contract/test_handoff_fixtures.py -v
"""

import json
from pathlib import Path

import pytest

from specify_cli.spec_kitty_events.models import Event
from specify_cli.sync.emitter import _PAYLOAD_RULES, VALID_EVENT_TYPES

# ---------------------------------------------------------------------------
# Fixture data: one event per documented event type.
# These match the examples in contracts/batch-api-contract.md.
# ---------------------------------------------------------------------------

FIXTURE_EVENTS = [
    # 1. WPStatusChanged (from fixture_01)
    {
        "event_id": "01JMBY7K8N3QRVX2DPFG5HWT4E",
        "event_type": "WPStatusChanged",
        "aggregate_id": "WP01",
        "payload": {
            "wp_id": "WP01",
            "from_lane": "planned",
            "to_lane": "in_progress",
            "actor": "claude-agent",
            "feature_slug": "039-cli-2x-readiness",
        },
        "timestamp": "2026-02-12T10:00:00+00:00",
        "node_id": "a1b2c3d4e5f6",
        "lamport_clock": 1,
        "causation_id": None,
    },
    # 2. WPCreated (from fixture_02)
    {
        "event_id": "01JMBYA1B2C3D4E5F6G7H8J9KB",
        "event_type": "WPCreated",
        "aggregate_id": "WP10",
        "payload": {
            "wp_id": "WP10",
            "title": "End-to-end integration test suite",
            "feature_slug": "039-cli-2x-readiness",
            "dependencies": ["WP02", "WP03"],
        },
        "timestamp": "2026-02-12T11:01:00+00:00",
        "node_id": "a1b2c3d4e5f6",
        "lamport_clock": 11,
        "causation_id": None,
    },
    # 3. WPAssigned
    {
        "event_id": "01JMBYD5E6F7G8H9J0K1W2MACP",
        "event_type": "WPAssigned",
        "aggregate_id": "WP07",
        "payload": {
            "wp_id": "WP07",
            "agent_id": "wp07-agent",
            "phase": "implementation",
            "retry_count": 0,
        },
        "timestamp": "2026-02-12T10:26:30+00:00",
        "node_id": "a1b2c3d4e5f6",
        "lamport_clock": 5,
        "causation_id": None,
    },
    # 4. FeatureCreated (from fixture_02)
    {
        "event_id": "01JMBYA1B2C3D4E5F6G7H8J9KC",
        "event_type": "FeatureCreated",
        "aggregate_id": "040-next-feature",
        "payload": {
            "feature_slug": "040-next-feature",
            "feature_number": "040",
            "target_branch": "main",
            "wp_count": 5,
            "created_at": "2026-02-12T11:02:00+00:00",
        },
        "timestamp": "2026-02-12T11:02:00+00:00",
        "node_id": "a1b2c3d4e5f6",
        "lamport_clock": 12,
        "causation_id": None,
    },
    # 5. FeatureCompleted
    {
        "event_id": "01JMBYE6F7G8H9J0K1W2M3NBDQ",
        "event_type": "FeatureCompleted",
        "aggregate_id": "039-cli-2x-readiness",
        "payload": {
            "feature_slug": "039-cli-2x-readiness",
            "total_wps": 9,
            "completed_at": "2026-02-12T18:00:00+00:00",
            "total_duration": "8h 30m",
        },
        "timestamp": "2026-02-12T18:00:00+00:00",
        "node_id": "a1b2c3d4e5f6",
        "lamport_clock": 100,
        "causation_id": None,
    },
    # 6. HistoryAdded
    {
        "event_id": "01JMBYF7G8H9J0K1W2M3N4PCER",
        "event_type": "HistoryAdded",
        "aggregate_id": "WP07",
        "payload": {
            "wp_id": "WP07",
            "entry_type": "note",
            "entry_content": "Completed contract document with fixture data",
            "author": "wp07-agent",
        },
        "timestamp": "2026-02-12T14:00:00+00:00",
        "node_id": "a1b2c3d4e5f6",
        "lamport_clock": 50,
        "causation_id": None,
    },
    # 7. ErrorLogged
    {
        "event_id": "01JMBYG8H9J0K1W2M3N4P5QDFS",
        "event_type": "ErrorLogged",
        "aggregate_id": "WP03",
        "payload": {
            "error_type": "validation",
            "error_message": "Missing required field: wp_id in WPCreated payload",
            "wp_id": "WP03",
            "stack_trace": None,
            "agent_id": "wp03-agent",
        },
        "timestamp": "2026-02-12T15:00:00+00:00",
        "node_id": "a1b2c3d4e5f6",
        "lamport_clock": 60,
        "causation_id": None,
    },
    # 8. DependencyResolved
    {
        "event_id": "01JMBYH9J0K1W2M3N4P5Q6REGT",
        "event_type": "DependencyResolved",
        "aggregate_id": "WP04",
        "payload": {
            "wp_id": "WP04",
            "dependency_wp_id": "WP02",
            "resolution_type": "completed",
        },
        "timestamp": "2026-02-12T16:00:00+00:00",
        "node_id": "a1b2c3d4e5f6",
        "lamport_clock": 70,
        "causation_id": None,
    },
]


def _event_test_id(event_data: dict) -> str:
    """Generate a human-readable test ID from fixture event."""
    return f"{event_data['event_type']}:{event_data['event_id'][:12]}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFixtureValidation:
    """Validate that every fixture event passes the Pydantic Event model."""

    @pytest.mark.parametrize(
        "event_data", FIXTURE_EVENTS, ids=_event_test_id
    )
    def test_fixture_validates_against_event_model(self, event_data: dict):
        """Each fixture event must parse successfully via the Pydantic Event model."""
        event = Event(**event_data)
        assert event.event_id == event_data["event_id"]
        assert event.event_type == event_data["event_type"]
        assert event.aggregate_id == event_data["aggregate_id"]
        assert event.lamport_clock == event_data["lamport_clock"]
        assert event.node_id == event_data["node_id"]

    @pytest.mark.parametrize(
        "event_data", FIXTURE_EVENTS, ids=_event_test_id
    )
    def test_fixture_event_id_is_valid_ulid(self, event_data: dict):
        """event_id must be exactly 26 Crockford Base32 characters."""
        import re
        ulid_pattern = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
        assert ulid_pattern.match(event_data["event_id"]), (
            f"event_id {event_data['event_id']!r} does not match ULID pattern"
        )

    @pytest.mark.parametrize(
        "event_data", FIXTURE_EVENTS, ids=_event_test_id
    )
    def test_fixture_payload_passes_emitter_rules(self, event_data: dict):
        """Each fixture payload must satisfy _PAYLOAD_RULES from the emitter."""
        event_type = event_data["event_type"]
        payload = event_data["payload"]
        rules = _PAYLOAD_RULES.get(event_type)
        assert rules is not None, (
            f"No payload rules found for event type: {event_type}"
        )

        # Check required fields
        missing = rules["required"] - set(payload.keys())
        assert not missing, (
            f"{event_type} payload missing required fields: {missing}"
        )

        # Run field-level validators
        for field_name, validator in rules["validators"].items():
            if field_name in payload:
                value = payload[field_name]
                assert validator(value), (
                    f"{event_type} payload field '{field_name}' has "
                    f"invalid value: {value!r}"
                )


class TestEventTypeCoverage:
    """Ensure fixtures cover all documented event types."""

    def test_all_event_types_covered(self):
        """Fixtures must include at least one event for each of the 8 documented types."""
        fixture_types = {e["event_type"] for e in FIXTURE_EVENTS}
        expected_types = {
            "WPStatusChanged",
            "WPCreated",
            "WPAssigned",
            "FeatureCreated",
            "FeatureCompleted",
            "HistoryAdded",
            "ErrorLogged",
            "DependencyResolved",
        }
        assert fixture_types == expected_types, (
            f"Missing types: {expected_types - fixture_types}, "
            f"Extra types: {fixture_types - expected_types}"
        )

    def test_valid_event_types_match_emitter(self):
        """Documented outbound types must match VALID_EVENT_TYPES from the emitter."""
        expected = {
            "WPStatusChanged",
            "WPCreated",
            "WPAssigned",
            "FeatureCreated",
            "FeatureCompleted",
            "HistoryAdded",
            "ErrorLogged",
            "DependencyResolved",
            "MissionDossierArtifactIndexed",
            "MissionDossierArtifactMissing",
            "MissionDossierParityDriftDetected",
            "MissionDossierSnapshotComputed",
        }
        assert VALID_EVENT_TYPES == expected


class TestFixtureJsonFiles:
    """Validate the fixture JSON files in contracts/fixtures/."""

    FIXTURES_DIR = (
        Path(__file__).resolve().parent.parent.parent
        / "contracts"
        / "fixtures"
    )

    def _load_fixture(self, filename: str) -> dict:
        """Load and parse a fixture JSON file."""
        path = self.FIXTURES_DIR / filename
        assert path.exists(), f"Fixture file not found: {path}"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_fixture_01_events_validate(self):
        """fixture_01 events pass Pydantic Event model."""
        data = self._load_fixture("fixture_01_single_wp_status_changed.json")
        for event_data in data["request"]["events"]:
            # Extract core fields for the Pydantic model
            core = {
                "event_id": event_data["event_id"],
                "event_type": event_data["event_type"],
                "aggregate_id": event_data["aggregate_id"],
                "payload": event_data["payload"],
                "timestamp": event_data["timestamp"],
                "node_id": event_data["node_id"],
                "lamport_clock": event_data["lamport_clock"],
                "causation_id": event_data.get("causation_id"),
            }
            event = Event(**core)
            assert event.event_id == event_data["event_id"]

    def test_fixture_02_events_validate(self):
        """fixture_02 events (mixed batch) pass Pydantic Event model."""
        data = self._load_fixture("fixture_02_mixed_batch.json")
        assert len(data["request"]["events"]) == 3
        for event_data in data["request"]["events"]:
            core = {
                "event_id": event_data["event_id"],
                "event_type": event_data["event_type"],
                "aggregate_id": event_data["aggregate_id"],
                "payload": event_data["payload"],
                "timestamp": event_data["timestamp"],
                "node_id": event_data["node_id"],
                "lamport_clock": event_data["lamport_clock"],
                "causation_id": event_data.get("causation_id"),
            }
            Event(**core)

    def test_fixture_03_is_same_event_id_as_fixture_01(self):
        """fixture_03 (duplicate) must use the same event_id as fixture_01."""
        f01 = self._load_fixture("fixture_01_single_wp_status_changed.json")
        f03 = self._load_fixture("fixture_03_duplicate_event.json")
        assert (
            f01["request"]["events"][0]["event_id"]
            == f03["request"]["events"][0]["event_id"]
        )

    def test_fixture_04_has_rejection(self):
        """fixture_04 expected response has 'rejected' status."""
        data = self._load_fixture("fixture_04_rejected_event.json")
        results = data["expected_response"]["body"]["results"]
        assert len(results) == 1
        assert results[0]["status"] == "rejected"
        assert "error" in results[0]

    def test_fixture_05_is_http_400(self):
        """fixture_05 expected response is HTTP 400 with error and details."""
        data = self._load_fixture("fixture_05_http_400_error.json")
        assert data["expected_response"]["status_code"] == 400
        body = data["expected_response"]["body"]
        assert "error" in body
        assert "details" in body


class TestLaneMapping:
    """Validate canonical 7-lane payload in fixtures."""

    def test_wp_status_changed_uses_canonical_7_lane_values(self):
        """WPStatusChanged fixture events use canonical 7-lane values."""
        valid_lanes = {"planned", "claimed", "in_progress", "for_review", "done", "blocked", "canceled"}
        for event_data in FIXTURE_EVENTS:
            if event_data["event_type"] == "WPStatusChanged":
                payload = event_data["payload"]
                assert payload["from_lane"] in valid_lanes, (
                    f"Invalid from_lane: {payload['from_lane']}"
                )
                assert payload["to_lane"] in valid_lanes, (
                    f"Invalid to_lane: {payload['to_lane']}"
                )
