"""Mission DSL v1 -- state machine missions with transitions library.

This subpackage provides:
- MissionProtocol: Runtime-checkable protocol defining the mission API surface
- StateMachineMission: Full v1 state machine backed by MarkupMachine
- MissionModel: Lightweight model object that holds context for guards/callbacks
- emit_event / read_events: Provisional JSONL event logging
- PhaseMission: v0 phase-list compatibility wrapper
- load_mission: Auto-detecting entry point (v0 vs v1)
- load_mission_by_name: Convenience wrapper that resolves a mission name to a path
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

import yaml

from specify_cli.mission_v1.compat import PhaseMission
from specify_cli.mission_v1.events import emit_event, read_events
from specify_cli.mission_v1.guards import compile_guards
from specify_cli.mission_v1.runner import MissionModel, StateMachineMission
from specify_cli.mission_v1.schema import (
    MissionValidationError,
    is_v1_mission,
    validate_mission_v1,
)


@runtime_checkable
class MissionProtocol(Protocol):
    """Protocol defining the common API surface for all mission types.

    Both PhaseMission (v0 wrapper) and StateMachineMission (v1 native)
    must satisfy this protocol, ensuring callers can treat them
    interchangeably.
    """

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def state(self) -> str: ...

    def trigger(self, trigger_name: str, **kwargs: object) -> bool: ...

    def get_triggers(self, state: str | None = None) -> list[str]: ...

    def get_states(self) -> list[str]: ...


# ---------------------------------------------------------------------------
# Dispatch: auto-detect v0 vs v1 and return the appropriate type
# ---------------------------------------------------------------------------


def load_mission(
    mission_path: Path,
    feature_dir: Path | None = None,
) -> StateMachineMission | PhaseMission:
    """Load a mission from a directory, auto-detecting v0 vs v1 format.

    Reads the ``mission.yaml`` inside *mission_path* as a raw dict **before**
    any Pydantic validation so that v1 keys (``states``, ``transitions``, etc.)
    don't trigger ``extra="forbid"`` errors in the v0 ``MissionConfig`` model.

    - If the config has ``states`` AND ``transitions`` top-level keys it is
      treated as **v1**: JSON Schema validation is run, guard expressions are
      compiled, and a :class:`StateMachineMission` is returned.
    - Otherwise the config is treated as **v0**: the existing
      :class:`~specify_cli.mission.Mission` class handles Pydantic
      validation, and the result is wrapped in a :class:`PhaseMission`.

    Args:
        mission_path: Path to the mission directory (must contain ``mission.yaml``).
        feature_dir: Optional feature directory for guard context.

    Returns:
        ``StateMachineMission`` for v1 configs, ``PhaseMission`` for v0.

    Raises:
        MissionNotFoundError: If *mission_path* or ``mission.yaml`` does not exist.
        MissionValidationError: If v1 schema validation fails.
        MissionError: If v0 Pydantic validation fails.
    """
    config_file = mission_path / "mission.yaml"

    if not config_file.exists():
        # Lazy import to avoid circular deps (mission.py must NOT import mission_v1)
        from specify_cli.mission import MissionNotFoundError

        raise MissionNotFoundError(f"Mission config not found: {config_file}")

    with open(config_file, "r", encoding="utf-8") as fh:
        raw_config = yaml.safe_load(fh) or {}

    if is_v1_mission(raw_config):
        # v1 path: validate with JSON Schema, compile guards, build machine
        validate_mission_v1(raw_config)
        compiled_config = compile_guards(raw_config, feature_dir=feature_dir)
        return StateMachineMission(
            compiled_config,
            feature_dir=feature_dir,
            validate_schema=False,
        )
    else:
        # v0 path: delegate to existing Mission class, wrap in PhaseMission
        from specify_cli.mission import Mission

        mission = Mission(mission_path)
        return PhaseMission(mission)


def load_mission_by_name(
    mission_name: str,
    kittify_dir: Path | None = None,
    feature_dir: Path | None = None,
) -> StateMachineMission | PhaseMission:
    """Load a mission by name with v0/v1 auto-detection.

    Convenience wrapper around :func:`load_mission` that constructs the
    mission path from the standard ``<kittify_dir>/missions/<name>`` layout.

    Args:
        mission_name: Mission directory name (e.g. ``"software-dev"``).
        kittify_dir: Path to the ``.kittify`` directory. Defaults to
            ``Path.cwd() / ".kittify"``.
        feature_dir: Optional feature directory for guard context.

    Returns:
        ``StateMachineMission`` for v1 configs, ``PhaseMission`` for v0.
    """
    if kittify_dir is None:
        kittify_dir = Path.cwd() / ".kittify"

    mission_path = kittify_dir / "missions" / mission_name
    return load_mission(mission_path, feature_dir=feature_dir)


__all__ = [
    "MissionModel",
    "MissionProtocol",
    "MissionValidationError",
    "PhaseMission",
    "StateMachineMission",
    "emit_event",
    "load_mission",
    "load_mission_by_name",
    "read_events",
]
