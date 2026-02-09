"""Mission DSL v1 -- state machine missions with transitions library.

This subpackage provides:
- StateMachineMission: Full v1 state machine backed by MarkupMachine
- PhaseMission: v0 phase-list compatibility wrapper
- load_mission: Auto-detecting entry point (v0 vs v1)
"""

__all__ = [
    "StateMachineMission",
    "PhaseMission",
    "load_mission",
    "MissionValidationError",
]
