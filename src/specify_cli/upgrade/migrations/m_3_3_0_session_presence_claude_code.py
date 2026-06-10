"""Migration: install session presence orientation for existing Claude Code projects.

Detects projects that have ``claude`` configured but are missing the orientation
section in ``.claude/CLAUDE.md``, the ``spec-kitty session-start`` SessionStart
entry, or the ``spec-kitty session-stop`` Stop entry in ``.claude/settings.json``,
and backfills all artefacts on ``spec-kitty upgrade``.  Idempotent: hook
registration no-ops when entries already exist; foreign hook entries are
preserved.
"""

from __future__ import annotations

from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class SessionPresenceClaudeCodeMigration(BaseMigration):
    """Backfill session presence orientation for existing Claude Code projects."""

    migration_id = "3_3_0_session_presence_claude_code"
    description = "Write session presence orientation to .claude/CLAUDE.md and register SessionStart + Stop hooks for existing Claude Code projects"
    target_version = "3.2.0rc39"
    runs_on_worktrees = False

    def detect(self, project_path: Path) -> bool:
        """Return ``True`` when ``claude`` is configured but presence is incomplete."""
        if not (project_path / ".kittify").is_dir():
            return False
        from specify_cli.core.agent_config import load_agent_config

        config = load_agent_config(project_path)
        if "claude" not in (config.available if config else []):
            return False
        from specify_cli.session_presence.writers.claude_code import ClaudeCodeWriter

        return not ClaudeCodeWriter().has_presence(project_path)

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check that the project is initialized before applying."""
        if not (project_path / ".kittify").is_dir():
            return False, ".kittify/ directory does not exist (not initialized)"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Write the CLAUDE.md section and register the SessionStart + Stop hooks."""
        if dry_run:
            return MigrationResult(
                success=True,
                changes_made=[
                    "Would write orientation to .claude/CLAUDE.md and register SessionStart + Stop hooks"
                ],
            )
        from specify_cli.core.agent_config import load_agent_config
        from specify_cli.session_presence.manager import SessionPresenceManager
        from specify_cli.session_presence.writers.claude_code import ClaudeCodeWriter

        agent_config = load_agent_config(project_path)
        manager = SessionPresenceManager(project_path, agent_config)
        content = manager._build_content()
        ClaudeCodeWriter().write(project_path, content)
        return MigrationResult(
            success=True,
            changes_made=[
                "Wrote spec-kitty orientation to .claude/CLAUDE.md",
                "Registered spec-kitty session-start SessionStart hook",
                "Registered spec-kitty session-stop Stop hook",
            ],
        )
