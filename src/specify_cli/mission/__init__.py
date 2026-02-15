"""
Mission collaboration CLI commands.

This package provides commands for mission participation, focus management,
drive intent, status display, commenting, and decision capture.

Contract Ownership:
- Feature 006: Event schemas/payloads (spec-kitty-events library)
- Feature 040: CLI commands, event emission, queue/replay logic

Backwards Compatibility:
This package also re-exports the original mission system components from
specify_cli.mission module to maintain backwards compatibility with existing
code that imports from specify_cli.mission.
"""

# Re-export Mission system components for backwards compatibility
from specify_cli.mission_system import (  # noqa: F401
    Mission,
    MissionConfig,
    MissionError,
    MissionNotFoundError,
    get_deliverables_path,
    get_feature_mission_key,
    get_mission_by_name,
    get_mission_for_feature,
    list_available_missions,
)

__all__ = [
    # Mission system (backwards compatibility)
    "Mission",
    "MissionConfig",
    "MissionError",
    "MissionNotFoundError",
    "get_deliverables_path",
    "get_feature_mission_key",
    "get_mission_by_name",
    "get_mission_for_feature",
    "list_available_missions",
]
