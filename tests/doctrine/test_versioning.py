"""Tests for doctrine.versioning — compatibility registry and bundle schema version."""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.versioning import (
    CURRENT_BUNDLE_SCHEMA_VERSION,
    MAX_READABLE_BUNDLE_SCHEMA,
    MIN_READABLE_BUNDLE_SCHEMA,
    BundleCompatibilityResult,
    BundleCompatibilityStatus,
    MigrationResult,
    check_bundle_compatibility,
    get_bundle_schema_version,
    repair_v2_synthesis_manifest_defaults,
    run_migration,
)

pytestmark = pytest.mark.fast


def _write_v1_bundle(bundle_root: Path) -> Path:
    provenance_dir = bundle_root / "provenance"
    provenance_dir.mkdir(parents=True, exist_ok=True)
    (bundle_root / "metadata.yaml").write_text(
        "timestamp_utc: 2026-01-01T00:00:00Z\n",
        encoding="utf-8",
    )
    (provenance_dir / "directive-use-prs.yaml").write_text(
        "\n".join(
            [
                "schema_version: '1'",
                "artifact_urn: drg:directive:directive-use-prs",
                "artifact_kind: directive",
                "artifact_slug: directive-use-prs",
                f"artifact_content_hash: {'a' * 64}",
                f"inputs_hash: {'b' * 64}",
                "adapter_id: fixture",
                "adapter_version: 1.0.0",
                "generated_at: '2026-01-01T00:00:00Z'",
                "source_section: review_policy",
                "source_urns:",
                "  - drg:directive:DIR-001",
                "corpus_snapshot_id: null",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (bundle_root / "synthesis-manifest.yaml").write_text(
        "\n".join(
            [
                "schema_version: '1'",
                "created_at: '2026-01-01T00:00:00Z'",
                "run_id: '01TEST000000000000000000001'",
                "adapter_id: fixture",
                "adapter_version: 1.0.0",
                "artifacts: []",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return provenance_dir / "directive-use-prs.yaml"


# ---------------------------------------------------------------------------
# Constants sanity check
# ---------------------------------------------------------------------------


def test_constants_have_expected_values() -> None:
    assert CURRENT_BUNDLE_SCHEMA_VERSION == 2
    assert MIN_READABLE_BUNDLE_SCHEMA == 1
    assert MAX_READABLE_BUNDLE_SCHEMA == 2


# ---------------------------------------------------------------------------
# check_bundle_compatibility — status and exit_code
# ---------------------------------------------------------------------------


def test_compatible_current_version() -> None:
    result = check_bundle_compatibility(2)
    assert result.status == BundleCompatibilityStatus.COMPATIBLE
    assert result.exit_code == 0
    assert result.bundle_version == 2


def test_needs_migration_v1() -> None:
    result = check_bundle_compatibility(1)
    assert result.status == BundleCompatibilityStatus.NEEDS_MIGRATION
    assert result.exit_code == 1
    assert result.bundle_version == 1


def test_missing_version() -> None:
    result = check_bundle_compatibility(None)
    assert result.status == BundleCompatibilityStatus.MISSING_VERSION
    assert result.exit_code == 1
    assert result.bundle_version is None


def test_incompatible_new() -> None:
    result = check_bundle_compatibility(99)
    assert result.status == BundleCompatibilityStatus.INCOMPATIBLE_NEW
    assert result.exit_code == 1
    assert result.bundle_version == 99


def test_incompatible_old_zero() -> None:
    result = check_bundle_compatibility(0)
    assert result.status == BundleCompatibilityStatus.INCOMPATIBLE_OLD
    assert result.exit_code == 1
    assert result.bundle_version == 0


def test_incompatible_old_negative() -> None:
    result = check_bundle_compatibility(-1)
    assert result.status == BundleCompatibilityStatus.INCOMPATIBLE_OLD
    assert result.exit_code == 1
    assert result.bundle_version == -1


# ---------------------------------------------------------------------------
# check_bundle_compatibility — message content
# ---------------------------------------------------------------------------


def test_compatible_message_contains_version() -> None:
    result = check_bundle_compatibility(2)
    assert "2" in result.message
    assert "supported" in result.message.lower()


def test_needs_migration_message_contains_spec_kitty_upgrade() -> None:
    result = check_bundle_compatibility(1)
    assert "spec-kitty upgrade" in result.message


def test_missing_version_message_contains_spec_kitty_upgrade() -> None:
    result = check_bundle_compatibility(None)
    assert "spec-kitty upgrade" in result.message


def test_incompatible_old_message_contains_contact_support() -> None:
    result = check_bundle_compatibility(0)
    assert "contact support" in result.message.lower()
    assert str(MIN_READABLE_BUNDLE_SCHEMA) in result.message


def test_incompatible_new_message_contains_upgrade_cli() -> None:
    result = check_bundle_compatibility(99)
    assert "upgrade your cli" in result.message.lower()
    assert str(MAX_READABLE_BUNDLE_SCHEMA) in result.message


# ---------------------------------------------------------------------------
# check_bundle_compatibility — supported_min/max fields
# ---------------------------------------------------------------------------


def test_result_carries_supported_range() -> None:
    result = check_bundle_compatibility(2)
    assert result.supported_min == MIN_READABLE_BUNDLE_SCHEMA
    assert result.supported_max == MAX_READABLE_BUNDLE_SCHEMA


# ---------------------------------------------------------------------------
# BundleCompatibilityResult.is_compatible property
# ---------------------------------------------------------------------------


def test_is_compatible_property_true_for_compatible() -> None:
    result = check_bundle_compatibility(CURRENT_BUNDLE_SCHEMA_VERSION)
    assert result.is_compatible is True


def test_is_compatible_property_false_for_needs_migration() -> None:
    assert check_bundle_compatibility(1).is_compatible is False


def test_is_compatible_property_false_for_missing_version() -> None:
    assert check_bundle_compatibility(None).is_compatible is False


def test_is_compatible_property_false_for_incompatible_old() -> None:
    assert check_bundle_compatibility(0).is_compatible is False


def test_is_compatible_property_false_for_incompatible_new() -> None:
    assert check_bundle_compatibility(99).is_compatible is False


# ---------------------------------------------------------------------------
# BundleCompatibilityResult.needs_migration property
# ---------------------------------------------------------------------------


def test_needs_migration_property_true_for_needs_migration() -> None:
    assert check_bundle_compatibility(1).needs_migration is True


def test_needs_migration_property_true_for_missing_version() -> None:
    assert check_bundle_compatibility(None).needs_migration is True


def test_needs_migration_property_false_for_compatible() -> None:
    assert check_bundle_compatibility(CURRENT_BUNDLE_SCHEMA_VERSION).needs_migration is False


def test_needs_migration_property_false_for_incompatible_old() -> None:
    assert check_bundle_compatibility(0).needs_migration is False


def test_needs_migration_property_false_for_incompatible_new() -> None:
    assert check_bundle_compatibility(99).needs_migration is False


# ---------------------------------------------------------------------------
# BundleCompatibilityResult is frozen (immutable)
# ---------------------------------------------------------------------------


def test_result_is_frozen() -> None:
    result = check_bundle_compatibility(2)
    with pytest.raises((AttributeError, TypeError)):
        result.exit_code = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# get_bundle_schema_version
#
# consolidate-charter-bundle (WP07 / T030): the read target moved from
# ``<charter_dir>/metadata.yaml`` (top-level ``bundle_schema_version`` key,
# now RETIRED) to ``<charter_dir>/charter.yaml``'s ``metadata:`` section
# (``charter.schemas.CharterYamlMetadata`` keeps this one field across the
# Landmine 2 retirement). Fixtures below write ``charter.yaml`` with the
# field nested under ``metadata:`` instead of ``metadata.yaml`` flat.
# ---------------------------------------------------------------------------


def test_returns_none_when_file_absent(tmp_path: Path) -> None:
    result = get_bundle_schema_version(tmp_path)
    assert result is None


def test_returns_none_when_field_absent(tmp_path: Path) -> None:
    charter_yaml = tmp_path / "charter.yaml"
    charter_yaml.write_text("metadata:\n  generated_at: '2026-01-01'\n")
    assert get_bundle_schema_version(tmp_path) is None


def test_returns_none_when_metadata_section_absent(tmp_path: Path) -> None:
    charter_yaml = tmp_path / "charter.yaml"
    charter_yaml.write_text("schema_version: '2.0.0'\n")
    assert get_bundle_schema_version(tmp_path) is None


def test_returns_int_when_present(tmp_path: Path) -> None:
    charter_yaml = tmp_path / "charter.yaml"
    charter_yaml.write_text("metadata:\n  bundle_schema_version: 2\n")
    result = get_bundle_schema_version(tmp_path)
    assert result == 2
    assert isinstance(result, int)


def test_returns_none_when_field_is_null(tmp_path: Path) -> None:
    charter_yaml = tmp_path / "charter.yaml"
    charter_yaml.write_text("metadata:\n  bundle_schema_version: null\n")
    assert get_bundle_schema_version(tmp_path) is None


def test_returns_none_when_field_is_string(tmp_path: Path) -> None:
    """String values (e.g. '2') should not be accepted — must be int."""
    charter_yaml = tmp_path / "charter.yaml"
    charter_yaml.write_text("metadata:\n  bundle_schema_version: '2'\n")
    assert get_bundle_schema_version(tmp_path) is None


def test_returns_none_when_file_is_not_a_mapping(tmp_path: Path) -> None:
    charter_yaml = tmp_path / "charter.yaml"
    charter_yaml.write_text("- item1\n- item2\n")
    assert get_bundle_schema_version(tmp_path) is None


def test_returns_correct_version_for_v1(tmp_path: Path) -> None:
    charter_yaml = tmp_path / "charter.yaml"
    charter_yaml.write_text("metadata:\n  bundle_schema_version: 1\n")
    assert get_bundle_schema_version(tmp_path) == 1


def test_ruamel_yaml_roundtrip_writes_integer(tmp_path: Path) -> None:
    """Verify ruamel.yaml serializes bundle_schema_version as an integer, not string."""
    from ruamel.yaml import YAML

    charter_yaml_path = tmp_path / "charter.yaml"
    yaml = YAML()
    yaml.dump({"metadata": {"bundle_schema_version": 2}, "other": "data"}, charter_yaml_path)

    # Read back and confirm type is int
    result = get_bundle_schema_version(tmp_path)
    assert result == 2
    assert isinstance(result, int)


# ---------------------------------------------------------------------------
# run_migration — error path
# ---------------------------------------------------------------------------


def test_run_migration_raises_key_error_for_unregistered_version(tmp_path: Path) -> None:
    with pytest.raises(KeyError, match="99"):
        run_migration(99, tmp_path)


def test_run_migration_v1_returns_migration_result(tmp_path: Path) -> None:
    """The v1 migration (WP03 implementation) returns a MigrationResult; does not raise."""
    # A metadata.yaml without bundle_schema_version is treated as v1 and gets stamped.
    (tmp_path / "metadata.yaml").write_text(
        "charter_slug: test-charter\n", encoding="utf-8"
    )
    # consolidate-charter-bundle (WP07 / T030): step 3 now stamps
    # charter.yaml's metadata section, not the retired metadata.yaml.
    (tmp_path / "charter.yaml").write_text(
        "schema_version: '2.0.0'\n", encoding="utf-8"
    )
    result = run_migration(1, tmp_path)
    assert isinstance(result, MigrationResult)
    assert result.from_version == 1
    assert result.to_version == 2
    assert result.errors == []
    assert any("charter.yaml" in change for change in result.changes_made)


def test_run_migration_v1_backfills_manifest_and_sidecar_fields(tmp_path: Path) -> None:
    from charter.synthesizer.manifest import load_yaml, verify_manifest_hash

    _write_v1_bundle(tmp_path)

    result = run_migration(1, tmp_path)

    assert result.errors == []
    manifest_path = tmp_path / "synthesis-manifest.yaml"
    manifest = manifest_path.read_text(encoding="utf-8")
    sidecar = (tmp_path / "provenance" / "directive-use-prs.yaml").read_text(
        encoding="utf-8"
    )
    assert "synthesizer_version: (pre-phase7-migration)" in manifest
    assert "mission_id:" in manifest
    assert "built_in_only: false" in manifest
    verify_manifest_hash(load_yaml(manifest_path))
    assert "synthesizer_version: (pre-phase7-migration)" in sidecar
    assert "synthesis_run_id: (pre-phase7-migration)" in sidecar
    assert "source_input_ids:" in sidecar


def test_run_migration_v1_uses_sentinel_when_sidecar_stat_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_sidecar = _write_v1_bundle(tmp_path)
    original_stat = Path.stat

    def _patched_stat(path: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
        if path == target_sidecar:
            raise OSError("stat blocked for test")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", _patched_stat)

    result = run_migration(1, tmp_path)

    assert result.errors == []
    sidecar = (tmp_path / "provenance" / "directive-use-prs.yaml").read_text(
        encoding="utf-8"
    )
    assert "produced_at: (pre-phase7-migration)" in sidecar


def _write_legacy_v2_manifest(
    bundle_root: Path,
    *,
    stored_hash: str | None = None,
) -> Path:
    import hashlib

    from doctrine.yaml_utils import canonical_yaml
    from ruamel.yaml import YAML

    manifest_data = {
        "schema_version": "2",
        "mission_id": None,
        "created_at": "2026-01-01T00:00:00Z",
        "run_id": "01TEST000000000000000000001",
        "adapter_id": "fixture",
        "adapter_version": "1.0.0",
        "synthesizer_version": "3.2.6",
        "artifacts": [],
    }
    manifest_data["manifest_hash"] = stored_hash or hashlib.sha256(  # noqa: TID251 — legacy v2 manifest self-hash fixture
        canonical_yaml(manifest_data)
    ).hexdigest()

    manifest_path = bundle_root / "synthesis-manifest.yaml"
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.explicit_start = False
    yaml.dump(manifest_data, manifest_path)
    return manifest_path


def test_repair_v2_manifest_no_manifest_is_noop(tmp_path: Path) -> None:
    result = repair_v2_synthesis_manifest_defaults(tmp_path)

    assert result.changes_made == []
    assert result.errors == []


def test_repair_v2_manifest_load_error_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import doctrine.versioning as versioning

    (tmp_path / "synthesis-manifest.yaml").write_text("schema_version: '2'\n")

    class BrokenYaml:
        default_flow_style = False
        explicit_start = False

        def load(self, _text: str) -> dict:
            raise RuntimeError("boom")

    monkeypatch.setattr(versioning, "YAML", BrokenYaml)

    result = repair_v2_synthesis_manifest_defaults(tmp_path)

    assert result.changes_made == []
    assert result.errors == ["Failed to load synthesis-manifest.yaml: boom"]


def test_repair_v2_manifest_ignores_non_v2_and_already_current(tmp_path: Path) -> None:
    from ruamel.yaml import YAML

    manifest_path = tmp_path / "synthesis-manifest.yaml"
    yaml = YAML()
    yaml.dump({"schema_version": "1"}, manifest_path)
    assert repair_v2_synthesis_manifest_defaults(tmp_path).changes_made == []

    yaml.dump({"schema_version": "2", "built_in_only": False}, manifest_path)
    assert repair_v2_synthesis_manifest_defaults(tmp_path).changes_made == []


def test_repair_v2_manifest_missing_hash_is_error(tmp_path: Path) -> None:
    from ruamel.yaml import YAML

    YAML().dump({"schema_version": "2"}, tmp_path / "synthesis-manifest.yaml")

    result = repair_v2_synthesis_manifest_defaults(tmp_path)

    assert result.changes_made == []
    assert result.errors == [
        "Cannot repair synthesis-manifest.yaml: manifest_hash is missing or invalid."
    ]


def test_repair_v2_manifest_hash_mismatch_is_error(tmp_path: Path) -> None:
    _write_legacy_v2_manifest(tmp_path, stored_hash="0" * 64)

    result = repair_v2_synthesis_manifest_defaults(tmp_path)

    assert result.changes_made == []
    assert result.errors == [
        "Cannot repair synthesis-manifest.yaml: existing manifest_hash does not "
        "match the pre-built_in_only v2 payload."
    ]


def test_repair_v2_manifest_writes_canonical_default(tmp_path: Path) -> None:
    from charter.synthesizer.manifest import load_yaml, verify_manifest_hash
    from ruamel.yaml import YAML

    manifest_path = _write_legacy_v2_manifest(tmp_path)

    result = repair_v2_synthesis_manifest_defaults(tmp_path)

    assert result.changes_made == [str(manifest_path)]
    assert result.errors == []
    assert YAML().load(manifest_path)["built_in_only"] is False
    verify_manifest_hash(load_yaml(manifest_path))


def test_repair_v2_manifest_dry_run_reports_without_write(tmp_path: Path) -> None:
    from ruamel.yaml import YAML

    manifest_path = _write_legacy_v2_manifest(tmp_path)

    result = repair_v2_synthesis_manifest_defaults(tmp_path, dry_run=True)

    assert result.changes_made == [str(manifest_path)]
    assert result.errors == []
    assert "built_in_only" not in YAML().load(manifest_path)


def test_repair_v2_manifest_write_error_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _write_legacy_v2_manifest(tmp_path)
    original_write_bytes = Path.write_bytes

    def patched_write_bytes(path: Path, data: bytes) -> int:
        if path == manifest_path:
            raise OSError("disk full")
        return original_write_bytes(path, data)

    monkeypatch.setattr(Path, "write_bytes", patched_write_bytes)

    result = repair_v2_synthesis_manifest_defaults(tmp_path)

    assert result.changes_made == []
    assert result.errors == ["Failed to write synthesis-manifest.yaml: disk full"]


# ---------------------------------------------------------------------------
# MigrationResult dataclass
# ---------------------------------------------------------------------------


def test_migration_result_construction() -> None:
    result = MigrationResult(
        changes_made=["updated metadata.yaml"],
        errors=[],
        from_version=1,
        to_version=2,
    )
    assert result.from_version == 1
    assert result.to_version == 2
    assert result.changes_made == ["updated metadata.yaml"]
    assert result.errors == []


# ---------------------------------------------------------------------------
# No circular imports — doctrine.versioning must not touch charter.*
# ---------------------------------------------------------------------------


def test_versioning_does_not_import_charter() -> None:
    """doctrine.versioning must not introduce charter.* into sys.modules."""
    import sys

    # Trigger import (already loaded, but explicit)
    import doctrine.versioning  # noqa: F401

    charter_modules = [k for k in sys.modules if k.startswith("charter")]
    # If charter was imported by versioning itself that would be a violation.
    # We can't guarantee charter isn't loaded by OTHER tests, but we can
    # inspect the module's __file__ and check it doesn't directly import charter.
    import ast
    import inspect

    source = inspect.getsource(doctrine.versioning)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("charter"), (
                    f"doctrine.versioning imports from charter: {node.module}"
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("charter"), (
                        f"doctrine.versioning imports charter: {alias.name}"
                    )
