"""Normalize legacy mission lifecycle inputs for the 3.2.0a4 MVP model.

This migration repairs historical ``kitty-specs`` missions enough that the
canonical lifecycle model can classify them consistently. It backfills
identity, rebuilds missing event logs from legacy state, and regenerates the
status/progress/lifecycle projections consumed by the CLI and Teamspace.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.migration.normalize_mission_lifecycle import normalize_repo

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


TARGET_VERSION = "3.2.0a4"


@MigrationRegistry.register
class NormalizeMissionLifecycleMigration(BaseMigration):
    """Upgrade migration for the MVP stale/abandoned mission lifecycle."""

    migration_id = "3.2.0a4_normalize_mission_lifecycle"
    description = "Normalize historical kitty-specs missions for canonical lifecycle state"
    target_version = TARGET_VERSION

    def detect(self, project_path: Path) -> bool:
        results = normalize_repo(project_path, dry_run=True)
        return any(result.status != "skipped" for result in results)

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if (project_path / "kitty-specs").exists() or (project_path / ".kittify").exists():
            return True, ""
        return False, "No kitty-specs/ directory found"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        results = normalize_repo(project_path, dry_run=dry_run)
        changes = [
            f"{result.slug}: {action}"
            for result in results
            if result.status == "normalized"
            for action in result.actions
        ]
        warnings = [
            f"{result.slug}: {warning}"
            for result in results
            for warning in result.warnings
        ]
        errors = [
            f"{result.slug}: {result.error}"
            for result in results
            if result.status == "error" and result.error
        ]
        return MigrationResult(
            success=not errors,
            changes_made=changes,
            warnings=warnings,
            errors=errors,
        )
