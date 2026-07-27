"""Integration tests for planning workflow (specify → plan → tasks)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def test_project(tmp_path):
    """Create a minimal test project with spec-kitty initialized."""
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)

    # Create minimal .kittify structure
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    # Create metadata.yaml
    (kittify_dir / "metadata.yaml").write_text("version: 0.11.0\n")

    # Create memory directory and constitution
    memory_dir = kittify_dir / "memory"
    memory_dir.mkdir()
    (memory_dir / "constitution.md").write_text("# Constitution\nTest constitution")

    # Create AGENTS.md
    (kittify_dir / "AGENTS.md").write_text("# Agents\nTest agents")

    # Create templates directory
    templates_dir = kittify_dir / "templates"
    templates_dir.mkdir()

    # Create spec template
    (templates_dir / "spec-template.md").write_text("""# Feature Specification

## Overview
Template content
""")

    # Create plan template
    (templates_dir / "plan-template.md").write_text("""# Implementation Plan

## Technical Context
Template content
""")

    # Create task prompt template
    (templates_dir / "task-prompt-template.md").write_text("""---
work_package_id: "{{WP_ID}}"
title: "{{TITLE}}"
lane: "planned"
dependencies: []
subtasks: []
---

# Work Package Prompt
Template content
""")

    # Create kitty-specs directory
    (tmp_path / "kitty-specs").mkdir()

    # Initial commit
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True, capture_output=True)

    return tmp_path


def test_planning_workflow_no_worktrees(test_project):
    """Test complete planning workflow creates artifacts in main without worktrees."""
    repo_root = test_project

    # Step 1: Create feature
    result = subprocess.run(
        ["spec-kitty", "agent", "feature", "create-feature", "test-feature", "--json"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    feature_data = json.loads(result.stdout)
    feature_slug = feature_data["feature"]
    feature_dir = Path(feature_data["feature_dir"])

    # Verify feature directory created in main repo
    assert feature_dir.exists()
    assert "kitty-specs" in feature_dir.parts
    assert feature_dir.name.startswith("001-")

    # Verify spec.md exists and was committed
    spec_file = feature_dir / "spec.md"
    assert spec_file.exists()

    # Check git log for spec commit
    log_result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    assert "Add spec for feature" in log_result.stdout

    # Verify NO worktree created
    worktrees_dir = repo_root / ".worktrees"
    if worktrees_dir.exists():
        # Should be empty or only contain workspace-per-WP worktrees (not feature worktree)
        feature_worktree = worktrees_dir / feature_slug
        assert not feature_worktree.exists(), "Feature worktree should not be created"

    # Step 2: Setup plan
    result = subprocess.run(
        ["spec-kitty", "agent", "feature", "setup-plan", "--json"],
        cwd=feature_dir,  # Run from feature directory
        capture_output=True,
        text=True,
        check=True
    )
    plan_data = json.loads(result.stdout)
    plan_file = Path(plan_data["plan_file"])

    # Verify plan.md exists and was committed
    assert plan_file.exists()
    assert plan_file == feature_dir / "plan.md"

    # Check git log for plan commit
    log_result = subprocess.run(
        ["git", "log", "--oneline", "-2"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    assert "Add plan for feature" in log_result.stdout

    # Still no worktree
    if worktrees_dir.exists():
        assert not (worktrees_dir / feature_slug).exists()

    # Step 3: Generate tasks manually (simulate LLM)
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)

    # Create tasks.md with dependencies
    tasks_md = feature_dir / "tasks.md"
    tasks_md.write_text("""# Work Packages

## Work Package WP01: Foundation

**Goal**: Setup infrastructure
**Dependencies**: None

### Included Subtasks
- T001 Create database schema

---

## Work Package WP02: API Implementation

**Goal**: Build REST API
**Dependencies**: Depends on WP01

### Included Subtasks
- T002 Create API endpoints
- T003 Add authentication

---

## Work Package WP03: UI Components

**Goal**: Build frontend
**Dependencies**: Depends on WP02

### Included Subtasks
- T004 Create React components
""")

    # Create WP files without dependencies (simulate LLM output)
    wp01_file = tasks_dir / "WP01-foundation.md"
    wp01_file.write_text("""---
work_package_id: "WP01"
title: "Foundation"
lane: "planned"
subtasks: ["T001"]
---

# WP01 - Foundation
Implementation details
""")

    wp02_file = tasks_dir / "WP02-api.md"
    wp02_file.write_text("""---
work_package_id: "WP02"
title: "API Implementation"
lane: "planned"
subtasks: ["T002", "T003"]
---

# WP02 - API
Implementation details
""")

    wp03_file = tasks_dir / "WP03-ui.md"
    wp03_file.write_text("""---
work_package_id: "WP03"
title: "UI Components"
lane: "planned"
subtasks: ["T004"]
---

# WP03 - UI
Implementation details
""")

    # Step 4: Run finalize-tasks to parse dependencies and commit
    result = subprocess.run(
        ["spec-kitty", "agent", "feature", "finalize-tasks", "--json"],
        cwd=feature_dir,
        capture_output=True,
        text=True,
        check=True
    )
    finalize_data = json.loads(result.stdout)
    assert finalize_data["result"] == "success"

    # Verify dependencies were added to frontmatter
    wp01_content = wp01_file.read_text()
    assert "dependencies: []" in wp01_content or "dependencies:\n  []" in wp01_content or "dependencies: [ ]" in wp01_content

    wp02_content = wp02_file.read_text()
    assert "WP01" in wp02_content  # Should have dependency on WP01

    wp03_content = wp03_file.read_text()
    assert "WP02" in wp03_content  # Should have dependency on WP02

    # Verify tasks committed to main
    log_result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    assert "Add tasks for feature" in log_result.stdout

    # Final verification: No WP worktrees created
    worktrees_dir = repo_root / ".worktrees"
    if worktrees_dir.exists():
        wp_worktrees = list(worktrees_dir.glob("*-WP*"))
        assert len(wp_worktrees) == 0, "No WP worktrees should exist after planning"


def test_circular_dependency_detection(test_project):
    """Test that finalize-tasks detects and rejects circular dependencies."""
    repo_root = test_project

    # Create feature
    result = subprocess.run(
        ["spec-kitty", "agent", "feature", "create-feature", "circular-test", "--json"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    feature_data = json.loads(result.stdout)
    feature_dir = Path(feature_data["feature_dir"])

    # Create tasks.md with circular dependency
    tasks_md = feature_dir / "tasks.md"
    tasks_md.write_text("""# Work Packages

## Work Package WP01: First
Dependencies: WP02

## Work Package WP02: Second
Dependencies: WP01
""")

    # Create WP files
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)

    for wp_num in ["01", "02"]:
        wp_file = tasks_dir / f"WP{wp_num}-task.md"
        wp_file.write_text(f"""---
work_package_id: "WP{wp_num}"
title: "Task {wp_num}"
lane: "planned"
---
# Content
""")

    # Run finalize-tasks - should fail
    result = subprocess.run(
        ["spec-kitty", "agent", "feature", "finalize-tasks", "--json"],
        cwd=feature_dir,
        capture_output=True,
        text=True,
        check=False  # Expect failure
    )

    # Should fail due to circular dependency
    assert result.returncode != 0
    output = json.loads(result.stdout)
    assert "error" in output
    assert "circular" in output["error"].lower() or "cycle" in str(output).lower()
