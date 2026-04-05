"""Stub: superseded by 3.1.1_charter_rename migration."""

from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class FixCharterDoctrineSkillMigration(BaseMigration):
    migration_id = "2.1.2_fix_charter_doctrine_skill"
    description = "Superseded by 3.1.1_charter_rename"
    target_version = "2.1.2"

    def detect(self, project_path: Path) -> bool:
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        return False, "Superseded by charter-rename migration"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        return MigrationResult(success=True, warnings=["Superseded by charter-rename"])
