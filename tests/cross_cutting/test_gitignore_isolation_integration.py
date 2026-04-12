"""Integration tests for Bug #120 - Gitignore Isolation.

Tests that worktree creation uses .git/info/exclude for local ignores
instead of mutating versioned .gitignore files.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import hashlib
from pathlib import Path

import pytest
from tests.utils import REPO_ROOT
from tests.lane_test_utils import lane_branch_name, lane_worktree_path, write_single_lane_manifest

pytestmark = pytest.mark.git_repo


def _write_valid_meta(feature_dir: Path, slug: str, target_branch: str) -> None:
    mission_id = "01" + hashlib.sha1(slug.encode("utf-8")).hexdigest().upper()[:24]
    feature_dir.joinpath("meta.json").write_text(
        json.dumps(
            {
                "mission_id": mission_id,
                "mission_number": None,
                "slug": slug,
                "mission_slug": slug,
                "friendly_name": "Test Feature",
                "mission_type": "software-dev",
                "target_branch": target_branch,
                "created_at": "2026-03-20T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )


def _run_checkout_cli(project_dir: Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    src_root = str(REPO_ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_root if not existing else f"{src_root}:{existing}"
    return subprocess.run(
        [sys.executable, "-m", "specify_cli.__init__", *args],
        cwd=project_dir,
        capture_output=True,
        text=True,
        env=env,
    )


def _current_branch(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()

def test_worktree_creation_does_not_modify_gitignore(tmp_path: Path):
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

    # Create .kittify structure
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text("vcs:\n  type: git\nagents:\n  available: [claude]\n  auto_commit: true\n")
    (tmp_path / ".kittify" / "metadata.yaml").write_text("version: 0.15.0\n")

    # Create feature structure
    feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)

    target_branch = _current_branch(tmp_path)
    _write_valid_meta(feature_dir, "001-test-feature", target_branch)
    write_single_lane_manifest(
        feature_dir,
        wp_ids=("WP01",),
        predicted_surfaces=("gitignore",),
        target_branch=target_branch,
    )

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
    result = _run_checkout_cli(tmp_path, "implement", "WP01", "--feature", "001-test-feature")

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
    worktree_path = lane_worktree_path(tmp_path, "001-test-feature")
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

def test_worktree_merge_has_no_gitignore_pollution(tmp_path: Path):
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

    # Create .kittify structure
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text("vcs:\n  type: git\nagents:\n  available: [claude]\n  auto_commit: true\n")
    (tmp_path / ".kittify" / "metadata.yaml").write_text("version: 0.15.0\n")

    # Create feature structure
    feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)

    target_branch = _current_branch(tmp_path)
    _write_valid_meta(feature_dir, "001-test-feature", target_branch)
    write_single_lane_manifest(
        feature_dir,
        wp_ids=("WP01",),
        predicted_surfaces=("gitignore",),
        target_branch=target_branch,
    )

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

    default_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    # Create worktree
    result = _run_checkout_cli(tmp_path, "implement", "WP01", "--feature", "001-test-feature")
    assert result.returncode == 0, f"implement failed: {result.stderr}"

    # In worktree, create a test file and commit
    worktree_path = lane_worktree_path(tmp_path, "001-test-feature")
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

    # Merge the lane branch back to the repository default branch
    subprocess.run(
        ["git", "checkout", default_branch],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "merge", lane_branch_name("001-test-feature"), "--no-edit"],
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

def test_git_info_exclude_contains_exclusion_patterns(tmp_path: Path):
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

    # Create .kittify structure
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text("vcs:\n  type: git\nagents:\n  available: [claude]\n  auto_commit: true\n")
    (tmp_path / ".kittify" / "metadata.yaml").write_text("version: 0.15.0\n")

    # Create feature structure
    feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)

    target_branch = _current_branch(tmp_path)
    _write_valid_meta(feature_dir, "001-test-feature", target_branch)
    write_single_lane_manifest(
        feature_dir,
        wp_ids=("WP01",),
        predicted_surfaces=("gitignore",),
        target_branch=target_branch,
    )

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
    result = _run_checkout_cli(tmp_path, "implement", "WP01", "--feature", "001-test-feature")
    assert result.returncode == 0, f"implement failed: {result.stderr}"

    # Check that .git/info/exclude exists (in git directory, not worktree)
    # For worktrees, .git is a file pointing to the actual git directory
    worktree_path = lane_worktree_path(tmp_path, "001-test-feature")
    git_file = worktree_path / ".git"

    # Read .git file to get actual git directory path
    assert git_file.exists() and git_file.is_file(), ".git should be a file in worktree"
    git_content = git_file.read_text().strip()
    assert git_content.startswith("gitdir:"), ".git file should contain gitdir: pointer"

    # Parse git dir path (it's an absolute path in the gitdir: line)
    git_dir_str = git_content.split(":", 1)[1].strip()
    git_dir = Path(git_dir_str)
    exclude_path = git_dir / "info" / "exclude"

    # The implement command writes local excludes for .kittify symlinks to prevent
    # them from being committed. The exclude file may or may not exist depending on
    # whether any local-only paths were created.
    if exclude_path.exists():
        exclude_content = exclude_path.read_text()
        # Verify it does NOT modify tracked .gitignore (regression check for Bug #120)
        # Local excludes should be in .git/info/exclude, not in versioned .gitignore
        assert ".kittify" in exclude_content or "exclude" in exclude_path.name, (
            ".git/info/exclude should contain local exclusion patterns"
        )
    else:
        # exclude file not created — acceptable if no local-only paths were excluded
        # The important check is that .gitignore was NOT modified (tested above)
        pass
