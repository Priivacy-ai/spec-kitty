"""Integration tests for safe_commit helper (Bug #122).

These tests verify that status commits don't capture unrelated staged files.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.git.commit_helpers import safe_commit


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository for testing."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    initial_file = repo / "README.md"
    initial_file.write_text("# Test Repo\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    return repo


def test_safe_commit_preserves_unrelated_staged_files(git_repo: Path):
    """T045: Pre-stage unrelated file, run safe_commit, assert unrelated file remains staged.

    This is the core bug fix: when updating WP status, any other staged files
    should NOT be included in the commit.
    """
    # Create and stage an unrelated file
    unrelated_file = git_repo / "unrelated.txt"
    unrelated_file.write_text("This should stay staged\n")
    subprocess.run(["git", "add", "unrelated.txt"], cwd=git_repo, check=True)

    # Create the file we actually want to commit
    wp_file = git_repo / "WP01.md"
    wp_file.write_text("---\nlane: doing\n---\n")

    # Use safe_commit to commit only the WP file
    result = safe_commit(
        repo_path=git_repo,
        files_to_commit=[wp_file],
        commit_message="Update WP01 status to doing",
        allow_empty=False,
    )

    assert result is True, "safe_commit should succeed"

    # Check that unrelated file is still staged (not committed)
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=git_repo,
        capture_output=True,
        text=True,
        check=True,
    )

    # File should be staged (index modified) - shown as "A " or "M " in first column
    assert "A  unrelated.txt" in status_result.stdout or "M  unrelated.txt" in status_result.stdout, (
        f"Unrelated file should remain staged. Got:\n{status_result.stdout}"
    )

    # Check that WP file was committed (not in status)
    assert "WP01.md" not in status_result.stdout, "WP01.md should be committed"

    # Verify commit message
    log_result = subprocess.run(
        ["git", "log", "-1", "--oneline"],
        cwd=git_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Update WP01 status to doing" in log_result.stdout


def test_safe_commit_nothing_to_commit_graceful(git_repo: Path):
    """T046: Test 'nothing to commit' graceful handling.

    When a file hasn't changed, safe_commit should handle it gracefully.
    """
    # Try to commit a file that hasn't changed
    readme = git_repo / "README.md"

    # allow_empty=False should return False
    result = safe_commit(
        repo_path=git_repo,
        files_to_commit=[readme],
        commit_message="No changes",
        allow_empty=False,
    )
    assert result is False, "Should return False when nothing to commit and allow_empty=False"

    # allow_empty=True should return True
    result = safe_commit(
        repo_path=git_repo,
        files_to_commit=[readme],
        commit_message="No changes",
        allow_empty=True,
    )
    assert result is True, "Should return True when nothing to commit and allow_empty=True"


def test_safe_commit_preserves_multiple_unrelated_staged_files(git_repo: Path):
    """T047: Test multiple unrelated staged files preserved.

    Ensures the fix works with multiple staged files, not just one.
    """
    # Stage multiple unrelated files
    file1 = git_repo / "feature1.py"
    file1.write_text("# Feature 1\n")
    subprocess.run(["git", "add", "feature1.py"], cwd=git_repo, check=True)

    file2 = git_repo / "feature2.py"
    file2.write_text("# Feature 2\n")
    subprocess.run(["git", "add", "feature2.py"], cwd=git_repo, check=True)

    file3 = git_repo / "docs.md"
    file3.write_text("# Docs\n")
    subprocess.run(["git", "add", "docs.md"], cwd=git_repo, check=True)

    # Create and commit only the WP file
    wp_file = git_repo / "WP02.md"
    wp_file.write_text("---\nlane: for_review\n---\n")

    result = safe_commit(
        repo_path=git_repo,
        files_to_commit=[wp_file],
        commit_message="Update WP02 status to for_review",
        allow_empty=False,
    )

    assert result is True, "safe_commit should succeed"

    # All three unrelated files should still be staged
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=git_repo,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "A  feature1.py" in status_result.stdout
    assert "A  feature2.py" in status_result.stdout
    assert "A  docs.md" in status_result.stdout
    assert "WP02.md" not in status_result.stdout, "WP02.md should be committed"


def test_safe_commit_with_absolute_paths(git_repo: Path):
    """Test safe_commit works with absolute file paths."""
    # Stage unrelated file
    unrelated = git_repo / "unrelated.txt"
    unrelated.write_text("Unrelated\n")
    subprocess.run(["git", "add", "unrelated.txt"], cwd=git_repo, check=True)

    # Commit using absolute path
    wp_file = git_repo / "WP03.md"
    wp_file.write_text("---\nlane: done\n---\n")

    result = safe_commit(
        repo_path=git_repo,
        files_to_commit=[wp_file.absolute()],  # Use absolute path
        commit_message="Update WP03 status to done",
        allow_empty=False,
    )

    assert result is True

    # Verify unrelated file still staged
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=git_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "A  unrelated.txt" in status_result.stdout


def test_safe_commit_with_subdirectory_files(git_repo: Path):
    """Test safe_commit works with files in subdirectories."""
    # Create subdirectory structure
    subdir = git_repo / "kitty-specs" / "038-feature" / "tasks"
    subdir.mkdir(parents=True)

    # Stage unrelated file in root
    unrelated = git_repo / "root_file.txt"
    unrelated.write_text("Root file\n")
    subprocess.run(["git", "add", "root_file.txt"], cwd=git_repo, check=True)

    # Commit file in subdirectory
    wp_file = subdir / "WP04.md"
    wp_file.write_text("---\nlane: doing\n---\n")

    result = safe_commit(
        repo_path=git_repo,
        files_to_commit=[wp_file],
        commit_message="Update WP04 in subdirectory",
        allow_empty=False,
    )

    assert result is True

    # Verify unrelated file still staged
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=git_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "A  root_file.txt" in status_result.stdout
    assert "WP04.md" not in status_result.stdout


def test_safe_commit_multiple_files_at_once(git_repo: Path):
    """Test committing multiple intended files while preserving staged files."""
    # Stage unrelated file
    unrelated = git_repo / "unrelated.txt"
    unrelated.write_text("Unrelated\n")
    subprocess.run(["git", "add", "unrelated.txt"], cwd=git_repo, check=True)

    # Create multiple files to commit together
    wp1 = git_repo / "WP05.md"
    wp1.write_text("---\nlane: done\n---\n")

    wp2 = git_repo / "WP06.md"
    wp2.write_text("---\nlane: done\n---\n")

    result = safe_commit(
        repo_path=git_repo,
        files_to_commit=[wp1, wp2],
        commit_message="Mark WP05 and WP06 as done",
        allow_empty=False,
    )

    assert result is True

    # Verify both WPs committed, unrelated still staged
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=git_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "A  unrelated.txt" in status_result.stdout
    assert "WP05.md" not in status_result.stdout
    assert "WP06.md" not in status_result.stdout


def test_safe_commit_fails_gracefully_on_invalid_file(git_repo: Path):
    """Test safe_commit returns False when file doesn't exist."""
    nonexistent = git_repo / "does_not_exist.md"

    result = safe_commit(
        repo_path=git_repo,
        files_to_commit=[nonexistent],
        commit_message="This should fail",
        allow_empty=False,
    )

    assert result is False, "Should return False when file doesn't exist"
