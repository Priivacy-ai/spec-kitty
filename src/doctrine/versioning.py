"""Bundle schema versioning and compatibility registry.

Provides the compatibility registry that maps bundle integer schema versions
to supported CLI version ranges. Used by charter modules to decide whether
a bundle can be read natively or needs migration.

Dependency direction: charter -> doctrine (never reversed).
This module must NOT import from charter.*.
"""

from __future__ import annotations

import dataclasses
import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from ruamel.yaml import YAML

from doctrine.yaml_utils import canonical_yaml

# --- Constants ---

CURRENT_BUNDLE_SCHEMA_VERSION: int = 2
"""The bundle schema version written by Phase 7 synthesis."""

MIN_READABLE_BUNDLE_SCHEMA: int = 1
"""Oldest bundle schema version this CLI can read (after migration)."""

MAX_READABLE_BUNDLE_SCHEMA: int = 2
"""Newest bundle schema version this CLI reads natively."""


# --- Enums ---


class BundleCompatibilityStatus(str, Enum):
    """Compatibility status of a bundle with the current CLI."""

    COMPATIBLE = "COMPATIBLE"
    NEEDS_MIGRATION = "NEEDS_MIGRATION"
    INCOMPATIBLE_OLD = "INCOMPATIBLE_OLD"
    INCOMPATIBLE_NEW = "INCOMPATIBLE_NEW"
    MISSING_VERSION = "MISSING_VERSION"


# --- Dataclasses ---


@dataclasses.dataclass(frozen=True)
class BundleCompatibilityResult:
    """Result of a bundle compatibility check."""

    status: BundleCompatibilityStatus
    bundle_version: int | None
    supported_min: int
    supported_max: int
    message: str
    exit_code: int

    @property
    def is_compatible(self) -> bool:
        """True if the bundle can be used without migration."""
        return self.status == BundleCompatibilityStatus.COMPATIBLE

    @property
    def needs_migration(self) -> bool:
        """True if the bundle needs migration before use."""
        return self.status in (
            BundleCompatibilityStatus.NEEDS_MIGRATION,
            BundleCompatibilityStatus.MISSING_VERSION,
        )


@dataclasses.dataclass
class MigrationResult:
    """Result of running a migration on a bundle."""

    changes_made: list[str]
    errors: list[str]
    from_version: int
    to_version: int


# --- Core functions ---


def check_bundle_compatibility(bundle_version: int | None) -> BundleCompatibilityResult:
    """Check whether a bundle schema version is compatible with this CLI.

    Pure function — no filesystem I/O.

    Args:
        bundle_version: Integer schema version read from bundle metadata,
            or None if the field was absent.

    Returns:
        BundleCompatibilityResult describing status and remediation action.
    """
    if bundle_version is None:
        return BundleCompatibilityResult(
            status=BundleCompatibilityStatus.MISSING_VERSION,
            bundle_version=None,
            supported_min=MIN_READABLE_BUNDLE_SCHEMA,
            supported_max=MAX_READABLE_BUNDLE_SCHEMA,
            message=(
                "Bundle schema version not found; treating as v1. "
                "Run `spec-kitty upgrade`."
            ),
            exit_code=1,
        )

    if bundle_version == CURRENT_BUNDLE_SCHEMA_VERSION:
        return BundleCompatibilityResult(
            status=BundleCompatibilityStatus.COMPATIBLE,
            bundle_version=bundle_version,
            supported_min=MIN_READABLE_BUNDLE_SCHEMA,
            supported_max=MAX_READABLE_BUNDLE_SCHEMA,
            message=f"Bundle schema version {bundle_version} is supported.",
            exit_code=0,
        )

    if MIN_READABLE_BUNDLE_SCHEMA <= bundle_version < CURRENT_BUNDLE_SCHEMA_VERSION:
        return BundleCompatibilityResult(
            status=BundleCompatibilityStatus.NEEDS_MIGRATION,
            bundle_version=bundle_version,
            supported_min=MIN_READABLE_BUNDLE_SCHEMA,
            supported_max=MAX_READABLE_BUNDLE_SCHEMA,
            message=(
                f"Bundle schema version {bundle_version} requires migration. "
                "Run `spec-kitty upgrade`."
            ),
            exit_code=1,
        )

    if bundle_version < MIN_READABLE_BUNDLE_SCHEMA:
        return BundleCompatibilityResult(
            status=BundleCompatibilityStatus.INCOMPATIBLE_OLD,
            bundle_version=bundle_version,
            supported_min=MIN_READABLE_BUNDLE_SCHEMA,
            supported_max=MAX_READABLE_BUNDLE_SCHEMA,
            message=(
                f"Bundle schema version {bundle_version} predates the earliest "
                f"supported version ({MIN_READABLE_BUNDLE_SCHEMA}). Contact support."
            ),
            exit_code=1,
        )

    # bundle_version > MAX_READABLE_BUNDLE_SCHEMA
    return BundleCompatibilityResult(
        status=BundleCompatibilityStatus.INCOMPATIBLE_NEW,
        bundle_version=bundle_version,
        supported_min=MIN_READABLE_BUNDLE_SCHEMA,
        supported_max=MAX_READABLE_BUNDLE_SCHEMA,
        message=(
            f"Bundle schema version {bundle_version} is newer than this CLI "
            f"supports ({MAX_READABLE_BUNDLE_SCHEMA}). Upgrade your CLI."
        ),
        exit_code=1,
    )


