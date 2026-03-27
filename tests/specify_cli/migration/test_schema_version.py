"""Tests for the schema version gate — T058.

Covers:
- T058-1: schema_version missing → CompatibilityStatus.UNMIGRATED
- T058-2: schema_version < CLI → CompatibilityStatus.OUTDATED
- T058-3: schema_version == CLI → CompatibilityStatus.COMPATIBLE
- T058-4: schema_version > CLI → CompatibilityStatus.CLI_OUTDATED
- T058-5: gate raises SystemExit for incompatible projects
- T058-6: gate allows ``upgrade`` command to pass through
- T058-7: gate skips when no ``.kittify/`` directory exists
- T058-8: get_project_schema_version returns None for missing metadata
- T058-9: check_schema_version does not raise for compatible project
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specify_cli.migration.schema_version import (
    REQUIRED_SCHEMA_VERSION,
    CompatibilityStatus,
    check_compatibility,
    get_project_schema_version,
)
from specify_cli.migration.gate import check_schema_version


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_metadata(tmp_path: Path, schema_version: int | None = None) -> None:
    """Write a minimal metadata.yaml into ``tmp_path/.kittify/``."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    data: dict = {
        "spec_kitty": {
            "version": "2.1.0",
            "initialized_at": "2026-01-01T00:00:00",
        }
    }
    if schema_version is not None:
        data["spec_kitty"]["schema_version"] = schema_version

    metadata_path = kittify / "metadata.yaml"
    with open(metadata_path, "w", encoding="utf-8") as fh:
        yaml.dump(data, fh)


# ---------------------------------------------------------------------------
# T058-1 through T058-4: check_compatibility logic
# ---------------------------------------------------------------------------


def test_check_compatibility_unmigrated():
    """schema_version=None → UNMIGRATED."""
    result = check_compatibility(None, REQUIRED_SCHEMA_VERSION)
    assert result.status == CompatibilityStatus.UNMIGRATED
    assert not result.is_compatible
    assert result.exit_code == 1
    assert "spec-kitty upgrade" in result.message


def test_check_compatibility_outdated():
    """schema_version < CLI → OUTDATED."""
    result = check_compatibility(REQUIRED_SCHEMA_VERSION - 1, REQUIRED_SCHEMA_VERSION)
    assert result.status == CompatibilityStatus.OUTDATED
    assert not result.is_compatible
    assert result.exit_code == 1
    assert "spec-kitty upgrade" in result.message
    assert str(REQUIRED_SCHEMA_VERSION - 1) in result.message


def test_check_compatibility_compatible():
    """schema_version == CLI → COMPATIBLE."""
    result = check_compatibility(REQUIRED_SCHEMA_VERSION, REQUIRED_SCHEMA_VERSION)
    assert result.status == CompatibilityStatus.COMPATIBLE
    assert result.is_compatible
    assert result.exit_code == 0


def test_check_compatibility_cli_outdated():
    """schema_version > CLI → CLI_OUTDATED."""
    result = check_compatibility(REQUIRED_SCHEMA_VERSION + 1, REQUIRED_SCHEMA_VERSION)
    assert result.status == CompatibilityStatus.CLI_OUTDATED
    assert not result.is_compatible
    assert result.exit_code == 1
    assert "pip install --upgrade spec-kitty-cli" in result.message
    assert str(REQUIRED_SCHEMA_VERSION + 1) in result.message


# ---------------------------------------------------------------------------
# T058-5: gate raises SystemExit for incompatible projects
# ---------------------------------------------------------------------------


def test_gate_raises_on_unmigrated(tmp_path):
    """Gate raises SystemExit(1) when schema_version is missing."""
    _write_metadata(tmp_path, schema_version=None)  # no schema_version field

    with pytest.raises(SystemExit) as exc_info:
        check_schema_version(tmp_path, invoked_subcommand="plan")
    assert exc_info.value.code == 1


def test_gate_raises_on_outdated(tmp_path):
    """Gate raises SystemExit(1) when project schema is behind CLI."""
    _write_metadata(tmp_path, schema_version=REQUIRED_SCHEMA_VERSION - 1)

    with pytest.raises(SystemExit) as exc_info:
        check_schema_version(tmp_path, invoked_subcommand="specify")
    assert exc_info.value.code == 1


def test_gate_raises_on_cli_outdated(tmp_path):
    """Gate raises SystemExit(1) when project schema is ahead of CLI."""
    _write_metadata(tmp_path, schema_version=REQUIRED_SCHEMA_VERSION + 1)

    with pytest.raises(SystemExit) as exc_info:
        check_schema_version(tmp_path, invoked_subcommand="specify")
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# T058-6: gate allows upgrade command to pass through
# ---------------------------------------------------------------------------


def test_gate_allows_upgrade_command(tmp_path):
    """Gate skips check when subcommand is 'upgrade', even for unmigrated project."""
    _write_metadata(tmp_path, schema_version=None)  # would normally fail

    # Must NOT raise — upgrade is exempt
    check_schema_version(tmp_path, invoked_subcommand="upgrade")


def test_gate_allows_init_command(tmp_path):
    """Gate skips check when subcommand is 'init'."""
    _write_metadata(tmp_path, schema_version=None)

    # Must NOT raise
    check_schema_version(tmp_path, invoked_subcommand="init")


# ---------------------------------------------------------------------------
# T058-7: gate skips when no .kittify/ exists
# ---------------------------------------------------------------------------


def test_gate_skips_for_uninitialized_project(tmp_path):
    """Gate is a no-op when .kittify/ does not exist."""
    # No .kittify/ directory at all
    assert not (tmp_path / ".kittify").exists()

    # Must NOT raise — uninitialized project, let init handle it
    check_schema_version(tmp_path, invoked_subcommand="anything")


# ---------------------------------------------------------------------------
# T058-8: get_project_schema_version edge cases
# ---------------------------------------------------------------------------


def test_get_project_schema_version_no_metadata(tmp_path):
    """Returns None when metadata.yaml does not exist."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    result = get_project_schema_version(tmp_path)
    assert result is None


def test_get_project_schema_version_missing_field(tmp_path):
    """Returns None when schema_version field is absent."""
    _write_metadata(tmp_path, schema_version=None)
    result = get_project_schema_version(tmp_path)
    assert result is None


def test_get_project_schema_version_present(tmp_path):
    """Returns the integer schema version when field is present."""
    _write_metadata(tmp_path, schema_version=REQUIRED_SCHEMA_VERSION)
    result = get_project_schema_version(tmp_path)
    assert result == REQUIRED_SCHEMA_VERSION


def test_get_project_schema_version_no_kittify(tmp_path):
    """Returns None when .kittify directory does not exist."""
    result = get_project_schema_version(tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# T058-9: gate does not raise for compatible project
# ---------------------------------------------------------------------------


def test_gate_passes_for_compatible_project(tmp_path):
    """Gate is a no-op when schema_version matches CLI requirement."""
    _write_metadata(tmp_path, schema_version=REQUIRED_SCHEMA_VERSION)

    # Must NOT raise
    check_schema_version(tmp_path, invoked_subcommand="plan")
