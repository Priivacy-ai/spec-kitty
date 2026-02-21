"""Migration: Remove mission-specific constitution directories."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class ConstitutionCleanupMigration(BaseMigration):
    """Remove mission-specific constitution directories.

    As of 0.10.12, spec-kitty uses only project-level constitutions
    at .kittify/memory/constitution.md. Mission-specific constitutions
    in .kittify/missions/*/constitution/ are removed.
    """

    migration_id = "0.10.12_constitution_cleanup"
    description = "Remove mission-specific constitution directories"
    target_version = "0.10.12"

    def detect(self, project_path: Path) -> bool:
        """Check if any mission has a constitution directory."""
        missions_dir = project_path / ".kittify" / "missions"
        if not missions_dir.exists():
            return False

        for mission_dir in missions_dir.iterdir():
            if mission_dir.is_dir() and (mission_dir / "constitution").exists():
                return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if migration can be applied."""
        kittify_dir = project_path / ".kittify"
        if not kittify_dir.exists():
            return False, "No .kittify directory (not a spec-kitty project)"

        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Remove constitution directories from all missions."""
        changes: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []

        missions_dir = project_path / ".kittify" / "missions"
        if not missions_dir.exists():
            return MigrationResult(
                success=True,
                changes_made=[],
                errors=[],
                warnings=[],
            )

        removed_from: List[str] = []
        for mission_dir in missions_dir.iterdir():
            if not mission_dir.is_dir():
                continue

            constitution_dir = mission_dir / "constitution"
            if not constitution_dir.exists():
                continue

            if dry_run:
                changes.append(f"Would remove {mission_dir.name}/constitution/")
                continue

            try:
                shutil.rmtree(constitution_dir)
                changes.append(f"Removed {mission_dir.name}/constitution/")
                removed_from.append(mission_dir.name)
            except OSError as e:
                errors.append(f"Failed to remove {mission_dir.name}/constitution/: {e}")

        if removed_from:
            warnings.append(
                "Mission-specific constitutions removed from: "
                f"{', '.join(removed_from)}. "
                "Spec-kitty now uses a single project-level constitution at "
                ".kittify/memory/constitution.md."
            )
        elif not changes:
            changes.append("No mission-specific constitutions found (already clean)")

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
