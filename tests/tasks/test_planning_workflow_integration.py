"""Integration tests for planning workflow in main repository (v0.11.0+).

Tests that /spec-kitty.specify, /spec-kitty.plan, and /spec-kitty.tasks workflows
work correctly in main repository WITHOUT creating worktrees.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.git_repo

def test_create_feature_in_main_no_worktree(test_project: Path, run_cli) -> None:
    """Test that create command works in main without creating worktree."""
    # Run create command
    result = run_cli(
        test_project,
        "agent",
        "mission",
        "create",
        "test-planning-workflow",
        "--json",
    )

    assert result.returncode == 0, f"create failed: {result.stderr}"

    # Verify feature directory created in main repo
    feature_dir = test_project / "kitty-specs" / "001-test-planning-workflow"
    assert feature_dir.exists(), "Feature directory not created in main repo"
    assert (feature_dir / "spec.md").exists(), "spec.md not created"
    assert (feature_dir / "tasks").is_dir(), "tasks/ directory not created"
    assert (feature_dir / "checklists").is_dir(), "checklists/ directory not created"
    assert (feature_dir / "research").is_dir(), "research/ directory not created"

    # Verify NO worktree was created
    worktree_dir = test_project / ".worktrees" / "001-test-planning-workflow"
    assert not worktree_dir.exists(), "Worktree should NOT be created during feature creation"

    # Verify spec.md was committed to main
    log_result = subprocess.run(
        ["git", "log", "--oneline", "-2"],
        cwd=test_project,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "spec" in log_result.stdout.lower(), "spec.md should be committed to main"

def test_setup_plan_in_main(test_project: Path, run_cli) -> None:
    """Test that setup-plan command works in main repo and commits plan.md."""
    # First create a mission
    run_cli(
        test_project,
        "agent",
        "mission",
        "create",
        "plan-test",
        "--json",
    )

    feature_dir = test_project / "kitty-specs" / "001-plan-test"

    # Create a minimal plan template for testing
    plan_template_dir = test_project / ".kittify" / "templates"
    plan_template_dir.mkdir(parents=True, exist_ok=True)
    plan_template = plan_template_dir / "plan-template.md"
    plan_template.write_text(
        "# Implementation Plan\n\nThis is a test plan template.\n",
        encoding="utf-8"
    )

    # Run setup-plan command
    result = run_cli(
        test_project,
        "agent",
        "mission",
        "setup-plan",
        "--mission",
        "001-plan-test",
        "--json",
    )

    assert result.returncode == 0, f"setup-plan failed: {result.stderr}"

    # Verify plan.md created in feature directory
    plan_file = feature_dir / "plan.md"
    assert plan_file.exists(), "plan.md not created"

    # Verify plan.md was committed to main
    log_result = subprocess.run(
        ["git", "log", "--oneline", "-2"],
        cwd=test_project,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "plan" in log_result.stdout.lower(), "plan.md should be committed to main"

def test_setup_plan_explicit_feature_reports_spec_path(test_project: Path, run_cli) -> None:
    """setup-plan with explicit --mission returns deterministic context fields."""
    import json

    run_cli(
        test_project,
        "agent",
        "mission",
        "create",
        "plan-explicit-test",
        "--json",
    )

    mission_slug = "001-plan-explicit-test"
    feature_dir = test_project / "kitty-specs" / mission_slug

    plan_template_dir = test_project / ".kittify" / "templates"
    plan_template_dir.mkdir(parents=True, exist_ok=True)
    (plan_template_dir / "plan-template.md").write_text(
        "# Implementation Plan\n\nExplicit mission flow.\n",
        encoding="utf-8",
    )

    result = run_cli(
        test_project,
        "agent",
        "mission",
        "setup-plan",
        "--mission",
        mission_slug,
        "--json",
    )

    assert result.returncode == 0, f"setup-plan failed: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["result"] == "success"
    assert payload["mission_slug"] == mission_slug
    assert payload["feature_dir"] == str(feature_dir)
    assert payload["spec_file"] == str(feature_dir / "spec.md")
    assert payload["plan_file"] == str(feature_dir / "plan.md")

def test_setup_plan_ambiguous_context_returns_candidates(test_project: Path, run_cli) -> None:
    """setup-plan without explicit context returns candidate missions and remediation."""
    import json

    run_cli(
        test_project,
        "agent",
        "mission",
        "create",
        "feature-a",
        "--json",
    )
    run_cli(
        test_project,
        "agent",
        "mission",
        "create",
        "feature-b",
        "--json",
    )

    result = run_cli(
        test_project,
        "agent",
        "mission",
        "setup-plan",
        "--json",
    )

    assert result.returncode != 0, "setup-plan should fail without explicit mission in ambiguous context"
    payload = json.loads(result.stdout.strip().split("\n")[0])
    assert payload["error_code"] == "PLAN_CONTEXT_UNRESOLVED"
    assert len(payload["available_missions"]) >= 2
    assert "--mission" in payload["example_command"]

def test_setup_plan_missing_spec_reports_absolute_path(test_project: Path, run_cli) -> None:
    """setup-plan should fail when spec.md is missing for an explicit mission."""
    import json

    run_cli(
        test_project,
        "agent",
        "mission",
        "create",
        "missing-spec",
        "--json",
    )
    mission_slug = "001-missing-spec"
    feature_dir = test_project / "kitty-specs" / mission_slug
    spec_file = feature_dir / "spec.md"
    spec_file.unlink()

    result = run_cli(
        test_project,
        "agent",
        "mission",
        "setup-plan",
        "--mission",
        mission_slug,
        "--json",
    )

    assert result.returncode != 0, "setup-plan should fail when spec.md is missing"
    payload = json.loads(result.stdout.strip().split("\n")[0])
    assert payload["error_code"] == "SPEC_FILE_MISSING"
    assert payload["mission_slug"] == mission_slug
    assert payload["spec_file"] == str(spec_file.resolve())

def test_full_planning_workflow_no_worktrees(test_project: Path, run_cli) -> None:
    """Test complete planning workflow (specify → plan → [manual tasks]) without worktrees."""
    # Create plan template
    plan_template_dir = test_project / ".kittify" / "templates"
    plan_template_dir.mkdir(parents=True, exist_ok=True)
    (plan_template_dir / "plan-template.md").write_text(
        "# Plan Template\n",
        encoding="utf-8"
    )

    # Step 1: Create mission (specify phase)
    result = run_cli(
        test_project,
        "agent",
        "mission",
        "create",
        "full-workflow-test",
        "--json",
    )
    assert result.returncode == 0, "Mission creation failed"

    feature_dir = test_project / "kitty-specs" / "001-full-workflow-test"
    assert feature_dir.exists(), "Feature directory not created"
    assert (feature_dir / "spec.md").exists(), "spec.md not created"

    # Step 2: Setup plan (plan phase)
    result = run_cli(
        test_project,
        "agent",
        "mission",
        "setup-plan",
        "--mission",
        "001-full-workflow-test",
        "--json",
    )
    assert result.returncode == 0, "Plan setup failed"
    assert (feature_dir / "plan.md").exists(), "plan.md not created"

    # Populate spec requirements referenced by tasks.md
    spec_md = feature_dir / "spec.md"
    spec_md.write_text(
        """# Full Workflow Test Spec

