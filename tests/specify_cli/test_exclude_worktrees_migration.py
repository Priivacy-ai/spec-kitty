"""Tests for the exclude worktrees migration (0.13.1)."""

from pathlib import Path

import pytest

from specify_cli.core.git_ops import run_command
from specify_cli.upgrade.migrations.m_0_13_1_exclude_worktrees import ExcludeWorktreesMigration


@pytest.fixture(name="_git_identity")
def git_identity_fixture(monkeypatch):
    """Ensure git commands can commit even if the user has no global config."""
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Spec Kitty")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "spec@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Spec Kitty")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "spec@example.com")


@pytest.fixture
def git_project(tmp_path, _git_identity):
    """Create a git project for testing."""
    repo = tmp_path / "project"
    repo.mkdir()

    # Initialize git repo
    run_command(["git", "init"], cwd=repo)
    run_command(["git", "commit", "--allow-empty", "-m", "Initial commit"], cwd=repo)

    # Create .kittify directory
    kittify = repo / ".kittify"
    kittify.mkdir()

    return repo


@pytest.fixture
def non_git_project(tmp_path):
    """Create a non-git project for testing."""
    repo = tmp_path / "project"
    repo.mkdir()

    # Create .kittify directory (but no git repo)
    kittify = repo / ".kittify"
    kittify.mkdir()

    return repo


class TestExcludeWorktreesMigration:
    """Tests for ExcludeWorktreesMigration."""

    def test_detect_returns_true_when_exclusion_missing(self, git_project):
        """Test that detect returns True when .worktrees/ not in exclude."""
        migration = ExcludeWorktreesMigration()

        # Exclusion should be missing initially
        assert migration.detect(git_project) is True

    def test_detect_returns_false_when_exclusion_exists(self, git_project):
        """Test that detect returns False when .worktrees/ already in exclude."""
        migration = ExcludeWorktreesMigration()

        # Add exclusion
        exclude_file = git_project / ".git" / "info" / "exclude"
        with exclude_file.open("a") as f:
            f.write("\n.worktrees/\n")

        # Detection should return False (already excluded)
        assert migration.detect(git_project) is False

    def test_detect_returns_false_for_non_git_repo(self, non_git_project):
        """Test that detect returns False for non-git repositories."""
        migration = ExcludeWorktreesMigration()

        # Should return False for non-git projects
        assert migration.detect(non_git_project) is False

    def test_can_apply_succeeds_for_git_repo(self, git_project):
        """Test that can_apply returns True for git repositories."""
        migration = ExcludeWorktreesMigration()

        can_apply, reason = migration.can_apply(git_project)

        assert can_apply is True
        assert reason == ""

    def test_can_apply_fails_for_non_git_repo(self, non_git_project):
        """Test that can_apply returns False for non-git repositories."""
        migration = ExcludeWorktreesMigration()

        can_apply, reason = migration.can_apply(non_git_project)

        assert can_apply is False
        assert "Not a git repository" in reason

    def test_apply_adds_exclusion(self, git_project):
        """Test that apply adds .worktrees/ to .git/info/exclude."""
        migration = ExcludeWorktreesMigration()

        # Apply migration
        result = migration.apply(git_project, dry_run=False)

        # Should succeed
        assert result.success is True
        assert len(result.errors) == 0

        # Verify exclusion was added
        exclude_file = git_project / ".git" / "info" / "exclude"
        content = exclude_file.read_text()
        assert ".worktrees/" in content

        # Check changes reported
        assert any("Added .worktrees/" in change for change in result.changes_made)

    def test_apply_dry_run(self, git_project):
        """Test that dry run doesn't modify files."""
        migration = ExcludeWorktreesMigration()

        # Get initial state
        exclude_file = git_project / ".git" / "info" / "exclude"
        initial_content = exclude_file.read_text()

        # Apply dry run
        result = migration.apply(git_project, dry_run=True)

        # Should succeed
        assert result.success is True

        # File should not be modified
        final_content = exclude_file.read_text()
        assert final_content == initial_content

        # Should report what would happen
        assert any("Would add" in change for change in result.changes_made)

    def test_apply_skips_non_git_repo(self, non_git_project):
        """Test that apply skips non-git repositories."""
        migration = ExcludeWorktreesMigration()

        # Apply migration
        result = migration.apply(non_git_project, dry_run=False)

        # Should succeed but skip
        assert result.success is True
        assert any("Skipped" in change for change in result.changes_made)

    def test_apply_idempotent(self, git_project):
        """Test that applying migration multiple times is safe."""
        migration = ExcludeWorktreesMigration()

        # Apply migration twice
        result1 = migration.apply(git_project, dry_run=False)
        result2 = migration.apply(git_project, dry_run=False)

        # Both should succeed
        assert result1.success is True
        assert result2.success is True

        # Verify exclusion appears only once
        exclude_file = git_project / ".git" / "info" / "exclude"
        content = exclude_file.read_text()
        assert content.count(".worktrees/") == 1

    def test_migration_metadata(self):
        """Test that migration has correct metadata."""
        migration = ExcludeWorktreesMigration()

        assert migration.migration_id == "0.13.1_exclude_worktrees"
        assert migration.target_version == "0.13.1"
        assert "exclude" in migration.description.lower()
