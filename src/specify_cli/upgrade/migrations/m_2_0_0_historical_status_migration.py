"""Upgrade migration: reconstruct full event history from WP frontmatter.

NOTE: This migration is now a no-op. The ``status.migrate`` module has been
removed as part of making the event log the sole authority for WP state.
All features are assumed to already have canonical event logs.

Migration ID ``2.0.0_historical_status_migration`` is kept in the registry
for idempotency across environments that may have already run it.
"""

from __future__ import annotations

from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class HistoricalStatusMigration(BaseMigration):
    """No-op stub: event log bootstrap migration has been superseded."""

    migration_id = "2.0.0_historical_status_migration"
    description = "No-op: event log is now the sole authority (status.migrate removed)"
    target_version = "2.0.0"

    def detect(self, project_path: Path) -> bool:
        """Always returns False — migration has been superseded."""
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """No-op: nothing to migrate."""
        return MigrationResult(success=True, changes_made=["Already complete (no-op)"])
