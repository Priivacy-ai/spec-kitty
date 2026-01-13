"""Utilities for AI agents working with spec-kitty.

This package provides helper functions that agents can import and use directly,
without needing to go through CLI commands.
"""

from .status import show_kanban_status

__all__ = ["show_kanban_status"]
