"""Integration tests for implement command with multi-parent dependencies.

Tests the complete workflow:
1. Create feature with WPs having multi-parent dependencies
2. Run spec-kitty implement for multi-parent WP
3. Verify auto-merge base creation
4. Verify workspace created with correct base
5. Verify frontmatter and context tracking
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.cli.commands.implement import implement
from specify_cli.frontmatter import read_frontmatter
from specify_cli.workspace_context import load_context


@pytest.fixture
def feature_repo(tmp_path: Path) -> Path:
    """Create a repository with feature structure and multi-parent dependencies."""
    repo = tmp_path / "test-project"
    repo.mkdir()

    # Initialize git
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

    # Create main branch with initial commit
    (repo / "README.md").write_text("# Test Project\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create .kittify structure
    kittify = repo / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("vcs: git\n")
    (kittify / "metadata.yaml").write_text("version: 0.11.2\n")

    # Create feature structure
    feature_dir = repo / "kitty-specs" / "010-multi-parent-test"
    feature_dir.mkdir(parents=True)

    # Create meta.json
    meta = {
        "feature_number": "010",
        "feature_slug": "010-multi-parent-test",
        "vcs": "git",
        "created_at": "2026-01-23T10:00:00Z",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    # Create tasks directory
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()

    # Create WP files
    # WP01: No dependencies
    wp01_content = """---
work_package_id: WP01
title: Database Setup
lane: planned
dependencies: []
---

## Tasks
- Set up database schema
"""
    (tasks_dir / "WP01-database.md").write_text(wp01_content)

    # WP02: Depends on WP01
    wp02_content = """---
work_package_id: WP02
title: User API
lane: planned
dependencies:
  - WP01
---

## Tasks
- Implement user endpoints
"""
    (tasks_dir / "WP02-user-api.md").write_text(wp02_content)

    # WP03: Depends on WP01
    wp03_content = """---
work_package_id: WP03
title: Auth API
lane: planned
dependencies:
  - WP01
---

## Tasks
- Implement auth endpoints
"""
    (tasks_dir / "WP03-auth-api.md").write_text(wp03_content)

    # WP04: Depends on WP02 AND WP03 (multi-parent!)
    wp04_content = """---
work_package_id: WP04
title: Admin Dashboard
lane: planned
dependencies:
  - WP02
  - WP03
---

