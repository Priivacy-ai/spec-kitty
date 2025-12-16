"""Migration: Remove deprecated .kittify/active-mission file/symlink."""

from __future__ import annotations

from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class RemoveActiveMissionMigration(BaseMigration):
    """Remove deprecated .kittify/active-mission file or symlink.

    As of v0.8.0, missions are selected per-feature during /spec-kitty.specify.
    The project-level .kittify/active-mission symlink/file is no longer used.

    This migration removes the obsolete active-mission file and informs the
    user about the new per-feature mission workflow.
    """

    migration_id = "0.8.0_remove_active_mission"
    description = "Remove deprecated .kittify/active-mission (missions are now per-feature)"
    target_version = "0.8.0"

    def detect(self, project_path: Path) -> bool:
        """Check if .kittify/active-mission exists."""
        kittify_dir = project_path / ".kittify"
        active_mission = kittify_dir / "active-mission"

        # Check for file, symlink, or broken symlink
        return active_mission.exists() or active_mission.is_symlink()

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Migration can always be applied if active-mission exists."""
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Remove .kittify/active-mission file or symlink."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        kittify_dir = project_path / ".kittify"
        active_mission = kittify_dir / "active-mission"

        if active_mission.exists() or active_mission.is_symlink():
            if dry_run:
                changes.append(
                    "Would remove .kittify/active-mission"
                )
                changes.append(
                    "  -> Missions are now selected per-feature during /spec-kitty.specify"
                )
            else:
                try:
                    active_mission.unlink()
                    changes.append(
                        "Removed deprecated .kittify/active-mission"
                    )
                    changes.append(
                        "  -> Missions are now selected per-feature during /spec-kitty.specify"
                    )
                    changes.append(
                        "  -> Existing features will use 'software-dev' mission by default"
                    )
                except OSError as e:
                    errors.append(
                        f"Failed to remove .kittify/active-mission: {e}"
                    )
        else:
            warnings.append(
                "No .kittify/active-mission found (already migrated or new project)"
            )

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
