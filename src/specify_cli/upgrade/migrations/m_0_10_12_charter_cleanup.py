"""Stub: superseded by 3.1.1_charter_rename migration."""

from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class CharterCleanupMigration(BaseMigration):
    migration_id = "0.10.12_charter_cleanup"
    description = "Superseded by 3.1.1_charter_rename"
    target_version = "0.10.12"

    def detect(self, project_path: Path) -> bool:
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        return False, "Superseded by charter-rename migration"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        return MigrationResult(success=True, warnings=["Superseded by charter-rename"])
