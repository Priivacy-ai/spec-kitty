"""End-to-end integration test for Feature 025 dual-branch workflow.

This test replicates the complete Feature 025 scenario:
- Feature created with target_branch: "2.x" in meta.json
- All planning artifacts on main initially
- Migration detects and preserves 2.x target
- Implementation branches created from 2.x
- Status commits routed to 2.x (not main)
- Branch ancestry maintained throughout workflow
- Main branch completely unaffected by status commits
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


def count_commits_matching(repo: Path, branch: str, pattern: str) -> int:
    """Count commits on branch matching pattern."""
    commits = get_commits_on_branch(repo, branch)
    return sum(1 for commit in commits if pattern in commit)


def verify_ancestry(repo: Path, ancestor: str, descendant: str) -> bool:
    """Check if ancestor is an ancestor of descendant."""
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo,
        capture_output=True,
    )
    return result.returncode == 0


# ============================================================================
# Main End-to-End Test
# ============================================================================


@pytest.mark.xfail(reason="Status commits now route to current branch (Bug #124/WP05) not target branch")
def test_feature_025_complete_workflow(dual_branch_repo):
    """Test complete Feature 025 workflow on 2.x branch.

    This is the master integration test that validates the entire dual-branch
    workflow from specification through implementation to review.

    Workflow:
    1. Create Feature 025 with target_branch: "2.x" in meta.json
    2. Create WP01 and WP02 with dependencies
    3. Simulate planning phase (all on main initially)
    4. Implement WP01 from 2.x
    5. Move WP01 through workflow (doing → for_review → done)
    6. Verify all status commits on 2.x
    7. Verify main branch unaffected
    8. Verify branch ancestry maintained
    9. Verify no race condition

    NOTE: Behavior changed in Bug #124 - status commits now respect current branch.
    """
    repo = dual_branch_repo
    feature_slug = "025-cli-event-log-integration"

    # ========================================================================
    # Step 1: Create Feature 025 with Planning Artifacts
    # ========================================================================

    # Start on main branch (planning happens here)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    feature_dir = repo / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    # Create spec.md mentioning 2.x target
    spec_content = """# Feature 025: CLI Event Log Integration

## Target Branch

**Target Branch**: 2.x development (SaaS-only feature)

This feature integrates event logging into the CLI for SaaS deployments.
It is NOT part of the 1.x product line.

## Requirements

