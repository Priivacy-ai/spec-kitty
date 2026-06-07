"""Writer registry — maps harness keys to Writer instances.

Phase 1 / WP02: ``claude`` is wired to ``ClaudeCodeWriter()``.
WP05 populates all remaining harness entries.
"""

from __future__ import annotations

from .base import Writer
from .claude_code import ClaudeCodeWriter
from .null_writer import NullWriter

__all__ = ["WRITER_REGISTRY", "get_writer"]

WRITER_REGISTRY: dict[str, Writer] = {
    "claude": ClaudeCodeWriter(),
    # Phase 2 entries added by WP05
}


def get_writer(agent_key: str) -> Writer:
    """Return the Writer for the given agent key, or NullWriter if unregistered."""
    return WRITER_REGISTRY.get(agent_key, NullWriter(agent_key))
