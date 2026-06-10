"""ClaudeCodeWriter — session presence writer for Claude Code.

Extends ``MarkdownRulesWriter`` targeting ``.claude/CLAUDE.md`` (append mode)
and additionally manages the ``SessionStart`` and ``Stop`` hooks in
``.claude/settings.json`` via ``ClaudeCodeHookRegistrar``.

``has_presence()`` returns ``True`` only when **all** artefacts are present:
1. The orientation section in ``.claude/CLAUDE.md``.
2. The ``spec-kitty session-start`` SessionStart entry in ``.claude/settings.json``.
3. The ``spec-kitty session-stop`` Stop entry in ``.claude/settings.json``.

This means the session-presence migration's ``detect()`` triggers a re-write
when any artefact is missing — existing projects pick up the Stop hook on
``spec-kitty upgrade``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..content import SessionPresenceContent
from ..hooks.claude_code_hook import (
    SESSION_START_EVENT,
    STOP_EVENT,
    ClaudeCodeHookRegistrar,
)
from .markdown_rules import MarkdownRulesWriter

__all__ = ["ClaudeCodeWriter", "SESSION_START_CMD", "SESSION_STOP_CMD"]

SESSION_START_CMD = "spec-kitty session-start"
SESSION_STOP_CMD = "spec-kitty session-stop"


@dataclass
class ClaudeCodeWriter(MarkdownRulesWriter):
    """Writer for the Claude Code harness.

    Manages two artefacts:
    - ``.claude/CLAUDE.md`` — orientation section (via ``MarkdownRulesWriter``).
    - ``.claude/settings.json`` — ``SessionStart`` and ``Stop`` hooks (via
      ``ClaudeCodeHookRegistrar``).

    Both artefacts are written/removed together so the harness stays consistent.
    """

    harness_key: str = field(default="claude")
    rules_path: str = field(default=".claude/CLAUDE.md")
    append_mode: bool = field(default=True)

    def write(self, project_root: Path, content: SessionPresenceContent) -> None:
        """Write the CLAUDE.md section AND register the SessionStart + Stop hooks."""
        super().write(project_root, content)
        ClaudeCodeHookRegistrar(SESSION_START_EVENT).register(project_root, SESSION_START_CMD)
        ClaudeCodeHookRegistrar(STOP_EVENT).register(project_root, SESSION_STOP_CMD)

    def remove(self, project_root: Path) -> None:
        """Remove the CLAUDE.md section AND unregister the SessionStart + Stop hooks."""
        super().remove(project_root)
        ClaudeCodeHookRegistrar(SESSION_START_EVENT).unregister(project_root, SESSION_START_CMD)
        ClaudeCodeHookRegistrar(STOP_EVENT).unregister(project_root, SESSION_STOP_CMD)

    def has_presence(self, project_root: Path) -> bool:
        """Return ``True`` only when the CLAUDE.md section AND both hooks exist."""
        return (
            super().has_presence(project_root)
            and ClaudeCodeHookRegistrar(SESSION_START_EVENT).is_registered(
                project_root, SESSION_START_CMD
            )
            and ClaudeCodeHookRegistrar(STOP_EVENT).is_registered(project_root, SESSION_STOP_CMD)
        )
