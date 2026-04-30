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
    run_migration,
)


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
# ---------------------------------------------------------------------------


def test_returns_none_when_file_absent(tmp_path: Path) -> None:
    result = get_bundle_schema_version(tmp_path)
    assert result is None


def test_returns_none_when_field_absent(tmp_path: Path) -> None:
    metadata = tmp_path / "metadata.yaml"
    metadata.write_text("schema_version: '1.0.0'\nextracted_at: '2026-01-01'\n")
    assert get_bundle_schema_version(tmp_path) is None


def test_returns_int_when_present(tmp_path: Path) -> None:
    metadata = tmp_path / "metadata.yaml"
    metadata.write_text("bundle_schema_version: 2\n")
    result = get_bundle_schema_version(tmp_path)
    assert result == 2
    assert isinstance(result, int)


def test_returns_none_when_field_is_null(tmp_path: Path) -> None:
    metadata = tmp_path / "metadata.yaml"
    metadata.write_text("bundle_schema_version: null\n")
    assert get_bundle_schema_version(tmp_path) is None


def test_returns_none_when_field_is_string(tmp_path: Path) -> None:
    """String values (e.g. '2') should not be accepted — must be int."""
    metadata = tmp_path / "metadata.yaml"
    metadata.write_text("bundle_schema_version: '2'\n")
    assert get_bundle_schema_version(tmp_path) is None


def test_returns_none_when_file_is_not_a_mapping(tmp_path: Path) -> None:
    metadata = tmp_path / "metadata.yaml"
    metadata.write_text("- item1\n- item2\n")
    assert get_bundle_schema_version(tmp_path) is None


def test_returns_correct_version_for_v1(tmp_path: Path) -> None:
    metadata = tmp_path / "metadata.yaml"
    metadata.write_text("bundle_schema_version: 1\n")
    assert get_bundle_schema_version(tmp_path) == 1


def test_ruamel_yaml_roundtrip_writes_integer(tmp_path: Path) -> None:
    """Verify ruamel.yaml serializes bundle_schema_version as an integer, not string."""
    from ruamel.yaml import YAML

    metadata_path = tmp_path / "metadata.yaml"
    yaml = YAML()
    yaml.dump({"bundle_schema_version": 2, "other": "data"}, metadata_path)

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
    result = run_migration(1, tmp_path)
    assert isinstance(result, MigrationResult)
    assert result.from_version == 1
    assert result.to_version == 2
    assert result.errors == []
    assert any("metadata.yaml" in change for change in result.changes_made)


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
