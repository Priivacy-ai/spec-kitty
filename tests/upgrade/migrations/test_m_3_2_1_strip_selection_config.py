"""Tests for migration 3.2.1: strip selection block from config.yaml."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.fast

from specify_cli.upgrade.migrations.m_3_2_1_strip_selection_config import (
    StripSelectionConfigMigration,
)


@pytest.fixture
def migration() -> StripSelectionConfigMigration:
    return StripSelectionConfigMigration()


def _write_config(tmp_path: Path, content: str) -> Path:
    config_dir = tmp_path / ".kittify"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(content)
    return config_file


# Test 1: agents.selection removed; other config preserved
def test_removes_agents_selection(tmp_path: Path, migration: StripSelectionConfigMigration) -> None:
    config_file = _write_config(
        tmp_path,
        (
            "agents:\n"
            "  available:\n    - claude\n"
            "  selection:\n    preferred_implementer: claude\n    preferred_reviewer: opencode\n"
            "  auto_commit: true\n"
        ),
    )
    assert migration.detect(tmp_path) is True
    result = migration.apply(tmp_path)
    assert result.success
    content = config_file.read_text()
    assert "preferred_implementer" not in content
    assert "selection" not in content
    assert "claude" in content  # available list preserved
    assert "auto_commit" in content  # other config preserved


# Test 2: tools.selection removed (post-m_2_0_1 projects)
def test_removes_tools_selection(tmp_path: Path, migration: StripSelectionConfigMigration) -> None:
    _write_config(
        tmp_path,
        (
            "tools:\n"
            "  available:\n    - opencode\n"
            "  selection:\n    preferred_implementer: opencode\n"
        ),
    )
    assert migration.detect(tmp_path) is True
    result = migration.apply(tmp_path)
    assert result.success
    assert "preferred_implementer" not in (tmp_path / ".kittify" / "config.yaml").read_text()


# Test 3: No selection key — detect returns False, no changes
def test_no_selection_key(tmp_path: Path, migration: StripSelectionConfigMigration) -> None:
    _write_config(tmp_path, "agents:\n  available:\n    - claude\n  auto_commit: true\n")
    assert migration.detect(tmp_path) is False


# Test 4: Empty/missing selection value — no crash
def test_empty_selection(tmp_path: Path, migration: StripSelectionConfigMigration) -> None:
    _write_config(tmp_path, "agents:\n  available:\n    - claude\n  selection: {}\n")
    assert migration.detect(tmp_path) is True
    result = migration.apply(tmp_path)
    assert result.success


# Test 5: Dry-run — no file write
def test_dry_run_no_write(tmp_path: Path, migration: StripSelectionConfigMigration) -> None:
    original = (
        "agents:\n  available:\n    - claude\n"
        "  selection:\n    preferred_implementer: claude\n"
    )
    config_file = _write_config(tmp_path, original)
    result = migration.apply(tmp_path, dry_run=True)
    assert result.success
    assert any("Would remove" in c for c in result.changes_made)
    assert config_file.read_text() == original  # unchanged
