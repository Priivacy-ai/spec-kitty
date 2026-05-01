"""FR-010 / NFR-005 — POLICY_TABLE coverage + resolve_projection contract.

Tests cover:
- T033: projection_policy module (T035 coverage tests)
- T038: golden-path regression — existing timeline behaviour preserved

All 16 rows of POLICY_TABLE are tested individually via parametrize, plus
golden-path assertions for rows that govern existing dashboard behaviour (3.2.0a5).
"""
from __future__ import annotations

import pytest

from specify_cli.invocation.projection_policy import (
    POLICY_TABLE,
    EventKind,
    ModeOfWork,
    ProjectionRule,
    resolve_projection,
)


# ---------------------------------------------------------------------------
# T035 — POLICY_TABLE completeness
# ---------------------------------------------------------------------------


def test_policy_table_covers_all_16_pairs() -> None:
    """Every (ModeOfWork, EventKind) product must appear in POLICY_TABLE."""
    expected_pairs = {(m, e) for m in ModeOfWork for e in EventKind}
    assert set(POLICY_TABLE.keys()) == expected_pairs


@pytest.mark.parametrize("mode", list(ModeOfWork))
@pytest.mark.parametrize("event", list(EventKind))
def test_every_row_returns_a_projection_rule(mode: ModeOfWork, event: EventKind) -> None:
    """resolve_projection always returns a ProjectionRule for every known (mode, event)."""
    rule = resolve_projection(mode, event)
    assert isinstance(rule, ProjectionRule)


# ---------------------------------------------------------------------------
# T035 — Golden-path assertions (specific row values)
# ---------------------------------------------------------------------------


def test_task_execution_started_projects_with_body() -> None:
    """TASK_EXECUTION/STARTED projects with request_text included."""
    rule = resolve_projection(ModeOfWork.TASK_EXECUTION, EventKind.STARTED)
    assert rule == ProjectionRule(True, True, False)


def test_task_execution_completed_includes_evidence() -> None:
    """TASK_EXECUTION/COMPLETED projects with both body and evidence_ref."""
    rule = resolve_projection(ModeOfWork.TASK_EXECUTION, EventKind.COMPLETED)
    assert rule == ProjectionRule(True, True, True)


def test_mission_step_completed_includes_evidence() -> None:
    """MISSION_STEP/COMPLETED projects with both body and evidence_ref."""
    rule = resolve_projection(ModeOfWork.MISSION_STEP, EventKind.COMPLETED)
    assert rule == ProjectionRule(True, True, True)


def test_advisory_events_omit_body() -> None:
    """All ADVISORY events project without request_text or evidence_ref."""
    for event in EventKind:
        rule = resolve_projection(ModeOfWork.ADVISORY, event)
        assert not rule.include_request_text, (
            f"ADVISORY/{event} should not include request_text"
        )
        assert not rule.include_evidence_ref, (
            f"ADVISORY/{event} should not include evidence_ref"
        )


def test_query_never_projects() -> None:
    """QUERY mode never projects to SaaS for any event kind."""
    for event in EventKind:
        rule = resolve_projection(ModeOfWork.QUERY, event)
        assert not rule.project, f"QUERY/{event} should not project"


def test_correlation_events_on_advisory_do_not_project() -> None:
    """ADVISORY correlation events (artifact_link, commit_link) produce no SaaS traffic."""
    for event in (EventKind.ARTIFACT_LINK, EventKind.COMMIT_LINK):
        rule = resolve_projection(ModeOfWork.ADVISORY, event)
        assert not rule.project, (
            f"ADVISORY/{event} should not project (correlation event suppressed for advisory)"
        )


def test_correlation_events_on_task_execution_project_without_body() -> None:
    """TASK_EXECUTION correlation events project but without request_text."""
    for event in (EventKind.ARTIFACT_LINK, EventKind.COMMIT_LINK):
        rule = resolve_projection(ModeOfWork.TASK_EXECUTION, event)
        assert rule.project, f"TASK_EXECUTION/{event} should project"
        assert not rule.include_request_text, (
            f"TASK_EXECUTION/{event} should not include request_text"
        )


def test_null_mode_falls_back_to_task_execution() -> None:
    """Pre-mission records (mode_of_work=None) keep 3.2.0a5 projection behaviour (TASK_EXECUTION)."""
    for event in EventKind:
        rule_none = resolve_projection(None, event)
        rule_task_exec = resolve_projection(ModeOfWork.TASK_EXECUTION, event)
        assert rule_none == rule_task_exec, (
            f"None mode should be identical to TASK_EXECUTION for event={event}, "
            f"got {rule_none!r} vs {rule_task_exec!r}"
        )


# ---------------------------------------------------------------------------
# T038 — Golden-path regression: existing timeline behaviour preserved
# ---------------------------------------------------------------------------


def test_golden_path_task_execution_started() -> None:
    """task_execution/started MUST project with request_text (3.2.0a5 behaviour)."""
    rule = resolve_projection(ModeOfWork.TASK_EXECUTION, EventKind.STARTED)
    assert rule.project is True
    assert rule.include_request_text is True


def test_golden_path_mission_step_completed() -> None:
    """mission_step/completed MUST project with evidence_ref (3.2.0a5 behaviour)."""
    rule = resolve_projection(ModeOfWork.MISSION_STEP, EventKind.COMPLETED)
    assert rule.project is True
    assert rule.include_evidence_ref is True


def test_golden_path_null_mode_preserves_unconditional_projection() -> None:
    """Pre-WP06 records (no mode_of_work) project as before — same as TASK_EXECUTION/STARTED."""
    rule = resolve_projection(None, EventKind.STARTED)
    assert rule.project is True
    assert rule.include_request_text is True
