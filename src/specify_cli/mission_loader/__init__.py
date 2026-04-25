"""Custom-mission loader package.

Public surface for validating custom-mission YAML templates discovered in
project, user, and pack tiers. The package is consumed by:

- the CLI ``spec-kitty mission run`` command (WP05) -- to render a
  validated template or operator-fixable error envelope, and
- the runtime bridge (WP05) -- to register synthesized step contracts.

Stability notes (NFR-002): the wire spelling of every code in
:class:`LoaderErrorCode` and :class:`LoaderWarningCode` is part of the
contract. Renames or removals are breaking changes; additions are
non-breaking.
"""

from __future__ import annotations

from specify_cli.mission_loader.command import (
    RunCustomMissionResult,
    run_custom_mission,
)
from specify_cli.mission_loader.contract_synthesis import synthesize_contracts
from specify_cli.mission_loader.errors import (
    LoaderError,
    LoaderErrorCode,
    LoaderWarning,
    LoaderWarningCode,
    ValidationReport,
)
from specify_cli.mission_loader.registry import (
    RuntimeContractRegistry,
    get_runtime_contract_registry,
    lookup_contract,
    registered_runtime_contracts,
)
from specify_cli.mission_loader.retrospective import (
    RETROSPECTIVE_MARKER_ID,
    has_retrospective_marker,
)
from specify_cli.mission_loader.validator import validate_custom_mission

__all__ = [
    "RETROSPECTIVE_MARKER_ID",
    "LoaderError",
    "LoaderErrorCode",
    "LoaderWarning",
    "LoaderWarningCode",
    "RunCustomMissionResult",
    "RuntimeContractRegistry",
    "ValidationReport",
    "get_runtime_contract_registry",
    "has_retrospective_marker",
    "lookup_contract",
    "registered_runtime_contracts",
    "run_custom_mission",
    "synthesize_contracts",
    "validate_custom_mission",
]
