"""Tests for spec-kitty sync diagnose validation module.

Covers envelope validation (Pydantic Event model), extended envelope
checks, and per-event-type payload validation using ``_PAYLOAD_RULES``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from specify_cli.sync.diagnose import DiagnoseResult, diagnose_events


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

# Pre-generated 26-char ULID strings for deterministic tests
_ULID_DEFAULT = "01KH8PBENZ9QGY8HFFC6G3BVKT"
_ULID_ALT_1 = "01KH8PBENZ9QGY8HFFC6G3BVK1"
_ULID_ALT_2 = "01KH8PBENZ9QGY8HFFC6G3BVK2"


def _make_valid_event(**overrides) -> dict:
    """Return a fully valid event dict matching the Event model + payload rules.

    All required fields are present with correct types/formats.
    ``overrides`` are merged on top (use ``payload={...}`` to replace
    the entire payload).
    """
    base = {
        "event_id": _ULID_DEFAULT,
        "event_type": "WPStatusChanged",
        "aggregate_id": "WP01",
        "aggregate_type": "WorkPackage",
        "payload": {
            "wp_id": "WP01",
            "previous_status": "planned",
            "new_status": "doing",
            "changed_by": "test-agent",
            "feature_slug": "039-test",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node_id": "test-node",
        "lamport_clock": 1,
        "causation_id": None,
        "team_slug": "test-team",
        "project_uuid": "550e8400-e29b-41d4-a716-446655440000",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Envelope validation (T016)
# ---------------------------------------------------------------------------

class TestEnvelopeValidation:
    """Validate events against the Pydantic Event model."""

    def test_valid_event_passes(self):
        """A well-formed event passes all validation checks."""
        results = diagnose_events([_make_valid_event()])
        assert len(results) == 1
        assert results[0].valid is True
        assert results[0].errors == []
        assert results[0].event_type == "WPStatusChanged"

    def test_missing_event_id(self):
        """Event missing event_id reports specific error."""
        event = _make_valid_event()
        del event["event_id"]
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("event_id" in e for e in results[0].errors)
        assert results[0].event_id == "unknown"

    def test_invalid_ulid_too_short(self):
        """Event with wrong-length event_id reports format error."""
        event = _make_valid_event(event_id="short")
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("event_id" in e for e in results[0].errors)

    def test_invalid_ulid_too_long(self):
        """Event with event_id longer than 26 chars fails."""
        event = _make_valid_event(event_id="A" * 27)
        results = diagnose_events([event])
        assert results[0].valid is False

    def test_invalid_lamport_clock_type(self):
        """Event with string lamport_clock reports type error."""
        event = _make_valid_event(lamport_clock="not-an-int")
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("lamport_clock" in e for e in results[0].errors)

    def test_negative_lamport_clock(self):
        """Event with negative lamport_clock fails ge=0 constraint."""
        event = _make_valid_event(lamport_clock=-1)
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("lamport_clock" in e for e in results[0].errors)

    def test_missing_event_type(self):
        """Event missing event_type fails."""
        event = _make_valid_event()
        del event["event_type"]
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("event_type" in e for e in results[0].errors)

    def test_missing_aggregate_id(self):
        """Event missing aggregate_id fails."""
        event = _make_valid_event()
        del event["aggregate_id"]
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("aggregate_id" in e for e in results[0].errors)

    def test_missing_timestamp(self):
        """Event missing timestamp fails."""
        event = _make_valid_event()
        del event["timestamp"]
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("timestamp" in e for e in results[0].errors)

    def test_missing_node_id(self):
        """Event missing node_id fails."""
        event = _make_valid_event()
        del event["node_id"]
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("node_id" in e for e in results[0].errors)


# ---------------------------------------------------------------------------
# Extended envelope checks
# ---------------------------------------------------------------------------

class TestExtendedEnvelope:
    """Extended checks for aggregate_type and event_type membership."""

    def test_invalid_aggregate_type(self):
        """Unknown aggregate_type produces an error."""
        event = _make_valid_event(aggregate_type="BadType")
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("aggregate_type" in e for e in results[0].errors)

    def test_unknown_event_type(self):
        """Unknown event_type produces an error."""
        event = _make_valid_event(event_type="NotARealEvent")
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any(
            "event_type" in e.lower() or "unknown" in e.lower()
            for e in results[0].errors
        )


# ---------------------------------------------------------------------------
# Payload validation -- WPStatusChanged (T017)
# ---------------------------------------------------------------------------

class TestWPStatusChangedPayload:
    """Validate WPStatusChanged payloads against emitter rules."""

    def test_valid_payload_passes(self):
        """WPStatusChanged with valid payload passes."""
        results = diagnose_events([_make_valid_event()])
        assert results[0].valid is True

    def test_payload_missing_required_wp_id(self):
        """WPStatusChanged payload missing wp_id reports error."""
        event = _make_valid_event()
        del event["payload"]["wp_id"]
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("wp_id" in e for e in results[0].errors)

    def test_payload_missing_previous_status(self):
        """WPStatusChanged payload missing previous_status fails."""
        event = _make_valid_event()
        del event["payload"]["previous_status"]
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("previous_status" in e for e in results[0].errors)

    def test_payload_missing_new_status(self):
        """WPStatusChanged payload missing new_status fails."""
        event = _make_valid_event()
        del event["payload"]["new_status"]
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("new_status" in e for e in results[0].errors)

    def test_payload_invalid_wp_id_format(self):
        """WPStatusChanged with invalid wp_id format (not WP##) fails."""
        event = _make_valid_event()
        event["payload"]["wp_id"] = "bad-id"
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("wp_id" in e for e in results[0].errors)

    def test_payload_invalid_previous_status_value(self):
        """WPStatusChanged with unknown previous_status lane fails."""
        event = _make_valid_event()
        event["payload"]["previous_status"] = "nonexistent_lane"
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("previous_status" in e for e in results[0].errors)

    def test_payload_invalid_new_status_value(self):
        """WPStatusChanged with unknown new_status lane fails."""
        event = _make_valid_event()
        event["payload"]["new_status"] = "nonexistent_lane"
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("new_status" in e for e in results[0].errors)


# ---------------------------------------------------------------------------
# Payload validation -- other event types
# ---------------------------------------------------------------------------

class TestOtherPayloads:
    """Validate payloads for non-WPStatusChanged event types."""

    def test_wp_created_valid(self):
        """WPCreated with valid payload passes."""
        event = _make_valid_event(
            event_type="WPCreated",
            payload={
                "wp_id": "WP01",
                "title": "First work package",
                "feature_slug": "039-test",
                "dependencies": [],
            },
        )
        results = diagnose_events([event])
        assert results[0].valid is True

    def test_wp_created_missing_title(self):
        """WPCreated missing title fails."""
        event = _make_valid_event(
            event_type="WPCreated",
            payload={
                "wp_id": "WP01",
                "feature_slug": "039-test",
            },
        )
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("title" in e for e in results[0].errors)

    def test_feature_created_valid(self):
        """FeatureCreated with valid payload passes."""
        event = _make_valid_event(
            event_type="FeatureCreated",
            aggregate_id="039-test-feature",
            aggregate_type="Feature",
            payload={
                "feature_slug": "039-test-feature",
                "feature_number": "039",
                "target_branch": "main",
                "wp_count": 5,
            },
        )
        results = diagnose_events([event])
        assert results[0].valid is True

    def test_feature_created_invalid_slug_format(self):
        """FeatureCreated with invalid feature_slug format fails."""
        event = _make_valid_event(
            event_type="FeatureCreated",
            aggregate_id="bad",
            aggregate_type="Feature",
            payload={
                "feature_slug": "BAD FORMAT",
                "feature_number": "039",
                "target_branch": "main",
                "wp_count": 5,
            },
        )
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("feature_slug" in e for e in results[0].errors)


# ---------------------------------------------------------------------------
# Batch / mixed results (T019)
# ---------------------------------------------------------------------------

class TestMixedBatch:
    """Batch of valid + invalid events returns correct counts."""

    def test_mixed_batch(self):
        """Batch with 2 valid and 1 invalid yields correct totals."""
        valid1 = _make_valid_event(event_id=_ULID_ALT_1)
        valid2 = _make_valid_event(event_id=_ULID_ALT_2)
        invalid = _make_valid_event(event_id="short")  # bad ULID

        results = diagnose_events([valid1, valid2, invalid])
        assert len(results) == 3

        valid_count = sum(1 for r in results if r.valid)
        invalid_count = sum(1 for r in results if not r.valid)
        assert valid_count == 2
        assert invalid_count == 1

    def test_empty_queue(self):
        """Empty input yields empty results."""
        results = diagnose_events([])
        assert results == []

    def test_all_invalid(self):
        """All malformed events correctly report as invalid."""
        bad1 = _make_valid_event(event_id="x")
        bad2 = _make_valid_event(lamport_clock="string")
        results = diagnose_events([bad1, bad2])
        assert all(not r.valid for r in results)

    def test_all_valid(self):
        """All well-formed events correctly report as valid."""
        e1 = _make_valid_event(event_id=_ULID_ALT_1)
        e2 = _make_valid_event(event_id=_ULID_ALT_2)
        results = diagnose_events([e1, e2])
        assert all(r.valid for r in results)


# ---------------------------------------------------------------------------
# Error categorization reuse (WP02)
# ---------------------------------------------------------------------------

class TestErrorCategorization:
    """Verify diagnose reuses batch.py error categorization."""

    def test_schema_mismatch_category(self):
        """Missing required field error categorised as schema_mismatch."""
        event = _make_valid_event()
        del event["event_type"]
        results = diagnose_events([event])
        assert results[0].valid is False
        # The error message contains "field" keyword which
        # categorize_error maps to "schema_mismatch"
        assert results[0].error_category == "schema_mismatch"

    def test_valid_event_has_no_category(self):
        """Valid events have empty error_category."""
        results = diagnose_events([_make_valid_event()])
        assert results[0].error_category == ""


# ---------------------------------------------------------------------------
# DiagnoseResult dataclass
# ---------------------------------------------------------------------------

class TestDiagnoseResult:
    """DiagnoseResult dataclass structure tests."""

    def test_defaults(self):
        """DiagnoseResult defaults are sensible."""
        r = DiagnoseResult(event_id="abc", valid=True)
        assert r.errors == []
        assert r.event_type == ""
        assert r.error_category == ""

    def test_with_errors(self):
        """DiagnoseResult stores error list correctly."""
        r = DiagnoseResult(
            event_id="abc",
            valid=False,
            errors=["field missing", "type wrong"],
            event_type="WPStatusChanged",
            error_category="schema_mismatch",
        )
        assert len(r.errors) == 2
        assert r.error_category == "schema_mismatch"
