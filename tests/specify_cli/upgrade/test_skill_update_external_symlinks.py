"""Tests for HOME-managed external-symlink tolerance in skill writes (#1184).

The gstack convention installs SKILL.md files as symlinks pointing to a
canonical copy in the operator's HOME directory. ``spec-kitty upgrade``
must NOT treat write failures on those symlinks as errors that change
the exit code — instead it should skip them and emit a warning.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from specify_cli.upgrade.skill_update import (
    is_external_symlink,
    write_skill_text,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# is_external_symlink
# ---------------------------------------------------------------------------


class TestIsExternalSymlink:
    def test_regular_file_is_not_external_symlink(self, tmp_path: Path) -> None:
        f = tmp_path / "SKILL.md"
        f.write_text("hello", encoding="utf-8")
        assert is_external_symlink(f, tmp_path) is False

    def test_in_repo_symlink_is_not_external(self, tmp_path: Path) -> None:
        target = tmp_path / "canonical.md"
        target.write_text("canonical", encoding="utf-8")
        link = tmp_path / "SKILL.md"
        os.symlink(target, link)
        assert is_external_symlink(link, tmp_path) is False

    def test_symlink_targeting_outside_repo_is_external(self, tmp_path: Path) -> None:
        external = tmp_path / "home" / "canonical.md"
        external.parent.mkdir(parents=True)
        external.write_text("canonical", encoding="utf-8")

        repo = tmp_path / "repo"
        repo.mkdir()
        link = repo / "SKILL.md"
        os.symlink(external, link)
        assert is_external_symlink(link, repo) is True

    def test_parent_directory_symlink_targeting_outside_repo_is_external(self, tmp_path: Path) -> None:
        external_skill_dir = tmp_path / "home" / ".claude" / "skills" / "x"
        external_skill_dir.mkdir(parents=True)
        (external_skill_dir / "SKILL.md").write_text("canonical", encoding="utf-8")

        repo = tmp_path / "repo"
        skill_parent = repo / ".claude" / "skills"
        skill_parent.mkdir(parents=True)
        os.symlink(external_skill_dir, skill_parent / "x")

        assert is_external_symlink(skill_parent / "x" / "SKILL.md", repo) is True

    def test_parent_directory_symlink_targeting_inside_repo_is_not_external(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        target_skill_dir = repo / "shared" / "x"
        target_skill_dir.mkdir(parents=True)
        (target_skill_dir / "SKILL.md").write_text("canonical", encoding="utf-8")

        skill_parent = repo / ".claude" / "skills"
        skill_parent.mkdir(parents=True)
        os.symlink(target_skill_dir, skill_parent / "x")

        assert is_external_symlink(skill_parent / "x" / "SKILL.md", repo) is False

    def test_missing_path_is_not_external_symlink(self, tmp_path: Path) -> None:
        missing = tmp_path / "no_such_file"
        assert is_external_symlink(missing, tmp_path) is False


# ---------------------------------------------------------------------------
# write_skill_text — the regression coverage for #1184
# ---------------------------------------------------------------------------


class TestWriteSkillTextExternalSymlink:
    """A SKILL.md symlink pointing outside the repo must be tolerated."""

    def test_external_symlink_is_skipped_and_warns(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        # External canonical copy (e.g. HOME-managed)
        external_home = tmp_path / "home" / ".claude" / "skills"
        external_home.mkdir(parents=True)
        canonical = external_home / "SKILL.md"
        canonical.write_text("CANONICAL CONTENT", encoding="utf-8")
        canonical_mtime = canonical.stat().st_mtime

        # Repo with a symlink pointing at the external canonical copy
        repo = tmp_path / "repo"
        skill_dir = repo / ".claude" / "skills" / "spec-kitty-glossary-context"
        skill_dir.mkdir(parents=True)
        link = skill_dir / "SKILL.md"
        os.symlink(canonical, link)

        with caplog.at_level(logging.WARNING, logger="specify_cli.upgrade.skill_update"):
            wrote, warning = write_skill_text(link, "NEW CONTENT", repo)

        # (a) writer did not raise, did not flag this as an error
        assert wrote is False
        assert warning is not None
        assert "symlink" in warning.lower()
        assert ".claude/skills/spec-kitty-glossary-context/SKILL.md" in warning

        # (b) the canonical file outside the repo is NOT modified
        assert canonical.read_text(encoding="utf-8") == "CANONICAL CONTENT"
        assert canonical.stat().st_mtime == canonical_mtime

        # (c) a warning was emitted
        assert any("symlink" in r.message.lower() for r in caplog.records)

    def test_regular_in_repo_file_is_written_normally(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / ".claude" / "skills" / "spec-kitty-glossary-context"
        skill_dir.mkdir(parents=True)
        dest = skill_dir / "SKILL.md"
        dest.write_text("OLD", encoding="utf-8")

        wrote, warning = write_skill_text(dest, "NEW", tmp_path)

        assert wrote is True
        assert warning is None
        assert dest.read_text(encoding="utf-8") == "NEW"

    def test_in_repo_symlink_is_written_normally(self, tmp_path: Path) -> None:
        """Symlinks whose target is INSIDE the repo are still written."""
        target = tmp_path / "shared" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("OLD", encoding="utf-8")

        skill_dir = tmp_path / ".claude" / "skills" / "x"
        skill_dir.mkdir(parents=True)
        link = skill_dir / "SKILL.md"
        os.symlink(target, link)

        wrote, warning = write_skill_text(link, "NEW", tmp_path)

        assert wrote is True
        assert warning is None
        # The write went through the symlink to the in-repo target.
        assert target.read_text(encoding="utf-8") == "NEW"

    def test_external_parent_directory_symlink_is_skipped(self, tmp_path: Path) -> None:
        """A symlinked skill directory pointing outside the repo is also skipped."""
        external_skill_dir = tmp_path / "home" / ".claude" / "skills" / "spec-kitty-runtime-next"
        external_skill_dir.mkdir(parents=True)
        canonical = external_skill_dir / "SKILL.md"
        canonical.write_text("CANONICAL CONTENT", encoding="utf-8")
        canonical_mtime = canonical.stat().st_mtime

        repo = tmp_path / "repo"
        skill_parent = repo / ".claude" / "skills"
        skill_parent.mkdir(parents=True)
        os.symlink(external_skill_dir, skill_parent / "spec-kitty-runtime-next")

        wrote, warning = write_skill_text(
            skill_parent / "spec-kitty-runtime-next" / "SKILL.md",
            "NEW CONTENT",
            repo,
        )

        assert wrote is False
        assert warning is not None
        assert "symlinked path" in warning
        assert canonical.read_text(encoding="utf-8") == "CANONICAL CONTENT"
        assert canonical.stat().st_mtime == canonical_mtime


# ---------------------------------------------------------------------------
# End-to-end through the glossary-context migration (#1184 reproduction)
# ---------------------------------------------------------------------------


class TestGlossaryContextMigrationToleratesExternalSymlink:
    """Reproduces the exact rc15 failure mode from issue #1184."""

    def test_external_symlink_does_not_fail_migration(self, tmp_path: Path) -> None:
        from specify_cli.upgrade.migrations.m_2_1_2_fix_glossary_context_skill import (
            FixGlossaryContextSkillMigration,
        )

        # HOME-managed canonical copy outside the repo
        external = tmp_path / "home" / ".claude" / "skills" / "spec-kitty-glossary-context" / "SKILL.md"
        external.parent.mkdir(parents=True)
        # Use the OLD marker so the migration considers this file needs update.
        external.write_text(
            "## Step 1: Locate Glossary Context\n\nIdentify the glossary state\n",
            encoding="utf-8",
        )
        external_mtime = external.stat().st_mtime

        # Repo with .claude/skills/<name>/SKILL.md as an external symlink
        repo = tmp_path / "repo"
        skill_dir = repo / ".claude" / "skills" / "spec-kitty-glossary-context"
        skill_dir.mkdir(parents=True)
        link = skill_dir / "SKILL.md"
        os.symlink(external, link)

        migration = FixGlossaryContextSkillMigration()
        result = migration.apply(repo, dry_run=False)

        # Migration succeeded (does NOT flip exit code)
        assert result.success is True
        assert result.errors == []
        # Canonical file outside the repo is NOT modified
        assert external.stat().st_mtime == external_mtime
        assert "## Step 1: Locate Glossary Context" in external.read_text(encoding="utf-8")
