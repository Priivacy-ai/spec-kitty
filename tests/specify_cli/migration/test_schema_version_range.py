"""Tests for WP07 schema range activation — T029.

Covers:
- MIN_SUPPORTED_SCHEMA <= MAX_SUPPORTED_SCHEMA invariant.
- REQUIRED_SCHEMA_VERSION == MIN_SUPPORTED_SCHEMA (deprecated alias, non-None int).
- check_compatibility range semantics: COMPATIBLE, OUTDATED, CLI_OUTDATED, UNMIGRATED.
"""

from __future__ import annotations

from specify_cli.migration.schema_version import (
    MAX_SUPPORTED_SCHEMA,
    MIN_SUPPORTED_SCHEMA,
    REQUIRED_SCHEMA_VERSION,
    CompatibilityStatus,
    check_compatibility,
)


# ---------------------------------------------------------------------------
# Range invariants
# ---------------------------------------------------------------------------


def test_min_lte_max() -> None:
    """MIN_SUPPORTED_SCHEMA must be <= MAX_SUPPORTED_SCHEMA."""
    assert MIN_SUPPORTED_SCHEMA <= MAX_SUPPORTED_SCHEMA


def test_required_schema_version_equals_min() -> None:
    """REQUIRED_SCHEMA_VERSION is a non-None int equal to MIN_SUPPORTED_SCHEMA."""
    assert REQUIRED_SCHEMA_VERSION is not None
    assert isinstance(REQUIRED_SCHEMA_VERSION, int)
    assert REQUIRED_SCHEMA_VERSION == MIN_SUPPORTED_SCHEMA


# ---------------------------------------------------------------------------
# check_compatibility semantics against the range
# ---------------------------------------------------------------------------


def test_check_compatibility_compatible() -> None:
    """project_version == cli_version → COMPATIBLE (no-op for existing projects)."""
    result = check_compatibility(project_version=3, cli_version=3)
    assert result.status == CompatibilityStatus.COMPATIBLE
    assert result.is_compatible
    assert result.exit_code == 0


def test_check_compatibility_outdated() -> None:
    """project_version < cli_version → OUTDATED (project must be upgraded)."""
    result = check_compatibility(project_version=2, cli_version=3)
    assert result.status == CompatibilityStatus.OUTDATED
    assert not result.is_compatible
    assert result.exit_code == 1


def test_check_compatibility_cli_outdated() -> None:
    """project_version > cli_version → CLI_OUTDATED (CLI must be upgraded)."""
    result = check_compatibility(project_version=4, cli_version=3)
    assert result.status == CompatibilityStatus.CLI_OUTDATED
    assert not result.is_compatible
    assert result.exit_code == 1


def test_check_compatibility_unmigrated() -> None:
    """project_version=None → UNMIGRATED (legacy project, no schema_version field)."""
    result = check_compatibility(project_version=None, cli_version=3)
    assert result.status == CompatibilityStatus.UNMIGRATED
    assert not result.is_compatible
    assert result.exit_code == 1
