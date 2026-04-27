"""Migration runner for Spec Kitty upgrade system."""

from __future__ import annotations

import logging
import platform
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from packaging.version import InvalidVersion, Version
from rich.console import Console

logger = logging.getLogger(__name__)

from specify_cli.core.constants import KITTIFY_DIR, WORKTREES_DIR
from specify_cli.migration.schema_version import REQUIRED_SCHEMA_VERSION

from .detector import VersionDetector
from .metadata import ProjectMetadata
from .migrations.base import BaseMigration, MigrationResult
from .registry import MigrationRegistry


@dataclass
class UpgradeResult:
    """Result of an upgrade operation."""

    success: bool
    from_version: str
    to_version: str
    migrations_applied: list[str] = field(default_factory=list)
    migrations_skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dry_run: bool = False
    # Per-migration ``MigrationResult`` keyed by migration_id. Used by the
    # CLI --json path to surface schema-shaped reports emitted by individual
    # migrations (e.g. m_3_2_3_unified_bundle's contract-shaped payload).
    migration_results: dict[str, MigrationResult] = field(default_factory=dict)


def validate_upgrade_target(from_version: str, target_version: str) -> str | None:
    """Return an error message when the requested target would downgrade state."""
    if from_version == "unknown":
        return None

    try:
        if Version(target_version) < Version(from_version):
            return f"Refusing to downgrade project metadata from {from_version} to {target_version}"
    except InvalidVersion:
        return None

    return None


