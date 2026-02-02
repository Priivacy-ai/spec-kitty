"""Utilities for AI agents working with spec-kitty.

This package provides helper functions that agents can import and use directly,
without needing to go through CLI commands.
"""

from .directories import (
    AGENT_DIRS,
    AGENT_DIR_TO_KEY,
    get_agent_dirs_for_project,
)
from .status import show_kanban_status

__all__ = [
    "AGENT_DIRS",
    "AGENT_DIR_TO_KEY",
    "get_agent_dirs_for_project",
    "show_kanban_status",
]
