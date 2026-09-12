"""Tests for migration m_0_12_1_remove_kitty_specs_from_gitignore."""

from __future__ import annotations

import os
import pytest
from pathlib import Path

from specify_cli.gitignore_manager import IgnoreFilePathError
from specify_cli.upgrade.migrations.m_0_12_1_remove_kitty_specs_from_gitignore import (
    RemoveKittySpecsFromGitignoreMigration,
    is_blocking_pattern,
    find_blocking_entries,
    remove_blocking_entries,
)

pytestmark = pytest.mark.fast


class TestIsBlockingPattern:
    """Test the pattern detection logic."""

    @pytest.mark.parametrize(
        "pattern",
        [
            "kitty-specs",
            "kitty-specs/",
            "/kitty-specs",
            "/kitty-specs/",
        ],
    )
    def test_blocking_patterns_detected(self, pattern: str):
        """Patterns that block the entire kitty-specs directory should be detected."""
        assert is_blocking_pattern(pattern) is True

    @pytest.mark.parametrize(
        "pattern",
        [
            "kitty-specs/**/tasks/*.md",
            "kitty-specs/*/tasks/*.md",
            "kitty-specs/**/tasks/",
            "# kitty-specs/",  # Comment
            "",  # Empty line
            "node_modules/",  # Unrelated
            ".kittify/",  # Unrelated
        ],
    )
    def test_non_blocking_patterns_ignored(self, pattern: str):
        """Patterns that don't block entire directory should NOT be detected."""
        assert is_blocking_pattern(pattern) is False


class TestFindBlockingEntries:
    """Test finding blocking entries in .gitignore."""

    def test_finds_blocking_entries(self, tmp_path: Path):
        """Should find line numbers of blocking entries."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("""# Some comments
node_modules/
.env
kitty-specs/
.kittify/
""")
        entries = find_blocking_entries(gitignore)
        assert entries == [(4, "kitty-specs/")]

    def test_finds_multiple_blocking_entries(self, tmp_path: Path):
        """Should find all blocking entries."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("""kitty-specs
node_modules/
/kitty-specs/
""")
        entries = find_blocking_entries(gitignore)
        assert entries == [(1, "kitty-specs"), (3, "/kitty-specs/")]

    def test_ignores_subpath_patterns(self, tmp_path: Path):
        """Should ignore patterns that only block specific subpaths."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("""# Worktree-specific patterns (should be kept)
