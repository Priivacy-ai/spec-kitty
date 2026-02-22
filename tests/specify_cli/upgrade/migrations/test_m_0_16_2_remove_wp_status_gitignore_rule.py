"""Tests for migration m_0_16_2_remove_wp_status_gitignore_rule."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_0_16_2_remove_wp_status_gitignore_rule import (
    RemoveWpStatusGitignoreRuleMigration,
    find_wp_status_entries,
    is_wp_status_ignore_pattern,
    remove_wp_status_entries,
)


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


class TestMigration:
    """Migration wrapper behavior."""

    def test_detect(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("kitty-specs/**/tasks/*.md\n", encoding="utf-8")

        migration = RemoveWpStatusGitignoreRuleMigration()
        assert migration.detect(tmp_path) is True

    def test_apply(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(
            "# Block WP status files (managed in main repo, prevents merge conflicts)\n"
            "kitty-specs/**/tasks/*.md\n",
            encoding="utf-8",
        )

        migration = RemoveWpStatusGitignoreRuleMigration()
        result = migration.apply(tmp_path)
        assert result.success is True
        assert not result.errors
        assert any("Removed" in change for change in result.changes_made)

        content = gitignore.read_text(encoding="utf-8")
        assert "kitty-specs/**/tasks/*.md" not in content
