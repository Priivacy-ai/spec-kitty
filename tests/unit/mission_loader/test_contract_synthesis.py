"""Tests for ``mission_loader.contract_synthesis.synthesize_contracts`` (R-004).

Locks the synthesis output shape per FR-008: one
:class:`MissionStepContract` per composed step, decision-required gates
and contract-ref-bound steps and the retrospective marker skipped, ids
of the form ``custom:<mission-key>:<step-id>``.
"""

from __future__ import annotations

from doctrine.mission_step_contracts.models import MissionStepContract

from specify_cli.mission_loader.contract_synthesis import synthesize_contracts
from specify_cli.next._internal_runtime.schema import (
    MissionMeta,
    MissionTemplate,
    PromptStep,
)


def _meta(key: str = "custom-demo") -> MissionMeta:
    return MissionMeta(key=key, name="Demo", version="1.0.0")


def _template(steps: list[PromptStep], key: str = "custom-demo") -> MissionTemplate:
    return MissionTemplate(mission=_meta(key), steps=steps)


def test_one_contract_per_composed_step() -> None:
    template = _template(
        [
            PromptStep(id="plan", title="Plan", agent_profile="planner"),
            PromptStep(id="implement", title="Implement", agent_profile="implementer"),
            PromptStep(id="review", title="Review", agent_profile="reviewer"),
            PromptStep(id="retrospective", title="Retro"),
        ]
    )

    contracts = synthesize_contracts(template)

    assert len(contracts) == 3
    assert [c.action for c in contracts] == ["plan", "implement", "review"]


def test_skips_decision_required_steps() -> None:
    template = _template(
        [
            PromptStep(id="plan", title="Plan", agent_profile="planner"),
            PromptStep(id="ask-user", title="Ask", requires_inputs=["choice"]),
            PromptStep(id="retrospective", title="Retro"),
        ]
    )

    contracts = synthesize_contracts(template)

    actions = [c.action for c in contracts]
    assert "ask-user" not in actions
    assert actions == ["plan"]


def test_skips_contract_ref_steps() -> None:
    template = _template(
        [
            PromptStep(id="plan", title="Plan", agent_profile="planner"),
            PromptStep(id="bound", title="Bound", contract_ref="abc"),
            PromptStep(id="retrospective", title="Retro"),
        ]
    )

    contracts = synthesize_contracts(template)

    actions = [c.action for c in contracts]
    assert "bound" not in actions
    assert actions == ["plan"]


def test_skips_retrospective_step() -> None:
    template = _template(
        [
            PromptStep(id="plan", title="Plan", agent_profile="planner"),
            PromptStep(id="retrospective", title="Retro", agent_profile="reviewer"),
        ]
    )

    contracts = synthesize_contracts(template)

    actions = [c.action for c in contracts]
    assert "retrospective" not in actions


def test_id_shape() -> None:
    template = _template(
        [
            PromptStep(id="plan", title="Plan", agent_profile="planner"),
            PromptStep(id="implement", title="Implement", agent_profile="implementer"),
            PromptStep(id="retrospective", title="Retro"),
        ],
        key="my-mission",
    )

    contracts = synthesize_contracts(template)

    assert [c.id for c in contracts] == [
        "custom:my-mission:plan",
        "custom:my-mission:implement",
    ]


def test_mission_and_action_set() -> None:
    template = _template(
        [
            PromptStep(id="design", title="Design", agent_profile="designer"),
            PromptStep(id="retrospective", title="Retro"),
        ],
        key="erp-flow",
    )

    contracts = synthesize_contracts(template)

    assert len(contracts) == 1
    contract = contracts[0]
    assert contract.mission == "erp-flow"
    assert contract.action == "design"


def test_empty_template_returns_empty() -> None:
    template = MissionTemplate.model_construct(
        mission=_meta(),
        steps=[],
        audit_steps=[],
    )

    assert synthesize_contracts(template) == []


def test_inner_step_shape_uses_execute_id_and_description() -> None:
    template = _template(
        [
            PromptStep(
                id="plan",
                title="Plan the work",
                description="Decompose the request into tasks.",
                agent_profile="planner",
            ),
            PromptStep(id="retrospective", title="Retro"),
        ]
    )

    contracts = synthesize_contracts(template)
    assert len(contracts) == 1
    inner = contracts[0].steps
    assert len(inner) == 1
    assert inner[0].id == "plan.execute"
    assert inner[0].description == "Decompose the request into tasks."
    # No delegation, no inline command (v1 custom missions are flat).
    assert inner[0].delegates_to is None
    assert inner[0].command is None


def test_inner_step_description_falls_back_to_title_when_blank() -> None:
    template = _template(
        [
            PromptStep(id="design", title="Design phase", agent_profile="designer"),
            PromptStep(id="retrospective", title="Retro"),
        ]
    )

    contracts = synthesize_contracts(template)
    assert contracts[0].steps[0].description == "Design phase"


def test_preserves_template_step_order() -> None:
    template = _template(
        [
            PromptStep(id="alpha", title="Alpha", agent_profile="x"),
            PromptStep(id="beta", title="Beta", agent_profile="y"),
            PromptStep(id="gamma", title="Gamma", agent_profile="z"),
            PromptStep(id="retrospective", title="Retro"),
        ]
    )

    contracts = synthesize_contracts(template)

    assert [c.action for c in contracts] == ["alpha", "beta", "gamma"]


def test_returns_mission_step_contract_instances() -> None:
    template = _template(
        [
            PromptStep(id="plan", title="Plan", agent_profile="planner"),
            PromptStep(id="retrospective", title="Retro"),
        ]
    )

    contracts = synthesize_contracts(template)

    assert all(isinstance(c, MissionStepContract) for c in contracts)
