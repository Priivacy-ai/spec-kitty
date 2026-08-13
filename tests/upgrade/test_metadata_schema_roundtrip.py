"""T011 — ``ProjectMetadata`` round-trips ``spec_kitty.schema_version`` (#3334).

Root cause (see ``tests/upgrade/test_failed_upgrade_recoverable.py`` for the
end-to-end reproduction): ``ProjectMetadata.save()`` used to rebuild
``metadata.yaml`` from a fixed three-key ``spec_kitty`` dict that never
included ``schema_version`` — the field was written *only* by a separate,
success-path-gated ``_stamp_schema_version`` helper in
``specify_cli.upgrade.runner``. Any ``save()`` call that ran outside that
narrow success path (a failed-migration record, ``normalize_and_save_legacy_ids``,
``doctor``/regeneration flows, ...) silently stripped ``schema_version`` from
disk, reclassifying the project as ``LEGACY`` and blocking every non-exempt
command with no way back in.

The fix (#3334, C-008) makes ``schema_version`` an ordinary round-tripped
field: ``load()`` reads it into ``ProjectMetadata.schema_version`` and
``save()`` writes it back whenever it is not ``None``. These tests pin that
round-trip directly against ``ProjectMetadata``, independent of the
migration runner.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from kernel.clock import datetime

from specify_cli.upgrade.metadata import ProjectMetadata, _mask_volatile_metadata

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# Deliberately NOT the current REQUIRED_SCHEMA_VERSION (3): a fixture value
# equal to REQUIRED would pass even if a bug hardcoded a re-stamp to REQUIRED
# on every save() instead of genuinely round-tripping whatever was loaded.
_ARBITRARY_SCHEMA_VERSION = 2


def _write_metadata(kdir: Path, *, schema_version: int | None) -> None:
    kdir.mkdir(parents=True, exist_ok=True)
    schema_line = f"  schema_version: {schema_version}\n" if schema_version is not None else ""
    (kdir / "metadata.yaml").write_text(
        "spec_kitty:\n"
        "  version: '3.2.0'\n"
        "  initialized_at: '2026-01-01T00:00:00+00:00'\n"
        "  last_upgraded_at: '2026-01-01T00:00:00+00:00'\n"
        f"{schema_line}"
        "environment:\n"
        "  python_version: '3.12'\n"
        "  platform: linux\n"
        "  platform_version: ''\n"
        "migrations:\n"
        "  applied: []\n",
        encoding="utf-8",
    )


def test_load_populates_schema_version_field(tmp_path: Path) -> None:
    """load() reads spec_kitty.schema_version into the model (T009)."""
    kdir = tmp_path / ".kittify"
    _write_metadata(kdir, schema_version=_ARBITRARY_SCHEMA_VERSION)

    metadata = ProjectMetadata.load(kdir)

    assert metadata is not None
    assert metadata.schema_version == _ARBITRARY_SCHEMA_VERSION


def test_load_with_no_schema_version_key_yields_none(tmp_path: Path) -> None:
    """A genuinely pre-3.x file (no schema_version key) loads as None (stays LEGACY)."""
    kdir = tmp_path / ".kittify"
    _write_metadata(kdir, schema_version=None)

    metadata = ProjectMetadata.load(kdir)

    assert metadata is not None
    assert metadata.schema_version is None


def test_save_after_material_change_preserves_schema_version(tmp_path: Path) -> None:
    """save() after an unrelated material change does not drop schema_version.

    This is the exact shape of the #3334 bug: load metadata, mutate something
    that has nothing to do with schema_version (here: append a migration
    record, mirroring ``_record_migration_result``), and save. Before the
    fix, ``schema_version`` vanished from disk on this save because
    ``save()`` never emitted it.
    """
    kdir = tmp_path / ".kittify"
    _write_metadata(kdir, schema_version=_ARBITRARY_SCHEMA_VERSION)

    metadata = ProjectMetadata.load(kdir)
    assert metadata is not None

    # A material, schema_version-unrelated change: append a migration record.
    recorded = metadata.record_migration("some_unrelated_migration", "failed", "boom")
    assert recorded is True

    wrote = metadata.save(kdir)
    assert wrote is True, "a new migration record is material and must force a write"

    on_disk = yaml.safe_load((kdir / "metadata.yaml").read_text(encoding="utf-8"))
    assert on_disk["spec_kitty"]["schema_version"] == _ARBITRARY_SCHEMA_VERSION, (
        "schema_version must survive a save() triggered by an unrelated metadata change"
    )

    # Re-loading confirms the round-trip is stable across repeated cycles.
    reloaded = ProjectMetadata.load(kdir)
    assert reloaded is not None
    assert reloaded.schema_version == _ARBITRARY_SCHEMA_VERSION


def test_save_with_schema_version_none_writes_no_key(tmp_path: Path) -> None:
    """A genuinely unmigrated project (schema_version=None) must keep writing
    no key at all -- otherwise every save() would forge a schema stamp for a
    project that was never actually migrated (a *worse* bug than #3334:
    fabricating COMPATIBLE status for a truly pre-3.x project)."""
    kdir = tmp_path / ".kittify"
    _write_metadata(kdir, schema_version=None)

    metadata = ProjectMetadata.load(kdir)
    assert metadata is not None
    assert metadata.schema_version is None

    metadata.version = "3.2.1"  # force a material change
    metadata.save(kdir)

    on_disk = yaml.safe_load((kdir / "metadata.yaml").read_text(encoding="utf-8"))
    assert "schema_version" not in on_disk["spec_kitty"]


def test_mask_volatile_metadata_does_not_mask_schema_version_line() -> None:
    """The compare-before-write mask must no longer neutralize schema_version
    lines: a real schema_version change has to be visible to the
    masked-equality check so the write is not incorrectly skipped."""
    before = (
        "spec_kitty:\n"
        "  version: '3.2.0'\n"
        "  last_upgraded_at: '2026-01-01T00:00:00+00:00'\n"
        "  schema_version: 2\n"
    )
    after = (
        "spec_kitty:\n"
        "  version: '3.2.0'\n"
        "  last_upgraded_at: '2026-01-02T00:00:00+00:00'\n"  # volatile: masked
        "  schema_version: 3\n"  # material: must NOT be masked away
    )

    assert _mask_volatile_metadata(before) != _mask_volatile_metadata(after), (
        "a legitimate schema_version change must not be masked into equality"
    )


def test_mask_volatile_metadata_still_masks_last_upgraded_at() -> None:
    """last_upgraded_at remains volatile/masked (issue #1871 behaviour intact)."""
    before = (
        "spec_kitty:\n"
        "  version: '3.2.0'\n"
        "  last_upgraded_at: '2026-01-01T00:00:00+00:00'\n"
        "  schema_version: 3\n"
    )
    after = (
        "spec_kitty:\n"
        "  version: '3.2.0'\n"
        "  last_upgraded_at: '2026-06-13T12:00:00+00:00'\n"
        "  schema_version: 3\n"
    )

    assert _mask_volatile_metadata(before) == _mask_volatile_metadata(after), (
        "last_upgraded_at alone must still compare equal (no-op upgrades stay silent)"
    )


def test_compare_before_write_skips_when_only_timestamp_differs(tmp_path: Path) -> None:
    """End-to-end save(): schema_version present and unchanged, only the
    volatile timestamp differs -> write is skipped (issue #1871 preserved)."""
    kdir = tmp_path / ".kittify"
    metadata = ProjectMetadata(
        version="3.2.0",
        initialized_at=datetime(2026, 1, 1, 0, 0, 0),
        schema_version=_ARBITRARY_SCHEMA_VERSION,
    )
    assert metadata.save(kdir) is True  # first write
    path = kdir / "metadata.yaml"
    before = path.read_bytes()

    metadata.last_upgraded_at = datetime(2026, 6, 13, 12, 0, 0)
    assert metadata.save(kdir) is False, "a volatile-only timestamp change must not force a write"
    assert path.read_bytes() == before

    # A material schema_version change IS written.
    metadata.schema_version = _ARBITRARY_SCHEMA_VERSION + 1
    assert metadata.save(kdir) is True
    assert path.read_bytes() != before
