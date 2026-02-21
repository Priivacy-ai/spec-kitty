"""Migration: Move constitution to `.kittify/constitution/` directory."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

logger = logging.getLogger(__name__)


@MigrationRegistry.register
class ConstitutionDirectoryMigration(BaseMigration):
    """Move constitution file from memory root to dedicated constitution directory."""

    migration_id = "2.0.0_constitution_directory"
    description = "Move constitution to .kittify/constitution/ directory"
    target_version = "2.0.0"

    def detect(self, project_path: Path) -> bool:
        """Return True when legacy constitution location is still in use."""
        old_path = project_path / ".kittify" / "memory" / "constitution.md"
        new_path = project_path / ".kittify" / "constitution" / "constitution.md"
        return old_path.exists() or new_path.exists()

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """This migration only requires project filesystem access."""
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Apply constitution relocation and optional initial sync extraction."""
        result = MigrationResult(success=True)

        old_path = project_path / ".kittify" / "memory" / "constitution.md"
        new_dir = project_path / ".kittify" / "constitution"
        new_path = new_dir / "constitution.md"

        # Scenario 1: Old path exists, new doesn't -> move
        if old_path.exists() and not new_path.exists():
            if dry_run:
                result.changes_made.append(
                    f"Would move {old_path.relative_to(project_path)} -> {new_path.relative_to(project_path)}"
                )
                return result

            new_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_path), str(new_path))
            result.changes_made.append(
                f"Moved {old_path.relative_to(project_path)} -> {new_path.relative_to(project_path)}"
            )

            # Trigger initial extraction
            try:
                from specify_cli.constitution.sync import sync

                sync_result = sync(new_path, force=True)
                if sync_result.synced:
                    result.changes_made.append(
                        f"Initial extraction: {len(sync_result.files_written)} YAML files created"
                    )
                elif sync_result.error:
                    result.warnings.append(f"Initial extraction failed: {sync_result.error}")
            except Exception as e:
                result.warnings.append(
                    f"Initial extraction skipped ({e}). Run 'spec-kitty constitution sync' manually."
                )
            return result

        # Scenario 2: Both exist -> skip (user already migrated manually)
        if old_path.exists() and new_path.exists():
            result.changes_made.append(
                f"Constitution already at {new_path.relative_to(project_path)}, "
                f"old copy remains at {old_path.relative_to(project_path)}"
            )
            return result

        # Scenario 3: New exists, old doesn't -> skip (already migrated)
        if new_path.exists() and not old_path.exists():
            result.changes_made.append(f"Constitution already at {new_path.relative_to(project_path)}")
            return result

        # Scenario 4: Neither exists -> skip (no constitution)
        result.changes_made.append("No constitution found, skipping migration")
        return result


class Migration:
    """Backward-compatible migration wrapper for legacy tests/imports."""

    version = "2.0.0"
    description = ConstitutionDirectoryMigration.description

    def apply(self, project_path: Path, dry_run: bool = False) -> list[str]:
        impl = ConstitutionDirectoryMigration()
        result = impl.apply(project_path, dry_run=dry_run)
        # Legacy contract expected a flat list of change/warning strings.
        return [*result.changes_made, *(f"Warning: {w}" for w in result.warnings)]
