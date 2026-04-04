"""Migration: Remove mission-specific charter directories."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class CharterCleanupMigration(BaseMigration):
    """Remove mission-specific charter directories.

    As of 0.10.12, spec-kitty uses only project-level charters
    at .kittify/memory/charter.md. Mission-specific charters
    in .kittify/missions/*/charter/ are removed.
    """

    migration_id = "0.10.12_charter_cleanup"
    description = "Remove mission-specific charter directories"
    target_version = "0.10.12"

    def detect(self, project_path: Path) -> bool:
        """Check if any mission has a charter directory."""
        missions_dir = project_path / ".kittify" / "missions"
        if not missions_dir.exists():
            return False

        for mission_dir in missions_dir.iterdir():
            if mission_dir.is_dir() and (mission_dir / "charter").exists():
                return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if migration can be applied."""
        kittify_dir = project_path / ".kittify"
        if not kittify_dir.exists():
            return False, "No .kittify directory (not a spec-kitty project)"

        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Remove charter directories from all missions."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        missions_dir = project_path / ".kittify" / "missions"
        if not missions_dir.exists():
            return MigrationResult(
                success=True,
                changes_made=[],
                errors=[],
                warnings=[],
            )

        removed_from: list[str] = []
        for mission_dir in missions_dir.iterdir():
            if not mission_dir.is_dir():
                continue

            charter_dir = mission_dir / "charter"
            if not charter_dir.exists():
                continue

            if dry_run:
                changes.append(f"Would remove {mission_dir.name}/charter/")
                continue

            try:
                shutil.rmtree(charter_dir)
                changes.append(f"Removed {mission_dir.name}/charter/")
                removed_from.append(mission_dir.name)
            except OSError as e:
                errors.append(f"Failed to remove {mission_dir.name}/charter/: {e}")

        if removed_from:
            warnings.append(
                "Mission-specific charters removed from: "
                f"{', '.join(removed_from)}. "
                "Spec-kitty now uses a single project-level charter at "
                ".kittify/memory/charter.md."
            )
        elif not changes:
            changes.append("No mission-specific charters found (already clean)")

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
