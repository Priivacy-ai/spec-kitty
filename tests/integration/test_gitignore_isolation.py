"""Integration tests for Bug #120 - Gitignore Isolation.

Tests that worktree creation uses .git/info/exclude for local ignores
instead of mutating versioned .gitignore files.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

import pytest

from tests.test_isolation_helpers import get_source_version


def test_worktree_creation_does_not_modify_gitignore(
    tmp_path: Path,
    run_cli: Callable[[Path, str], subprocess.CompletedProcess[str]],
):
    """Test that worktree creation doesn't modify tracked .gitignore file.

    Bug #120: Worktree .gitignore mutation pollutes planning branch history.
    Fix: Use .git/info/exclude instead of versioned .gitignore.
    """
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create .kittify structure with dynamic version
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text("agents:\n  available: []\n")
    current_version = get_source_version()
    (tmp_path / ".kittify" / "metadata.yaml").write_text(
        f"spec_kitty:\n  version: {current_version}\n"
    )

    # Create feature structure
    feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)

    # Create meta.json
    meta_path = feature_dir / "meta.json"
    meta_path.write_text('{"feature_slug": "001-test-feature", "target_branch": "main"}')

    # Create WP task file
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    wp_path = tasks_dir / "WP01-test-task.md"
    wp_path.write_text("""---
work_package_id: WP01
title: Test Task
lane: planned
dependencies: []
---

# Test work package
""")

    # Create initial .gitignore if it exists
    gitignore_path = tmp_path / ".gitignore"
    gitignore_path.write_text("# Initial gitignore\n*.pyc\n")

    # Commit initial state
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Get initial gitignore content
    initial_gitignore = gitignore_path.read_text()

    # Run spec-kitty implement to create worktree
    result = run_cli(tmp_path, "implement", "WP01")

    # Verify command succeeded
    assert result.returncode == 0, f"implement failed: {result.stderr}"

    # Verify .gitignore in main repo was NOT modified
    final_gitignore = gitignore_path.read_text()
    assert final_gitignore == initial_gitignore, (
        "Tracked .gitignore in main repo should not be modified by worktree creation. "
        f"Expected:\n{initial_gitignore}\nGot:\n{final_gitignore}"
    )

    # Verify no uncommitted changes to .gitignore in main repo
    git_status = subprocess.run(
        ["git", "status", "--porcelain", ".gitignore"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert git_status.stdout.strip() == "", (
        ".gitignore should not be modified (no git status changes)"
    )

    # CRITICAL TEST: Verify .gitignore in WORKTREE was not created/modified either
    worktree_path = tmp_path / ".worktrees" / "001-test-feature-WP01"
    worktree_gitignore = worktree_path / ".gitignore"

    # The worktree should have the same .gitignore as main (or none if not in main)
    if gitignore_path.exists():
        # If .gitignore exists in main, worktree should have same content
        assert worktree_gitignore.read_text() == initial_gitignore, (
            "Worktree .gitignore should match main repo (not be modified)"
        )

    # Check git status in worktree - should show no changes to .gitignore
    worktree_git_status = subprocess.run(
        ["git", "status", "--porcelain", ".gitignore"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert worktree_git_status.stdout.strip() == "", (
        "Worktree .gitignore should not be modified (no git status changes in worktree)"
    )


@pytest.mark.xfail(reason="Test has git checkout issue - needs investigation")
def test_worktree_merge_has_no_gitignore_pollution(
    tmp_path: Path,
    run_cli: Callable[[Path, str], subprocess.CompletedProcess[str]],
):
    """Test that merging a worktree doesn't pollute history with .gitignore changes.

    Bug #120: .gitignore modifications in worktree leak into planning branch commits.
    """
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create .kittify structure with dynamic version
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text("agents:\n  available: []\n")
    current_version = get_source_version()
    (tmp_path / ".kittify" / "metadata.yaml").write_text(
        f"spec_kitty:\n  version: {current_version}\n"
    )

    # Create feature structure
    feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)

    # Create meta.json
    meta_path = feature_dir / "meta.json"
    meta_path.write_text('{"feature_slug": "001-test-feature", "target_branch": "main"}')

    # Create WP task file
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    wp_path = tasks_dir / "WP01-test-task.md"
    wp_path.write_text("""---
