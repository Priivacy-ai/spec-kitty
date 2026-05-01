"""spec-kitty next -- canonical agent loop command.

Provides a single ``spec-kitty next --agent <name>`` entry point that agents
call repeatedly.  The system decides what to do next based on mission state,
feature artifacts, and WP lane states, returning a deterministic JSON decision
plus a prompt file.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {"Decision", "DecisionKind", "decide_next"}


def __getattr__(name: str) -> Any:
    """Lazily expose decision helpers without loading the mutation engine."""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module("specify_cli.next.decision"), name)
    globals()[name] = value
    return value

__all__ = [
    "Decision",
    "DecisionKind",
    "decide_next",
]
