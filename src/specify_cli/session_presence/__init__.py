"""session_presence — shared foundation for session presence functionality.

Injects an orientation block into each agent's config files so AI agents know
what Spec Kitty is and how to use it from the first session.

Phase 1 public API (WP01):
- ``SessionPresenceContent`` / ``render()`` — builds the orientation block text.
- ``SECTION_OPEN`` / ``SECTION_CLOSE`` — delimiters used by all writers.
- ``UpgradeChecker`` — background PyPI version cache management.
- ``Writer`` protocol — interface all harness writers must satisfy.
- ``NullWriter`` — no-op writer for unregistered harnesses.
- ``get_writer()`` — registry lookup.

WP02 adds ``ClaudeCodeWriter``; WP03 adds ``SessionPresenceManager`` /
``InstallResult``; WP05 populates the full registry.
"""

from __future__ import annotations

from .content import SECTION_CLOSE, SECTION_OPEN, SessionPresenceContent
from .upgrade_check import UpgradeChecker
from .writers import NullWriter, Writer, get_writer

__all__ = [
    "SECTION_CLOSE",
    "SECTION_OPEN",
    "SessionPresenceContent",
    "UpgradeChecker",
    "Writer",
    "NullWriter",
    "get_writer",
]
