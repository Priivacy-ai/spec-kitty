"""
Mission collaboration domain logic.

This package contains use-cases (service.py), collision detection (warnings.py),
and materialized view state management (state.py).

Responsibilities:
- Use-case orchestration: join_mission, set_focus, set_drive, etc.
- Advisory collision detection (soft coordination, not hard locks)
- Local state cache (roster, participant context)
"""

__all__ = []  # Will be populated by domain modules
