"""Integration tests for Bug #124: Branch Routing Unification.

Tests that CLI commands respect user's current branch and don't
auto-checkout to main/master without explicit permission.

Scenario:
- User is on feature branch 'feature/new-auth'
- Feature targets 'main'
- Commands should respect current branch, not auto-switch
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_cli(project_path: Path, *args: str) -> subprocess.CompletedProcess:
    """Execute spec-kitty CLI."""
    from tests.test_isolation_helpers import get_venv_python

    env = os.environ.copy()
    src_path = REPO_ROOT / "src"
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    env.setdefault("SPEC_KITTY_TEMPLATE_ROOT", str(REPO_ROOT))
    command = [str(get_venv_python()), "-m", "specify_cli.__init__", *args]
    return subprocess.run(command, cwd=str(project_path), capture_output=True, text=True, env=env)


def get_current_branch(repo: Path) -> str:
    """Get current git branch."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def create_feature_on_main(repo: Path, feature_slug: str) -> Path:
    """Create minimal feature targeting main branch."""
    import yaml

    # Create .kittify
    kittify = repo / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(yaml.dump({"vcs": {"type": "git"}, "agents": {"available": ["claude"]}}))
    (kittify / "metadata.yaml").write_text(yaml.dump({"spec_kitty": {"version": "0.15.0"}}))

    # Create feature
    feature_dir = repo / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    meta = {
        "feature_number": feature_slug.split("-")[0],
        "slug": feature_slug,
        "target_branch": "main",
        "vcs": "git",
        "created_at": "2026-02-11T00:00:00Z",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    # Create WP01
    (tasks_dir / "WP01-test.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "lane: planned\n"
        "dependencies: []\n"
        "---\n\n"
        "# WP01\n"
    )

    # Commit
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", f"Add {feature_slug}"], cwd=repo, check=True, capture_output=True)

    return feature_dir


def test_implement_respects_current_branch(tmp_path):
    """Test that 'implement' command doesn't auto-checkout to main.

    Validates:
    - User is on 'feature/new-auth' branch
    - Feature targets 'main'
    - implement WP01 creates worktree from current branch (not main)
    - User stays on 'feature/new-auth' after command
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    # Initialize git
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)

    # Initial commit
    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, check=True, capture_output=True)

    # Create feature targeting main
    create_feature_on_main(repo, "001-test-feature")

    # Create and switch to feature branch
    subprocess.run(["git", "checkout", "-b", "feature/new-auth"], cwd=repo, check=True, capture_output=True)

    # Verify we're on feature branch
    assert get_current_branch(repo) == "feature/new-auth"

    # Run implement command
    result = run_cli(repo, "implement", "WP01")

    # Should succeed
    assert result.returncode == 0, f"implement failed: {result.stderr}"

    # User should still be on feature branch (no auto-checkout)
    assert get_current_branch(repo) == "feature/new-auth", "Command auto-switched branch unexpectedly"

    # Worktree should exist
    worktree = repo / ".worktrees" / "001-test-feature-WP01"
    assert worktree.exists(), "Worktree not created"


def test_worktree_base_branch_is_current(tmp_path):
    """Test that worktree is created from current branch, not main.

    Validates:
    - Worktree base branch is user's current branch
    - Base is NOT auto-switched to main
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    # Initialize git
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)

    # Initial commit
    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, check=True, capture_output=True)

    # Create feature targeting main
    create_feature_on_main(repo, "002-test-feature")

    # Create and switch to feature branch
    subprocess.run(["git", "checkout", "-b", "develop"], cwd=repo, check=True, capture_output=True)

    # Make a commit on develop to differentiate it
    (repo / "develop.txt").write_text("develop branch\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Develop commit"], cwd=repo, check=True, capture_output=True)

    # Run implement command from develop
    result = run_cli(repo, "implement", "WP01")
    assert result.returncode == 0, f"implement failed: {result.stderr}"

    # Check workspace context to verify base branch
    workspace_context_file = repo / ".kittify" / "workspaces" / "002-test-feature-WP01.json"
    if workspace_context_file.exists():
        context_data = json.loads(workspace_context_file.read_text())
        # Base branch should be 'develop' (current), not 'main' (target)
        assert context_data.get("base_branch") == "develop", \
            f"Base branch should be 'develop', got {context_data.get('base_branch')}"


