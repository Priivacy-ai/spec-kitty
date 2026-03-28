"""Migration: add NEW runtime state surfaces to .gitignore.

Adds the 5 runtime gitignore entries introduced by this sprint to existing
projects.  Existing entries (.dashboard, workspaces/, constitution/*,
missions/__pycache__/) are already present in projects that were initialized
before this migration -- they are NOT re-added here.

Per constraint C-001, constitution surfaces are explicitly excluded from
this migration's scope.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.gitignore_manager import GitignoreManager

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

# Only the entries introduced by this sprint.  Existing projects already
# have .dashboard, workspaces/, constitution/*, and missions/__pycache__/
# in their .gitignore.  We intentionally do NOT use the full
# get_runtime_gitignore_entries() helper here to avoid backfilling
# constitution surfaces or other pre-existing entries.
# The kitty-specs/**/.kittify/dossiers/ entry covers mission-local dossier
# snapshots saved by src/specify_cli/dossier/snapshot.py.
_NEW_RUNTIME_ENTRIES = [
    ".kittify/runtime/",
    ".kittify/merge-state.json",
    ".kittify/events/",
    ".kittify/dossiers/",
    "kitty-specs/**/.kittify/dossiers/",
]


@MigrationRegistry.register
class StateGitignoreMigration(BaseMigration):
    """Add runtime state surfaces to .gitignore."""

    migration_id = "2.0.9_state_gitignore"
    description = "Add runtime state surfaces to .gitignore"
    target_version = "2.0.9"

    def detect(self, project_path: Path) -> bool:
        """Return True if any of the 5 new runtime entries are missing."""
        gitignore_path = project_path / ".gitignore"
        if not gitignore_path.exists():
            return True
        content = gitignore_path.read_text()
        return any(entry not in content for entry in _NEW_RUNTIME_ENTRIES)

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if the project directory exists and is writable."""
        if not project_path.exists():
            return False, f"Project path does not exist: {project_path}"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Add the 5 new runtime state entries to .gitignore."""
        if dry_run:
            return MigrationResult(
                success=True,
                changes_made=[
                    f"Would add {len(_NEW_RUNTIME_ENTRIES)} runtime state entries to .gitignore"
                ],
            )

        manager = GitignoreManager(project_path)
        modified = manager.ensure_entries(_NEW_RUNTIME_ENTRIES)

        if modified:
            return MigrationResult(
                success=True,
                changes_made=[
                    f"Added runtime state entries to .gitignore: {', '.join(_NEW_RUNTIME_ENTRIES)}"
                ],
            )

        return MigrationResult(
            success=True,
            changes_made=["All runtime state entries already present in .gitignore"],
        )