def get_bundle_schema_version(charter_dir: Path) -> int | None:
    """Read the bundle_schema_version integer from <charter_dir>/metadata.yaml.

    Args:
        charter_dir: Path to the charter bundle directory containing metadata.yaml.

    Returns:
        Integer schema version, or None if the file is absent, the key is absent,
        the value is null, or the value is not an integer.
        Never raises.
    """
    metadata_path = charter_dir / "metadata.yaml"
    if not metadata_path.exists():
        return None
    yaml = YAML()
    data = yaml.load(metadata_path)
    if not isinstance(data, dict):
        return None
    value = data.get("bundle_schema_version")
    if not isinstance(value, int):
        return None
    return value


# --- Migration registry ---

# Maps from_version → migration_function
_MIGRATIONS: dict[int, Callable[[Path, bool], MigrationResult]] = {}
PRE_PHASE7_MIGRATION_SENTINEL = "(pre-phase7-migration)"


def _register_migration(
    from_version: int,
    fn: Callable[[Path, bool], MigrationResult],
) -> None:
    """Register a migration function for a given from-version.

    Args:
        from_version: The bundle schema version this migration upgrades from.
        fn: Callable accepting (bundle_root, dry_run) and returning MigrationResult.
    """
    _MIGRATIONS[from_version] = fn


