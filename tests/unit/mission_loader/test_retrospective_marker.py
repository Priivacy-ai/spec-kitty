"""Tests for ``mission_loader.retrospective.has_retrospective_marker`` (R-001)."""

from __future__ import annotations

from specify_cli.mission_loader.retrospective import (
    RETROSPECTIVE_MARKER_ID,
    has_retrospective_marker,
)
from specify_cli.next._internal_runtime.schema import (
    MissionMeta,
    MissionTemplate,
    PromptStep,
)


def _meta() -> MissionMeta:
    return MissionMeta(key="demo", name="Demo", version="1.0.0")


def test_marker_present_returns_true() -> None:
    template = MissionTemplate(
        mission=_meta(),
        steps=[
            PromptStep(id="plan", title="Plan", agent_profile="planner"),
            PromptStep(id="retrospective", title="Retro", agent_profile="reviewer"),
        ],
    )
    assert has_retrospective_marker(template) is True


def test_marker_absent_returns_false() -> None:
    template = MissionTemplate(
        mission=_meta(),
        steps=[
            PromptStep(id="plan", title="Plan", agent_profile="planner"),
            PromptStep(id="write-report", title="Write report", agent_profile="writer"),
        ],
    )
    assert has_retrospective_marker(template) is False


def test_no_steps_returns_false() -> None:
    # Build an instance whose .steps list is empty without going through
    # the load() path (load enforces non-empty steps).
    template = MissionTemplate.model_construct(
        mission=_meta(),
        steps=[],
        audit_steps=[],
    )
    assert has_retrospective_marker(template) is False


def test_marker_not_last_returns_false() -> None:
    template = MissionTemplate(
        mission=_meta(),
        steps=[
            PromptStep(id="retrospective", title="Retro", agent_profile="reviewer"),
            PromptStep(id="ship", title="Ship", agent_profile="shipper"),
        ],
    )
    assert has_retrospective_marker(template) is False


def test_marker_constant_spelling_is_locked() -> None:
    # NFR-002: the constant is part of the wire contract.
    assert RETROSPECTIVE_MARKER_ID == "retrospective"
