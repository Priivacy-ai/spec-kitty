"""Integration tests for two-branch strategy (ADR-12)."""

import json
import subprocess

import pytest

pytestmark = pytest.mark.git_repo


@pytest.fixture
def git_repo_with_2x_mission(tmp_path):
    """Create a git repo with a mission targeting 2.x branch."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Initialize git repo with explicit main branch (CI may default to master)
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True)

    # Create .kittify marker
    (repo / ".kittify").mkdir()
    (repo / ".kittify" / ".gitkeep").write_text("")

    # Create mission with target_branch = "2.x"
    mission_dir = repo / "kitty-specs" / "025-test-mission"
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    (mission_dir / "meta.json").write_text(json.dumps({
        "mission_number": "025",
        "slug": "025-test-mission",
        "target_branch": "2.x",
        "mission": "software-dev"
    }))

    # Create WP01 task
    (tasks_dir / "WP01-test.md").write_text("""---
work_package_id: "WP01"
title: "Test Task"
lane: "planned"
dependencies: []
---
# Test
""")

    # Commit to main
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    # Create 2.x branch
    subprocess.run(["git", "branch", "2.x"], cwd=repo, check=True)

    return repo


def test_target_branch_detection_from_meta_json(git_repo_with_2x_mission):
    """Bug #1: Should use target_branch from meta.json for validation."""
    from specify_cli.core.mission_detection import get_mission_target_branch

    repo = git_repo_with_2x_mission
    target = get_mission_target_branch(repo, "025-test-mission")

    assert target == "2.x", "Should read target_branch from meta.json"


def test_target_branch_defaults_to_main_for_legacy(git_repo_with_2x_mission):
    """Bug #1: Should default to main for missions without target_branch."""
    from specify_cli.core.mission_detection import get_mission_target_branch

    repo = git_repo_with_2x_mission

    # Create legacy mission without target_branch
    mission_dir = repo / "kitty-specs" / "024-legacy"
    mission_dir.mkdir()
    (mission_dir / "meta.json").write_text(json.dumps({
        "mission_number": "024",
        "slug": "024-legacy",
        "mission": "software-dev"
        # No target_branch field
    }))

    target = get_mission_target_branch(repo, "024-legacy")

    assert target == "main", "Should default to main for legacy missions"
