"""Migration: Install documentation mission to user projects (v0.12.0)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class InstallDocumentationMission(BaseMigration):
    """Install the documentation mission to user projects.

    This migration copies the documentation mission from the spec-kitty
    installation (src/doctrine/missions/documentation/) to the user's
    project (.kittify/missions/documentation/).

    The documentation mission enables users to create and maintain software
    documentation following Write the Docs and Divio principles.
    """

    migration_id = "0.12.0_documentation_mission"
    description = "Install documentation mission to user projects"
    target_version = "0.12.0"

    def detect(self, project_path: Path) -> bool:
        """Detect if documentation mission needs to be installed.

        Args:
            project_path: Root directory of user's spec-kitty project

        Returns:
            True if documentation mission is missing, False if already installed
        """
        kittify_dir = project_path / ".kittify"

        if not kittify_dir.exists():
            # Not a spec-kitty project, migration doesn't apply
            return False

        missions_dir = kittify_dir / "missions"

        if not missions_dir.exists():
            # Missions directory doesn't exist (very old project)
            # Migration should run to create it
            return True

        doc_mission_dir = missions_dir / "documentation"

        # Check if documentation mission already exists
        if doc_mission_dir.exists() and (doc_mission_dir / "mission.yaml").exists():
            # Already installed
            return False

        # Documentation mission is missing, migration should run
        return True

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if migration can be safely applied.

        Args:
            project_path: Root of the project

        Returns:
            (can_apply, reason) - True if safe, False with explanation if not
        """
        # Check if source mission exists
        source_mission = self._find_source_mission()
        if source_mission is None:
            return (
                False,
                "Could not locate documentation mission source in spec-kitty installation. "
                "This may indicate an incomplete installation.",
            )

        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Copy documentation mission to user project.

        Args:
            project_path: Root directory of user's spec-kitty project
            dry_run: If True, only simulate changes

        Returns:
            MigrationResult indicating success or failure
        """
        changes: list[str] = []
        errors: list[str] = []

        kittify_dir = project_path / ".kittify"
        missions_dir = kittify_dir / "missions"

        # Find source documentation mission
        source_mission = self._find_source_mission()

        if source_mission is None:
            errors.append("Could not find documentation mission source in spec-kitty installation")
            return MigrationResult(success=False, errors=errors)

        # Destination
        dest_mission = missions_dir / "documentation"

        # Check if destination already exists
        if dest_mission.exists() and (dest_mission / "mission.yaml").exists():
            return MigrationResult(
                success=True,
                changes_made=["Documentation mission already installed (skipped)"]
            )

        # Ensure missions directory exists
        if not missions_dir.exists():
            if dry_run:
                changes.append("Would create .kittify/missions/ directory")
            else:
                missions_dir.mkdir(parents=True, exist_ok=True)
                changes.append("Created .kittify/missions/ directory")

        # Copy mission directory
        if dry_run:
            changes.append("Would copy documentation mission to .kittify/missions/documentation/")
        else:
            try:
                shutil.copytree(source_mission, dest_mission)

                # Count copied files for reporting
                copied_files = list(dest_mission.rglob("*"))
                file_count = len([f for f in copied_files if f.is_file()])

                changes.append(f"Copied documentation mission ({file_count} files)")

            except Exception as e:
                errors.append(f"Failed to copy documentation mission: {e}")
                return MigrationResult(success=False, errors=errors)

        return MigrationResult(success=True, changes_made=changes)

    def _find_source_mission(self) -> Optional[Path]:
        """Find the documentation mission in spec-kitty's installation.

        Returns:
            Path to source mission directory, or None if not found
        """
        # The source is relative to this migration file
        migrations_dir = Path(__file__).parent
        src_dir = migrations_dir.parent.parent  # Up to src/specify_cli/
        source_mission = src_dir / "missions" / "documentation"

        if source_mission.exists() and (source_mission / "mission.yaml").exists():
            return source_mission

        return None
