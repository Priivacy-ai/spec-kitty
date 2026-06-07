"""session_presence.writers — harness-specific Writer implementations.

Public exports grow as WP02 and WP05 add concrete writers.
"""

from __future__ import annotations

from .base import Writer
from .claude_code import ClaudeCodeWriter
from .markdown_rules import MarkdownRulesWriter
from .null_writer import NullWriter
from .registry import WRITER_REGISTRY, get_writer

__all__ = [
    "Writer",
    "ClaudeCodeWriter",
    "MarkdownRulesWriter",
    "NullWriter",
    "WRITER_REGISTRY",
    "get_writer",
]
