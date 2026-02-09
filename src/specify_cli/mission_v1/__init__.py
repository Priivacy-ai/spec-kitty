"""Mission DSL v1 -- state machine missions with transitions library.

This subpackage provides:
- MissionProtocol: Runtime-checkable protocol defining the mission API surface
- StateMachineMission: Full v1 state machine backed by MarkupMachine
- MissionModel: Lightweight model object that holds context for guards/callbacks
- PhaseMission: v0 phase-list compatibility wrapper
- load_mission: Auto-detecting entry point (v0 vs v1)
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from specify_cli.mission_v1.compat import PhaseMission
from specify_cli.mission_v1.runner import MissionModel, StateMachineMission
from specify_cli.mission_v1.schema import MissionValidationError


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

    def trigger(self, trigger_name: str, **kwargs) -> bool: ...

    def get_triggers(self, state: str | None = None) -> list[str]: ...

    def get_states(self) -> list[str]: ...


__all__ = [
    "MissionModel",
    "MissionProtocol",
    "MissionValidationError",
    "PhaseMission",
    "StateMachineMission",
    "load_mission",
]