## Functional Requirements

| ID | Requirement | Acceptance Criteria | Status |
| --- | --- | --- | --- |
| FR-001 | Foundation tasks are implemented first. | WP01 is planned and finalized. | proposed |
| FR-002 | API tasks can depend on foundation tasks. | WP02 depends on WP01. | proposed |

## Non-Functional Requirements

| ID | Requirement | Measurable Threshold | Status |
| --- | --- | --- | --- |
| NFR-001 | Finalization must be deterministic. | Re-running finalize does not rewrite unchanged files. | proposed |
| NFR-002 | Dependency parsing must remain explicit. | Dependency links are represented in WP frontmatter. | proposed |

## Constraints

| ID | Constraint | Rationale | Status |
| --- | --- | --- | --- |
| C-001 | Keep generated artifacts in kitty-specs. | Maintains planning workflow structure. | fixed |
""",
        encoding="utf-8",
    )

    # Step 3: Generate sample WP files and tasks.md (simulating /spec-kitty.tasks LLM output)
    tasks_dir = feature_dir / "tasks"

    # Create tasks.md with dependencies
    tasks_md = feature_dir / "tasks.md"
    tasks_md.write_text("""# Work Packages

## Work Package WP01: Foundation
**Dependencies**: None
**Requirement Refs**: FR-001, NFR-001, C-001

### Included Subtasks
- T001 Setup infrastructure
- T002 Create base schema

---

## Work Package WP02: API Layer
**Dependencies**: Depends on WP01
**Requirement Refs**: FR-002, NFR-002

### Included Subtasks
- T003 Build REST endpoints
""", encoding="utf-8")

    # Create WP files WITHOUT dependencies (simulate LLM before finalize-tasks)
    wp01_content = """---
work_package_id: "WP01"
title: "Foundation"
subtasks:
  - "T001"
  - "T002"
