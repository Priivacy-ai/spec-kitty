"""Custom-mission contract synthesis (R-004, FR-008).

Builds one :class:`MissionStepContract` per *composed* step of a custom
:class:`MissionTemplate`. The synthesized contracts are kept entirely
in-memory; the on-disk :class:`MissionStepContractRepository` is never
mutated by this module.

Skipped at synthesis time
-------------------------
* **Decision-required gates** -- ``step.requires_inputs`` is non-empty.
  These steps route through the engine planner's ``decision_required``
  shape and never need a contract.
* **Steps already bound to an existing contract** -- ``step.contract_ref``
  is non-empty. The repository is expected to resolve the referenced id;
  synthesizing a duplicate would shadow the canonical record.
* **The retrospective marker** -- ``step.id == "retrospective"``. The
  marker is structural only this tranche; it carries no execution side
  effect (see :mod:`specify_cli.mission_loader.retrospective`).

Synthesized shape (per data-model.md "Synthesized contract record")
-------------------------------------------------------------------
For every in-scope step the function emits::

    MissionStepContract(
        id=f"custom:{template.mission.key}:{step.id}",
        schema_version="1.0",
        action=step.id,
        mission=template.mission.key,
        steps=[
            MissionStep(
                id=f"{step.id}.execute",
                description=step.description or step.title or step.id,
            ),
        ],
    )

The actual :class:`MissionStepContract` schema (see
``src/doctrine/mission_step_contracts/models.py``) requires ``id``,
``schema_version``, ``action``, ``mission`` and a non-empty ``steps``
list. The inner :class:`MissionStep` requires ``id`` and ``description``;
``command``, ``delegates_to`` and ``guidance`` are intentionally left
unset for v1 custom missions (no delegation, no inline command).

Order is preserved: synthesized contracts appear in the same order as
``template.steps``.
"""

from __future__ import annotations

from doctrine.mission_step_contracts.models import (
    MissionStep,
    MissionStepContract,
)

from specify_cli.mission_loader.retrospective import RETROSPECTIVE_MARKER_ID
from specify_cli.next._internal_runtime.schema import MissionTemplate, PromptStep


_SYNTHESIZED_SCHEMA_VERSION = "1.0"


def _is_composed_step(step: PromptStep) -> bool:
    """Return True iff ``step`` should produce a synthesized contract.

    A step is *composed* when it is neither a decision-required gate
    (``requires_inputs`` non-empty), nor already bound to a pre-existing
    contract (``contract_ref`` set), nor the retrospective marker.
    """
    if step.requires_inputs:
        return False
    if step.contract_ref:
        return False
    return bool(step.id != RETROSPECTIVE_MARKER_ID)


def _build_contract(template: MissionTemplate, step: PromptStep) -> MissionStepContract:
    """Build a single :class:`MissionStepContract` for ``step``."""
    description = step.description or step.title or step.id
    inner_step = MissionStep(
        id=f"{step.id}.execute",
        description=description,
    )
    return MissionStepContract(
        id=f"custom:{template.mission.key}:{step.id}",
        schema_version=_SYNTHESIZED_SCHEMA_VERSION,
        action=step.id,
        mission=template.mission.key,
        steps=[inner_step],
    )


def synthesize_contracts(template: MissionTemplate) -> list[MissionStepContract]:
    """Build one :class:`MissionStepContract` per composed step in ``template``.

    Skips:

    * Decision-required gates (``step.requires_inputs`` is non-empty).
    * Steps that already point to an existing contract
      (``step.contract_ref`` is set).
    * The retrospective marker step (``step.id == "retrospective"``).

    Returns a list of contracts ordered the same as ``template.steps``.
    Each contract's ``id`` has the form ``"custom:<mission-key>:<step.id>"``.
    """
    contracts: list[MissionStepContract] = []
    for step in template.steps:
        if not _is_composed_step(step):
            continue
        contracts.append(_build_contract(template, step))
    return contracts


__all__ = ["synthesize_contracts"]
