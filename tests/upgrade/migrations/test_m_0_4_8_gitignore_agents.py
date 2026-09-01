"""Tests for migration m_0_4_8_gitignore_agents."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_0_4_8_gitignore_agents import (
    GitignoreAgentsMigration,
)

pytestmark = pytest.mark.fast


class TestDetect:
    """Test detecting missing agent directories in .gitignore."""

    def test_detects_missing_agents_when_no_gitignore(self, tmp_path: Path) -> None:
        migration = GitignoreAgentsMigration()
        assert migration.detect(tmp_path) is True

    def test_detects_missing_agents_when_incomplete(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".claude/\n")

        migration = GitignoreAgentsMigration()
        assert migration.detect(tmp_path) is True

    def test_returns_false_when_all_agents_present(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("\n".join(GitignoreAgentsMigration.EXPECTED_AGENTS) + "\n")

        migration = GitignoreAgentsMigration()
        assert migration.detect(tmp_path) is False

    def test_symlinked_gitignore_fails_closed(self, tmp_path: Path) -> None:
        """detect() must not follow a symlinked .gitignore; it should report
        the migration as needed rather than read through it."""
        outside_target = tmp_path.parent / f"outside-target-{os.getpid()}.txt"
        outside_target.write_text("\n".join(GitignoreAgentsMigration.EXPECTED_AGENTS) + "\n")
        gitignore = tmp_path / ".gitignore"
        gitignore.symlink_to(outside_target)
        try:
            migration = GitignoreAgentsMigration()
            assert migration.detect(tmp_path) is True
        finally:
            outside_target.unlink(missing_ok=True)