class MigrationRunner:
    """Orchestrates the migration process."""

    def __init__(self, project_path: Path, console: Console | None = None):
        """Initialize the runner.

        Args:
            project_path: Root of the project
            console: Optional Rich console for output
        """
        self.project_path = project_path
        self.kittify_dir = project_path / KITTIFY_DIR
        self.console = console or Console()
        self.detector = VersionDetector(project_path)

    def upgrade(
        self,
        target_version: str,
        dry_run: bool = False,
        force: bool = False,  # noqa: ARG002
        include_worktrees: bool = True,
    ) -> UpgradeResult:
        """Run all needed migrations to reach target version.

        Args:
            target_version: Version to upgrade to
            dry_run: If True, simulate but don't apply
            force: If True, skip confirmation prompts
            include_worktrees: If True, also upgrade worktrees

        Returns:
            UpgradeResult with details of the upgrade
        """
        from_version = self.detector.detect_version()

        result = UpgradeResult(
            success=True,
            from_version=from_version,
            to_version=target_version,
            dry_run=dry_run,
        )

        validation_error = validate_upgrade_target(from_version, target_version)
        if validation_error:
            result.success = False
            result.errors.append(validation_error)
            return result

        # Get applicable migrations
        version_for_migration = "0.0.0" if from_version == "unknown" else from_version
        migrations = MigrationRegistry.get_applicable(
            version_for_migration,
            target_version,
            project_path=self.project_path,
        )

        if not migrations:
            # Still update version stamp even when no migrations needed
            metadata = ProjectMetadata.load(self.kittify_dir)
            if metadata and not dry_run and metadata.version != target_version:
                metadata.version = target_version
                metadata.last_upgraded_at = datetime.now()
                metadata.save(self.kittify_dir)
            # Why: even when no schema-changing migrations are needed (e.g. an
            # idempotent 3.2.0a4 -> 3.2.0a4 re-run on a legacy project), the
            # schema_version stamp must still land so the gate does not block
            # the next agent command. Stamping after any save() is required
            # because ProjectMetadata.save() does not preserve unknown keys.
            # See FR-002 / #705.
            if not dry_run and REQUIRED_SCHEMA_VERSION is not None:
                self._stamp_schema_version(self.kittify_dir, REQUIRED_SCHEMA_VERSION)

            result.warnings.append(f"No migrations needed from {from_version} to {target_version}")
            return result

        # Load or create metadata
        metadata = ProjectMetadata.load(self.kittify_dir)
        if metadata is None:
            metadata = self._create_initial_metadata(from_version)

        # Normalize legacy migration IDs before checking has_migration()
        if not dry_run:
            norm_changes = metadata.normalize_and_save_legacy_ids(self.kittify_dir)
            result.warnings.extend(norm_changes)

        # Apply each migration to main project
        for migration in migrations:
            migration_result, status = self._apply_migration(migration, metadata, dry_run)
            result.warnings.extend(migration_result.warnings)
            # Preserve each migration's structured payload so the CLI --json
            # layer can surface schema-shaped reports (Finding 2 / review
            # cycle 1). We record applied and skipped results alike so
            # operators can see both no-op and refresh payloads.
            if status in ("applied", "skipped"):
                result.migration_results[migration.migration_id] = migration_result

            if status == "applied":
                result.migrations_applied.append(migration.migration_id)
            elif status == "skipped":
                result.migrations_skipped.append(migration.migration_id)
            else:
                result.success = False
                result.errors.extend(migration_result.errors)
                # Still record the failed payload for observability.
                result.migration_results[migration.migration_id] = migration_result
                # Stop on first failure
                break

        # Update and save metadata for main project
        if not dry_run and result.success:
            metadata.version = target_version
            metadata.last_upgraded_at = datetime.now()
            metadata.save(self.kittify_dir)
            # Why: MUST run after metadata.save(). ProjectMetadata.save() reconstructs
            # the YAML from a fixed three-key dict and does not preserve unknown keys,
            # so stamping schema_version before save() would silently clobber it.
            # See FR-002 / #705.
            if REQUIRED_SCHEMA_VERSION is not None:
                self._stamp_schema_version(self.kittify_dir, REQUIRED_SCHEMA_VERSION)

        # Handle worktrees
        if include_worktrees:
            worktrees_result = self._upgrade_worktrees(target_version, migrations, dry_run)
            result.warnings.extend(worktrees_result.get("warnings", []))
            if worktrees_result.get("errors"):
                result.errors.extend(worktrees_result["errors"])
                # Don't fail the whole upgrade for worktree issues
                result.warnings.append("Some worktrees had issues - check errors above")

        return result

    def _apply_migration(
        self,
        migration: BaseMigration,
        metadata: ProjectMetadata,
        dry_run: bool,
    ) -> tuple[MigrationResult, str]:
        """Apply a single migration.

        Args:
            migration: The migration to apply
            metadata: Project metadata
            dry_run: Whether to simulate only

        Returns:
            Tuple of (MigrationResult, status) where status is one of
            ``applied``, ``skipped``, or ``failed``.
        """
        # Skip if already applied
        if metadata.has_migration(migration.migration_id):
            return (
                MigrationResult(
                    success=True,
                    warnings=[f"Migration {migration.migration_id} already applied, skipping"],
                ),
                "skipped",
            )

        # Check if migration is needed via detection
        if not migration.detect(self.project_path):
            # Migration not needed - project doesn't have old state
            if not dry_run:
                self._record_migration_result(
                    metadata,
                    self.kittify_dir,
                    migration.migration_id,
                    "skipped",
                    "Not applicable",
                )
            return (MigrationResult(
                success=True,
                warnings=[f"Migration {migration.migration_id} not needed (project already in target state)"],),
                "skipped",
            )

        # Check if safe to apply
        can_apply, reason = migration.can_apply(self.project_path)
        if not can_apply:
            return (
                MigrationResult(
                    success=False,
                    errors=[f"Cannot apply {migration.migration_id}: {reason}"],
                ),
                "failed",
            )

        # Apply the migration
        result = migration.apply(self.project_path, dry_run=dry_run)

        # Record in metadata
        if not dry_run:
            self._record_migration_result(
                metadata,
                self.kittify_dir,
                migration.migration_id,
                "success" if result.success else "failed",
                "; ".join(result.changes_made) if result.changes_made else None,
            )

        return result, ("applied" if result.success else "failed")

    def _upgrade_worktrees(
        self,
        target_version: str,
        migrations: list[BaseMigration],
        dry_run: bool,
    ) -> dict[str, Any]:
        """Upgrade all worktrees in .worktrees/ directory.

        Args:
            target_version: Target version
            migrations: List of migrations to apply
            dry_run: Whether to simulate only

        Returns:
            Dict with warnings and errors lists
        """
        result: dict[str, Any] = {"warnings": [], "errors": []}
        worktree_migrations = [migration for migration in migrations if migration.runs_on_worktrees]

        if not worktree_migrations:
            return result

        worktrees_dir = self.project_path / WORKTREES_DIR
        if not worktrees_dir.exists():
            return result

        # Use deterministic ordering so migrations and logs are reproducible.
        for worktree in sorted(worktrees_dir.iterdir(), key=lambda p: p.name):
            if not worktree.is_dir():
                continue

            wt_kittify = worktree / KITTIFY_DIR
            has_upgradeable_state = wt_kittify.exists() or (worktree / "kitty-specs").exists() or (worktree / ".specify").exists()
            if not has_upgradeable_state:
                continue

            # Load or create worktree metadata
            wt_metadata = ProjectMetadata.load(wt_kittify)
            if wt_metadata is None:
                wt_detector = VersionDetector(worktree)
                wt_version = wt_detector.detect_version()
                wt_metadata = self._create_initial_metadata(wt_version)

            # Apply migrations to worktree
            for migration in worktree_migrations:
                if wt_metadata.has_migration(migration.migration_id):
                    continue

                if not migration.detect(worktree):
                    if not dry_run:
                        self._record_migration_result(
                            wt_metadata,
                            wt_kittify,
                            migration.migration_id,
                            "skipped",
                            "Not applicable",
                        )
                    continue

                can_apply, reason = migration.can_apply(worktree)
                if not can_apply:
                    result["warnings"].append(
                        f"Worktree {worktree.name}: Cannot apply {migration.migration_id}: {reason}"
                    )
                    continue

                migration_result = migration.apply(worktree, dry_run=dry_run)

                if migration_result.success:
                    if not dry_run:
                        self._record_migration_result(
                            wt_metadata,
                            wt_kittify,
                            migration.migration_id,
                            "success",
                            "; ".join(migration_result.changes_made) if migration_result.changes_made else None,
                        )
                    result["warnings"].extend([f"Worktree {worktree.name}: {w}" for w in migration_result.warnings])
                else:
                    if not dry_run:
                        self._record_migration_result(
                            wt_metadata,
                            wt_kittify,
                            migration.migration_id,
                            "failed",
                            "; ".join(migration_result.errors) if migration_result.errors else None,
                        )
                    result["errors"].extend([f"Worktree {worktree.name}: {e}" for e in migration_result.errors])

            # Save worktree metadata only when at least one migration in this
            # upgrade target is allowed to touch worktrees.
            if not dry_run:
                wt_metadata.version = target_version
                wt_metadata.last_upgraded_at = datetime.now()
                wt_metadata.save(wt_kittify)

        return result

    def _create_initial_metadata(self, detected_version: str) -> ProjectMetadata:
        """Create initial metadata for a project without it.

        Args:
            detected_version: Version detected from heuristics

        Returns:
            New ProjectMetadata instance
        """
        return ProjectMetadata(
            version=detected_version,
            initialized_at=datetime.now(),
            python_version=platform.python_version(),
            platform=sys.platform,
            platform_version=platform.platform(),
        )

    def _record_migration_result(
        self,
        metadata: ProjectMetadata,
        metadata_dir: Path,
        migration_id: str,
        result: str,
        notes: str | None = None,
    ) -> None:
        """Persist each migration record immediately for crash/failure recovery."""
        metadata.record_migration(migration_id, result, notes)
        metadata.save(metadata_dir)

    @staticmethod
    def _stamp_schema_version(kittify_dir: Path, schema_version: int) -> None:
        """Write ``spec_kitty.schema_version`` into ``.kittify/metadata.yaml``.

        This is the single step that allows the gate to pass after an upgrade.
        We update the raw YAML rather than going through ProjectMetadata so that
        the stamp survives even if metadata parsing is partial.

        Args:
            kittify_dir: Path to the ``.kittify/`` directory.
            schema_version: The new schema version integer to stamp.
        """
        import io

        import yaml

        from specify_cli.core.atomic import atomic_write

        metadata_path = kittify_dir / "metadata.yaml"
        if not metadata_path.exists():
            # Why: every spec-kitty project has metadata.yaml after init, so this
            # branch is unreachable in normal operation. Log instead of raising
            # so a corrupted dev environment surfaces a diagnostic. See FU-4 in
            # kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/follow-ups.md.
            logger.warning(
                "schema_version stamp skipped: %s does not exist", metadata_path
            )
            return

        try:
            with open(metadata_path, encoding="utf-8-sig") as fh:
                data = yaml.safe_load(fh)
        except (OSError, yaml.YAMLError) as exc:
            # Why: a parse failure here means the metadata file became corrupt
            # between the upgrade entry point and this stamp call. Surface the
            # cause so operators can repair it. See FU-4 in
            # kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/follow-ups.md.
            logger.warning(
                "schema_version stamp skipped: failed to read %s (%s)",
                metadata_path,
                exc,
            )
            return

        if not isinstance(data, dict):
            return

        if "spec_kitty" not in data or not isinstance(data["spec_kitty"], dict):
            data["spec_kitty"] = {}

        data["spec_kitty"]["schema_version"] = schema_version

        header = (
            "# Spec Kitty Project Metadata\n"
            "# Auto-generated by spec-kitty init/upgrade\n"
            "# DO NOT EDIT MANUALLY\n\n"
        )
        buf = io.StringIO()
        buf.write(header)
        yaml.dump(data, buf, default_flow_style=False, sort_keys=False)
        atomic_write(metadata_path, buf.getvalue(), mkdir=True)
