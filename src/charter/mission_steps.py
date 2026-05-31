"""Charter facade for mission-step-contract types.

This module is the charter-layer proxy for runtime callers that historically
imported from ``doctrine.mission_step_contracts`` (now retired). The
runtime → charter → doctrine boundary (ADR 2026-03-27-1, tightened by
mission ``charter-mediated-doctrine-selection-01KRTZCA``) requires runtime
modules under ``src/specify_cli/`` to reach doctrine artifacts only through
charter facades.

WP01 of mission ``charter-doctrine-mission-type-configuration-01KSWJVX``
relocated the legacy contract types into
:mod:`doctrine.missions.step_contracts`. The unified mission-step model
(FR-011) now lives at :class:`doctrine.missions.models.MissionStep`; the
legacy ``MissionStepContract`` shape is preserved as a compatibility
surface for the runtime contract registry and on-disk
``*.step-contract.yaml`` loader.

The exported ``MissionStep`` symbol is the **unified** model owned by
``MissionType`` (per FR-011). The legacy step-shape used by
``MissionStepContract.steps`` is :class:`MissionStepContractStep`.

This file is a **pure re-export** module — no behaviour, no wrappers, no
type aliases.
"""

from doctrine.missions.mission_step_repository import MissionStepRepository
from doctrine.missions.models import MissionStep
from doctrine.missions.step_contracts import (
    MissionStepContract,
    MissionStepContractRepository,
    MissionStepContractStep,
)

__all__ = [
    "MissionStep",
    "MissionStepContract",
    "MissionStepContractRepository",
    "MissionStepContractStep",
    "MissionStepRepository",
]