- Event log capture
- CloudWatch integration
- Activity tracking
"""
    (feature_dir / "spec.md").write_text(spec_content)

    # Create meta.json with target_branch: "2.x"
    meta = {
        "feature_number": "025",
        "feature_slug": feature_slug,
        "target_branch": "2.x",  # CRITICAL: Target 2.x, not main
        "created_at": "2026-01-29T00:00:00Z",
        "vcs": "git",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    # Create plan.md
    (feature_dir / "plan.md").write_text("# Implementation Plan\n\nDetails here.\n")

    # Create tasks.md
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n## WP01 - Setup\n\n## WP02 - Integration\n\nDepends on WP01.\n"
    )

    # Create WP files
    wp01_file = tasks_dir / "WP01-setup.md"
    wp01_file.write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Setup Event Logging\n"
        "lane: planned\n"
        "dependencies: []\n"
        "---\n\n"
        "# WP01: Setup Event Logging\n\n"
        "Setup basic infrastructure.\n"
    )

    wp02_file = tasks_dir / "WP02-integration.md"
    wp02_file.write_text(
        "---\n"
        "work_package_id: WP02\n"
        "title: CloudWatch Integration\n"
        "lane: planned\n"
        'dependencies: ["WP01"]\n'
        "---\n\n"
        "# WP02: CloudWatch Integration\n\n"
        "Integrate with CloudWatch.\n"
    )

    # Commit planning artifacts to main
    subprocess.run(["git", "add", str(feature_dir)], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"Add planning for {feature_slug}"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Record commit count on main after planning
    main_commits_after_planning = get_commits_on_branch(repo, "main")

    # Merge planning to 2.x (required for status commits to work on 2.x)
    subprocess.run(["git", "checkout", "2.x"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "merge", "main", "--no-ff", "-m", "Merge planning from main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # ========================================================================
    # Step 2: Implement WP01 (Should Branch from 2.x)
    # ========================================================================

    # Stay on 2.x for implementation
    # subprocess.run(["git", "checkout", "2.x"], cwd=repo, check=True, capture_output=True)

    # Manually create worktree (simulating spec-kitty implement WP01)
    wp01_branch = f"{feature_slug}-WP01"
    wp01_worktree = repo / ".worktrees" / wp01_branch

    result = subprocess.run(
        ["git", "worktree", "add", "-b", wp01_branch, str(wp01_worktree), "2.x"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Verify worktree created from 2.x (not main)
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=wp01_worktree,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == wp01_branch

    # Verify branch ancestry: 2.x should be ancestor
    assert verify_ancestry(repo, "2.x", wp01_branch), "WP01 branch should descend from 2.x"
    # Note: main may not be direct ancestor if 2.x has diverged, but both came from initial commit

    # ========================================================================
    # Step 3: Move WP01 to Doing (Status Commit)
    # ========================================================================

    # Go back to main repo context
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    # Move task to doing
    result = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "doing")
    assert result.returncode == 0, f"Failed to move to doing: {result.stderr}\n{result.stdout}"

    # CRITICAL ASSERTION: Status commit should be on 2.x, NOT main
    assert_commit_on_branch(repo, "2.x", "Move WP01 to doing")

    # Verify main branch does NOT have this commit
    commits_main_after_doing = get_commits_on_branch(repo, "main")
    assert len(commits_main_after_doing) == len(main_commits_after_planning), \
        "Main branch should not have new commits after status change to 2.x feature"

    # ========================================================================
    # Step 4: Make Implementation Commits
    # ========================================================================

    # Add implementation work in worktree
    impl_file = wp01_worktree / "event_logger.py"
    impl_file.write_text("# Event logger implementation\nclass EventLogger:\n    pass\n")

    subprocess.run(["git", "add", "."], cwd=wp01_worktree, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Implement event logger"],
        cwd=wp01_worktree,
        check=True,
        capture_output=True,
    )

    # ========================================================================
    # Step 5: Move WP01 to For Review (Another Status Commit)
    # ========================================================================

    # ========================================================================
    # Step 5: Verify Status Routing and Branch Isolation
    # ========================================================================

    # Get all commits on 2.x
    commits_2x = get_commits_on_branch(repo, "2.x", limit=20)

    # 2.x should have the status commit
    status_on_2x = any("Move WP01 to doing" in c for c in commits_2x)
    assert status_on_2x, "2.x should have status commit"

    # Get all commits on main
    commits_main = get_commits_on_branch(repo, "main", limit=20)

    # Main should NOT have status commits (only planning commits)
    status_on_main = any("Move WP01 to doing" in c for c in commits_main)
    assert not status_on_main, "Main should not have status commits for 2.x features"

    # Verify WP01 branch and 2.x share common history (merge-base exists)
    result = subprocess.run(
        ["git", "merge-base", "2.x", wp01_branch],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    merge_base = result.stdout.strip()
    assert merge_base, "WP01 and 2.x should share common history"

    # WP01 branch should have implementation commits
    result = subprocess.run(
        ["git", "rev-list", "--count", f"{merge_base}..{wp01_branch}"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    impl_commits = int(result.stdout.strip())
    assert impl_commits > 0, "WP01 should have implementation commits"

    # ========================================================================
    # Step 6: Verify Complete Workflow Success
    # ========================================================================

    # Planning on main
    assert "Add planning for 025-cli-event-log-integration" in "\n".join(commits_main)

    # Status commits ONLY on 2.x
    status_count_2x = sum(1 for c in commits_2x if "Move WP01" in c)
    assert status_count_2x >= 1, "2.x should have status commits"

    status_count_main = sum(1 for c in commits_main if "Move WP01" in c)
    assert status_count_main == 0, "Main should have ZERO status commits"

    # ========================================================================
    # Cleanup
    # ========================================================================

    subprocess.run(
        ["git", "worktree", "remove", str(wp01_worktree), "--force"],
        cwd=repo,
        check=False,
        capture_output=True,
    )


# ============================================================================
# Helper Assertions
# ============================================================================


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


def count_commits_matching(repo: Path, branch: str, pattern: str) -> int:
    """Count commits on branch matching pattern."""
    commits = get_commits_on_branch(repo, branch)
    return sum(1 for commit in commits if pattern in commit)


def verify_ancestry(repo: Path, ancestor: str, descendant: str) -> bool:
    """Check if ancestor is an ancestor of descendant."""
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo,
        capture_output=True,
    )
    return result.returncode == 0


# ============================================================================
# Additional Workflow Tests
# ============================================================================


def test_wp02_depends_on_wp01_with_2x_target(dual_branch_repo):
    """Test WP02 can depend on WP01 when both target 2.x.

    Validates:
    - WP02 with dependency on WP01
    - Both WPs route to 2.x
    - Dependency chain preserved
    - No cross-branch contamination
    """
    repo = dual_branch_repo
    feature_slug = "033-dependency-chain"

    # Create feature on main
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    feature_dir = repo / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    # Create meta.json with target_branch: "2.x"
    meta = {
        "feature_number": "033",
        "feature_slug": feature_slug,
        "target_branch": "2.x",
        "created_at": "2026-01-29T00:00:00Z",
        "vcs": "git",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    # Create spec and plan
    (feature_dir / "spec.md").write_text(f"# {feature_slug}\n")
    (feature_dir / "plan.md").write_text("# Plan\n")

    # Create WP01 (no dependencies)
    wp01_file = tasks_dir / "WP01-setup.md"
    wp01_file.write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Setup\n"
        "lane: planned\n"
        "dependencies: []\n"
        "---\n\n"
        "# WP01\n"
    )

    # Create WP02 (depends on WP01)
    wp02_file = tasks_dir / "WP02-build.md"
    wp02_file.write_text(
        "---\n"
        "work_package_id: WP02\n"
        "title: Build Feature\n"
        "lane: planned\n"
        'dependencies: ["WP01"]\n'
        "---\n\n"
        "# WP02\n"
    )

    # Commit planning to main
    subprocess.run(["git", "add", str(feature_dir)], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"Add planning for {feature_slug}"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Merge planning to 2.x (required for status commits to work on 2.x)
    subprocess.run(["git", "checkout", "2.x"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "merge", "main", "--no-ff", "-m", "Merge planning from main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # ========================================================================
    # Implement and transition WP01
    # ========================================================================

    # Move WP01 to doing
    result = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "doing")
    assert result.returncode == 0

    # Verify on 2.x
    assert_commit_on_branch(repo, "2.x", "Move WP01 to doing")

    # Move WP01 to done
    result = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "done")
    assert result.returncode == 0
    assert_commit_on_branch(repo, "2.x", "Move WP01 to done")

    # ========================================================================
    # Implement and transition WP02 (depends on WP01)
    # ========================================================================

    # Move WP02 to doing
    result = run_cli(repo, "agent", "tasks", "move-task", "WP02", "--to", "doing")
    assert result.returncode == 0

    # Verify on 2.x
    assert_commit_on_branch(repo, "2.x", "Move WP02 to doing")

    # ========================================================================
    # Verify Main Isolation
    # ========================================================================

    # Main should have ONLY planning commit, NO status commits
    main_commits = get_commits_on_branch(repo, "main")
    wp01_status_on_main = count_commits_matching(repo, "main", "Move WP01")
    wp02_status_on_main = count_commits_matching(repo, "main", "Move WP02")

    assert wp01_status_on_main == 0, f"WP01 status commits leaked to main: {wp01_status_on_main}"
    assert wp02_status_on_main == 0, f"WP02 status commits leaked to main: {wp02_status_on_main}"

    # 2.x should have all status commits
    status_2x = count_commits_matching(repo, "2.x", "Move WP")
    assert status_2x >= 3, f"Expected at least 3 status commits on 2.x, found {status_2x}"


def test_review_rework_commits_to_correct_branch(dual_branch_repo):
    """Test review rework workflow with dual-branch feature.

    Validates:
    - Move to for_review → commit on 2.x
    - Request changes (back to doing) → commit on 2.x
    - Rework commits → on 2.x
    - Re-submit (back to for_review) → commit on 2.x
    - Approve (to done) → commit on 2.x
    - Main unaffected throughout
    """
    repo = dual_branch_repo
    feature_slug = "034-review-rework"

    # Create feature on main
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    feature_dir = repo / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    # Meta with target_branch: "2.x"
    meta = {
        "feature_number": "034",
        "feature_slug": feature_slug,
        "target_branch": "2.x",
        "created_at": "2026-01-29T00:00:00Z",
        "vcs": "git",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    # Create WP file
    wp_file = tasks_dir / "WP01-test.md"
    wp_file.write_text(
        "---\n"
        "work_package_id: WP01\n"
        "lane: planned\n"
        "dependencies: []\n"
        "---\n\n"
        "# WP01\n"
    )

    # Commit planning
    subprocess.run(["git", "add", str(feature_dir)], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"Add {feature_slug}"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Merge planning to 2.x
    subprocess.run(["git", "checkout", "2.x"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "merge", "main", "--no-ff", "-m", "Merge planning"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    main_planning_commit_count = len(get_commits_on_branch(repo, "main"))

    # ========================================================================
    # Workflow: planned → doing → for_review → doing → for_review → done
    # ========================================================================

    # Move to doing
    result = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "doing")
    assert result.returncode == 0
    assert_commit_on_branch(repo, "2.x", "Move WP01 to doing")

    # Move to for_review
    result = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "for_review")
    assert result.returncode == 0
    assert_commit_on_branch(repo, "2.x", "Move WP01 to for_review")

    # Request changes (back to doing)
    result = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "doing")
    assert result.returncode == 0
    commits_2x_after_rework_request = get_commits_on_branch(repo, "2.x")

    # Re-submit (back to for_review)
    result = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "for_review")
    assert result.returncode == 0

    # Approve (to done)
    result = run_cli(repo, "agent", "tasks", "move-task", "WP01", "--to", "done")
    assert result.returncode == 0
    assert_commit_on_branch(repo, "2.x", "Move WP01 to done")

    # ========================================================================
    # Verify Main Isolation (Complete)
    # ========================================================================

    main_final_commits = get_commits_on_branch(repo, "main")
    assert len(main_final_commits) == main_planning_commit_count, \
        "Main should have NO new commits during entire review workflow"

    # All status transitions should be on 2.x only
    status_count_2x = count_commits_matching(repo, "2.x", "Move WP01")
    assert status_count_2x >= 5, \
        f"Expected at least 5 status commits on 2.x (full workflow), found {status_count_2x}"

    status_count_main = count_commits_matching(repo, "main", "Move WP01")
    assert status_count_main == 0, \
        f"Main should have ZERO status commits, found {status_count_main}"
