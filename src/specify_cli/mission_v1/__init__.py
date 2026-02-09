"""Mission DSL v1 -- state machine missions with transitions library.

This subpackage provides:
- StateMachineMission: Full v1 state machine backed by MarkupMachine
- MissionModel: Lightweight model object that holds context for guards/callbacks
- emit_event / read_events: Provisional JSONL event logging
- PhaseMission: v0 phase-list compatibility wrapper (future WP)
- load_mission: Auto-detecting entry point (v0 vs v1) (future WP)
"""

from specify_cli.mission_v1.events import emit_event, read_events
from specify_cli.mission_v1.runner import MissionModel, StateMachineMission
from specify_cli.mission_v1.schema import MissionValidationError

__all__ = [
    "MissionModel",
    "MissionValidationError",
    "StateMachineMission",
    "emit_event",
    "read_events",
]
