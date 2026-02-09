"""Upgrade migration: reconstruct full event history from WP frontmatter.

Wraps ``specify_cli.status.migrate.migrate_feature()`` for the upgrade
framework so ``spec-kitty upgrade`` discovers and runs it automatically.

Migration ID ``2.0.0_historical_status_migration`` is shared across
2.x and 0.x branches for cross-branch idempotency.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

logger = logging.getLogger(__name__)


@MigrationRegistry.register
class HistoricalStatusMigration(BaseMigration):
    """Reconstruct full event history from WP frontmatter."""

    migration_id = "2.0.0_historical_status_migration"
    description = "Reconstruct full event history from WP frontmatter"
    target_version = "2.0.0"

    def detect(self, project_path: Path) -> bool:
        """Return True if any feature has WPs but no full-history events."""
        kitty_specs = project_path / "kitty-specs"
        if not kitty_specs.exists():
            return False

        for feature_dir in sorted(kitty_specs.iterdir()):
            if not feature_dir.is_dir():
                continue
            tasks_dir = feature_dir / "tasks"
            if not tasks_dir.exists():
                continue
            wp_files = list(tasks_dir.glob("WP*.md"))
            if not wp_files:
                continue

            events_file = feature_dir / "status.events.jsonl"
            if not events_file.exists():
                return True

            content = events_file.read_text(encoding="utf-8").strip()
            if not content:
                return True

            # Check for migration-only events (legacy bootstrap, needs upgrade)
            from specify_cli.status.store import read_events, StoreError

            try:
                events = read_events(feature_dir)
                if not events:
                    return True
                # Has marker? Already migrated with full history.
                if any(
                    e.reason and "historical_frontmatter_to_jsonl:v1" in e.reason
                    for e in events
                ):
                    continue
                # Has non-migration actors? Live data, skip.
                if any(not e.actor.startswith("migration") for e in events):
                    continue
                # All migration actors, no marker -> legacy bootstrap, needs upgrade
                return True
            except StoreError:
                return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check that kitty-specs exists and status module is importable."""
        kitty_specs = project_path / "kitty-specs"
        if not kitty_specs.exists():
            return False, "No kitty-specs directory found"

        try:
            from specify_cli.status.migrate import migrate_feature  # noqa: F401

            return True, ""
        except ImportError as e:
            return False, f"Status module not available: {e}"

    def apply(
        self, project_path: Path, dry_run: bool = False
    ) -> MigrationResult:
        """Run full-history migration across all features."""
        from specify_cli.status.migrate import migrate_feature

        result = MigrationResult(success=True)
        kitty_specs = project_path / "kitty-specs"

        if not kitty_specs.exists():
            return result

        for feature_dir in sorted(kitty_specs.iterdir()):
            if not feature_dir.is_dir():
                continue
            tasks_dir = feature_dir / "tasks"
            if not tasks_dir.exists() or not list(tasks_dir.glob("WP*.md")):
                continue

            try:
                fr = migrate_feature(feature_dir, dry_run=dry_run)
                if fr.status == "migrated":
                    wp_count = sum(
                        1 for wp in fr.wp_details if wp.events_created > 0
                    )
                    total_events = sum(
                        wp.events_created for wp in fr.wp_details
                    )
                    result.changes_made.append(
                        f"{feature_dir.name}: migrated "
                        f"({wp_count} WPs, {total_events} events)"
                    )
                elif fr.status == "failed":
                    result.warnings.append(
                        f"{feature_dir.name}: {fr.error}"
                    )
            except Exception as e:
                result.errors.append(f"{feature_dir.name}: {e}")

        if result.errors:
            result.success = False
        return result
