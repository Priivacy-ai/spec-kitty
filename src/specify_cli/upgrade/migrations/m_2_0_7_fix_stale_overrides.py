"""Migration: remove stale overrides created by version-skew during 2.0.6 upgrade.

When upgrading to 2.0.6, ensure_runtime() updated ~/.kittify/ BEFORE
execute_migration() ran. This caused classify_asset() to compare project files
against the already-updated global — every managed file from the older version
differed and was misclassified as CUSTOMIZED, then moved to .kittify/overrides/.

This repair migration scans .kittify/overrides/ for files that are byte-identical
to the current package-bundled defaults and removes them (they were never real
user customizations). Genuine user customizations are preserved.
"""

from __future__ import annotations

import filecmp
from pathlib import Path

from specify_cli.runtime.home import get_package_asset_root
from specify_cli.runtime.migrate import SHARED_ASSET_DIRS, SHARED_ASSET_FILES

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class FixStaleOverridesMigration(BaseMigration):
    """Remove stale overrides created by version-skew during upgrade."""

    migration_id = "2.0.7_fix_stale_overrides"
    description = "Remove stale overrides that match current package defaults"
    target_version = "2.0.7"

    def detect(self, project_path: Path) -> bool:
        """Return True if any override file is byte-identical to a package default."""
        overrides_dir = project_path / ".kittify" / "overrides"
        if not overrides_dir.exists():
            return False

        try:
            package_root = get_package_asset_root()
        except FileNotFoundError:
            return False

        for override_file in overrides_dir.rglob("*"):
            if not override_file.is_file():
                continue
            rel = override_file.relative_to(overrides_dir)
            if _is_shared_asset(rel) and _matches_package_default(
                override_file, rel, package_root
            ):
                return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if the overrides directory exists."""
        overrides_dir = project_path / ".kittify" / "overrides"
        if overrides_dir.exists():
            return True, ""
        return False, "No .kittify/overrides/ directory found"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Remove stale overrides that match package defaults."""
        changes: list[str] = []
        warnings: list[str] = []

        overrides_dir = project_path / ".kittify" / "overrides"
        if not overrides_dir.exists():
            return MigrationResult(success=True, changes_made=["No overrides directory — nothing to do"])

        try:
            package_root = get_package_asset_root()
        except FileNotFoundError:
            return MigrationResult(
                success=False,
                errors=["Cannot locate package assets — unable to compare overrides"],
            )

        removed_count = 0
        for override_file in sorted(overrides_dir.rglob("*")):
            if not override_file.is_file():
                continue

            rel = override_file.relative_to(overrides_dir)
            if not _is_shared_asset(rel):
                continue

            if _matches_package_default(override_file, rel, package_root):
                removed_count += 1
                verb = "Would remove" if dry_run else "Removed"
                changes.append(f"{verb} stale override: overrides/{rel}")
                if not dry_run:
                    override_file.unlink()

        # Clean up empty directories in overrides/
        if not dry_run and overrides_dir.exists():
            _cleanup_empty_override_dirs(overrides_dir)

        if not changes:
            changes.append("No stale overrides found — nothing to do")

        return MigrationResult(success=True, changes_made=changes, warnings=warnings)


def _is_shared_asset(rel: Path) -> bool:
    """Check if a relative path corresponds to a shared asset."""
    top_level = rel.parts[0] if rel.parts else ""
    return top_level in SHARED_ASSET_DIRS or rel.name in SHARED_ASSET_FILES


def _matches_package_default(
    override_file: Path,
    rel: Path,
    package_root: Path,
    mission: str = "software-dev",
) -> bool:
    """Check if an override file is byte-identical to a package-bundled default."""
    # Try mission-specific path first
    pkg_path = package_root / mission / str(rel)
    if pkg_path.exists() and pkg_path.is_file():
        return filecmp.cmp(str(override_file), str(pkg_path), shallow=False)

    # Fall back to direct path under package root
    pkg_path = package_root / str(rel)
    if pkg_path.exists() and pkg_path.is_file():
        return filecmp.cmp(str(override_file), str(pkg_path), shallow=False)

    return False


def _cleanup_empty_override_dirs(overrides_dir: Path) -> None:
    """Remove empty directories within overrides/, bottom-up."""
    for dirpath in sorted(overrides_dir.rglob("*"), reverse=True):
        if dirpath.is_dir() and not any(dirpath.iterdir()):
            dirpath.rmdir()

    # Remove overrides/ itself if empty
    if overrides_dir.exists() and not any(overrides_dir.iterdir()):
        overrides_dir.rmdir()
