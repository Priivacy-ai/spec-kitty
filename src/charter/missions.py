"""Charter facade for mission-template / mission-type repository types.

This module is the charter-layer proxy for runtime callers that historically
imported the mission-template, mission-type, and mission-step repository
surfaces directly from ``doctrine.missions.*``. The runtime → charter →
doctrine boundary (ADR 2026-03-27-1, tightened by mission
``charter-mediated-doctrine-selection-01KRTZCA`` and re-affirmed by mission
``doctrine-public-api-surface-01KZPDSR``) requires runtime modules under
``src/specify_cli/`` to reach doctrine artifacts only through such charter
facades.

Every path re-exported here is dispositioned ``FACADE-ONLY`` in the WP01
census (``tests/architectural/test_doctrine_census.py::DISPOSITION``): a clean
charter door is preferred over widening ``doctrine/api.py`` (these types are
not part of the ``spec-kitty-doctrine`` wheel's public contract).

This file is a **pure re-export** module — no behaviour, no wrappers, no type
aliases. Object identity is preserved (e.g.
``charter.missions.MissionTemplateRepository is
doctrine.missions.repository.MissionTemplateRepository``), enforced by
``tests/architectural/test_charter_facades_reexport_doctrine.py``.
"""

from doctrine.missions.mission_step_repository import MissionStepRepository
from doctrine.missions.mission_type_repository import (
    MissionTypeRepository,
    builtin_mission_type_ids,
)
from doctrine.missions.repository import (
    MissionsRootNotFound,
    MissionTemplateRepository,
)
from doctrine.missions.step_projection import project_template_set

__all__ = [
    "MissionsRootNotFound",
    "MissionStepRepository",
    "MissionTemplateRepository",
    "MissionTypeRepository",
    "builtin_mission_type_ids",
    "project_template_set",
]
