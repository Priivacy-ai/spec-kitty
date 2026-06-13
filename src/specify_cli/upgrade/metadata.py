"""Project metadata management for Spec Kitty upgrade system."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

from specify_cli.core.atomic import atomic_write

_LEGACY_MIGRATION_ID_MAP: dict[str, str] = {
    "0.10.12_constitution_cleanup": "0.10.12_charter_cleanup",
    "0.13.0_update_constitution_templates": "0.13.0_update_charter_templates",
    "2.0.0_constitution_directory": "2.0.0_charter_directory",
    "2.0.2_constitution_context_bootstrap": "2.0.2_charter_context_bootstrap",
    "2.1.2_fix_constitution_doctrine_skill": "2.1.2_fix_charter_doctrine_skill",
}


def _mask_volatile_metadata(text: str) -> str:
    """Return ``text`` with volatile metadata lines neutralized for
    compare-before-write (issue #1871).

    Two fields must not, by themselves, force a rewrite of ``metadata.yaml``:

    - ``last_upgraded_at`` — the migrations-applied upgrade path bumps it on
      every successful run, even a no-op; masking its value lets a no-op save
      compare equal and skip, keeping the on-disk timestamp stable.
    - ``schema_version`` — ``ProjectMetadata.save`` does not emit it (it is
      written separately by ``_stamp_schema_version``), so the on-disk file
      carries it while freshly-rendered content does not; dropping the line
      keeps the comparison apples-to-apples.
    """
    masked: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("schema_version:"):
            continue
        if stripped.startswith("last_upgraded_at:"):
            indent = line[: len(line) - len(stripped)]
            masked.append(f"{indent}last_upgraded_at: <masked>")
            continue
        masked.append(line)
    return "\n".join(masked)


@dataclass
class MigrationRecord:
    """Record of a single migration application."""

    id: str
    applied_at: datetime
    result: str  # "success", "skipped", "failed"
    notes: str | None = None


@dataclass
class ProjectMetadata:
    """Metadata for a Spec Kitty project stored in .kittify/metadata.yaml."""

    version: str
    initialized_at: datetime
    last_upgraded_at: datetime | None = None
    python_version: str = ""
    platform: str = ""
    platform_version: str = ""
    applied_migrations: list[MigrationRecord] = field(default_factory=list)

    @classmethod
    def load(cls, kittify_dir: Path) -> ProjectMetadata | None:
        """Load metadata from .kittify/metadata.yaml.

        Args:
            kittify_dir: Path to the .kittify directory

        Returns:
            ProjectMetadata if file exists, None otherwise
        """
        metadata_path = kittify_dir / "metadata.yaml"
        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, encoding="utf-8-sig") as f:
                data = yaml.safe_load(f)
        except (OSError, yaml.YAMLError):
            return None

        if not data:
            return None

        spec_kitty = data.get("spec_kitty", {})
        env = data.get("environment", {})
        migrations_data = data.get("migrations", {}).get("applied", [])

        applied = []
        for m in migrations_data:
            try:
                applied.append(
                    MigrationRecord(
                        id=m["id"],
                        applied_at=datetime.fromisoformat(m["applied_at"]),
                        result=m["result"],
                        notes=m.get("notes"),
                    )
                )
            except (KeyError, ValueError):
                # Skip malformed migration records
                continue

        initialized_at_str = spec_kitty.get("initialized_at")
        try:
            initialized_at = datetime.fromisoformat(initialized_at_str) if initialized_at_str else datetime.now()
        except ValueError:
            initialized_at = datetime.now()

        last_upgraded_str = spec_kitty.get("last_upgraded_at")
        try:
            last_upgraded_at = datetime.fromisoformat(last_upgraded_str) if last_upgraded_str else None
        except ValueError:
            last_upgraded_at = None

        metadata = cls(
            version=spec_kitty.get("version", "unknown"),
            initialized_at=initialized_at,
            last_upgraded_at=last_upgraded_at,
            python_version=env.get("python_version", ""),
            platform=env.get("platform", ""),
            platform_version=env.get("platform_version", ""),
            applied_migrations=applied,
        )
        # Note: legacy ID normalization is NOT performed on load.
        # It must be triggered explicitly via normalize_and_save_legacy_ids()
        # to avoid mutating files during dry-run or read-only operations.
        return metadata

    def normalize_and_save_legacy_ids(self, kittify_dir: Path) -> list[str]:
        """Normalize constitution-era migration IDs and persist if changed.

        Returns a list of change descriptions for reporting.
        Call this explicitly from the migration runner or charter-rename
        migration -- never from load().
        """
        changes: list[str] = []
        if self._normalize_legacy_ids():
            self.save(kittify_dir)
            changes.append("Normalized legacy constitution-era migration IDs to charter-era IDs")
        return changes

    def _normalize_legacy_ids(self) -> bool:
        """Rewrite constitution-era migration IDs to charter-era IDs.

        Returns True if any IDs were rewritten.
        """
        changed = False
        for record in self.applied_migrations:
            new_id = _LEGACY_MIGRATION_ID_MAP.get(record.id)
            if new_id:
                record.id = new_id
                changed = True
        return changed

    def save(self, kittify_dir: Path) -> bool:
        """Save metadata to .kittify/metadata.yaml.

        Performs a masked compare-before-write (issue #1871): if the only
        differences between the rendered content and the file already on disk
        are the volatile ``last_upgraded_at`` timestamp (which the migrations-
        applied upgrade path bumps unconditionally) and ``schema_version``
        (written separately by ``_stamp_schema_version`` and intentionally
        omitted here), the write is skipped. This stops no-op upgrades from
        churning the file/mtime or advancing ``last_upgraded_at``, and closes
        the class for every ``save()`` caller (upgrade/doctor/regeneration)
        rather than adding per-path guards.

        Args:
            kittify_dir: Path to the .kittify directory

        Returns:
            ``True`` if the file was written; ``False`` if the write was
            skipped because nothing material changed.
        """
        metadata_path = kittify_dir / "metadata.yaml"

        data = {
            "spec_kitty": {
                "version": self.version,
                "initialized_at": self.initialized_at.isoformat(),
                "last_upgraded_at": (self.last_upgraded_at.isoformat() if self.last_upgraded_at else None),
            },
            "environment": {
                "python_version": self.python_version,
                "platform": self.platform,
                "platform_version": self.platform_version,
            },
            "migrations": {
                "applied": [
                    {
                        "id": m.id,
                        "applied_at": m.applied_at.isoformat(),
                        "result": m.result,
                        "notes": m.notes,
                    }
                    for m in self.applied_migrations
                ]
            },
        }

        # Add header comment
        header = (
            "# Spec Kitty Project Metadata\n# Auto-generated by spec-kitty init/upgrade\n# DO NOT EDIT MANUALLY\n\n"
        )

        buf = io.StringIO()
        buf.write(header)
        yaml.dump(data, buf, default_flow_style=False, sort_keys=False)
        new_content = buf.getvalue()

        if metadata_path.exists():
            try:
                existing = metadata_path.read_text(encoding="utf-8-sig")
            except OSError:
                existing = None
            if existing is not None and _mask_volatile_metadata(existing) == _mask_volatile_metadata(new_content):
                return False

        atomic_write(metadata_path, new_content, mkdir=True)
        return True

    def has_migration(self, migration_id: str) -> bool:
        """Check if a migration has been successfully applied.

        Args:
            migration_id: The ID of the migration to check

        Returns:
            True if migration was applied successfully
        """
        return any(m.id == migration_id and m.result == "success" for m in self.applied_migrations)

    def record_migration(self, migration_id: str, result: str, notes: str | None = None) -> bool:
        """Record a migration application.

        Recording is idempotent: if an identical ``(migration_id, result)``
        record already exists, this is a no-op. Without this, a migration whose
        ``detect()`` is ``False`` is re-recorded as ``skipped`` / "Not
        applicable" on *every* upgrade run over the same version range, growing
        ``applied_migrations`` without bound and churning timestamps (issue
        #1872). A genuine result transition (e.g. a previously ``failed``
        migration that now succeeds) carries a different ``result`` and is
        still appended.

        Args:
            migration_id: The ID of the migration
            result: The result ("success", "skipped", "failed")
            notes: Optional notes about the migration

        Returns:
            ``True`` if a new record was appended; ``False`` if an identical
            record already existed and the call was a no-op.
        """
        if any(
            m.id == migration_id and m.result == result
            for m in self.applied_migrations
        ):
            return False
        self.applied_migrations.append(
            MigrationRecord(
                id=migration_id,
                applied_at=datetime.now(),
                result=result,
                notes=notes,
            )
        )
        return True
