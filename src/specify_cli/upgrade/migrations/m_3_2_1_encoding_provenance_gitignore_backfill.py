"""Migration: backfill encoding-provenance gitignore coverage for 3.2.1 projects."""

from __future__ import annotations

from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class EncodingProvenanceGitignoreBackfillMigration(BaseMigration):  # type: ignore[misc]
    """Re-run the runtime git hygiene repair for already-shipped 3.2.1 installs."""

    migration_id = "3.2.1_encoding_provenance_gitignore_backfill"
    description = "Backfill encoding-provenance gitignore coverage"
    target_version = "3.2.1"

    def detect(self, project_path: Path) -> bool:
        from .m_3_2_0rc35_sync_state_gitignore import (
            KittifyRuntimeGitHygieneMigration,
        )

        return KittifyRuntimeGitHygieneMigration().detect(project_path)

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        from .m_3_2_0rc35_sync_state_gitignore import (
            KittifyRuntimeGitHygieneMigration,
        )

        return KittifyRuntimeGitHygieneMigration().can_apply(project_path)

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        from .m_3_2_0rc35_sync_state_gitignore import (
            KittifyRuntimeGitHygieneMigration,
        )

        return KittifyRuntimeGitHygieneMigration().apply(project_path, dry_run=dry_run)