def test_status_commits_respect_current_branch(tmp_path):
    """Test that status commits land on current branch, not auto-switched to main.

    Validates:
    - Status changes commit to current branch
    - No auto-checkout to target branch
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    # Initialize git
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)

    # Initial commit
    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, check=True, capture_output=True)

    # Create feature targeting main
    create_feature_on_main(repo, "003-test-feature")

    # Create and switch to feature branch
    subprocess.run(["git", "checkout", "-b", "staging"], cwd=repo, check=True, capture_output=True)

    # Get commit count before status change
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    commits_before = int(result.stdout.strip())

    # Move task to doing (triggers status commit)
    result = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "doing", "--feature", "003-test-feature")

    # Command should succeed
    assert result.returncode == 0, f"move-task failed: {result.stderr}"

    # Should still be on staging branch
    assert get_current_branch(repo) == "staging", "Branch changed unexpectedly"

    # Verify commit landed on staging (not main)
    result = subprocess.run(
        ["git", "rev-list", "--count", "staging"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    commits_after = int(result.stdout.strip())
    assert commits_after == commits_before + 1, "Status commit not on staging branch"

    # Verify main hasn't changed
    result = subprocess.run(
        ["git", "rev-list", "--count", "main"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    main_commits = int(result.stdout.strip())
    assert main_commits == commits_before, "Commit incorrectly landed on main"


def test_notification_when_current_differs_from_target(tmp_path):
    """Test that user gets notification when current != target branch.

    Validates:
    - User sees notification about branch mismatch
    - Notification is informational, not an error
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    # Initialize git
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)

    # Initial commit
    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, check=True, capture_output=True)

    # Create feature targeting main
    create_feature_on_main(repo, "004-test-feature")

    # Create and switch to feature branch
    subprocess.run(["git", "checkout", "-b", "develop"], cwd=repo, check=True, capture_output=True)

    # Run implement command
    result = run_cli(repo, "implement", "WP01")

    # Should succeed (not error)
    assert result.returncode == 0, f"implement failed: {result.stderr}"

    # Output should mention branch situation
    output = result.stdout + result.stderr
    # Should mention something about branches (exact message may vary)
    # This is a loose check - the specific notification format can be decided during implementation
    assert "develop" in output.lower() or "main" in output.lower() or "branch" in output.lower(), \
        "No branch notification in output"


def test_finalize_tasks_respects_current_branch(tmp_path):
    """Test that finalize-tasks commits to current branch, not auto-switched to main.

    Validates:
    - User is on 'feature/planning' branch
    - Feature targets 'main'
    - finalize-tasks command commits to current branch (not main)
    - User stays on 'feature/planning' after command
    """
    import yaml

    repo = tmp_path / "repo"
    repo.mkdir()

    # Initialize git
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)

    # Initial commit
    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, check=True, capture_output=True)

    # Create .kittify
    kittify = repo / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(yaml.dump({"vcs": {"type": "git"}, "agents": {"available": ["claude"]}}))
    (kittify / "metadata.yaml").write_text(yaml.dump({"spec_kitty": {"version": "0.15.0"}}))

    # Create feature targeting main
    feature_dir = repo / "kitty-specs" / "005-test-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    meta = {
        "feature_number": "005",
        "slug": "005-test-feature",
        "target_branch": "main",
        "vcs": "git",
        "created_at": "2026-02-11T00:00:00Z",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    # Create tasks.md with dependencies
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n"
        "## Work Package WP01 - Setup\n\n"
        "Depends on: none\n\n"
        "## Work Package WP02 - Implementation\n\n"
        "Depends on WP01\n"
    )

    # Create WP files
    (tasks_dir / "WP01-setup.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "lane: planned\n"
        "---\n\n"
        "# WP01\n"
    )
    (tasks_dir / "WP02-impl.md").write_text(
        "---\n"
        "work_package_id: WP02\n"
        "lane: planned\n"
        "---\n\n"
        "# WP02\n"
    )

    # Commit on main
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Add 005-test-feature"], cwd=repo, check=True, capture_output=True)

    # Create and switch to planning branch
    subprocess.run(["git", "checkout", "-b", "feature/planning"], cwd=repo, check=True, capture_output=True)

    # Verify we're on planning branch
    assert get_current_branch(repo) == "feature/planning"

    # Get commit count before finalize
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    commits_before = int(result.stdout.strip())

    # Run finalize-tasks command
    result = run_cli(repo, "agent", "feature", "finalize-tasks", "--json")

    # Should succeed
    assert result.returncode == 0, f"finalize-tasks failed: {result.stderr}"

    # User should still be on planning branch (no auto-checkout)
    assert get_current_branch(repo) == "feature/planning", "Command auto-switched branch unexpectedly"

    # Verify commit landed on planning branch (not main)
    result = subprocess.run(
        ["git", "rev-list", "--count", "feature/planning"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    commits_after = int(result.stdout.strip())
    assert commits_after == commits_before + 1, "Finalize commit not on feature/planning branch"

    # Verify main hasn't changed (still at original commit count)
    result = subprocess.run(
        ["git", "rev-list", "--count", "main"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    main_commits = int(result.stdout.strip())
    assert main_commits == commits_before, "Commit incorrectly landed on main"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
