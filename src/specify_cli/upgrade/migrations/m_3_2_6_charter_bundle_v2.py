"""Migration m_3_2_6_charter_bundle_v2: upgrade charter bundle schema from v1 to v2.

Phase 7 provenance hardening — adds mandatory ``synthesizer_version``,
``source_input_ids``, ``produced_at``, ``synthesis_run_id`` fields to all
provenance sidecars, computes ``manifest_hash`` on the synthesis manifest, and
stamps ``bundle_schema_version: 2`` in ``metadata.yaml``.

Decision DM-01KQEG9HTZ8RSZW4D50CN8V6CJ (Option C): spec-kitty upgrade is the
single migration entry point.  Normal charter commands check
``bundle_schema_version`` and block with a "run ``spec-kitty upgrade``" error
when the bundle is incompatible.
"""

from __future__ import annotations

from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult as BaseMigrationResult
from doctrine.versioning import (
    CURRENT_BUNDLE_SCHEMA_VERSION,
    get_bundle_schema_version,
    run_migration,
)


@MigrationRegistry.register
class CharterBundleV2Migration(BaseMigration):
    """Upgrades charter doctrine bundles from v1 to v2 (Phase 7 hardening)."""

    migration_id = "3.2.6_charter_bundle_v2"
    target_version = "3.2.6"
    description = (
        "Upgrade charter bundle schema from v1 to v2 (Phase 7 provenance hardening): "
        "adds synthesizer_version, source_input_ids, produced_at, synthesis_run_id "
        "to provenance sidecars; stamps bundle_schema_version: 2 in metadata.yaml."
    )

    def detect(self, project_path: Path) -> bool:
        """Return True if the project has a charter bundle that needs migration."""
        charter_dir = project_path / ".kittify" / "charter"
        if not charter_dir.exists():
            return False
        bundle_version = get_bundle_schema_version(charter_dir)
        return bundle_version is None or bundle_version < CURRENT_BUNDLE_SCHEMA_VERSION

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Return (True, '') when the charter directory is present."""
        charter_dir = project_path / ".kittify" / "charter"
        if not charter_dir.exists():
            return False, "No charter directory found at .kittify/charter"
        return True, ""

    def apply(
        self, project_path: Path, dry_run: bool = False
    ) -> BaseMigrationResult:
        """Apply all pending charter bundle migrations up to CURRENT_BUNDLE_SCHEMA_VERSION."""
        charter_dir = project_path / ".kittify" / "charter"

        bundle_version = get_bundle_schema_version(charter_dir)
        if bundle_version is None:
            bundle_version = 1  # Treat missing version field as v1.

        if bundle_version >= CURRENT_BUNDLE_SCHEMA_VERSION:
            # Bundle is already current — nothing to do.
            return BaseMigrationResult(
                success=True,
                changes_made=[],
                errors=[],
            )

        all_changes: list[str] = []
        all_errors: list[str] = []
        current = bundle_version

        while current < CURRENT_BUNDLE_SCHEMA_VERSION:
            result = run_migration(current, charter_dir, dry_run=dry_run)
            all_changes.extend(result.changes_made)
            all_errors.extend(result.errors)
            current += 1

        return BaseMigrationResult(
            success=len(all_errors) == 0,
            changes_made=all_changes,
            errors=all_errors,
        )
