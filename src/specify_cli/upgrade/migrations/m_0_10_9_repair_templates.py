"""Migration: Repair broken templates for users affected by #62, #63, #64."""

from __future__ import annotations

from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class RepairTemplatesMigration(BaseMigration):
    """Repair templates for projects with broken bash script references.

    This migration addresses issues #62, #63, #64 where PyPI installations
    received outdated templates with bash script references. It detects
    broken templates and regenerates them from the correct source.
    """

    migration_id = "0.10.9_repair_templates"
    description = "Repair broken templates with bash script references"
    target_version = "0.10.9"

    def detect(self, project_path: Path) -> bool:  # noqa: ARG002
        """Always returns False — command templates removed in WP10 (canonical context architecture).

        Shim generation (spec-kitty agent shim) now replaces template-based agent commands.
        There are no bash-script-reference templates to repair; this migration is permanently inert.
        """
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:  # noqa: ARG002
        """WP10: Command templates were removed; this migration is permanently inert."""
        return False, "WP10: Command templates were removed. Shim generation replaces template-based commands."

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:  # noqa: ARG002
        """No-op: command templates no longer exist to repair."""
        return MigrationResult(
            success=True,
            changes_made=["Skipped: command templates removed in WP10; shim generation replaces them"],
            errors=[],
            warnings=[],
        )
