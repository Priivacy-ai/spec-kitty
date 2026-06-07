"""Writer registry — maps harness keys to Writer instances.

Phase 1 skeleton: all keys fall through to NullWriter.
WP02 replaces the ``claude`` entry with ``ClaudeCodeWriter()``.
WP05 populates all remaining harness entries.
"""

from __future__ import annotations

from .base import Writer
from .null_writer import NullWriter

__all__ = ["WRITER_REGISTRY", "get_writer"]

# Phase 1 skeleton — WP02 replaces the claude entry; WP05 populates the rest.
WRITER_REGISTRY: dict[str, Writer] = {}


def get_writer(agent_key: str) -> Writer:
    """Return the Writer for the given agent key, or NullWriter if unregistered."""
    return WRITER_REGISTRY.get(agent_key, NullWriter(agent_key))
