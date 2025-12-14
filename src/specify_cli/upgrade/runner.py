"""Migration runner for Spec Kitty upgrade system."""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rich.console import Console

from .detector import VersionDetector
from .metadata import ProjectMetadata
from .migrations.base import BaseMigration, MigrationResult
from .registry import MigrationRegistry


@dataclass
class UpgradeResult:
    """Result of an upgrade operation."""

    success: bool
    from_version: str
    to_version: str
    migrations_applied: List[str] = field(default_factory=list)
    migrations_skipped: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    dry_run: bool = False


class MigrationRunner:
    """Orchestrates the migration process."""

    def __init__(self, project_path: Path, console: Optional[Console] = None):
        """Initialize the runner.

        Args:
            project_path: Root of the project
            console: Optional Rich console for output
        """
        self.project_path = project_path
        self.kittify_dir = project_path / ".kittify"
        self.console = console or Console()
        self.detector = VersionDetector(project_path)

    def upgrade(
        self,
        target_version: str,
        dry_run: bool = False,
        force: bool = False,
        include_worktrees: bool = True,
    ) -> UpgradeResult:
        """Run all needed migrations to reach target version.

        Args:
            target_version: Version to upgrade to
            dry_run: If True, simulate but don't apply
            force: If True, skip confirmation prompts
            include_worktrees: If True, also upgrade worktrees

        Returns:
            UpgradeResult with details of the upgrade
        """
        from_version = self.detector.detect_version()

        result = UpgradeResult(
            success=True,
            from_version=from_version,
            to_version=target_version,
            dry_run=dry_run,
        )

        # Get applicable migrations
        migrations = MigrationRegistry.get_applicable(from_version, target_version)

        if not migrations:
            result.warnings.append(
                f"No migrations needed from {from_version} to {target_version}"
            )
            return result

        # Load or create metadata
        metadata = ProjectMetadata.load(self.kittify_dir)
        if metadata is None:
            metadata = self._create_initial_metadata(from_version)

        # Apply each migration to main project
        for migration in migrations:
            migration_result = self._apply_migration(migration, metadata, dry_run)

            if migration_result.success:
                result.migrations_applied.append(migration.migration_id)
                result.warnings.extend(migration_result.warnings)
            else:
                # Check if it was skipped (already applied)
                if metadata.has_migration(migration.migration_id):
                    result.migrations_skipped.append(migration.migration_id)
                else:
                    result.success = False
                    result.errors.extend(migration_result.errors)
                    # Stop on first failure
                    break

        # Update and save metadata for main project
        if not dry_run and result.success:
            metadata.version = target_version
            metadata.last_upgraded_at = datetime.now()
            metadata.save(self.kittify_dir)

        # Handle worktrees
        if include_worktrees:
            worktrees_result = self._upgrade_worktrees(
                target_version, migrations, dry_run
            )
            result.warnings.extend(worktrees_result.get("warnings", []))
            if worktrees_result.get("errors"):
                result.errors.extend(worktrees_result["errors"])
                # Don't fail the whole upgrade for worktree issues
                result.warnings.append(
                    "Some worktrees had issues - check errors above"
                )

        return result

    def _apply_migration(
        self,
        migration: BaseMigration,
        metadata: ProjectMetadata,
        dry_run: bool,
    ) -> MigrationResult:
        """Apply a single migration.

        Args:
            migration: The migration to apply
            metadata: Project metadata
            dry_run: Whether to simulate only

        Returns:
            MigrationResult with details
        """
        # Skip if already applied
        if metadata.has_migration(migration.migration_id):
            return MigrationResult(
                success=True,
                warnings=[f"Migration {migration.migration_id} already applied, skipping"],
            )

        # Check if migration is needed via detection
        if not migration.detect(self.project_path):
            # Migration not needed - project doesn't have old state
            if not dry_run:
                metadata.record_migration(
                    migration.migration_id, "skipped", "Not applicable"
                )
            return MigrationResult(
                success=True,
                warnings=[
                    f"Migration {migration.migration_id} not needed (project already in target state)"
                ],
            )

        # Check if safe to apply
        can_apply, reason = migration.can_apply(self.project_path)
        if not can_apply:
            return MigrationResult(
                success=False,
                errors=[f"Cannot apply {migration.migration_id}: {reason}"],
            )

        # Apply the migration
        result = migration.apply(self.project_path, dry_run=dry_run)

        # Record in metadata
        if not dry_run:
            metadata.record_migration(
                migration.migration_id,
                "success" if result.success else "failed",
                "; ".join(result.changes_made) if result.changes_made else None,
            )

        return result

    def _upgrade_worktrees(
        self,
        target_version: str,
        migrations: List[BaseMigration],
        dry_run: bool,
    ) -> dict:
        """Upgrade all worktrees in .worktrees/ directory.

        Args:
            target_version: Target version
            migrations: List of migrations to apply
            dry_run: Whether to simulate only

        Returns:
            Dict with warnings and errors lists
        """
        result: dict = {"warnings": [], "errors": []}

        worktrees_dir = self.project_path / ".worktrees"
        if not worktrees_dir.exists():
            return result

        for worktree in worktrees_dir.iterdir():
            if not worktree.is_dir():
                continue

            wt_kittify = worktree / ".kittify"
            if not wt_kittify.exists():
                continue

            # Load or create worktree metadata
            wt_metadata = ProjectMetadata.load(wt_kittify)
            if wt_metadata is None:
                wt_detector = VersionDetector(worktree)
                wt_version = wt_detector.detect_version()
                wt_metadata = self._create_initial_metadata(wt_version)

            # Apply migrations to worktree
            for migration in migrations:
                if wt_metadata.has_migration(migration.migration_id):
                    continue

                if not migration.detect(worktree):
                    if not dry_run:
                        wt_metadata.record_migration(
                            migration.migration_id, "skipped", "Not applicable"
                        )
                    continue

                can_apply, reason = migration.can_apply(worktree)
                if not can_apply:
                    result["warnings"].append(
                        f"Worktree {worktree.name}: Cannot apply {migration.migration_id}: {reason}"
                    )
                    continue

                migration_result = migration.apply(worktree, dry_run=dry_run)

                if migration_result.success:
                    if not dry_run:
                        wt_metadata.record_migration(
                            migration.migration_id,
                            "success",
                            "; ".join(migration_result.changes_made)
                            if migration_result.changes_made
                            else None,
                        )
                    result["warnings"].extend(
                        [f"Worktree {worktree.name}: {w}" for w in migration_result.warnings]
                    )
                else:
                    result["errors"].extend(
                        [f"Worktree {worktree.name}: {e}" for e in migration_result.errors]
                    )

            # Save worktree metadata
            if not dry_run:
                wt_metadata.version = target_version
                wt_metadata.last_upgraded_at = datetime.now()
                wt_metadata.save(wt_kittify)

        return result

    def _create_initial_metadata(self, detected_version: str) -> ProjectMetadata:
        """Create initial metadata for a project without it.

        Args:
            detected_version: Version detected from heuristics

        Returns:
            New ProjectMetadata instance
        """
        return ProjectMetadata(
            version=detected_version,
            initialized_at=datetime.now(),
            python_version=platform.python_version(),
            platform=sys.platform,
            platform_version=platform.platform(),
        )
