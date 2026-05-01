"""Tests for decisions.emit — T016.

Covers:
- emit_decision_opened produces correct event_type and planning_interview origin_surface.
- emit_decision_resolved with RESOLVED terminal_outcome emits correct event with final_answer.
- emit_decision_resolved with DEFERRED terminal_outcome emits correct event with rationale.
- Round-trip: each payload validates against the Pydantic model.
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path


from specify_cli.decisions.emit import emit_decision_opened, emit_decision_resolved
from specify_cli.decisions.models import DecisionStatus, IndexEntry, OriginFlow
from spec_kitty_events.decisionpoint import (
    DECISION_POINT_OPENED,
    DECISION_POINT_RESOLVED,
    DecisionPointOpenedInterviewPayload,
    DecisionPointResolvedInterviewPayload,
)
from spec_kitty_events.decision_moment import OriginSurface


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


MISSION_SLUG = "test-mission-01KPWT8PXXX"
MISSION_ID = "01KPWT8PNY8683QX3WBW6VXYM7"
ACTOR = "test-actor"


def _make_entry(
    decision_id: str,
    status: DecisionStatus = DecisionStatus.OPEN,
    step_id: str | None = "charter.q1",
    slot_key: str | None = None,
    final_answer: str | None = None,
    rationale: str | None = None,
    other_answer: bool = False,
    resolved_at: datetime | None = None,
    resolved_by: str | None = None,
) -> IndexEntry:
    return IndexEntry(
        decision_id=decision_id,
        origin_flow=OriginFlow.CHARTER,
        step_id=step_id,
        slot_key=slot_key,
        input_key="auth_strategy",
        question="Which auth strategy?",
        options=("session", "oauth2"),
        status=status,
        final_answer=final_answer,
        rationale=rationale,
        other_answer=other_answer,
        created_at=datetime(2026, 4, 23, 10, 0, 0, tzinfo=UTC),
        resolved_at=resolved_at,
        resolved_by=resolved_by,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
    )


def _read_events(repo_root: Path, mission_slug: str) -> list[dict]:
    path = repo_root / "kitty-specs" / mission_slug / "status.events.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Tests: emit_decision_opened
# ---------------------------------------------------------------------------


def test_emit_decision_opened_writes_event(tmp_path: Path) -> None:
    """emit_decision_opened appends a DecisionPointOpened event."""
    entry = _make_entry("01AAAAAAAAAAAAAAAAAAAAAAAA")
    lamport = emit_decision_opened(
        tmp_path, MISSION_SLUG, decision_id="01AAAAAAAAAAAAAAAAAAAAAAAA", entry=entry, actor=ACTOR
    )

    events = _read_events(tmp_path, MISSION_SLUG)
    assert len(events) == 1
    assert events[0]["event_type"] == DECISION_POINT_OPENED
    assert lamport == 1


def test_emit_decision_opened_event_type(tmp_path: Path) -> None:
    """Event has event_type=DecisionPointOpened."""
    entry = _make_entry("01BBBBBBBBBBBBBBBBBBBBBBBB")
    emit_decision_opened(
        tmp_path, MISSION_SLUG, decision_id="01BBBBBBBBBBBBBBBBBBBBBBBB", entry=entry, actor=ACTOR
    )
    events = _read_events(tmp_path, MISSION_SLUG)
    assert events[0]["event_type"] == DECISION_POINT_OPENED


def test_emit_decision_opened_origin_surface(tmp_path: Path) -> None:
    """Payload has origin_surface=planning_interview."""
    entry = _make_entry("01CCCCCCCCCCCCCCCCCCCCCCCC")
    emit_decision_opened(
        tmp_path, MISSION_SLUG, decision_id="01CCCCCCCCCCCCCCCCCCCCCCCC", entry=entry, actor=ACTOR
    )
    events = _read_events(tmp_path, MISSION_SLUG)
    payload = events[0]["payload"]
    assert payload["origin_surface"] == OriginSurface.PLANNING_INTERVIEW.value


def test_emit_decision_opened_payload_roundtrip(tmp_path: Path) -> None:
    """Payload round-trips through DecisionPointOpenedInterviewPayload."""
    entry = _make_entry("01DDDDDDDDDDDDDDDDDDDDDDDD")
    emit_decision_opened(
        tmp_path, MISSION_SLUG, decision_id="01DDDDDDDDDDDDDDDDDDDDDDDD", entry=entry, actor=ACTOR
    )
    events = _read_events(tmp_path, MISSION_SLUG)
    payload_dict = events[0]["payload"]
    # Should not raise
    model = DecisionPointOpenedInterviewPayload.model_validate(payload_dict)
    assert model.decision_point_id == "01DDDDDDDDDDDDDDDDDDDDDDDD"
    assert model.origin_surface == OriginSurface.PLANNING_INTERVIEW
    assert model.question == "Which auth strategy?"
    assert model.actor_id == ACTOR


def test_emit_decision_opened_step_id_wire_uses_slot_key_fallback(tmp_path: Path) -> None:
    """When step_id is None, slot_key is used as the wire step_id."""
    entry = _make_entry("01EEEEEEEEEEEEEEEEEEEEEEEE", step_id=None, slot_key="specify.q1")
    emit_decision_opened(
        tmp_path, MISSION_SLUG, decision_id="01EEEEEEEEEEEEEEEEEEEEEEEE", entry=entry, actor=ACTOR
    )
    events = _read_events(tmp_path, MISSION_SLUG)
    payload = events[0]["payload"]
    assert payload["step_id"] == "specify.q1"


# ---------------------------------------------------------------------------
# Tests: emit_decision_resolved (resolved)
# ---------------------------------------------------------------------------


def test_emit_decision_resolved_writes_resolved_event(tmp_path: Path) -> None:
    """emit_decision_resolved emits DecisionPointResolved."""
    entry = _make_entry(
        "01FFFFFFFFFFFFFFFFFFFFFFFG",
        status=DecisionStatus.RESOLVED,
        final_answer="oauth2",
        resolved_at=datetime(2026, 4, 23, 10, 1, 0, tzinfo=UTC),
        resolved_by=ACTOR,
    )
    lamport = emit_decision_resolved(
        tmp_path, MISSION_SLUG, decision_id="01FFFFFFFFFFFFFFFFFFFFFFFG", entry=entry, actor=ACTOR
    )
    events = _read_events(tmp_path, MISSION_SLUG)
    assert len(events) == 1
    assert events[0]["event_type"] == DECISION_POINT_RESOLVED
    assert lamport == 1


def test_emit_decision_resolved_payload_has_final_answer(tmp_path: Path) -> None:
    """Resolved event payload contains final_answer."""
    entry = _make_entry(
        "01GGGGGGGGGGGGGGGGGGGGGGGX",
        status=DecisionStatus.RESOLVED,
        final_answer="session",
        resolved_at=datetime(2026, 4, 23, 10, 2, 0, tzinfo=UTC),
        resolved_by=ACTOR,
    )
    emit_decision_resolved(
        tmp_path, MISSION_SLUG, decision_id="01GGGGGGGGGGGGGGGGGGGGGGGX", entry=entry, actor=ACTOR
    )
    events = _read_events(tmp_path, MISSION_SLUG)
    payload = events[0]["payload"]
    assert payload["terminal_outcome"] == "resolved"
    assert payload["final_answer"] == "session"


def test_emit_decision_resolved_payload_roundtrip(tmp_path: Path) -> None:
    """Resolved payload round-trips through DecisionPointResolvedInterviewPayload."""
    entry = _make_entry(
        "01HHHHHHHHHHHHHHHHHHHHHHHX",
        status=DecisionStatus.RESOLVED,
        final_answer="oauth2",
        resolved_at=datetime(2026, 4, 23, 10, 3, 0, tzinfo=UTC),
        resolved_by=ACTOR,
    )
    emit_decision_resolved(
        tmp_path, MISSION_SLUG, decision_id="01HHHHHHHHHHHHHHHHHHHHHHHX", entry=entry, actor=ACTOR
    )
    events = _read_events(tmp_path, MISSION_SLUG)
    payload_dict = events[0]["payload"]
    model = DecisionPointResolvedInterviewPayload.model_validate(payload_dict)
    assert model.terminal_outcome.value == "resolved"
    assert model.final_answer == "oauth2"
    assert model.origin_surface == OriginSurface.PLANNING_INTERVIEW


# ---------------------------------------------------------------------------
# Tests: emit_decision_resolved (deferred)
# ---------------------------------------------------------------------------


def test_emit_decision_resolved_deferred_has_rationale(tmp_path: Path) -> None:
    """Deferred event has no final_answer and rationale is set."""
    entry = _make_entry(
        "01IIIIIIIIIIIIIIIIIIIIIIIIX",
        status=DecisionStatus.DEFERRED,
        rationale="discuss with team",
        resolved_at=datetime(2026, 4, 23, 10, 4, 0, tzinfo=UTC),
        resolved_by=ACTOR,
    )
    emit_decision_resolved(
        tmp_path, MISSION_SLUG, decision_id="01IIIIIIIIIIIIIIIIIIIIIIIIX", entry=entry, actor=ACTOR
    )
    events = _read_events(tmp_path, MISSION_SLUG)
    payload = events[0]["payload"]
    assert payload["event_type"] if "event_type" in payload else events[0]["event_type"] == DECISION_POINT_RESOLVED
    assert events[0]["event_type"] == DECISION_POINT_RESOLVED
    assert payload["terminal_outcome"] == "deferred"
    assert payload.get("final_answer") is None
    assert payload["rationale"] == "discuss with team"


def test_emit_decision_resolved_deferred_payload_roundtrip(tmp_path: Path) -> None:
    """Deferred payload validates against Pydantic model."""
    entry = _make_entry(
        "01JJJJJJJJJJJJJJJJJJJJJJJX",
        status=DecisionStatus.DEFERRED,
        rationale="revisit later",
        resolved_at=datetime(2026, 4, 23, 10, 5, 0, tzinfo=UTC),
        resolved_by=ACTOR,
    )
    emit_decision_resolved(
        tmp_path, MISSION_SLUG, decision_id="01JJJJJJJJJJJJJJJJJJJJJJJX", entry=entry, actor=ACTOR
    )
    events = _read_events(tmp_path, MISSION_SLUG)
    payload_dict = events[0]["payload"]
    model = DecisionPointResolvedInterviewPayload.model_validate(payload_dict)
    assert model.terminal_outcome.value == "deferred"
    assert model.final_answer is None
    assert model.rationale == "revisit later"
