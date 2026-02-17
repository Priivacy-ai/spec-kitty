"""spec-kitty next -- canonical agent loop command.

Provides a single ``spec-kitty next --agent <name>`` entry point that agents
call repeatedly.  The system decides what to do next based on mission state,
feature artifacts, and WP lane states, returning a deterministic JSON decision
plus a prompt file.
"""

from __future__ import annotations

from specify_cli.next.decision import Decision, DecisionKind, decide_next

__all__ = [
    "Decision",
    "DecisionKind",
    "decide_next",
]
