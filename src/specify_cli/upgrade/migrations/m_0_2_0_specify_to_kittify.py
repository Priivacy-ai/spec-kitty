"""Migration: Rename .specify/ to .kittify/ and /specs/ to /kitty-specs/."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class SpecifyToKittifyMigration(BaseMigration):
    """Migrate from .specify/ to .kittify/ and /specs/ to /kitty-specs/.

    This migration handles the rebranding from the original "specify"
    naming to "kittify" naming introduced in v0.2.0.
    """

    migration_id = "0.2.0_specify_to_kittify"
    description = "Rename .specify/ to .kittify/ and /specs/ to /kitty-specs/"
    target_version = "0.2.0"

    def detect(self, project_path: Path) -> bool:
        """Check if project uses old .specify/ directory."""
        return (project_path / ".specify").exists()

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if migration can be safely applied."""
        specify_dir = project_path / ".specify"
        kittify_dir = project_path / ".kittify"

        if not specify_dir.exists():
            return False, ".specify/ directory does not exist"

        if kittify_dir.exists():
            return False, ".kittify/ already exists - manual merge required"

        specs_dir = project_path / "specs"
        kitty_specs_dir = project_path / "kitty-specs"

        if specs_dir.exists() and kitty_specs_dir.exists():
            return False, "Both /specs/ and /kitty-specs/ exist - manual merge required"

        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Apply the migration."""
        changes: list[str] = []
        errors: list[str] = []

        specify_dir = project_path / ".specify"
        kittify_dir = project_path / ".kittify"
        specs_dir = project_path / "specs"
        kitty_specs_dir = project_path / "kitty-specs"

        # Rename .specify/ to .kittify/
        if specify_dir.exists():
            if dry_run:
                changes.append(f"Would rename {specify_dir} to {kittify_dir}")
            else:
                try:
                    shutil.move(str(specify_dir), str(kittify_dir))
                    changes.append(f"Renamed {specify_dir} to {kittify_dir}")
                except OSError as e:
                    errors.append(f"Failed to rename .specify/ to .kittify/: {e}")

        # Rename /specs/ to /kitty-specs/
        if specs_dir.exists() and not kitty_specs_dir.exists():
            if dry_run:
                changes.append(f"Would rename {specs_dir} to {kitty_specs_dir}")
            else:
                try:
                    shutil.move(str(specs_dir), str(kitty_specs_dir))
                    changes.append(f"Renamed {specs_dir} to {kitty_specs_dir}")
                except OSError as e:
                    errors.append(f"Failed to rename /specs/ to /kitty-specs/: {e}")

        success = len(errors) == 0
        return MigrationResult(success=success, changes_made=changes, errors=errors)
