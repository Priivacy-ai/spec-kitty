"""Migration: add runtime state surfaces to .gitignore from state contract.

Ensures that all runtime gitignore entries defined in the state contract
are present in existing projects' .gitignore files. This keeps the git
boundary aligned with the authoritative state contract.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.gitignore_manager import GitignoreManager
from specify_cli.state_contract import get_runtime_gitignore_entries

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class StateGitignoreMigration(BaseMigration):
    """Add runtime state surfaces to .gitignore."""

    migration_id = "2.0.9_state_gitignore"
    description = "Add runtime state surfaces to .gitignore"
    target_version = "2.0.9"

    def detect(self, project_path: Path) -> bool:
        """Return True if any runtime entries are missing from .gitignore."""
        gitignore_path = project_path / ".gitignore"
        if not gitignore_path.exists():
            return True
        content = gitignore_path.read_text()
        entries = get_runtime_gitignore_entries()
        return any(entry not in content for entry in entries)

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if the project directory exists and is writable."""
        if not project_path.exists():
            return False, f"Project path does not exist: {project_path}"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Add runtime state entries to .gitignore."""
        entries = get_runtime_gitignore_entries()

        if dry_run:
            return MigrationResult(
                success=True,
                changes_made=[
                    f"Would add {len(entries)} runtime state entries to .gitignore"
                ],
            )

        manager = GitignoreManager(project_path)
        modified = manager.ensure_entries(entries)

        if modified:
            return MigrationResult(
                success=True,
                changes_made=[
                    f"Added runtime state entries to .gitignore: {', '.join(entries)}"
                ],
            )

        return MigrationResult(
            success=True,
            changes_made=["All runtime state entries already present in .gitignore"],
        )
