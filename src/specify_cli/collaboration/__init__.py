"""
Mission collaboration domain logic.

This package contains use-cases (service.py), collision detection (warnings.py),
and materialized view state management (state.py).

Responsibilities:
- Use-case orchestration: join_mission, set_focus, set_drive, etc.
- Advisory collision detection (soft coordination, not hard locks)
- Local state cache (roster, participant context)
"""

from specify_cli.collaboration.session import (
    get_session_path,
    save_session_state,
    load_session_state,
    update_session_state,
    ensure_joined,
    get_mission_dir,
    get_active_mission_path,
    set_active_mission,
    get_active_mission,
    resolve_mission_id,
    validate_participant_id,
    validate_session_integrity,
    validate_session_before_command,
)

from specify_cli.collaboration.service import (
    join_mission,
    set_focus,
    set_drive,
    acknowledge_warning,
)

from specify_cli.collaboration.warnings import (
    detect_collision,
)

from specify_cli.collaboration.state import (
    get_mission_roster,
)

__all__ = [
    # Session management
    "get_session_path",
    "save_session_state",
    "load_session_state",
    "update_session_state",
    "ensure_joined",
    "get_mission_dir",
    "get_active_mission_path",
    "set_active_mission",
    "get_active_mission",
    "resolve_mission_id",
    "validate_participant_id",
    "validate_session_integrity",
    "validate_session_before_command",
    # Service use-cases
    "join_mission",
    "set_focus",
    "set_drive",
    "acknowledge_warning",
    # Collision detection
    "detect_collision",
    # State management
    "get_mission_roster",
]
