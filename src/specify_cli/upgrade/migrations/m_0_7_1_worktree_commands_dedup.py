"""Migration: Remove duplicate .claude/commands/ when worktrees exist."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class WorktreeCommandsDedupMigration(BaseMigration):
    """Remove .claude/commands/ from main repo when worktrees exist.

    Claude Code traverses parent directories looking for .claude/commands/.
    When a worktree is located inside the main repo (at .worktrees/),
    Claude Code finds commands in both locations, causing duplicates.

    This migration removes .claude/commands/ from the main repo when
    worktrees exist, since each worktree has its own .claude/commands/.
    """

    migration_id = "0.7.1_worktree_commands_dedup"
    description = "Remove duplicate .claude/commands/ from main repo when using worktrees"
    target_version = "0.7.1"

    def detect(self, project_path: Path) -> bool:
        """Check if main repo has .claude/commands/ AND worktrees with same."""
        main_claude_commands = project_path / ".claude" / "commands"
        worktrees_dir = project_path / ".worktrees"

        # Only relevant if main repo has .claude/commands/
        if not main_claude_commands.exists():
            return False

        # And worktrees exist with their own .claude/commands/
        if not worktrees_dir.exists():
            return False

        for worktree in worktrees_dir.iterdir():
            if worktree.is_dir():
                wt_commands = worktree / ".claude" / "commands"
                if wt_commands.exists():
                    return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Always safe to apply - we're removing duplicates."""
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Remove .claude/commands/ from main repo."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        main_claude_commands = project_path / ".claude" / "commands"

        if main_claude_commands.exists():
            if dry_run:
                changes.append(
                    "Would remove .claude/commands/ from main repo (worktrees have their own)"
                )
            else:
                try:
                    shutil.rmtree(main_claude_commands)
                    changes.append(
                        "Removed .claude/commands/ from main repo (worktrees have their own)"
                    )
                except OSError as e:
                    errors.append(f"Failed to remove .claude/commands/: {e}")

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