def migrate_v1_to_v2(bundle_root: Path, dry_run: bool = False) -> MigrationResult:
    """Migrate a v1 charter bundle to v2 format (Phase 7 provenance hardening).

    Adds the mandatory Phase 7 fields to provenance sidecars and the
    synthesis manifest, and stamps ``bundle_schema_version: 2`` in
    ``metadata.yaml``.

    Sentinel values are used for fields that cannot be reconstructed from
    the v1 state:
    - ``synthesizer_version: "(pre-phase7-migration)"``
    - ``synthesis_run_id: "(pre-phase7-migration)"``
    - ``produced_at: <file mtime in ISO 8601 UTC>`` (or sentinel on OSError)
    - ``source_input_ids: <copy of existing source_urns>``
    - ``corpus_snapshot_id: "(none)"`` (only when the existing value is null)

    Args:
        bundle_root: Path to the ``.kittify/charter/`` directory.
        dry_run: If True, compute and report changes without writing any files.

    Returns:
        MigrationResult with ``changes_made`` listing every file that was (or
        would be) updated.  ``errors`` is empty on success.
    """
    _yaml = YAML()
    _yaml.default_flow_style = False
    _yaml.explicit_start = False

    changes_made: list[str] = []
    errors: list[str] = []

    # -------------------------------------------------------------------------
    # 1. Migrate provenance sidecars
    # -------------------------------------------------------------------------
    provenance_dir = bundle_root / "provenance"
    if provenance_dir.exists():
        for sidecar_path in sorted(provenance_dir.glob("*.yaml")):
            try:
                data = _yaml.load(sidecar_path)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Failed to load sidecar {sidecar_path.name}: {exc}")
                continue

            if not isinstance(data, dict):
                errors.append(
                    f"Sidecar {sidecar_path.name} is not a YAML mapping; skipping."
                )
                continue

            if data.get("schema_version") == "2":
                continue  # Already migrated — skip (idempotent).

            # Add missing v2 fields using sentinel values where needed.
            data.setdefault("synthesizer_version", PRE_PHASE7_MIGRATION_SENTINEL)
            data.setdefault("synthesis_run_id", PRE_PHASE7_MIGRATION_SENTINEL)

            if "produced_at" not in data:
                try:
                    mtime = sidecar_path.stat().st_mtime
                    data["produced_at"] = datetime.fromtimestamp(
                        mtime, tz=UTC
                    ).isoformat()
                except OSError:
                    data["produced_at"] = PRE_PHASE7_MIGRATION_SENTINEL

            if "source_input_ids" not in data:
                data["source_input_ids"] = list(data.get("source_urns", []))

            if data.get("corpus_snapshot_id") is None:
                data["corpus_snapshot_id"] = "(none)"

            data["schema_version"] = "2"

            changes_made.append(str(sidecar_path))
            if not dry_run:
                try:
                    import io as _io

                    buf = _io.BytesIO()
                    _yaml.dump(data, buf)
                    sidecar_path.write_bytes(buf.getvalue())
                except Exception as exc:  # noqa: BLE001
                    errors.append(
                        f"Failed to write sidecar {sidecar_path.name}: {exc}"
                    )

    # -------------------------------------------------------------------------
    # 2. Migrate synthesis-manifest.yaml
    # -------------------------------------------------------------------------
    manifest_path = bundle_root / "synthesis-manifest.yaml"
    if manifest_path.exists():
        try:
            manifest_data = _yaml.load(manifest_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Failed to load synthesis-manifest.yaml: {exc}")
            manifest_data = None

        if isinstance(manifest_data, dict) and manifest_data.get("schema_version") != "2":
            manifest_data.setdefault("synthesizer_version", PRE_PHASE7_MIGRATION_SENTINEL)

            # Compute manifest_hash over all fields except manifest_hash itself.
            fields_for_hash = {
                k: v for k, v in manifest_data.items() if k != "manifest_hash"
            }
            # Set schema_version to "2" in the hash-input fields too, so the
            # hash covers the post-migration state.
            fields_for_hash["schema_version"] = "2"
            manifest_hash = hashlib.sha256(canonical_yaml(fields_for_hash)).hexdigest()

            manifest_data["schema_version"] = "2"
            manifest_data["manifest_hash"] = manifest_hash

            changes_made.append(str(manifest_path))
            if not dry_run:
                try:
                    import io as _io

                    buf = _io.BytesIO()
                    _yaml.dump(manifest_data, buf)
                    manifest_path.write_bytes(buf.getvalue())
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"Failed to write synthesis-manifest.yaml: {exc}")

    # -------------------------------------------------------------------------
    # 3. Update metadata.yaml — stamp bundle_schema_version: 2
    # -------------------------------------------------------------------------
    metadata_path = bundle_root / "metadata.yaml"
    if metadata_path.exists():
        try:
            metadata = _yaml.load(metadata_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Failed to load metadata.yaml: {exc}")
            metadata = None

        if isinstance(metadata, dict) and metadata.get("bundle_schema_version") != 2:
            metadata["bundle_schema_version"] = 2

            changes_made.append(str(metadata_path))
            if not dry_run:
                try:
                    import io as _io

                    buf = _io.BytesIO()
                    _yaml.dump(metadata, buf)
                    metadata_path.write_bytes(buf.getvalue())
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"Failed to write metadata.yaml: {exc}")

    return MigrationResult(
        changes_made=changes_made,
        errors=errors,
        from_version=1,
        to_version=2,
    )


_register_migration(1, migrate_v1_to_v2)


def run_migration(
    from_version: int, bundle_root: Path, dry_run: bool = False
) -> MigrationResult:
    """Run the registered migration for the given from-version.

    Args:
        from_version: The bundle schema version to migrate from.
        bundle_root: Path to the bundle root directory.
        dry_run: If True, report changes without applying them.

    Returns:
        MigrationResult describing what was changed.

    Raises:
        KeyError: If no migration is registered for from_version.
    """
    if from_version not in _MIGRATIONS:
        raise KeyError(f"No migration registered for bundle version {from_version}")
    fn = _MIGRATIONS[from_version]
    return fn(bundle_root, dry_run)


__all__ = [
    "CURRENT_BUNDLE_SCHEMA_VERSION",
    "MIN_READABLE_BUNDLE_SCHEMA",
    "MAX_READABLE_BUNDLE_SCHEMA",
    "BundleCompatibilityStatus",
    "BundleCompatibilityResult",
    "MigrationResult",
    "check_bundle_compatibility",
    "get_bundle_schema_version",
    "migrate_v1_to_v2",
    "run_migration",
]
