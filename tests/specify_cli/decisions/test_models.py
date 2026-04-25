"""Unit tests for specify_cli.decisions.models.

Covers enum values, IndexEntry field constraints, model validators,
JSON round-trips, and response model construction.
"""

from __future__ import annotations

from datetime import datetime, UTC

import pytest
from pydantic import ValidationError

from specify_cli.decisions.models import (
    DecisionErrorCode,
    DecisionIndex,
    DecisionOpenResponse,
    DecisionStatus,
    DecisionTerminalResponse,
    IndexEntry,
    OriginFlow,
    logical_key,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NOW = datetime(2026, 4, 23, 10, 0, 0, tzinfo=UTC)
ULID = "01KPWT8PNY8683QX3WBW6VXYM7"
MISSION = "my-mission-id"
SLUG = "my-mission-slug"


def _make_entry(**overrides: object) -> IndexEntry:
    defaults: dict = {
        "decision_id": ULID,
        "origin_flow": OriginFlow.SPECIFY,
        "step_id": "specify.step1",
        "input_key": "auth_strategy",
        "question": "Which auth strategy?",
        "status": DecisionStatus.OPEN,
        "created_at": NOW,
        "mission_id": MISSION,
        "mission_slug": SLUG,
    }
    defaults.update(overrides)
    return IndexEntry(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Enum value tests
# ---------------------------------------------------------------------------


class TestOriginFlowEnum:
    def test_charter_value(self) -> None:
        assert OriginFlow.CHARTER == "charter"
        assert OriginFlow.CHARTER.value == "charter"

    def test_specify_value(self) -> None:
        assert OriginFlow.SPECIFY == "specify"

    def test_plan_value(self) -> None:
        assert OriginFlow.PLAN == "plan"

    def test_all_members(self) -> None:
        values = {m.value for m in OriginFlow}
        assert values == {"charter", "specify", "plan"}


class TestDecisionStatusEnum:
    def test_open(self) -> None:
        assert DecisionStatus.OPEN == "open"

    def test_resolved(self) -> None:
        assert DecisionStatus.RESOLVED == "resolved"

    def test_deferred(self) -> None:
        assert DecisionStatus.DEFERRED == "deferred"

    def test_canceled(self) -> None:
        assert DecisionStatus.CANCELED == "canceled"


class TestDecisionErrorCodeEnum:
    def test_missing_step_or_slot(self) -> None:
        assert DecisionErrorCode.MISSING_STEP_OR_SLOT == "DECISION_MISSING_STEP_OR_SLOT"

    def test_already_closed(self) -> None:
        assert DecisionErrorCode.ALREADY_CLOSED == "DECISION_ALREADY_CLOSED"

    def test_terminal_conflict(self) -> None:
        assert DecisionErrorCode.TERMINAL_CONFLICT == "DECISION_TERMINAL_CONFLICT"

    def test_not_found(self) -> None:
        assert DecisionErrorCode.NOT_FOUND == "DECISION_NOT_FOUND"

    def test_mission_not_found(self) -> None:
        assert DecisionErrorCode.MISSION_NOT_FOUND == "MISSION_NOT_FOUND"

    def test_verify_drift(self) -> None:
        assert DecisionErrorCode.VERIFY_DRIFT == "DECISION_VERIFY_DRIFT"


# ---------------------------------------------------------------------------
# IndexEntry construction
# ---------------------------------------------------------------------------


class TestIndexEntryConstruction:
    def test_step_id_only_valid(self) -> None:
        entry = _make_entry(step_id="step1", slot_key=None)
        assert entry.step_id == "step1"
        assert entry.slot_key is None

    def test_slot_key_only_valid(self) -> None:
        entry = _make_entry(step_id=None, slot_key="specify.slot1")
        assert entry.slot_key == "specify.slot1"
        assert entry.step_id is None

    def test_both_set_valid(self) -> None:
        entry = _make_entry(step_id="step1", slot_key="slot1")
        assert entry.step_id == "step1"
        assert entry.slot_key == "slot1"

    def test_neither_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_entry(step_id=None, slot_key=None)

    def test_empty_input_key_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_entry(input_key="")

    def test_empty_question_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_entry(question="")

    def test_extra_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            IndexEntry(  # type: ignore[call-arg]
                decision_id=ULID,
                origin_flow=OriginFlow.SPECIFY,
                step_id="s1",
                input_key="k",
                question="q",
                status=DecisionStatus.OPEN,
                created_at=NOW,
                mission_id=MISSION,
                mission_slug=SLUG,
                unknown_field="oops",
            )

    def test_frozen(self) -> None:
        entry = _make_entry()
        with pytest.raises(ValidationError):
            entry.input_key = "new"  # type: ignore[misc]

    def test_defaults(self) -> None:
        entry = _make_entry()
        assert entry.options == ()
        assert entry.final_answer is None
        assert entry.rationale is None
        assert entry.other_answer is False
        assert entry.resolved_at is None
        assert entry.resolved_by is None


# ---------------------------------------------------------------------------
# IndexEntry round-trip
# ---------------------------------------------------------------------------


class TestIndexEntryRoundTrip:
    def test_json_round_trip(self) -> None:
        entry = _make_entry(options=("a", "b", "c"))
        json_str = entry.model_dump_json()
        restored = IndexEntry.model_validate_json(json_str)
        assert restored.decision_id == entry.decision_id
        assert restored.origin_flow == entry.origin_flow
        assert restored.options == entry.options
        assert restored.created_at == entry.created_at


# ---------------------------------------------------------------------------
# DecisionIndex
# ---------------------------------------------------------------------------


class TestDecisionIndex:
    def test_default_empty(self) -> None:
        idx = DecisionIndex(mission_id=MISSION)
        assert idx.version == 1
        assert idx.entries == ()

    def test_json_round_trip_multiple_entries(self) -> None:
        e1 = _make_entry(decision_id=ULID, step_id="step1")
        e2 = _make_entry(
            decision_id="01KPWT8PNY8683QX3WBW6VXYM8",
            step_id="step2",
            input_key="deployment_target",
            question="Where to deploy?",
        )
        idx = DecisionIndex(mission_id=MISSION, entries=(e1, e2))
        json_str = idx.model_dump_json()
        restored = DecisionIndex.model_validate_json(json_str)
        assert len(restored.entries) == 2
        assert restored.entries[0].decision_id == e1.decision_id
        assert restored.entries[1].decision_id == e2.decision_id

    def test_version_literal(self) -> None:
        idx = DecisionIndex(mission_id=MISSION)
        assert idx.version == 1

    def test_extra_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            DecisionIndex(mission_id=MISSION, bogus=True)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# logical_key helper
# ---------------------------------------------------------------------------


class TestLogicalKey:
    def test_step_id_used_when_set(self) -> None:
        entry = _make_entry(step_id="step1", slot_key=None)
        key = logical_key(entry)
        assert key == (MISSION, OriginFlow.SPECIFY, "step1", "auth_strategy")

    def test_slot_key_used_when_step_id_none(self) -> None:
        entry = _make_entry(step_id=None, slot_key="specify.slot1")
        key = logical_key(entry)
        assert key == (MISSION, OriginFlow.SPECIFY, "specify.slot1", "auth_strategy")

    def test_step_id_preferred_over_slot_key(self) -> None:
        entry = _make_entry(step_id="step1", slot_key="slot1")
        key = logical_key(entry)
        assert key[2] == "step1"

    def test_stable_across_constructions(self) -> None:
        e1 = _make_entry(step_id="same-step")
        e2 = _make_entry(step_id="same-step")
        assert logical_key(e1) == logical_key(e2)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class TestDecisionOpenResponse:
    def test_construction(self) -> None:
        resp = DecisionOpenResponse(
            decision_id=ULID,
            idempotent=False,
            mission_id=MISSION,
            artifact_path="kitty-specs/slug/decisions/DM-abc.md",
            event_lamport=1,
        )
        assert resp.decision_id == ULID
        assert resp.idempotent is False
        assert resp.event_lamport == 1

    def test_event_lamport_optional(self) -> None:
        resp = DecisionOpenResponse(
            decision_id=ULID,
            idempotent=True,
            mission_id=MISSION,
            artifact_path="path/to/file.md",
        )
        assert resp.event_lamport is None


class TestDecisionTerminalResponse:
    def test_construction(self) -> None:
        resp = DecisionTerminalResponse(
            decision_id=ULID,
            status=DecisionStatus.RESOLVED,
            terminal_outcome="resolved",
            idempotent=False,
            event_lamport=2,
        )
        assert resp.status == DecisionStatus.RESOLVED
        assert resp.terminal_outcome == "resolved"

    def test_event_lamport_optional(self) -> None:
        resp = DecisionTerminalResponse(
            decision_id=ULID,
            status=DecisionStatus.DEFERRED,
            terminal_outcome="deferred",
            idempotent=False,
        )
        assert resp.event_lamport is None
