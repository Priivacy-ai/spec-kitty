"""ClaudeCodeWriter — session presence writer for Claude Code.

Extends ``MarkdownRulesWriter`` targeting ``.claude/CLAUDE.md`` (append mode)
and additionally manages the ``SessionStart`` hook in ``.claude/settings.json``
via ``ClaudeCodeHookRegistrar``.

``has_presence()`` returns ``True`` only when **both** artefacts are present:
1. The orientation section in ``.claude/CLAUDE.md``.
2. The ``spec-kitty session-start`` entry in ``.claude/settings.json``.

This means the Phase 1 migration's ``detect()`` triggers a re-write when
either artefact is missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..content import SessionPresenceContent
from ..hooks.claude_code_hook import ClaudeCodeHookRegistrar
from .markdown_rules import MarkdownRulesWriter

__all__ = ["ClaudeCodeWriter", "SESSION_START_CMD"]

SESSION_START_CMD = "spec-kitty session-start"


@dataclass
class ClaudeCodeWriter(MarkdownRulesWriter):
    """Writer for the Claude Code harness.

    Manages two artefacts:
    - ``.claude/CLAUDE.md`` — orientation section (via ``MarkdownRulesWriter``).
    - ``.claude/settings.json`` — ``SessionStart`` hook (via
      ``ClaudeCodeHookRegistrar``).

    Both artefacts are written/removed together so the harness stays consistent.
    """

    harness_key: str = field(default="claude")
    rules_path: str = field(default=".claude/CLAUDE.md")
    append_mode: bool = field(default=True)

    def write(self, project_root: Path, content: SessionPresenceContent) -> None:
        """Write the CLAUDE.md section AND register the SessionStart hook."""
        super().write(project_root, content)
        ClaudeCodeHookRegistrar().register(project_root, SESSION_START_CMD)

    def remove(self, project_root: Path) -> None:
        """Remove the CLAUDE.md section AND unregister the SessionStart hook."""
        super().remove(project_root)
        ClaudeCodeHookRegistrar().unregister(project_root, SESSION_START_CMD)

    def has_presence(self, project_root: Path) -> bool:
        """Return ``True`` only when both the CLAUDE.md section AND the hook exist."""
        return super().has_presence(project_root) and ClaudeCodeHookRegistrar().is_registered(
            project_root, SESSION_START_CMD
        )