phase: "Phase 1"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
owned_files:
  - src/foundation/**
authoritative_surface: src/foundation/
history:
  - at: "2025-01-01T00:00:00Z"
    actor: "system"
    action: "Generated via test"
---

# Work Package: WP01

Test work package content.
"""
    (tasks_dir / "WP01-foundation.md").write_text(wp01_content, encoding="utf-8")

    wp02_content = """---
work_package_id: "WP02"
title: "API Layer"
subtasks:
  - "T003"
phase: "Phase 1"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
owned_files:
  - src/api/**
authoritative_surface: src/api/
history:
  - at: "2025-01-01T00:00:00Z"
    actor: "system"
    action: "Generated via test"
---

# Work Package: WP02

Test work package content.
"""
    (tasks_dir / "WP02-api.md").write_text(wp02_content, encoding="utf-8")

    # Step 4: Run finalize-tasks to parse dependencies and commit
    result = run_cli(
        test_project,
        "agent",
        "mission",
        "finalize-tasks",
        "--mission",
        "001-full-workflow-test",
        "--json",
    )
    assert result.returncode == 0, f"finalize-tasks failed: {result.stderr}"

    # Verify dependencies were added by finalize-tasks
    wp01_updated = (tasks_dir / "WP01-foundation.md").read_text()
    assert "dependencies" in wp01_updated.lower(), "WP01 should have dependencies field"
    assert "planning_base_branch: main" in wp01_updated, (
        "WP01 should record the planning branch used to generate tasks"
    )
    assert "merge_target_branch: main" in wp01_updated, (
        "WP01 should record the final merge target"
    )

    wp02_updated = (tasks_dir / "WP02-api.md").read_text()
    assert "dependencies" in wp02_updated.lower(), "WP02 should have dependencies field"
    assert "WP01" in wp02_updated, "WP02 should depend on WP01"
    assert "planning_base_branch: main" in wp02_updated
    assert "merge_target_branch: main" in wp02_updated

    # Verify: NO worktrees directory exists
    worktrees_dir = test_project / ".worktrees"
    if worktrees_dir.exists():
        # Directory might exist but should be empty
        worktree_contents = list(worktrees_dir.iterdir())
        assert len(worktree_contents) == 0, "No worktrees should be created during planning"

    # Verify: All artifacts committed to main branch
    log_result = subprocess.run(
        ["git", "log", "--oneline", "--all"],
        cwd=test_project,
        capture_output=True,
        text=True,
        check=True,
    )
    commit_log = log_result.stdout.lower()

    assert "spec" in commit_log, "spec.md commit missing"
    assert "plan" in commit_log, "plan.md commit missing"
    assert "tasks" in commit_log, "tasks commit missing"

    # Verify tasks.md included in latest commit
    commit_files = subprocess.run(
        ["git", "show", "--name-only", "--pretty=format:%H", "HEAD"],
        cwd=test_project,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "tasks.md" in commit_files.stdout, "tasks.md should be committed with tasks"

    # Verify: Current branch is still main
    branch_result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=test_project,
        capture_output=True,
        text=True,
        check=True,
    )
    default_branch = branch_result.stdout.strip()
    assert default_branch in ("main", "master"), f"Should still be on default branch, got: {default_branch}"

def test_check_prerequisites_works_in_main(test_project: Path, run_cli) -> None:
    """Test that check-prerequisites command works when run from main repo."""
    # Create a mission first
    run_cli(
        test_project,
        "agent",
        "mission",
        "create",
        "prereq-test",
        "--json",
    )

    # Run check-prerequisites from main repo
    result = run_cli(
        test_project,
        "agent",
        "mission",
        "check-prerequisites",
        "--mission",
        "001-prereq-test",
        "--json",
    )

    assert result.returncode == 0, f"check-prerequisites failed: {result.stderr}"

    # Should find the latest mission and validate its structure
    import json
    output = json.loads(result.stdout)
    assert output["valid"] is True, "Feature structure should be valid"
    assert "spec_file" in output["paths"], "Should detect spec.md"

def test_check_prerequisites_ambiguous_context_returns_candidates(
    test_project: Path, run_cli
) -> None:
    """check-prerequisites should fail with remediation when feature context is ambiguous."""
    import json

    run_cli(
        test_project,
        "agent",
        "mission",
        "create",
        "ambiguous-a",
        "--json",
    )
    run_cli(
        test_project,
        "agent",
        "mission",
        "create",
        "ambiguous-b",
        "--json",
    )

    result = run_cli(
        test_project,
        "agent",
        "mission",
        "check-prerequisites",
        "--json",
        "--paths-only",
        "--include-tasks",
    )

    assert result.returncode != 0, "Ambiguous mission context should fail without --mission"
    payload = json.loads(result.stdout.strip().split("\n")[0])
    assert payload["error_code"] == "FEATURE_CONTEXT_UNRESOLVED"
    assert len(payload["available_missions"]) >= 2
    assert "--mission" in payload["example_command"]

def test_finalize_tasks_ambiguous_context_returns_candidates(
    test_project: Path, run_cli
) -> None:
    """finalize-tasks should fail with remediation when feature context is ambiguous."""
    import json

    run_cli(
        test_project,
        "agent",
        "mission",
        "create",
        "ambiguous-finalize-a",
        "--json",
    )
    run_cli(
        test_project,
        "agent",
        "mission",
        "create",
        "ambiguous-finalize-b",
        "--json",
    )

    result = run_cli(
        test_project,
        "agent",
        "mission",
        "finalize-tasks",
        "--json",
    )

    assert result.returncode != 0, "Ambiguous mission context should fail without --mission"
    payload = json.loads(result.stdout.strip().split("\n")[0])
    assert payload["error_code"] == "FEATURE_CONTEXT_UNRESOLVED"
    assert len(payload["available_missions"]) >= 2
    assert "finalize-tasks --mission" in payload["example_command"]
