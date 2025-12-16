"""Migration: Update scripts to latest version."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class UpdateScriptsMigration(BaseMigration):
    """Update .kittify/scripts/ to latest version.

    The create-new-feature.sh script was fixed in v0.7.3 to scan both
    kitty-specs/ AND .worktrees/ for existing feature numbers. Projects
    initialized before v0.7.3 have the old script that only scans kitty-specs/,
    causing duplicate feature numbers when using worktrees.
    """

    migration_id = "0.7.3_update_scripts"
    description = "Update scripts to fix worktree feature numbering"
    target_version = "0.7.3"

    def detect(self, project_path: Path) -> bool:
        """Check if project has old scripts that need updating."""
        script_path = project_path / ".kittify" / "scripts" / "bash" / "create-new-feature.sh"

        if not script_path.exists():
            return False

        # Check if script has the fix (scans .worktrees/)
        try:
            content = script_path.read_text(encoding="utf-8")
            # Old script doesn't have this line
            if "Also scan .worktrees/" not in content:
                return True
        except (OSError, UnicodeDecodeError):
            return False

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if we can find the template scripts."""
        # We need access to the template scripts from the installed package
        import specify_cli

        pkg_root = Path(specify_cli.__file__).parent
        template_script = pkg_root / "scripts" / "bash" / "create-new-feature.sh"

        if not template_script.exists():
            return False, "Template scripts not found in installed package"

        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Copy updated scripts from package templates."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        import specify_cli

        pkg_root = Path(specify_cli.__file__).parent

        # Scripts to update
        scripts = [
            ("scripts/bash/create-new-feature.sh", ".kittify/scripts/bash/create-new-feature.sh"),
            ("scripts/bash/common.sh", ".kittify/scripts/bash/common.sh"),
        ]

        for src_rel, dest_rel in scripts:
            src = pkg_root / src_rel
            dest = project_path / dest_rel

            if not src.exists():
                warnings.append(f"Template {src_rel} not found in package")
                continue

            if not dest.parent.exists():
                if not dry_run:
                    dest.parent.mkdir(parents=True, exist_ok=True)

            if dry_run:
                changes.append(f"Would update {dest_rel}")
            else:
                try:
                    shutil.copy2(src, dest)
                    changes.append(f"Updated {dest_rel}")
                except OSError as e:
                    errors.append(f"Failed to update {dest_rel}: {e}")

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