work_package_id: WP01
title: Test Task
lane: planned
dependencies: []
---

# Test work package
""")

    # Create initial .gitignore
    gitignore_path = tmp_path / ".gitignore"
    gitignore_path.write_text("# Initial gitignore\n*.pyc\n")

    # Commit initial state
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create worktree
    result = run_cli(tmp_path, "implement", "WP01")
    assert result.returncode == 0, f"implement failed: {result.stderr}"

    # In worktree, create a test file and commit
    worktree_path = tmp_path / ".worktrees" / "001-test-feature-WP01"
    test_file = worktree_path / "test.txt"
    test_file.write_text("test content")

    subprocess.run(
        ["git", "add", "test.txt"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add test file"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Merge WP branch back to main
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "merge", "001-test-feature-WP01", "--no-edit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Check git log for .gitignore changes
    git_log = subprocess.run(
        ["git", "log", "--all", "--oneline", "--", ".gitignore"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    # Only the initial commit should mention .gitignore
    gitignore_commits = [
        line for line in git_log.stdout.split("\n")
        if line.strip()
    ]

    # Should only be 1 commit (initial commit)
    assert len(gitignore_commits) <= 1, (
        f".gitignore should not appear in merge commits. "
        f"Found commits: {gitignore_commits}"
    )


def test_git_info_exclude_contains_exclusion_patterns(
    tmp_path: Path,
    run_cli: Callable[[Path, str], subprocess.CompletedProcess[str]],
):
    """Test that .git/info/exclude contains the exclusion patterns.

    Bug #120: Fix uses .git/info/exclude instead of .gitignore for local ignores.
    """
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create .kittify structure with dynamic version
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text("agents:\n  available: []\n")
    current_version = get_source_version()
    (tmp_path / ".kittify" / "metadata.yaml").write_text(
        f"spec_kitty:\n  version: {current_version}\n"
    )

    # Create feature structure
    feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)

    # Create meta.json
    meta_path = feature_dir / "meta.json"
    meta_path.write_text('{"feature_slug": "001-test-feature", "target_branch": "main"}')

    # Create WP task file
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    wp_path = tasks_dir / "WP01-test-task.md"
    wp_path.write_text("""---
work_package_id: WP01
title: Test Task
lane: planned
dependencies: []
---

# Test work package
""")

    # Commit initial state
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create worktree
    result = run_cli(tmp_path, "implement", "WP01")
    assert result.returncode == 0, f"implement failed: {result.stderr}"

    # Check that .git/info/exclude exists (in git directory, not worktree)
    # For worktrees, .git is a file pointing to the actual git directory
    worktree_path = tmp_path / ".worktrees" / "001-test-feature-WP01"
    git_file = worktree_path / ".git"

    # Read .git file to get actual git directory path
    assert git_file.exists() and git_file.is_file(), ".git should be a file in worktree"
    git_content = git_file.read_text().strip()
    assert git_content.startswith("gitdir:"), ".git file should contain gitdir: pointer"

    # Parse git dir path (it's an absolute path in the gitdir: line)
    git_dir_str = git_content.split(":", 1)[1].strip()
    git_dir = Path(git_dir_str)
    exclude_path = git_dir / "info" / "exclude"

    assert exclude_path.exists(), (
        f".git/info/exclude should exist at {exclude_path}"
    )

    # Verify it contains the exclusion pattern for WP status files
    exclude_content = exclude_path.read_text()
    assert "kitty-specs/**/tasks/*.md" in exclude_content, (
        ".git/info/exclude should contain 'kitty-specs/**/tasks/*.md' pattern. "
        f"Content:\n{exclude_content}"
    )

    # Verify comment is included
    assert "Block WP status files" in exclude_content or "managed in planning branch" in exclude_content, (
        ".git/info/exclude should contain explanatory comment. "
        f"Content:\n{exclude_content}"
    )
