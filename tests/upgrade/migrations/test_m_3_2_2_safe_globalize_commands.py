"""Tests for migration 3.2.2: safe per-project command file removal."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch
from specify_cli.upgrade.migrations.m_3_2_2_safe_globalize_commands import (
    SafeGlobalizeCommandsMigration,
    _VERSION_MARKER_PREFIX,
)

pytestmark = pytest.mark.fast

_MARKER = f"{_VERSION_MARKER_PREFIX} 3.1.1a2 -->\n"


@pytest.fixture
def migration() -> SafeGlobalizeCommandsMigration:
    return SafeGlobalizeCommandsMigration()


def _make_project(tmp_path: Path, agent_files: dict[str, str]) -> Path:
    """Create project with agent command files. agent_files: {'.claude/commands/file.md': content}"""
    (tmp_path / ".kittify").mkdir()
    for rel_path, content in agent_files.items():
        full = tmp_path / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
    return tmp_path


# Test 1: No global runtime → all agents skipped, warning in changes
def test_no_global_runtime_skips_all(tmp_path: Path, migration: SafeGlobalizeCommandsMigration) -> None:
    project = _make_project(tmp_path, {
        ".claude/commands/spec-kitty.implement.md": f"{_MARKER}# content"
    })
    with patch.object(migration, "_global_runtime_present", return_value=False):
        result = migration.apply(project)
    assert result.success
    assert any("global runtime" in c for c in result.changes_made)
    # File must NOT be deleted
    assert (project / ".claude/commands/spec-kitty.implement.md").exists()


# Test 2: Global commands absent for claude, present for codex → claude skipped, codex cleaned
def test_per_agent_skip(tmp_path: Path, migration: SafeGlobalizeCommandsMigration) -> None:
    project = _make_project(tmp_path, {
        ".claude/commands/spec-kitty.implement.md": f"{_MARKER}# content",
        ".codex/prompts/spec-kitty.implement.md": f"{_MARKER}# content",
    })

    def mock_global_commands(agent_root: str, subdir: str) -> bool:
        return agent_root == ".codex"

    with patch.object(migration, "_global_runtime_present", return_value=True), \
         patch.object(migration, "_global_commands_present", side_effect=mock_global_commands):
        result = migration.apply(project)

    assert result.success
    assert (project / ".claude/commands/spec-kitty.implement.md").exists()  # skipped
    assert not (project / ".codex/prompts/spec-kitty.implement.md").exists()  # removed


# Test 3: Local file lacks version header → skipped; sibling with header removed
def test_no_version_header_skips_file(tmp_path: Path, migration: SafeGlobalizeCommandsMigration) -> None:
    project = _make_project(tmp_path, {
        ".claude/commands/spec-kitty.implement.md": f"{_MARKER}# generated",
        ".claude/commands/spec-kitty.custom.md": "# no marker here\n# user-authored",
    })
    with patch.object(migration, "_global_runtime_present", return_value=True), \
         patch.object(migration, "_global_commands_present", return_value=True):
        result = migration.apply(project)

    assert not (project / ".claude/commands/spec-kitty.implement.md").exists()  # removed
    assert (project / ".claude/commands/spec-kitty.custom.md").exists()  # kept (no marker)


# Test 4: Dry-run — no files deleted, "Would remove" in changes
def test_dry_run_no_deletions(tmp_path: Path, migration: SafeGlobalizeCommandsMigration) -> None:
    project = _make_project(tmp_path, {
        ".claude/commands/spec-kitty.implement.md": f"{_MARKER}# content",
    })
    with patch.object(migration, "_global_runtime_present", return_value=True), \
         patch.object(migration, "_global_commands_present", return_value=True):
        result = migration.apply(project, dry_run=True)

    assert result.success
    assert any("Would remove" in c for c in result.changes_made)
    assert (project / ".claude/commands/spec-kitty.implement.md").exists()  # NOT deleted


# Test 5: Mixed project — two agents safe, one not
def test_mixed_agents(tmp_path: Path, migration: SafeGlobalizeCommandsMigration) -> None:
    project = _make_project(tmp_path, {
        ".claude/commands/spec-kitty.implement.md": f"{_MARKER}# content",
        ".codex/prompts/spec-kitty.implement.md": f"{_MARKER}# content",
        ".opencode/command/spec-kitty.implement.md": f"{_MARKER}# content",
    })

    def mock_global(agent_root: str, subdir: str) -> bool:
        return agent_root in (".claude", ".opencode")  # codex has no global

    with patch.object(migration, "_global_runtime_present", return_value=True), \
         patch.object(migration, "_global_commands_present", side_effect=mock_global):
        result = migration.apply(project)

    assert not (project / ".claude/commands/spec-kitty.implement.md").exists()
    assert (project / ".codex/prompts/spec-kitty.implement.md").exists()  # skipped
    assert not (project / ".opencode/command/spec-kitty.implement.md").exists()


# Test 6: detect() returns False when no spec-kitty.* files present
def test_detect_false_when_no_files(tmp_path: Path, migration: SafeGlobalizeCommandsMigration) -> None:
    _make_project(tmp_path, {".claude/commands/my-custom.md": "# user file"})
    assert migration.detect(tmp_path) is False
