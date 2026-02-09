"""Mission DSL v1 -- state machine missions with transitions library.

This subpackage provides:
- StateMachineMission: Full v1 state machine backed by MarkupMachine
- MissionModel: Lightweight model object that holds context for guards/callbacks
- PhaseMission: v0 phase-list compatibility wrapper
- load_mission: Auto-detecting entry point (v0 vs v1)
"""

from specify_cli.mission_v1.runner import MissionModel, StateMachineMission
from specify_cli.mission_v1.schema import MissionValidationError

__all__ = [
    "MissionModel",
    "MissionValidationError",
    "PhaseMission",
    "StateMachineMission",
    "load_mission",
]
