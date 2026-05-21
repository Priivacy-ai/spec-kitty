"""Tests for spec-kitty sync diagnose validation module.

Covers envelope validation (Pydantic Event model), extended envelope
checks, and per-event-type payload validation using ``_PAYLOAD_RULES``.
"""

from __future__ import annotations

from datetime import datetime, UTC

from specify_cli.sync.diagnose import DiagnoseResult, diagnose_events

import pytest

pytestmark = pytest.mark.fast


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
            "from_lane": "planned",
            "to_lane": "in_progress",
            "actor": "test-agent",
            "mission_slug": "039-test",
            "execution_mode": "direct_repo",
        },
        "timestamp": datetime.now(UTC).isoformat(),
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
        assert any("event_type" in e.lower() or "unknown" in e.lower() for e in results[0].errors)


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

    def test_payload_missing_from_lane(self):
        """WPStatusChanged payload missing from_lane fails."""
        event = _make_valid_event()
        del event["payload"]["from_lane"]
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("from_lane" in e for e in results[0].errors)

    def test_payload_missing_to_lane(self):
        """WPStatusChanged payload missing to_lane fails."""
        event = _make_valid_event()
        del event["payload"]["to_lane"]
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("to_lane" in e for e in results[0].errors)

    def test_payload_invalid_wp_id_format(self):
        """WPStatusChanged with invalid wp_id format (not WP##) fails."""
        event = _make_valid_event()
        event["payload"]["wp_id"] = "bad-id"
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("wp_id" in e for e in results[0].errors)

    def test_payload_invalid_from_lane_value(self):
        """WPStatusChanged with unknown from_lane lane fails."""
        event = _make_valid_event()
        event["payload"]["from_lane"] = "nonexistent_lane"
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("from_lane" in e for e in results[0].errors)

    def test_payload_invalid_to_lane_value(self):
        """WPStatusChanged with unknown to_lane lane fails."""
        event = _make_valid_event()
        event["payload"]["to_lane"] = "nonexistent_lane"
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("to_lane" in e for e in results[0].errors)


# ---------------------------------------------------------------------------
# Payload validation -- other event types
# ---------------------------------------------------------------------------


class TestOtherPayloads:
    """Validate payloads for non-WPStatusChanged event types."""

    def test_wp_created_valid(self):
        """WPCreated with canonical payload passes.

        Payload keys follow events 5.1.0 ``wp_created_payload`` schema:
        ``wp_title`` (not ``title``), ``depends_on`` (not ``dependencies``),
        ``actor`` required. See Priivacy-ai/spec-kitty#1203 mask 1.
        """
        event = _make_valid_event(
            event_type="WPCreated",
            payload={
                "wp_id": "WP01",
                "wp_title": "First work package",
                "mission_slug": "039-test",
                "depends_on": [],
                "actor": "cli",
            },
        )
        results = diagnose_events([event])
        assert results[0].valid is True

    def test_wp_created_missing_title(self):
        """WPCreated missing wp_title fails."""
        event = _make_valid_event(
            event_type="WPCreated",
            payload={
                "wp_id": "WP01",
                "mission_slug": "039-test",
                "actor": "cli",
            },
        )
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("wp_title" in e for e in results[0].errors)

    def test_mission_created_valid(self):
        """MissionCreated with valid payload passes."""
        event = _make_valid_event(
            event_type="MissionCreated",
            aggregate_id="039-test-feature",
            aggregate_type="Mission",
            payload={
                "mission_slug": "039-test-feature",
                "mission_number": 39,  # int, not str (FR-044, WP02)
                "mission_type": "software-dev",
                "target_branch": "main",
                "wp_count": 5,
                "friendly_name": "039 Test Feature",
                "purpose_tldr": "039 Test Feature",
                "purpose_context": "Deliver 039 Test Feature on main.",
            },
        )
        results = diagnose_events([event])
        assert results[0].valid is True

    def test_mission_created_invalid_slug_format(self):
        """MissionCreated with invalid mission_slug format fails."""
        event = _make_valid_event(
            event_type="MissionCreated",
            aggregate_id="bad",
            aggregate_type="Mission",
            payload={
                "mission_slug": "BAD FORMAT",
                "mission_number": 39,  # int, not str (FR-044, WP02)
                "target_branch": "main",
                "wp_count": 5,
            },
        )
        results = diagnose_events([event])
        assert results[0].valid is False
        assert any("mission_slug" in e for e in results[0].errors)


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


# ---------------------------------------------------------------------------
# Canonical-registry recognition (#1222)
# ---------------------------------------------------------------------------


