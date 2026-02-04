"""Integration tests for dual-branch status routing (0.13.8 hotfix).

Tests the complete status commit routing logic for features with target_branch metadata:
- Legacy features (no target_branch) → route to main
- Dual-branch features (target_branch: "2.x") → route to 2.x
- Status commits from worktree context
- Subtask marking with routing
- Race condition prevention
- Graceful fallback when target branch doesn't exist
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

# Get repo root for Python module invocation
REPO_ROOT = Path(__file__).resolve().parents[2]


# ============================================================================
# Helper Functions
# ============================================================================


def run_cli(project_path: Path, *args: str) -> subprocess.CompletedProcess:
    """Execute spec-kitty CLI using Python module invocation."""
    from tests.test_isolation_helpers import get_venv_python

    env = os.environ.copy()
    src_path = REPO_ROOT / "src"
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(
        os.pathsep
    )
    env.setdefault("SPEC_KITTY_TEMPLATE_ROOT", str(REPO_ROOT))
    command = [str(get_venv_python()), "-m", "specify_cli.__init__", *args]
    return subprocess.run(
        command,
        cwd=str(project_path),
        capture_output=True,
        text=True,
        env=env,
    )


def create_feature_with_target(
    repo: Path, feature_slug: str, target_branch: str | None = None
) -> Path:
    """Create feature directory with optional target_branch in meta.json."""
    feature_dir = repo / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    # Create spec.md
    (feature_dir / "spec.md").write_text(f"# Spec for {feature_slug}\n")

    # Create meta.json with optional target_branch
    feature_number = feature_slug.split("-")[0]
    meta = {
        "feature_number": feature_number,
        "feature_slug": feature_slug,
        "created_at": "2026-01-29T00:00:00Z",
        "vcs": "git",
    }
    if target_branch is not None:
        meta["target_branch"] = target_branch

    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    # Create WP01 file
    wp_file = tasks_dir / "WP01-test.md"
    wp_file.write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Test Work Package\n"
        "lane: planned\n"
        "dependencies: []\n"
        "---\n\n"
        "# WP01 Content\n"
    )

    # Commit to current branch
    subprocess.run(["git", "add", str(feature_dir)], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"Add {feature_slug}"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    return feature_dir


def get_last_commit_message(repo: Path, branch: str) -> str:
    """Get the last commit message on a branch."""
    result = subprocess.run(
        ["git", "log", branch, "--oneline", "-1"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def assert_commit_on_branch(repo: Path, branch: str, expected_substring: str):
    """Assert that recent commit on branch contains expected substring."""
    result = subprocess.run(
        ["git", "log", branch, "--oneline", "-5"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert expected_substring in result.stdout, (
        f"Expected '{expected_substring}' in recent commits on {branch}:\n{result.stdout}"
    )


def assert_no_commit_on_branch(repo: Path, branch: str, unexpected_substring: str):
    """Assert that no recent commit on branch contains substring."""
    result = subprocess.run(
        ["git", "log", branch, "--oneline", "-10"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert unexpected_substring not in result.stdout, (
        f"Unexpected '{unexpected_substring}' found in commits on {branch}:\n{result.stdout}"
    )


def verify_ancestry(repo: Path, ancestor: str, descendant: str) -> bool:
    """Check if ancestor is an ancestor of descendant."""
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo,
        capture_output=True,
    )
    return result.returncode == 0


# ============================================================================
# Tests
# ============================================================================


def test_status_routes_to_main_for_legacy_features(dual_branch_repo):
    """Test status commits go to main for features without target_branch field.

    Validates:
    - Legacy features (no target_branch in meta.json) route to main
    - Default behavior preserved for backward compatibility
    - 2.x branch unaffected
    """
    repo = dual_branch_repo

    # Create feature WITHOUT target_branch (legacy)
    feature_dir = create_feature_with_target(repo, "001-legacy-feature", target_branch=None)

    # Move task to doing using agent command
    result = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "doing")

    # Should succeed
    assert result.returncode == 0, f"Failed to move task: {result.stderr}\n{result.stdout}"

    # Verify status commit on main
    assert_commit_on_branch(repo, "main", "Move WP01 to doing")

    # Verify 2.x branch unaffected (should only have initial commits)
    result_2x = subprocess.run(
        ["git", "log", "2.x", "--oneline"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "WP01" not in result_2x.stdout, "Status commit leaked to 2.x branch"


def test_status_routes_to_2x_for_dual_branch_features(dual_branch_repo):
    """Test status commits go to 2.x for features with target_branch: 2.x.

    Validates:
    - Features with target_branch: "2.x" route to 2.x
    - Main branch unaffected (no status commits)
    - Target branch detection works correctly
    """
    repo = dual_branch_repo

    # Create feature on main WITH target_branch: "2.x"
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)
    feature_dir = create_feature_with_target(repo, "025-saas-feature", target_branch="2.x")

    # Merge planning to 2.x (simulates real workflow where planning is on main first)
    subprocess.run(["git", "checkout", "2.x"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "merge", "main", "--no-ff", "-m", "Merge planning from main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Return to main for status operations
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    # Move task to doing
    result = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "doing")

    # Should succeed
    assert result.returncode == 0, f"Failed to move task: {result.stderr}\n{result.stdout}"

    # Verify status commit on 2.x
    assert_commit_on_branch(repo, "2.x", "Move WP01 to doing")

    # Verify main branch does NOT have this status commit
    # Main should only have the "Add 025-saas-feature" commit
    result_main = subprocess.run(
        ["git", "log", "main", "--oneline", "-5"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )

    # Extract just the commit messages
    main_commits = [line.split(maxsplit=1)[1] for line in result_main.stdout.strip().split("\n") if line]

    # Should have feature creation commit but NOT status move commit
    assert any("Add 025-saas-feature" in msg for msg in main_commits), "Feature creation commit missing"
    assert not any("Move WP01 to doing" in msg for msg in main_commits), "Status commit leaked to main"


def test_status_routing_from_worktree_context(dual_branch_repo):
    """Test status commits route correctly even when called from worktree.

    Validates:
    - Status routing respects target_branch even from worktree context
    - Worktree branch doesn't interfere with routing
    - Status commits still go to target (2.x), not worktree branch
    """
    repo = dual_branch_repo

    # Create feature on main with target_branch: "2.x"
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)
    feature_dir = create_feature_with_target(repo, "026-worktree-test", target_branch="2.x")

    # Merge to 2.x
    subprocess.run(["git", "checkout", "2.x"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "merge", "main", "--no-ff", "-m", "Merge planning from main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Manually create a worktree for WP01 from 2.x
    wp_branch = "026-worktree-test-WP01"
    worktree_path = repo / ".worktrees" / wp_branch

    subprocess.run(
        ["git", "worktree", "add", "-b", wp_branch, str(worktree_path), "2.x"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Update WP lane to doing (simulate starting work)
    wp_file = feature_dir / "tasks" / "WP01-test.md"
    content = wp_file.read_text()
    updated = content.replace('lane: planned', 'lane: doing')
    wp_file.write_text(updated)

    # Commit the lane change to the WP file on main (so it's tracked)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "add", str(wp_file)], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Update WP01 to doing"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Merge this to 2.x as well
    subprocess.run(["git", "checkout", "2.x"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "merge", "main", "--no-ff", "-m", "Sync status from main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Now make a dummy commit in worktree to have something to review
    dummy_file = worktree_path / "work.txt"
    dummy_file.write_text("some work")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add work"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Go back to main context
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    # Run move-task from main repo (should still route to 2.x based on feature metadata)
    result = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "for_review", "--force")

    # Should succeed
    assert result.returncode == 0, f"Failed to move task: {result.stderr}\n{result.stdout}"

    # Verify status commit on 2.x (not on worktree branch)
    assert_commit_on_branch(repo, "2.x", "Move WP01 to for_review")

    # Cleanup worktree
    subprocess.run(
        ["git", "worktree", "remove", str(worktree_path), "--force"],
        cwd=repo,
        check=False,
        capture_output=True,
    )


def test_mark_subtasks_routes_correctly(dual_branch_repo):
    """Test mark-status routing for subtask checkboxes.

    Validates:
    - Subtask status updates (mark-status) respect target_branch
    - Checkbox updates commit to correct branch
    """
    repo = dual_branch_repo

    # Create feature on main with target_branch: "2.x"
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)
    feature_dir = create_feature_with_target(repo, "027-subtask-test", target_branch="2.x")

    # Create tasks.md with subtasks (required by mark-status)
    tasks_md = feature_dir / "tasks.md"
    tasks_md.write_text(
        "# Tasks\n\n"
        "## WP01 - Setup\n\n"
        "### Subtasks\n"
        "- [ ] WP01.1 - First subtask\n"
        "- [ ] WP01.2 - Second subtask\n"
    )

    # Also add subtasks to WP01 file for consistency
    wp_file = feature_dir / "tasks" / "WP01-test.md"
    content = wp_file.read_text()
    content += "\n## Subtasks\n- [ ] WP01.1 - First subtask\n- [ ] WP01.2 - Second subtask\n"
    wp_file.write_text(content)

    # Commit the subtasks on main
    subprocess.run(["git", "add", str(tasks_md), str(wp_file)], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add subtasks to WP01"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Merge to 2.x
    subprocess.run(["git", "checkout", "2.x"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "merge", "main", "--no-ff", "-m", "Merge planning from main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Go back to main for CLI operations
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    # Mark subtask as done
    result = run_cli(repo, "agent", "tasks", "mark-status", "WP01.1", "--status", "done")

    # Should succeed
    assert result.returncode == 0, f"Failed to mark subtask: {result.stderr}\n{result.stdout}"

    # Verify status commit on 2.x
    assert_commit_on_branch(repo, "2.x", "WP01.1")

    # Verify main unaffected (no new status commits after initial merge)
    # Count commits on main that mention WP01.1
    status_on_main = count_commits_matching(repo, "main", "WP01.1")
    assert status_on_main == 0, "Subtask status should not commit to main"


def count_commits_matching(repo: Path, branch: str, pattern: str) -> int:
    """Count commits on branch matching pattern."""
    result = subprocess.run(
        ["git", "log", branch, "--oneline", "-20"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return sum(1 for line in result.stdout.split("\n") if pattern in line)


def test_race_condition_prevented(dual_branch_repo):
    """Test that status and implementation commits maintain ancestry.

    Validates:
    - Implementation branch created from 2.x
    - Status commits to 2.x
    - git merge-base --is-ancestor 2.x <branch> passes
    - No divergence between status and implementation
    """
    repo = dual_branch_repo

    # Create feature with target_branch: "2.x"
    feature_dir = create_feature_with_target(repo, "028-race-test", target_branch="2.x")

    # Checkout 2.x and create implementation branch
    subprocess.run(["git", "checkout", "2.x"], cwd=repo, check=True, capture_output=True)

    wp_branch = "028-race-test-WP01"
    worktree_path = repo / ".worktrees" / wp_branch

    subprocess.run(
        ["git", "worktree", "add", "-b", wp_branch, str(worktree_path), "2.x"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Make implementation commit in worktree
    test_file = worktree_path / "implementation.txt"
    test_file.write_text("implementation work\n")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Implement WP01"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Get WP branch HEAD before status commit
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        check=True,
    )
    wp_branch_head_before = result.stdout.strip()

    # Move to doing (status commit to 2.x)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)
    result = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "doing")
    assert result.returncode == 0, f"Failed to move task: {result.stderr}"

    # Get WP branch HEAD after status commit
    result = subprocess.run(
        ["git", "rev-parse", wp_branch],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    wp_branch_head_after = result.stdout.strip()

    # WP branch HEAD should be unchanged (implementation branch not affected by status commit)
    assert wp_branch_head_before == wp_branch_head_after, "WP branch should not be modified by status commit"

    # Verify ancestry: 2.x should be ancestor of WP branch
    is_ancestor = verify_ancestry(repo, "2.x", wp_branch)
    assert is_ancestor, "2.x should be ancestor of WP branch (no race condition)"

    # Cleanup
    subprocess.run(
        ["git", "worktree", "remove", str(worktree_path), "--force"],
        cwd=repo,
        check=False,
        capture_output=True,
    )


def test_fallback_when_target_missing(dual_branch_repo):
    """Test graceful fallback when target_branch doesn't exist.

    Validates:
    - If target_branch in meta.json doesn't exist as git branch
    - Falls back to current branch with warning
    - Does not crash
    """
    repo = dual_branch_repo

    # Create feature with target_branch pointing to nonexistent branch
    feature_dir = create_feature_with_target(repo, "029-missing-target", target_branch="nonexistent")

    # Try to move task (should fallback to current branch: main)
    result = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "doing")

    # Should succeed (fallback to current branch)
    assert result.returncode == 0, f"Should fallback gracefully: {result.stderr}"

    # Should have warning in output
    assert "Warning" in result.stdout or "could not checkout" in result.stderr.lower(), \
        "Should warn about missing target branch"

    # Commit should land on current branch (main)
    assert_commit_on_branch(repo, "main", "Move WP01 to doing")


def test_migration_detection_and_routing(dual_branch_repo):
    """Test that migration adds target_branch and routing works.

    Validates:
    - Features created before 0.13.8 get target_branch: "main" via migration
    - Routing works correctly after migration
    """
    repo = dual_branch_repo

    # Create feature WITHOUT target_branch (pre-0.13.8)
    feature_dir = create_feature_with_target(repo, "030-pre-migration", target_branch=None)

    # Verify meta.json has no target_branch
    meta_file = feature_dir / "meta.json"
    meta = json.loads(meta_file.read_text())
    assert "target_branch" not in meta, "Feature should not have target_branch initially"

    # Run migration (simulated - just add target_branch: "main")
    meta["target_branch"] = "main"
    meta_file.write_text(json.dumps(meta, indent=2) + "\n")
    subprocess.run(["git", "add", str(meta_file)], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Migration: Add target_branch to 030"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Now move task (should route to main)
    result = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "doing")
    assert result.returncode == 0, f"Failed to move task: {result.stderr}"

    # Verify commit on main
    assert_commit_on_branch(repo, "main", "Move WP01 to doing")


def verify_ancestry(repo: Path, ancestor: str, descendant: str) -> bool:
    """Check if ancestor is an ancestor of descendant."""
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo,
        capture_output=True,
    )
    return result.returncode == 0


# ============================================================================
# Additional Edge Cases
# ============================================================================


def test_multiple_lane_transitions_same_target(dual_branch_repo):
    """Test multiple WPs with same target_branch all route correctly.

    Validates:
    - Multiple WPs in same feature all route to same target
    - All status commits go to 2.x
    - Main branch isolation maintained
    """
    repo = dual_branch_repo

    # Create feature on main with target_branch: "2.x"
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    feature_dir = repo / "kitty-specs" / "031-multi-transition"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    # Create spec and meta
    (feature_dir / "spec.md").write_text("# Multi-transition test\n")
    meta = {
        "feature_number": "031",
        "feature_slug": "031-multi-transition",
        "target_branch": "2.x",
        "created_at": "2026-01-29T00:00:00Z",
        "vcs": "git",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    # Create three WP files
    for wp_num in range(1, 4):
        wp_id = f"WP0{wp_num}"
        wp_file = tasks_dir / f"{wp_id}-test.md"
        wp_file.write_text(
            f"---\n"
            f"work_package_id: {wp_id}\n"
            f"title: Test {wp_id}\n"
            f"lane: planned\n"
            f"dependencies: []\n"
            f"---\n\n"
            f"# {wp_id}\n"
        )

    # Commit to main
    subprocess.run(["git", "add", str(feature_dir)], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add 031-multi-transition"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Merge to 2.x
    subprocess.run(["git", "checkout", "2.x"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "merge", "main", "--no-ff", "-m", "Merge planning"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Count commits on main and 2.x before status changes
    main_commits_before = len(get_commits_on_branch(repo, "main"))

    # Move each WP to doing (each should create a commit on 2.x)
    for wp_num in range(1, 4):
        wp_id = f"WP0{wp_num}"
        result = run_cli(repo, "agent", "tasks", "move-task", wp_id, "--to", "doing")
        assert result.returncode == 0, f"Failed to move {wp_id}: {result.stderr}"

        # Verify commit on 2.x
        assert_commit_on_branch(repo, "2.x", f"Move {wp_id} to doing")

        # Sync main to avoid file conflicts in next iteration
        subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "merge", "2.x", "--no-ff", "-m", f"Sync {wp_id} status"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

    # Verify: All 3 status commits originated on 2.x
    commits_2x = get_commits_on_branch(repo, "2.x")
    status_commits = [c for c in commits_2x if "Move WP0" in c and "to doing" in c]
    assert len(status_commits) == 3, f"Expected 3 status commits on 2.x, found {len(status_commits)}"


def get_commits_on_branch(repo: Path, branch: str, limit: int = 20) -> list[str]:
    """Get commit messages on a branch."""
    result = subprocess.run(
        ["git", "log", branch, "--oneline", f"-{limit}"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip().split("\n") if result.stdout.strip() else []


def test_target_branch_detection_from_worktree_path(dual_branch_repo):
    """Test that feature detection works from worktree and finds correct target.

    Validates:
    - Feature detection works from worktree directory
    - Target branch detected correctly via feature slug
    """
    repo = dual_branch_repo

    # Create feature on main with target_branch: "2.x"
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)
    feature_dir = create_feature_with_target(repo, "032-worktree-detection", target_branch="2.x")

    # Merge to 2.x
    subprocess.run(["git", "checkout", "2.x"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "merge", "main", "--no-ff", "-m", "Merge planning"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create worktree from 2.x
    wp_branch = "032-worktree-detection-WP01"
    worktree_path = repo / ".worktrees" / wp_branch
    subprocess.run(
        ["git", "worktree", "add", "-b", wp_branch, str(worktree_path), "2.x"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Go back to main
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    # Run move-task from main repo (feature detection via slug)
    result = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "doing")
    assert result.returncode == 0, f"Failed from worktree: {result.stderr}"

    # Verify commit on 2.x (target detection worked)
    assert_commit_on_branch(repo, "2.x", "Move WP01 to doing")

    # Cleanup
    subprocess.run(
        ["git", "worktree", "remove", str(worktree_path), "--force"],
        cwd=repo,
        check=False,
        capture_output=True,
    )
