"""Integration tests for implementing WPs after dependencies are merged (ADR-18).

Simulates real workflow:
1. Implement WP01
2. Merge WP01 to target branch (2.x)
3. Clean up WP01 workspace (per ADR-9)
4. Implement WP02 (depends on WP01)
   - Should branch from 2.x (contains WP01's changes)
   - Should NOT error about missing WP01 workspace

This validates the fix in ADR-18 (Auto-Detect Merged Single-Parent Dependencies).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def feature_with_merged_dependency(test_project: Path, run_cli):
    """Create a feature with WP01 merged and WP02 waiting to be implemented.

    Simulates Feature 025 scenario where:
    - WP01 is merged to 2.x branch
    - WP01 workspace is cleaned up
    - WP02 depends on WP01 (should branch from 2.x)
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
        '{\n  "spec_number": "025",\n  "slug": "025-cli-event-log-integration",\n  "target_branch": "2.x"\n}',
        encoding="utf-8",
    )

    # Create WP01 in 'done' lane (merged)
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
        encoding="utf-8",
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
        encoding="utf-8",
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
        encoding="utf-8",
    )

    # Commit feature files
    subprocess.run(["git", "add", "."], cwd=test_project, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add Feature 025 with WP01 done, WP02/WP08 planned"], cwd=test_project, check=True
    )

    # Simulate WP01 merged to 2.x
    subprocess.run(["git", "checkout", "2.x"], cwd=test_project, check=True)
    (test_project / "src" / "specify_cli" / "events").mkdir(parents=True)
    events_file = test_project / "src" / "specify_cli" / "events" / "__init__.py"
    events_file.write_text('"""Event infrastructure (from WP01)."""\n', encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=test_project, check=True)
    subprocess.run(["git", "commit", "-m", "Merge WP01: Event infrastructure"], cwd=test_project, check=True)
    subprocess.run(["git", "checkout", "main"], cwd=test_project, check=True)

    # Merge 2.x changes to main (keep both in sync)
    subprocess.run(["git", "merge", "2.x", "--no-ff", "-m", "Merge 2.x to main"], cwd=test_project, check=True)

    return test_project


def test_implement_after_single_dependency_merged(feature_with_merged_dependency, run_cli):
    """Test implementing WP02 after WP01 is merged.

    Expected:
    - Detects WP01 is in 'done' lane
    - Branches from 2.x (contains WP01's changes)
    - Does NOT error about missing WP01 workspace
    - Creates WP02 workspace successfully
    """
    project = feature_with_merged_dependency

    # Run implement command for WP02
    result = run_cli(project, "implement", "WP02", "--feature", "025-cli-event-log-integration")

    # Should succeed
    assert result.returncode == 0, f"implement failed: {result.stderr}"

    # Should mention branching from target (2.x)
    assert "2.x" in result.stdout or "2.x" in result.stderr, "Should mention target branch"
    assert "done (merged)" in result.stdout or "done (merged)" in result.stderr, "Should detect WP01 is merged"

    # Should NOT mention "Base workspace WP01 does not exist"
    assert "does not exist" not in result.stdout.lower()
    assert "does not exist" not in result.stderr.lower()

    # Verify workspace created
    workspace_path = project / ".worktrees" / "025-cli-event-log-integration-WP02"
    assert workspace_path.exists(), "Workspace should be created"

    # Verify workspace contains WP01's changes (events/ directory from 2.x)
    events_dir = workspace_path / "src" / "specify_cli" / "events"
    assert events_dir.exists(), "Should inherit WP01's changes from 2.x"


def test_implement_second_dependent_after_merge(feature_with_merged_dependency, run_cli):
    """Test implementing WP08 after WP01 is merged (parallel to WP02).

    Expected:
    - Also detects WP01 is in 'done' lane
    - Branches from 2.x independently
    - Creates WP08 workspace successfully
    """
    project = feature_with_merged_dependency

    # Run implement command for WP08
    result = run_cli(project, "implement", "WP08", "--feature", "025-cli-event-log-integration")

    # Should succeed
    assert result.returncode == 0, f"implement failed: {result.stderr}"

    # Should mention branching from target (2.x)
    assert "2.x" in result.stdout or "2.x" in result.stderr, "Should mention target branch"

    # Verify workspace created
    workspace_path = project / ".worktrees" / "025-cli-event-log-integration-WP08"
    assert workspace_path.exists(), "Workspace should be created"

    # Verify workspace contains WP01's changes
    events_dir = workspace_path / "src" / "specify_cli" / "events"
    assert events_dir.exists(), "Should inherit WP01's changes from 2.x"


def test_implement_multi_parent_all_done_uses_target(test_project, run_cli):
    """Test implementing WP04 when all multi-parent dependencies are done.

    Expected:
    - Detects WP01, WP02, WP03 all in 'done' lane
    - Branches from main (optimization, skips merge base)
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
        '{\n  "spec_number": "010",\n  "slug": "010-workspace-per-wp",\n  "target_branch": "main"\n}', encoding="utf-8"
    )

    # Create WP01, WP02, WP03 all in 'done' lane
    for i in range(1, 4):
        wp_file = tasks_dir / f"WP0{i}-component-{i}.md"
        wp_file.write_text(
            f"---\nwork_package_id: WP0{i}\ntitle: Component {i}\nlane: done\ndependencies: []\n---\n# Component {i}\n",
            encoding="utf-8",
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
        encoding="utf-8",
    )

    # Commit feature files
    subprocess.run(["git", "add", "."], cwd=test_project, check=True)
    subprocess.run(["git", "commit", "-m", "Add Feature 010 with all deps done"], cwd=test_project, check=True)

    # Run implement command for WP04 (should auto-detect multi-parent all done)
    result = run_cli(test_project, "implement", "WP04", "--feature", "010-workspace-per-wp", "--force")

    # Should succeed
    assert result.returncode == 0, f"implement failed: {result.stderr}"

    # Should mention all dependencies are done
    assert "done (merged)" in result.stdout or "done (merged)" in result.stderr, "Should detect all deps merged"
    assert "main" in result.stdout or "main" in result.stderr, "Should mention target branch"

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
        '{\n  "spec_number": "025",\n  "slug": "025-cli-event-log-integration",\n  "target_branch": "main"\n}',
        encoding="utf-8",
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
        encoding="utf-8",
    )

    # Create WP02 depending on WP01
    wp02_file = tasks_dir / "WP02-event-logger.md"
    wp02_file.write_text(
        "---\nwork_package_id: WP02\ntitle: Event Logger\nlane: planned\ndependencies: [WP01]\n---\n# Event Logger\n",
        encoding="utf-8",
    )

    # Commit feature files
    subprocess.run(["git", "add", "."], cwd=test_project, check=True)
    subprocess.run(["git", "commit", "-m", "Add Feature 025 with WP01 in-progress"], cwd=test_project, check=True)

    # Run implement command for WP02 (should error - WP01 workspace doesn't exist)
    result = run_cli(test_project, "implement", "WP02", "--feature", "025-cli-event-log-integration")

    # Should fail (workspace doesn't exist)
    assert result.returncode != 0, "Should error when in-progress dependency workspace missing"

    # Should mention WP01 workspace doesn't exist
    assert "does not exist" in result.stderr or "does not exist" in result.stdout, (
        "Should error about missing workspace"
    )
    assert "WP01" in result.stderr or "WP01" in result.stdout, "Should mention WP01"
