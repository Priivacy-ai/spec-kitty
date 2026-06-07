"""AgentsMdWriter — session presence writer for AGENTS.md-based harnesses.

Pattern C: orientation injected into ``AGENTS.md`` at the project root.

Used by Codex, OpenCode, and Google Antigravity — all three resolve context
from ``AGENTS.md`` alongside their own config directories.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .markdown_rules import MarkdownRulesWriter

__all__ = ["AgentsMdWriter"]


@dataclass
class AgentsMdWriter(MarkdownRulesWriter):
    """Pattern C: orientation injected into AGENTS.md at project root.

    Used by Codex, OpenCode, and Google Antigravity — all three resolve context
    from AGENTS.md alongside their own config directories.

    ``can_write()`` always returns ``True`` because ``AGENTS.md`` lives at the
    project root, which is guaranteed to exist.  ``append_mode=True`` ensures
    orientation is appended (or replaced in-place) rather than overwriting any
    existing ``AGENTS.md`` content from other tools.
    """

    harness_key: str = field(default="")  # overridden per instance
    rules_path: str = field(default="AGENTS.md")
    append_mode: bool = field(default=True)
    check_dir: str | None = field(default=None)

    def can_write(self, _project_root: Path) -> bool:
        """Always returns ``True`` — AGENTS.md lives at the project root."""
        return True