kitty-specs/**/tasks/*.md
kitty-specs/*/tasks/*.md
""")
        entries = find_blocking_entries(gitignore)
        assert len(entries) == 0

    def test_no_gitignore_file(self, tmp_path: Path):
        """Should return empty list if no .gitignore exists."""
        gitignore = tmp_path / ".gitignore"
        entries = find_blocking_entries(gitignore)
        assert entries == []

    def test_symlinked_gitignore_raises(self, tmp_path: Path):
        """Should refuse to follow a symlinked .gitignore rather than read through it."""
        outside_target = tmp_path.parent / f"outside-target-{os.getpid()}.txt"
        outside_target.write_text("kitty-specs/\n")
        gitignore = tmp_path / ".gitignore"
        gitignore.symlink_to(outside_target)
        try:
            with pytest.raises(IgnoreFilePathError):
                find_blocking_entries(gitignore)
        finally:
            outside_target.unlink(missing_ok=True)


class TestRemoveBlockingEntries:
    """Test removing blocking entries from .gitignore."""

    def test_removes_blocking_entry(self, tmp_path: Path):
        """Should remove blocking entries and report changes."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("""node_modules/
kitty-specs/
.env
""")
        changes, errors = remove_blocking_entries(gitignore)

        assert len(errors) == 0
        assert "Removed 1 blocking entries" in changes[0]
        assert "kitty-specs/" in changes[1]

        # Verify file updated
        content = gitignore.read_text()
        assert "kitty-specs/" not in content
        assert "node_modules/" in content
        assert ".env" in content

    def test_removes_multiple_blocking_entries(self, tmp_path: Path):
        """Should remove all blocking entries."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("""kitty-specs
node_modules/
/kitty-specs/
.env
""")
        changes, errors = remove_blocking_entries(gitignore)

        assert len(errors) == 0
        assert "Removed 2 blocking entries" in changes[0]

        content = gitignore.read_text()
        assert "kitty-specs" not in content
        assert "node_modules/" in content
        assert ".env" in content

    def test_preserves_subpath_patterns(self, tmp_path: Path):
        """Should NOT remove worktree-specific patterns."""
        gitignore = tmp_path / ".gitignore"
        original = """node_modules/
kitty-specs/
kitty-specs/**/tasks/*.md
.env
"""
        gitignore.write_text(original)
        changes, errors = remove_blocking_entries(gitignore)

        assert len(errors) == 0

        content = gitignore.read_text()
        assert "kitty-specs/**/tasks/*.md" in content
        assert "kitty-specs/\n" not in content  # Blocking pattern removed

    def test_dry_run_doesnt_modify(self, tmp_path: Path):
        """Dry run should report changes but not modify file."""
        gitignore = tmp_path / ".gitignore"
        original = """kitty-specs/
node_modules/
"""
        gitignore.write_text(original)
        changes, errors = remove_blocking_entries(gitignore, dry_run=True)

        assert len(errors) == 0
        assert "Would remove" in changes[0]

        # File unchanged
        assert gitignore.read_text() == original

    def test_no_blocking_entries(self, tmp_path: Path):
        """Should report when no blocking entries found."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("""node_modules/
.env
""")
        changes, errors = remove_blocking_entries(gitignore)

        assert len(errors) == 0
        assert "No blocking kitty-specs/ entries" in changes[0]

    def test_symlinked_gitignore_reports_error_not_crash(self, tmp_path: Path):
        """Should report a readable error rather than following the symlink or raising."""
        outside_target = tmp_path.parent / f"outside-target-{os.getpid()}.txt"
        outside_target.write_text("kitty-specs/\n")
        gitignore = tmp_path / ".gitignore"
        gitignore.symlink_to(outside_target)
        try:
            changes, errors = remove_blocking_entries(gitignore)
            assert changes == []
            assert len(errors) == 1
            assert "symlink" in errors[0]
            # The symlink target must be untouched.
            assert outside_target.read_text() == "kitty-specs/\n"
        finally:
            outside_target.unlink(missing_ok=True)

    def test_dangling_symlink_is_rejected_not_treated_as_missing(self, tmp_path: Path):
        """A dangling symlinked .gitignore must error, not silently no-op as 'missing'.

        `Path.exists()` follows symlinks and returns False for a dangling
        symlink, which used to let this short-circuit to the "no .gitignore
        file found" no-op path before ever hitting the read. Checking
        `is_symlink()` first closes that gap.
        """
        gitignore = tmp_path / ".gitignore"
        missing_target = tmp_path / "does-not-exist"
        try:
            gitignore.symlink_to(missing_target)
        except OSError:
            pytest.skip("symlinks not supported on this filesystem")

        changes, errors = remove_blocking_entries(gitignore)

        assert changes == []
        assert len(errors) == 1
        assert "symlink" in errors[0]
        assert not gitignore.exists()  # still dangling, untouched

    def test_live_target_symlink_is_rejected(self, tmp_path: Path):
        """A symlink to a real file is also rejected, not followed."""
        real_file = tmp_path / "real-gitignore"
        real_file.write_text("kitty-specs/\n")
        gitignore = tmp_path / ".gitignore"
        try:
            gitignore.symlink_to(real_file)
        except OSError:
            pytest.skip("symlinks not supported on this filesystem")

        changes, errors = remove_blocking_entries(gitignore)

        assert changes == []
        assert len(errors) == 1
        assert "symlink" in errors[0]
        assert real_file.read_text() == "kitty-specs/\n"  # untouched

    def test_vanishing_symlink_is_still_rejected(self, tmp_path, monkeypatch):
        gitignore = tmp_path / ".gitignore"
        gitignore.symlink_to(tmp_path / "does-not-exist")

        def readlink_raises(*args, **kwargs):
            raise FileNotFoundError(f"simulated vanished symlink: {args}")

        monkeypatch.setattr(os, "readlink", readlink_raises)

        changes, errors = remove_blocking_entries(gitignore)

        assert changes == []
        assert len(errors) == 1
        assert "symlink" in errors[0]


class TestMigration:
    """Test the migration class."""

    def test_detect_finds_blocking_entries(self, tmp_path: Path):
        """detect() should return True when blocking entries exist."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("kitty-specs/\n")

        migration = RemoveKittySpecsFromGitignoreMigration()
        assert migration.detect(tmp_path) is True

    def test_detect_returns_false_when_clean(self, tmp_path: Path):
        """detect() should return False when no blocking entries."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("node_modules/\n")

        migration = RemoveKittySpecsFromGitignoreMigration()
        assert migration.detect(tmp_path) is False

    def test_detect_returns_false_no_gitignore(self, tmp_path: Path):
        """detect() should return False when no .gitignore exists."""
        migration = RemoveKittySpecsFromGitignoreMigration()
        assert migration.detect(tmp_path) is False

    def test_can_apply_returns_true(self, tmp_path: Path):
        """can_apply() should return True for readable .gitignore."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("kitty-specs/\n")

        migration = RemoveKittySpecsFromGitignoreMigration()
        can_apply, msg = migration.can_apply(tmp_path)
        assert can_apply is True
        assert msg == ""

    def test_detect_symlinked_gitignore_fails_closed(self, tmp_path: Path):
        """detect() should report the migration as needed rather than follow the symlink."""
        outside_target = tmp_path.parent / f"outside-target-{os.getpid()}.txt"
        outside_target.write_text("node_modules/\n")
        gitignore = tmp_path / ".gitignore"
        gitignore.symlink_to(outside_target)
        try:
            migration = RemoveKittySpecsFromGitignoreMigration()
            assert migration.detect(tmp_path) is True
        finally:
            outside_target.unlink(missing_ok=True)

    def test_can_apply_symlinked_gitignore_blocks(self, tmp_path: Path):
        """can_apply() should refuse a symlinked .gitignore rather than follow it."""
        outside_target = tmp_path.parent / f"outside-target-{os.getpid()}.txt"
        outside_target.write_text("node_modules/\n")
        gitignore = tmp_path / ".gitignore"
        gitignore.symlink_to(outside_target)
        try:
            migration = RemoveKittySpecsFromGitignoreMigration()
            can_apply, msg = migration.can_apply(tmp_path)
            assert can_apply is False
            assert "symlink" in msg
        finally:
            outside_target.unlink(missing_ok=True)

    def test_can_apply_rejects_dangling_symlink(self, tmp_path: Path):
        """can_apply() should reject a dangling symlinked .gitignore, not return True."""
        gitignore = tmp_path / ".gitignore"
        missing_target = tmp_path / "does-not-exist"
        try:
            gitignore.symlink_to(missing_target)
        except OSError:
            pytest.skip("symlinks not supported on this filesystem")

        migration = RemoveKittySpecsFromGitignoreMigration()
        can_apply, msg = migration.can_apply(tmp_path)
        assert can_apply is False
        assert "symlink" in msg

    def test_can_apply_rejects_vanishing_symlink(self, tmp_path, monkeypatch):
        gitignore = tmp_path / ".gitignore"
        gitignore.symlink_to(tmp_path / "does-not-exist")

        def readlink_raises(*args, **kwargs):
            raise FileNotFoundError(f"simulated vanished symlink: {args}")

        monkeypatch.setattr(os, "readlink", readlink_raises)

        migration = RemoveKittySpecsFromGitignoreMigration()
        can_apply, msg = migration.can_apply(tmp_path)
        assert can_apply is False
        assert "symlink" in msg

    def test_apply_removes_entries(self, tmp_path: Path):
        """apply() should remove blocking entries."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("""node_modules/
kitty-specs/
.env
""")
        migration = RemoveKittySpecsFromGitignoreMigration()
        result = migration.apply(tmp_path)

        assert result.success is True
        assert len(result.errors) == 0
        assert any("Removed" in c for c in result.changes_made)

        content = gitignore.read_text()
        assert "kitty-specs/" not in content
        assert "node_modules/" in content

    def test_apply_dry_run(self, tmp_path: Path):
        """apply() with dry_run should not modify file."""
        gitignore = tmp_path / ".gitignore"
        original = "kitty-specs/\n"
        gitignore.write_text(original)

        migration = RemoveKittySpecsFromGitignoreMigration()
        result = migration.apply(tmp_path, dry_run=True)

        assert result.success is True
        assert gitignore.read_text() == original


class TestRealWorldScenarios:
    """Test with realistic .gitignore content."""

    def test_user_reported_scenario(self, tmp_path: Path):
        """Test the exact scenario reported by the user: kitty-specs/ at line 105."""
        # Simulate a long .gitignore with kitty-specs/ buried in it
        lines = [f"entry_{i}\n" for i in range(104)]
        lines.append("kitty-specs/\n")
        lines.extend([f"entry_{i}\n" for i in range(105, 110)])

        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("".join(lines))

        migration = RemoveKittySpecsFromGitignoreMigration()

        # Should detect
        assert migration.detect(tmp_path) is True

        # Should find at line 105
        entries = find_blocking_entries(gitignore)
        assert entries == [(105, "kitty-specs/")]

        # Should fix
        result = migration.apply(tmp_path)
        assert result.success is True

        # Should no longer detect
        assert migration.detect(tmp_path) is False

    def test_mixed_patterns(self, tmp_path: Path):
        """Test file with both blocking and allowed patterns."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("""# Build output
dist/
build/

# Dependencies
node_modules/

# Spec Kitty (problematic)
kitty-specs/

# Worktree-specific (should be kept)
kitty-specs/**/tasks/*.md

# Environment
.env
.env.local
""")
        migration = RemoveKittySpecsFromGitignoreMigration()
        result = migration.apply(tmp_path)

        assert result.success is True

        content = gitignore.read_text()
        # Blocking pattern removed
        assert "\nkitty-specs/\n" not in content
        # Subpath pattern preserved
        assert "kitty-specs/**/tasks/*.md" in content
        # Other entries preserved
        assert "node_modules/" in content
        assert ".env" in content
