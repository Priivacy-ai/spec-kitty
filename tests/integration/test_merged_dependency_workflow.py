"""Integration tests for implementing WPs after dependencies are done.

Simulates real workflow:
1. Implement WP01 (creates worktree on branch feature-WP01)
2. WP01 completes review, lane set to "done"
3. Worktree cleaned up but branch still exists
4. Implement WP02 (depends on WP01)
   - Should branch from WP01's branch (contains WP01's changes)
   - Should NOT error about missing WP01 workspace

Note: "done" means review-complete, NOT merged to target. Per-WP merging to
target happens at feature level via `spec-kitty merge`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def feature_with_done_dependency(test_project: Path, run_cli):
    """Create a feature with WP01 done (review-complete) and WP02 waiting.

    Simulates real workflow where:
    - WP01 was implemented (branch exists with implementation code)
    - WP01 completed review → lane set to "done"
    - WP01 worktree cleaned up, but branch still exists
    - WP02 depends on WP01 (should branch from WP01's branch)

    Note: "done" does NOT mean merged to target. Merging happens at
    feature level via `spec-kitty merge`.
    """
    # Create target branch (2.x)
    subprocess.run(["git", "checkout", "-b", "2.x"], cwd=test_project, check=True)
    subprocess.run(["git", "checkout", "main"], cwd=test_project, check=True)

    # Create feature directory
    feature_slug = "025-cli-event-log-integration"
    feature_dir = test_project / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create meta.json with target_branch
    meta_file = feature_dir / "meta.json"
    meta_file.write_text(
        '{\n'
        '  "spec_number": "025",\n'
        '  "slug": "025-cli-event-log-integration",\n'
        f'  "target_branch": "2.x"\n'
        '}',
        encoding="utf-8"
    )

    # Create WP01 in 'done' lane (review-complete, NOT merged to target)
    wp01_file = tasks_dir / "WP01-event-infrastructure.md"
    wp01_file.write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Event Infrastructure\n"
        "lane: done\n"
        "dependencies: []\n"
        "---\n"
        "# Event Infrastructure\n"
        "\n"
        "Base event system implementation.\n",
        encoding="utf-8"
    )

    # Create WP02 in 'planned' lane (depends on WP01)
    wp02_file = tasks_dir / "WP02-event-logger.md"
    wp02_file.write_text(
        "---\n"
        "work_package_id: WP02\n"
        "title: Event Logger\n"
        "lane: planned\n"
        "dependencies: [WP01]\n"
        "---\n"
        "# Event Logger\n"
        "\n"
        "Uses event infrastructure from WP01.\n",
        encoding="utf-8"
    )

    # Create WP08 in 'planned' lane (also depends on WP01)
    wp08_file = tasks_dir / "WP08-event-cli.md"
    wp08_file.write_text(
        "---\n"
        "work_package_id: WP08\n"
        "title: Event CLI\n"
        "lane: planned\n"
        "dependencies: [WP01]\n"
        "---\n"
        "# Event CLI\n"
        "\n"
        "CLI commands for event system.\n",
        encoding="utf-8"
    )

    # Commit feature files
    subprocess.run(["git", "add", "."], cwd=test_project, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add Feature 025 with WP01 done, WP02/WP08 planned"],
        cwd=test_project,
        check=True
    )

    # Simulate WP01's implementation branch (created during implement, persists after done)
    wp01_branch = f"{feature_slug}-WP01"
    subprocess.run(
        ["git", "checkout", "-b", wp01_branch],
        cwd=test_project, check=True
    )
    (test_project / "src" / "specify_cli" / "events").mkdir(parents=True)
    events_file = test_project / "src" / "specify_cli" / "events" / "__init__.py"
    events_file.write_text(
        '"""Event infrastructure (from WP01)."""\n',
        encoding="utf-8"
    )
    subprocess.run(["git", "add", "."], cwd=test_project, check=True)
    subprocess.run(
        ["git", "commit", "-m", "feat(WP01): Event infrastructure implementation"],
        cwd=test_project,
        check=True
    )
    subprocess.run(["git", "checkout", "main"], cwd=test_project, check=True)

    return test_project


def test_implement_after_single_dependency_done(feature_with_done_dependency, run_cli):
    """Test implementing WP02 after WP01 is done (review-complete).

    Expected:
    - Detects WP01 is in 'done' lane
    - Branches from WP01's branch (contains WP01's implementation)
    - Does NOT error about missing WP01 workspace
    - Creates WP02 workspace successfully
    """
    project = feature_with_done_dependency
    feature_slug = "025-cli-event-log-integration"
    wp01_branch = f"{feature_slug}-WP01"

    # Run implement command for WP02
    result = run_cli(project, "implement", "WP02", "--feature", feature_slug)

    # Should succeed
    assert result.returncode == 0, f"implement failed: {result.stderr}"

    # Should mention branching from WP01's branch (not target)
    output = result.stdout + result.stderr
    assert wp01_branch in output, f"Should mention WP01 branch, got: {output}"
    assert "done" in output.lower(), "Should detect WP01 is done"

    # Should NOT mention "Base workspace WP01 does not exist"
    assert "does not exist" not in output.lower()

    # Verify workspace created
    workspace_path = project / ".worktrees" / f"{feature_slug}-WP02"
    assert workspace_path.exists(), "Workspace should be created"

    # Verify workspace contains WP01's changes (events/ directory from WP01's branch)
    events_dir = workspace_path / "src" / "specify_cli" / "events"
    assert events_dir.exists(), "Should inherit WP01's changes from WP01 branch"


def test_implement_second_dependent_after_done(feature_with_done_dependency, run_cli):
    """Test implementing WP08 after WP01 is done (parallel to WP02).

    Expected:
    - Also detects WP01 is in 'done' lane
    - Branches from WP01's branch independently
    - Creates WP08 workspace successfully
    """
    project = feature_with_done_dependency
    feature_slug = "025-cli-event-log-integration"
    wp01_branch = f"{feature_slug}-WP01"

    # Run implement command for WP08
    result = run_cli(project, "implement", "WP08", "--feature", feature_slug)

    # Should succeed
    assert result.returncode == 0, f"implement failed: {result.stderr}"

    # Should mention branching from WP01's branch
    output = result.stdout + result.stderr
    assert wp01_branch in output, f"Should mention WP01 branch, got: {output}"

    # Verify workspace created
    workspace_path = project / ".worktrees" / f"{feature_slug}-WP08"
    assert workspace_path.exists(), "Workspace should be created"

    # Verify workspace contains WP01's changes
    events_dir = workspace_path / "src" / "specify_cli" / "events"
    assert events_dir.exists(), "Should inherit WP01's changes from WP01 branch"


def test_implement_multi_parent_all_done_creates_merge_base(test_project, run_cli):
    """Test implementing WP04 when all multi-parent dependencies are done.

    Expected:
    - Detects WP01, WP02, WP03 all in 'done' lane
    - Creates merge base from their branches (not from target)
    - Creates WP04 workspace successfully
    """
    # Create feature directory
    feature_slug = "010-workspace-per-wp"
    feature_dir = test_project / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create meta.json (targets main)
    meta_file = feature_dir / "meta.json"
    meta_file.write_text(
        '{\n'
        '  "spec_number": "010",\n'
        '  "slug": "010-workspace-per-wp",\n'
        f'  "target_branch": "main"\n'
        '}',
        encoding="utf-8"
    )

    # Create WP01, WP02, WP03 all in 'done' lane
    for i in range(1, 4):
        wp_file = tasks_dir / f"WP0{i}-component-{i}.md"
        wp_file.write_text(
            f"---\n"
            f"work_package_id: WP0{i}\n"
            f"title: Component {i}\n"
            f"lane: done\n"
            f"dependencies: []\n"
            f"---\n"
            f"# Component {i}\n",
            encoding="utf-8"
        )

    # Create WP04 depending on all three
    wp04_file = tasks_dir / "WP04-integration.md"
    wp04_file.write_text(
        "---\n"
        "work_package_id: WP04\n"
        "title: Integration\n"
        "lane: planned\n"
        "dependencies: [WP01, WP02, WP03]\n"
        "---\n"
        "# Integration\n"
        "\n"
        "Combines all components.\n",
        encoding="utf-8"
    )

    # Commit feature files
    subprocess.run(["git", "add", "."], cwd=test_project, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add Feature 010 with all deps done"],
        cwd=test_project,
        check=True
    )

    # Create WP branches with implementation code (simulating done WPs)
    for i in range(1, 4):
        wp_branch = f"{feature_slug}-WP0{i}"
        subprocess.run(
            ["git", "checkout", "-b", wp_branch],
            cwd=test_project, check=True
        )
        comp_dir = test_project / "src" / f"component_{i}"
        comp_dir.mkdir(parents=True, exist_ok=True)
        (comp_dir / "__init__.py").write_text(
            f'"""Component {i} implementation."""\n',
            encoding="utf-8"
        )
        subprocess.run(["git", "add", "."], cwd=test_project, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"feat(WP0{i}): Component {i} implementation"],
            cwd=test_project, check=True
        )
        subprocess.run(["git", "checkout", "main"], cwd=test_project, check=True)

    # Run implement command for WP04 (should auto-detect multi-parent all done)
    result = run_cli(test_project, "implement", "WP04", "--feature", "010-workspace-per-wp", "--force")

    # Should succeed
    assert result.returncode == 0, f"implement failed: {result.stderr}"

    # Should mention all dependencies are done
    output = result.stdout + result.stderr
    assert "done" in output.lower(), "Should detect all deps done"

    # Verify workspace created
    workspace_path = test_project / ".worktrees" / "010-workspace-per-wp-WP04"
    assert workspace_path.exists(), "Workspace should be created"


def test_implement_in_progress_dependency_uses_workspace(test_project, run_cli):
    """Test implementing WP02 when WP01 is still in progress (regression test).

    Expected:
    - Detects WP01 is in 'doing' lane (NOT merged)
    - Looks for WP01 workspace
    - Errors if workspace missing (expected behavior)
    """
    # Create feature directory
    feature_slug = "025-cli-event-log-integration"
    feature_dir = test_project / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create meta.json
    meta_file = feature_dir / "meta.json"
    meta_file.write_text(
        '{\n'
        '  "spec_number": "025",\n'
        '  "slug": "025-cli-event-log-integration",\n'
        f'  "target_branch": "main"\n'
        '}',
        encoding="utf-8"
    )

    # Create WP01 in 'doing' lane (in-progress, NOT merged)
    wp01_file = tasks_dir / "WP01-event-infrastructure.md"
    wp01_file.write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Event Infrastructure\n"
        "lane: doing\n"
        "dependencies: []\n"
        "---\n"
        "# Event Infrastructure\n",
        encoding="utf-8"
    )

    # Create WP02 depending on WP01
    wp02_file = tasks_dir / "WP02-event-logger.md"
    wp02_file.write_text(
        "---\n"
        "work_package_id: WP02\n"
        "title: Event Logger\n"
        "lane: planned\n"
        "dependencies: [WP01]\n"
        "---\n"
        "# Event Logger\n",
        encoding="utf-8"
    )

    # Commit feature files
    subprocess.run(["git", "add", "."], cwd=test_project, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add Feature 025 with WP01 in-progress"],
        cwd=test_project,
        check=True
    )

    # Run implement command for WP02 (should error - WP01 workspace doesn't exist)
    result = run_cli(test_project, "implement", "WP02", "--feature", "025-cli-event-log-integration")

    # Should fail (workspace doesn't exist)
    assert result.returncode != 0, "Should error when in-progress dependency workspace missing"

    # Should mention WP01 workspace doesn't exist
    assert "does not exist" in result.stderr or "does not exist" in result.stdout, "Should error about missing workspace"
    assert "WP01" in result.stderr or "WP01" in result.stdout, "Should mention WP01"
