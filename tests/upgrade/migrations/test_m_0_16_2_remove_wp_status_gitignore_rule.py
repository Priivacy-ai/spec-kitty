"""Tests for migration m_0_16_2_remove_wp_status_gitignore_rule."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from specify_cli.gitignore_manager import IgnoreFilePathError
from specify_cli.upgrade.migrations.m_0_16_2_remove_wp_status_gitignore_rule import (
    RemoveWpStatusGitignoreRuleMigration,
    find_wp_status_entries,
    is_wp_status_ignore_pattern,
    remove_wp_status_entries,
)

pytestmark = pytest.mark.fast


class TestIsWpStatusIgnorePattern:
    """Pattern matching for stale WP status ignore entries."""

    @pytest.mark.parametrize(
        "line",
        [
            "kitty-specs/**/tasks/*.md",
            "kitty-specs/*/tasks/*.md",
            "# Block WP status files (managed in main repo, prevents merge conflicts)",
            "# Research artifacts in kitty-specs/**/research/ are allowed",
        ],
    )
    def test_matches_stale_entries(self, line: str) -> None:
        assert is_wp_status_ignore_pattern(line) is True

    @pytest.mark.parametrize(
        "line",
        [
            "",
            "   ",
            "# unrelated comment",
            "kitty-specs/",
            "node_modules/",
            ".claude/",
        ],
    )
    def test_ignores_unrelated_entries(self, line: str) -> None:
        assert is_wp_status_ignore_pattern(line) is False


class TestFindWpStatusEntries:
    """Finding stale entries in .gitignore."""

    def test_finds_all_matching_lines(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(
            "\n".join(
                [
                    "node_modules/",
                    "# Block WP status files (managed in main repo, prevents merge conflicts)",
                    "# Research artifacts in kitty-specs/**/research/ are allowed",
                    "kitty-specs/**/tasks/*.md",
                    ".claude/",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        entries = find_wp_status_entries(gitignore)
        assert entries == [
            (2, "# Block WP status files (managed in main repo, prevents merge conflicts)"),
            (3, "# Research artifacts in kitty-specs/**/research/ are allowed"),
            (4, "kitty-specs/**/tasks/*.md"),
        ]

    def test_returns_empty_when_no_gitignore(self, tmp_path: Path) -> None:
        assert find_wp_status_entries(tmp_path / ".gitignore") == []

    def test_symlinked_gitignore_raises(self, tmp_path: Path) -> None:
        """Should refuse to follow a symlinked .gitignore rather than read through it."""
        outside_target = tmp_path.parent / f"outside-target-{os.getpid()}.txt"
        outside_target.write_text("kitty-specs/**/tasks/*.md\n")
        gitignore = tmp_path / ".gitignore"
        gitignore.symlink_to(outside_target)
        try:
            with pytest.raises(IgnoreFilePathError):
                find_wp_status_entries(gitignore)
        finally:
            outside_target.unlink(missing_ok=True)


class TestRemoveWpStatusEntries:
    """Removing stale entries from .gitignore."""

    def test_removes_stale_entries_and_preserves_others(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(
            "\n".join(
                [
                    ".claude/",
                    "# Block WP status files (managed in main repo, prevents merge conflicts)",
                    "# Research artifacts in kitty-specs/**/research/ are allowed",
                    "kitty-specs/**/tasks/*.md",
                    "node_modules/",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        changes, errors = remove_wp_status_entries(gitignore)
        assert not errors
        assert "Removed 3 stale WP status ignore entries" in changes[0]

        content = gitignore.read_text(encoding="utf-8")
        assert ".claude/" in content
        assert "node_modules/" in content
        assert "kitty-specs/**/tasks/*.md" not in content
        assert "Block WP status files" not in content
        assert "Research artifacts in kitty-specs/**/research/ are allowed" not in content

    def test_dry_run_does_not_modify_file(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        original = "kitty-specs/**/tasks/*.md\n"
        gitignore.write_text(original, encoding="utf-8")

        changes, errors = remove_wp_status_entries(gitignore, dry_run=True)
        assert not errors
        assert "Would remove 1 stale WP status ignore entries" in changes[0]
        assert gitignore.read_text(encoding="utf-8") == original

    def test_reports_when_no_matching_entries(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("node_modules/\n", encoding="utf-8")

        changes, errors = remove_wp_status_entries(gitignore)
        assert not errors
        assert "No stale WP status ignore entries found in .gitignore" in changes[0]

    def test_symlinked_gitignore_reports_error_not_crash(self, tmp_path: Path) -> None:
        """Should report a readable error rather than following the symlink or raising."""
        outside_target = tmp_path.parent / f"outside-target-{os.getpid()}.txt"
        outside_target.write_text("kitty-specs/**/tasks/*.md\n")
        gitignore = tmp_path / ".gitignore"
        gitignore.symlink_to(outside_target)
        try:
            changes, errors = remove_wp_status_entries(gitignore)
            assert changes == []
            assert len(errors) == 1
            assert "symlink" in errors[0]
            assert outside_target.read_text() == "kitty-specs/**/tasks/*.md\n"
        finally:
            outside_target.unlink(missing_ok=True)

    def test_dangling_symlink_is_rejected_not_treated_as_missing(self, tmp_path: Path) -> None:
        """A dangling symlinked .gitignore must error, not silently no-op as 'missing'.

        `Path.exists()` follows symlinks and returns False for a dangling
        symlink, which used to let this short-circuit to the "no .gitignore
        file found" no-op path before ever hitting the read.
        """
        gitignore = tmp_path / ".gitignore"
        missing_target = tmp_path / "does-not-exist"
        try:
            gitignore.symlink_to(missing_target)
        except OSError:
            pytest.skip("symlinks not supported on this filesystem")

        changes, errors = remove_wp_status_entries(gitignore)

        assert changes == []
        assert len(errors) == 1
        assert "symlink" in errors[0]
        assert not gitignore.exists()  # still dangling, untouched

    def test_live_target_symlink_is_rejected(self, tmp_path: Path) -> None:
        """A symlink to a real file is also rejected, not followed."""
        real_file = tmp_path / "real-gitignore"
        real_file.write_text("kitty-specs/**/tasks/*.md\n")
        gitignore = tmp_path / ".gitignore"
        try:
            gitignore.symlink_to(real_file)
        except OSError:
            pytest.skip("symlinks not supported on this filesystem")

        changes, errors = remove_wp_status_entries(gitignore)

        assert changes == []
        assert len(errors) == 1
        assert "symlink" in errors[0]
        assert real_file.read_text() == "kitty-specs/**/tasks/*.md\n"  # untouched


class TestMigration:
    """Migration wrapper behavior."""

    def test_detect(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("kitty-specs/**/tasks/*.md\n", encoding="utf-8")

        migration = RemoveWpStatusGitignoreRuleMigration()
        assert migration.detect(tmp_path) is True

    def test_detect_symlinked_gitignore_fails_closed(self, tmp_path: Path) -> None:
        """detect() should report the migration as needed rather than follow the symlink."""
        outside_target = tmp_path.parent / f"outside-target-{os.getpid()}.txt"
        outside_target.write_text("node_modules/\n")
        gitignore = tmp_path / ".gitignore"
        gitignore.symlink_to(outside_target)
        try:
            migration = RemoveWpStatusGitignoreRuleMigration()
            assert migration.detect(tmp_path) is True
        finally:
            outside_target.unlink(missing_ok=True)

    def test_can_apply_symlinked_gitignore_blocks(self, tmp_path: Path) -> None:
        """can_apply() should refuse a symlinked .gitignore rather than follow it."""
        outside_target = tmp_path.parent / f"outside-target-{os.getpid()}.txt"
        outside_target.write_text("node_modules/\n")
        gitignore = tmp_path / ".gitignore"
        gitignore.symlink_to(outside_target)
        try:
            migration = RemoveWpStatusGitignoreRuleMigration()
            can_apply, msg = migration.can_apply(tmp_path)
            assert can_apply is False
            assert "symlink" in msg
        finally:
            outside_target.unlink(missing_ok=True)

    def test_can_apply_rejects_dangling_symlink(self, tmp_path: Path) -> None:
        """can_apply() should reject a dangling symlinked .gitignore, not return True."""
        gitignore = tmp_path / ".gitignore"
        missing_target = tmp_path / "does-not-exist"
        try:
            gitignore.symlink_to(missing_target)
        except OSError:
            pytest.skip("symlinks not supported on this filesystem")

        migration = RemoveWpStatusGitignoreRuleMigration()
        can_apply, msg = migration.can_apply(tmp_path)
        assert can_apply is False
        assert "symlink" in msg

    def test_apply(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(
            "# Block WP status files (managed in main repo, prevents merge conflicts)\nkitty-specs/**/tasks/*.md\n",
            encoding="utf-8",
        )

        migration = RemoveWpStatusGitignoreRuleMigration()
        result = migration.apply(tmp_path)
        assert result.success is True
        assert not result.errors
        assert any("Removed" in change for change in result.changes_made)

        content = gitignore.read_text(encoding="utf-8")
        assert "kitty-specs/**/tasks/*.md" not in content