## Tasks
- Build admin UI using user and auth APIs
"""
    (tasks_dir / "WP04-admin-dashboard.md").write_text(wp04_content)

    # Commit feature structure to main
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add feature structure"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    return repo


def test_implement_linear_dependency_chain(feature_repo: Path, monkeypatch):
    """Test implementing WP01 → WP02 → WP03 (linear chain, no auto-merge)."""
    monkeypatch.chdir(feature_repo)

    # Implement WP01 (no dependencies)
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()

    # WP01
    result = runner.invoke(app, ["implement", "WP01"])
    assert result.exit_code == 0
    assert "010-multi-parent-test-WP01" in result.stdout
    assert (feature_repo / ".worktrees" / "010-multi-parent-test-WP01").exists()

    # Verify frontmatter updated with base_branch
    wp01_file = feature_repo / "kitty-specs" / "010-multi-parent-test" / "tasks" / "WP01-database.md"
    fm01, _ = read_frontmatter(wp01_file)
    assert fm01["base_branch"] == "main"
    assert "base_commit" in fm01
    assert "created_at" in fm01

    # Verify context created
    ctx01 = load_context(feature_repo, "010-multi-parent-test-WP01")
    assert ctx01 is not None
    assert ctx01.wp_id == "WP01"
    assert ctx01.base_branch == "main"
    assert ctx01.dependencies == []

    # Make a commit in WP01 workspace
    wp01_workspace = feature_repo / ".worktrees" / "010-multi-parent-test-WP01"
    (wp01_workspace / "database.sql").write_text("CREATE TABLE users;\n")
    subprocess.run(["git", "add", "."], cwd=wp01_workspace, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add database schema"],
        cwd=wp01_workspace,
        check=True,
        capture_output=True,
    )

    # WP02 (depends on WP01)
    result = runner.invoke(app, ["implement", "WP02", "--base", "WP01"])
    assert result.exit_code == 0
    assert "010-multi-parent-test-WP02" in result.stdout

    # Verify WP02 base tracking
    wp02_file = feature_repo / "kitty-specs" / "010-multi-parent-test" / "tasks" / "WP02-user-api.md"
    fm02, _ = read_frontmatter(wp02_file)
    assert fm02["base_branch"] == "010-multi-parent-test-WP01"
    assert "base_commit" in fm02

    # Verify WP02 has database.sql from WP01
    wp02_workspace = feature_repo / ".worktrees" / "010-multi-parent-test-WP02"
    assert (wp02_workspace / "database.sql").exists()


def test_implement_multi_parent_auto_merge(feature_repo: Path, monkeypatch):
    """Test implementing WP04 which depends on both WP02 and WP03 (auto-merge)."""
    monkeypatch.chdir(feature_repo)

    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()

    # Implement WP01
    result = runner.invoke(app, ["implement", "WP01"])
    assert result.exit_code == 0

    wp01_workspace = feature_repo / ".worktrees" / "010-multi-parent-test-WP01"
    (wp01_workspace / "database.sql").write_text("CREATE TABLE users;\n")
    subprocess.run(["git", "add", "."], cwd=wp01_workspace, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add database"],
        cwd=wp01_workspace,
        check=True,
        capture_output=True,
    )

    # Implement WP02
    result = runner.invoke(app, ["implement", "WP02", "--base", "WP01"])
    assert result.exit_code == 0

    wp02_workspace = feature_repo / ".worktrees" / "010-multi-parent-test-WP02"
    (wp02_workspace / "user-api.py").write_text("# User API\n")
    subprocess.run(["git", "add", "."], cwd=wp02_workspace, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add user API"],
        cwd=wp02_workspace,
        check=True,
        capture_output=True,
    )

    # Implement WP03
    result = runner.invoke(app, ["implement", "WP03", "--base", "WP01"])
    assert result.exit_code == 0

    wp03_workspace = feature_repo / ".worktrees" / "010-multi-parent-test-WP03"
    (wp03_workspace / "auth-api.py").write_text("# Auth API\n")
    subprocess.run(["git", "add", "."], cwd=wp03_workspace, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add auth API"],
        cwd=wp03_workspace,
        check=True,
        capture_output=True,
    )

    # Implement WP04 (multi-parent: depends on WP02 AND WP03)
    # Should auto-detect and create merge base
    result = runner.invoke(app, ["implement", "WP04"])
    assert result.exit_code == 0
    assert "Multi-parent dependency detected" in result.stdout
    assert "Auto-creating merge base" in result.stdout
    assert "010-multi-parent-test-WP04" in result.stdout

    # Verify workspace created
    wp04_workspace = feature_repo / ".worktrees" / "010-multi-parent-test-WP04"
    assert wp04_workspace.exists()

    # Verify WP04 frontmatter has merge base branch
    wp04_file = feature_repo / "kitty-specs" / "010-multi-parent-test" / "tasks" / "WP04-admin-dashboard.md"
    fm04, _ = read_frontmatter(wp04_file)
    assert fm04["base_branch"] == "010-multi-parent-test-WP04-merge-base"
    assert "base_commit" in fm04
    assert fm04["dependencies"] == ["WP02", "WP03"]

    # Verify context indicates multi-parent merge
    ctx04 = load_context(feature_repo, "010-multi-parent-test-WP04")
    assert ctx04 is not None
    assert ctx04.wp_id == "WP04"
    assert ctx04.base_branch == "010-multi-parent-test-WP04-merge-base"
    assert set(ctx04.dependencies) == {"WP02", "WP03"}
    assert ctx04.created_by == "implement-command-multi-parent-merge"

    # Verify WP04 workspace has files from BOTH WP02 and WP03
    assert (wp04_workspace / "database.sql").exists()  # From WP01 (via both)
    assert (wp04_workspace / "user-api.py").exists()  # From WP02
    assert (wp04_workspace / "auth-api.py").exists()  # From WP03

    # Verify merge base branch exists
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "010-multi-parent-test-WP04-merge-base"],
        cwd=feature_repo,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0


def test_implement_multi_parent_with_conflicts(feature_repo: Path, monkeypatch):
    """Test that auto-merge detects conflicts and reports them clearly."""
    monkeypatch.chdir(feature_repo)

    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()

    # Implement WP01
    result = runner.invoke(app, ["implement", "WP01"])
    assert result.exit_code == 0

    wp01_workspace = feature_repo / ".worktrees" / "010-multi-parent-test-WP01"
    (wp01_workspace / "config.py").write_text("# Config from WP01\n")
    subprocess.run(["git", "add", "."], cwd=wp01_workspace, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add config"],
        cwd=wp01_workspace,
        check=True,
        capture_output=True,
    )

    # Implement WP02 with conflicting change
    result = runner.invoke(app, ["implement", "WP02", "--base", "WP01"])
    assert result.exit_code == 0

    wp02_workspace = feature_repo / ".worktrees" / "010-multi-parent-test-WP02"
    (wp02_workspace / "config.py").write_text("# Config from WP02 (DIFFERENT)\n")
    subprocess.run(["git", "add", "."], cwd=wp02_workspace, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Update config in WP02"],
        cwd=wp02_workspace,
        check=True,
        capture_output=True,
    )

    # Implement WP03 with different conflicting change
    result = runner.invoke(app, ["implement", "WP03", "--base", "WP01"])
    assert result.exit_code == 0

    wp03_workspace = feature_repo / ".worktrees" / "010-multi-parent-test-WP03"
    (wp03_workspace / "config.py").write_text("# Config from WP03 (ALSO DIFFERENT)\n")
    subprocess.run(["git", "add", "."], cwd=wp03_workspace, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Update config in WP03"],
        cwd=wp03_workspace,
        check=True,
        capture_output=True,
    )

    # Implement WP04 - should fail due to conflict
    result = runner.invoke(app, ["implement", "WP04"])
    assert result.exit_code == 1
    assert "Failed to create merge base" in result.stdout
    assert "conflict" in result.stdout.lower()
    assert "config.py" in result.stdout

    # Verify workspace NOT created
    wp04_workspace = feature_repo / ".worktrees" / "010-multi-parent-test-WP04"
    assert not wp04_workspace.exists()

    # Verify temp merge base branch cleaned up
    result_branch = subprocess.run(
        ["git", "rev-parse", "--verify", "010-multi-parent-test-WP04-merge-base"],
        cwd=feature_repo,
        capture_output=True,
        check=False,
    )
    assert result_branch.returncode != 0  # Branch should not exist
