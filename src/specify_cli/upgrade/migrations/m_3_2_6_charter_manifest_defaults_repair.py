"""Repair current v2 charter manifests missing verifier-visible defaults."""

from __future__ import annotations

from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult
from charter.versioning import (
    CURRENT_BUNDLE_SCHEMA_VERSION,
    BundleCompatibilityStatus,
    check_bundle_compatibility,
    get_bundle_schema_version,
    repair_v2_synthesis_manifest_defaults,
)


@MigrationRegistry.register
class CharterManifestDefaultsRepair(BaseMigration):
    """Repairs current v2 synthesis manifests from before built_in_only was serialized."""

    migration_id = "3.2.6_charter_manifest_defaults_repair"
    target_version = "3.2.6"
    description = (
        "Repair current v2 charter synthesis manifests that predate verifier-visible "
        "manifest defaults."
    )

    def detect(self, project_path: Path) -> bool:
        charter_dir = project_path / ".kittify" / "charter"
        if not charter_dir.exists():
            return False
        if get_bundle_schema_version(charter_dir) != CURRENT_BUNDLE_SCHEMA_VERSION:
            return False

        repair = repair_v2_synthesis_manifest_defaults(charter_dir, dry_run=True)
        return bool(repair.changes_made or repair.errors)

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        charter_dir = project_path / ".kittify" / "charter"
        if not charter_dir.exists():
            return False, "No charter directory found at .kittify/charter"

        bundle_version = get_bundle_schema_version(charter_dir)
        compatibility = check_bundle_compatibility(bundle_version)
        if compatibility.status in (
            BundleCompatibilityStatus.INCOMPATIBLE_OLD,
            BundleCompatibilityStatus.INCOMPATIBLE_NEW,
        ):
            return False, compatibility.message
        if bundle_version != CURRENT_BUNDLE_SCHEMA_VERSION:
            return False, "Charter bundle is not at current v2 schema."
        return True, ""

    def apply(
        self,
        project_path: Path,
        dry_run: bool = False,
    ) -> MigrationResult:
        repair = repair_v2_synthesis_manifest_defaults(
            project_path / ".kittify" / "charter",
            dry_run=dry_run,
        )
        return MigrationResult(
            success=len(repair.errors) == 0,
            changes_made=repair.changes_made,
            errors=repair.errors,
        )