def _has_unknown_event_type_error(result) -> bool:
    """True iff *result* has the diagnose "unknown event type" recognition
    error (as opposed to other event_type-mentioning Pydantic envelope errors
    such as 'event_type: Field required'). The recognition error always
    contains the substring ``"unknown event type"``.
    """
    return any("unknown event type" in e for e in result.errors)


class TestCanonicalRegistryRecognition:
    """Diagnose recognises every event type in the canonical
    ``spec_kitty_events.conformance.validators._EVENT_TYPE_TO_MODEL``
    registry plus the CLI-internal types from ``emitter._PAYLOAD_RULES``.

    This is the regression for Priivacy-ai/spec-kitty#1222 — before the
    fix, ``diagnose`` only recognised the 26 types in ``_PAYLOAD_RULES``
    (the emitter's outbound allowlist) and surfaced canonical-registry
    types (``TasksCompleted``, ``PlanCompleted``, ``GatePassed``, etc.)
    as ``"unknown event type"``.
    """

    def test_recognises_every_registry_type(self):
        """FR-001 — every key in the canonical registry is recognised."""
        from spec_kitty_events.conformance.validators import (
            _EVENT_TYPE_TO_MODEL,
        )

        offenders: list[str] = []
        for event_type in sorted(_EVENT_TYPE_TO_MODEL.keys()):
            event = _make_valid_event(event_type=event_type)
            results = diagnose_events([event])
            if _has_unknown_event_type_error(results[0]):
                offenders.append(event_type)
        assert offenders == [], (
            "diagnose flagged these canonical-registry event types as unknown: "
            f"{offenders}"
        )

    def test_recognises_cli_internal_types(self):
        """FR-002 — CLI-internal types (in `_PAYLOAD_RULES` but NOT in the
        canonical registry) continue to be recognised.

        These are the 7 types the CLI emits locally and validates against
        `_PAYLOAD_RULES` even though the canonical events package has no
        model for them (yet).
        """
        cli_internal_types = [
            "BuildHeartbeat",
            "BuildRegistered",
            "DependencyResolved",
            "ErrorLogged",
            "HistoryAdded",
            "MissionOriginBound",
            "WPAssigned",
        ]
        offenders: list[str] = []
        for event_type in cli_internal_types:
            event = _make_valid_event(event_type=event_type)
            results = diagnose_events([event])
            if _has_unknown_event_type_error(results[0]):
                offenders.append(event_type)
        assert offenders == [], (
            "diagnose flagged these CLI-internal event types as unknown: "
            f"{offenders}"
        )

    def test_rejects_genuinely_unknown_type(self):
        """FR-003 — a string in neither set is rejected with a clear error
        that mentions the offending value.
        """
        sentinel = "ThisIsDefinitelyNotARealEventType_x9q3"
        event = _make_valid_event(event_type=sentinel)
        results = diagnose_events([event])
        assert results[0].valid is False
        assert _has_unknown_event_type_error(results[0])
        assert any(sentinel in e for e in results[0].errors), (
            "diagnose error did not mention the offending value: "
            f"{results[0].errors!r}"
        )

    def test_drift_detector_picks_up_new_registry_entries(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """FR-004 — the recognition set is genuinely derived from the
        canonical registry at module-load time. If the events package
        ships a new event type, diagnose recognises it automatically
        — no code change in this repo.

        We prove this by inserting a synthetic entry into the canonical
        registry, reloading the diagnose module (which recomputes
        ``KNOWN_EVENT_TYPES``), and asserting the synthetic type is
        recognised.
        """
        import importlib
        from spec_kitty_events.conformance import validators as _validators

        synthetic_type = "_DriftDetectorSentinelEvent"
        # Use a placeholder model — diagnose only checks membership of the
        # *key*, not the value. The existing Event model is a convenient
        # placeholder that already imports cleanly.
        from spec_kitty_events import Event as _PlaceholderModel

        # Patch the canonical registry to include the synthetic type.
        monkeypatch.setitem(
            _validators._EVENT_TYPE_TO_MODEL,
            synthetic_type,
            _PlaceholderModel,
        )

        # Reload the diagnose module so it recomputes KNOWN_EVENT_TYPES
        # from the now-patched canonical registry.
        from specify_cli.sync import diagnose as _diagnose_mod

        try:
            importlib.reload(_diagnose_mod)

            event = _make_valid_event(event_type=synthetic_type)
            results = _diagnose_mod.diagnose_events([event])

            assert not _has_unknown_event_type_error(results[0]), (
                "drift detector: diagnose did NOT pick up the synthetic "
                f"registry entry {synthetic_type!r} after reload. Errors: "
                f"{results[0].errors!r}"
            )
        finally:
            # Restore the original module-level state so subsequent tests
            # in this process see the un-patched recognition set.
            importlib.reload(_diagnose_mod)
