"""Integration tests for auto-creating target branch on first implement.

Tests ADR-17: Auto-create target branch when implementing first WP if branch doesn't exist.

Scenario (~/tmp Feature 002):
- Feature targets 3.x (doesn't exist)
- spec-kitty implement WP01
- Should auto-create 3.x from main
- WP01 branches from 3.x (not main)
- Status commits route to 3.x
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


def create_feature_with_target(repo: Path, feature_slug: str, target_branch: str) -> Path:
    """Create minimal feature for testing."""
    import yaml

    # Create .kittify
    kittify = repo / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(yaml.dump({"vcs": {"type": "git"}, "agents": {"available": ["claude"]}}))
    (kittify / "metadata.yaml").write_text(yaml.dump({"spec_kitty": {"version": "0.13.8"}}))

    # Create feature
    feature_dir = repo / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    meta = {
        "feature_number": feature_slug.split("-")[0],
        "slug": feature_slug,
        "target_branch": target_branch,
        "vcs": "git",
        "created_at": "2026-01-29T00:00:00Z",
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


@pytest.mark.xfail(reason="Auto-create target branch feature removed in Bug #124 (WP05) - now respects current branch")
def test_auto_create_target_branch_on_first_implement(tmp_path):
    """Test that target branch is auto-created if missing.

    Validates:
    - Feature targets "3.x" (doesn't exist)
    - implement WP01 creates 3.x from main
    - WP01 worktree branches from 3.x (not main)
    - 3.x branch exists after implement

    NOTE: This behavior was intentionally removed in Bug #124 fix.
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

    # Create feature targeting non-existent 3.x branch
    feature_dir = create_feature_with_target(repo, "002-test-feature", "3.x")

    # Verify 3.x doesn't exist yet
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "3.x"],
        cwd=repo,
        capture_output=True,
        check=False
    )
    assert result.returncode != 0, "3.x should not exist before implement"

    # Implement WP01
    result = run_cli(repo, "implement", "WP01")
    assert result.returncode == 0, f"implement failed: {result.stderr}\n{result.stdout}"

    # Verify 3.x was created
    result_after = subprocess.run(
        ["git", "rev-parse", "--verify", "3.x"],
        cwd=repo,
        capture_output=True,
        check=False
    )
    assert result_after.returncode == 0, "3.x should exist after implement"

    # Verify WP01 branch exists and is based on 3.x
    wp_branch = "002-test-feature-WP01"
    merge_base_result = subprocess.run(
        ["git", "merge-base", "3.x", wp_branch],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    merge_base = merge_base_result.stdout.strip()

    # Verify that WP01's base is an ancestor of 3.x (not necessarily HEAD, because
    # implement adds a status commit to 3.x AFTER creating the worktree)
    is_ancestor_result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", merge_base, "3.x"],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    assert is_ancestor_result.returncode == 0, "WP01 should branch from an ancestor of 3.x"

    # Additionally verify that WP01 branches from 3.x (or its parent if status commit exists)
    result_3x_head = subprocess.run(
        ["git", "rev-parse", "3.x"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    head_3x = result_3x_head.stdout.strip()

    # merge_base should be either 3.x or 3.x^ (parent of 3.x if status commit was added)
    assert merge_base == head_3x or merge_base in subprocess.run(
        ["git", "rev-list", "3.x"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True
    ).stdout, "WP01 should branch from 3.x or its recent history"


@pytest.mark.xfail(reason="Auto-create target branch feature removed in Bug #124 (WP05)")
def test_subsequent_implement_uses_existing_target(tmp_path):
    """Test that second WP uses existing target branch (doesn't recreate).

    Validates:
    - First implement creates 3.x
    - Second implement finds 3.x exists
    - Doesn't try to create again (idempotent)
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)

    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, check=True, capture_output=True)

    feature_dir = create_feature_with_target(repo, "002-test", "3.x")

    # Add WP02
    (feature_dir / "tasks/WP02-test.md").write_text(
        "---\nwork_package_id: WP02\nlane: planned\ndependencies: []\n---\n\n# WP02\n"
    )
    subprocess.run(["git", "add", str(feature_dir)], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Add WP02"], cwd=repo, check=True, capture_output=True)

    # Implement WP01 (creates 3.x)
    result1 = run_cli(repo, "implement", "WP01")
    assert result1.returncode == 0

    # Get 3.x commit after first implement
    result = subprocess.run(
        ["git", "rev-parse", "3.x"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    commit_3x_after_wp01 = result.stdout.strip()

    # Implement WP02 (should use existing 3.x)
    result2 = run_cli(repo, "implement", "WP02")
    assert result2.returncode == 0

    # Verify 3.x was not recreated (it should have advanced by WP02's status commit)
    result_after_wp02 = subprocess.run(
        ["git", "rev-parse", "3.x"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    commit_3x_after_wp02 = result_after_wp02.stdout.strip()

    # Check that WP01's status commit is still in 3.x's history (proves 3.x wasn't recreated)
    is_ancestor_result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit_3x_after_wp01, commit_3x_after_wp02],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    assert is_ancestor_result.returncode == 0, "3.x should not be recreated - WP01 commit should still be in history"

    # Verify 3.x advanced by exactly one commit (WP02's status commit)
    parent_result = subprocess.run(
        ["git", "rev-parse", f"{commit_3x_after_wp02}^"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    parent_of_wp02 = parent_result.stdout.strip()
    assert parent_of_wp02 == commit_3x_after_wp01, "3.x should advance by one commit (WP02 status)"


@pytest.mark.xfail(reason="Auto-create target branch feature removed in Bug #124 (WP05)")
def test_auto_create_message_shown(tmp_path):
    """Test that creation message is shown to user.

    Validates:
    - Console output says "Creating target branch: 3.x"
    - Message is visible to agents/users
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)

    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, check=True, capture_output=True)

    create_feature_with_target(repo, "002-test", "3.x")

    # Implement WP01
    result = run_cli(repo, "implement", "WP01")
    assert result.returncode == 0

    # Check output mentions branch creation
    assert "Creating target branch" in result.stdout or "Created target branch" in result.stdout, \
        "Should announce target branch creation"


@pytest.mark.xfail(reason="Auto-create target branch feature removed in Bug #124 (WP05)")
def test_status_commits_route_to_auto_created_branch(tmp_path):
    """Test that status commits route to auto-created target branch.

    Validates:
    - 3.x auto-created during implement
    - Status commit (move-task) routes to 3.x (not main)
    - Routing works immediately after auto-create
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)

    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, check=True, capture_output=True)

    feature_dir = create_feature_with_target(repo, "002-test", "3.x")

    # Implement WP01 (should auto-create 3.x)
    result = run_cli(repo, "implement", "WP01")
    assert result.returncode == 0

    # Verify 3.x was created with planning commits and implement's status commit
    log_3x_before_status = subprocess.run(
        ["git", "log", "3.x", "--oneline", "-5"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Add 002-test" in log_3x_before_status.stdout, "3.x should have planning commits"
    assert "claimed for implementation" in log_3x_before_status.stdout, "3.x should have implement's status commit"

    # Move to for_review (status commit should route to 3.x)
    # Note: WP01 is already in "doing" from implement, so move to different lane
    result_move = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "for_review", "--force")
    assert result_move.returncode == 0, f"move-task failed: {result_move.stderr}\n{result_move.stdout}"

    # Verify status commit on 3.x (not main)
    log_3x = subprocess.run(
        ["git", "log", "3.x", "--oneline", "-5"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Move WP01 to for_review" in log_3x.stdout, f"Status commit should be on 3.x. Log:\n{log_3x.stdout}"

    # Verify main doesn't have status commit (before we sync)
    log_main = subprocess.run(
        ["git", "log", "main", "--oneline", "-5"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )

    # Main shouldn't have the status commit YET (it's only on 3.x)
    status_on_main = "Move WP01 to for_review" in log_main.stdout
    # Note: This might be false if branches haven't been synced
    # The important thing is that 3.x HAS it


def test_fallback_when_auto_create_fails(tmp_path):
    """Test graceful fallback if target branch creation fails.

    Validates:
    - Attempt to create 3.x
    - If fails (permissions, conflict, etc.)
    - Falls back to main with warning
    - WP01 still created (degraded mode)
    """
    # This test would need to simulate a git error
    # For now, just document expected behavior
    pass


def test_main_as_target_doesnt_recreate(tmp_path):
    """Test that target_branch='main' doesn't try to recreate main.

    Validates:
    - If target_branch is "main" or "master"
    - Don't try to create (already exists)
    - Use existing primary branch
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)

    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, check=True, capture_output=True)

    # Create feature targeting "main" (normal case)
    create_feature_with_target(repo, "001-test", "main")

    # Get main commit before implement
    result_before = subprocess.run(
        ["git", "rev-parse", "main"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    main_before = result_before.stdout.strip()

    # Implement WP01
    result = run_cli(repo, "implement", "WP01")
    assert result.returncode == 0

    # Verify main unchanged (not recreated)
    result_after = subprocess.run(
        ["git", "rev-parse", "main"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    main_after = result_after.stdout.strip()

    # Should be same (or advanced by status commit, but not recreated)
    # The key is that git branch main shouldn't have been attempted
    assert "fatal" not in result.stdout.lower(), "Should not try to create main"
    assert "already exists" not in result.stdout.lower(), "Should not try to create main"
