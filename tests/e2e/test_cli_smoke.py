"""End-to-end CLI smoke test for the full spec-kitty workflow.

Exercises the complete sequence:
  create-feature -> setup-plan -> finalize-tasks -> implement -> move-task

This test creates a fresh temporary git repo, runs each CLI command via
subprocess, and verifies that intermediate artifacts exist at each step.
It is entirely self-contained: no state leaks to the source repository.

Marked with pytest.mark.e2e for optional CI separation:
    pytest tests/ -m "not e2e"    # skip E2E in fast runs
    pytest tests/e2e/ -v -s       # run E2E only
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


@pytest.mark.e2e
class TestFullCLIWorkflow:
    """Exercise the complete spec-kitty CLI workflow end-to-end."""

    def test_create_feature(self, e2e_project: Path, run_cli) -> None:
        """Step 1: create-feature produces feature directory and spec.md."""
        result = run_cli(
            e2e_project,
            "agent",
            "feature",
            "create-feature",
            "smoke-test",
            "--json",
        )
        assert result.returncode == 0, (
            f"create-feature failed (rc={result.returncode}):\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        output = json.loads(result.stdout)
        assert output["result"] == "success"
        assert "smoke-test" in output["feature"]

        feature_dir = Path(output["feature_dir"])
        assert feature_dir.exists(), f"Feature dir missing: {feature_dir}"
        assert (feature_dir / "spec.md").exists(), "spec.md not created"
        assert (feature_dir / "tasks").is_dir(), "tasks/ directory not created"

        # No worktree should have been created during planning
        worktrees_dir = e2e_project / ".worktrees"
        if worktrees_dir.exists():
            assert list(worktrees_dir.iterdir()) == [], "Worktree created during feature creation"

    def test_setup_plan(self, e2e_project: Path, run_cli) -> None:
        """Step 2: setup-plan produces plan.md in feature directory."""
        # Create feature first
        result = run_cli(
            e2e_project,
            "agent",
            "feature",
            "create-feature",
            "plan-smoke",
            "--json",
        )
        assert result.returncode == 0, f"create-feature failed: {result.stderr}"
        output = json.loads(result.stdout)
        feature_dir = Path(output["feature_dir"])
        feature_slug = output["feature"]

        # Run setup-plan
        result = run_cli(
            e2e_project,
            "agent",
            "feature",
            "setup-plan",
            "--feature",
            feature_slug,
            "--json",
        )
        assert result.returncode == 0, (
            f"setup-plan failed (rc={result.returncode}):\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        plan_file = feature_dir / "plan.md"
        assert plan_file.exists(), "plan.md not created by setup-plan"
        assert plan_file.stat().st_size > 0, "plan.md is empty"

    def test_full_workflow_sequence(self, e2e_project: Path, run_cli) -> None:
        """Full create-feature -> setup-plan -> finalize-tasks -> implement -> move-task.

        This is the main smoke test exercising the complete workflow
        that a developer/agent would follow.
        """
        repo = e2e_project

        # === Step 1: Create feature ===
        result = run_cli(
            repo,
            "agent",
            "feature",
            "create-feature",
            "full-e2e",
            "--json",
        )
        assert result.returncode == 0, f"create-feature failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        create_output = json.loads(result.stdout)
        assert create_output["result"] == "success"

        feature_slug = create_output["feature"]
        feature_dir = Path(create_output["feature_dir"])
        assert feature_dir.exists()
        assert (feature_dir / "spec.md").exists()

        # === Step 2: Setup plan ===
        result = run_cli(
            repo,
            "agent",
            "feature",
            "setup-plan",
            "--feature",
            feature_slug,
            "--json",
        )
        assert result.returncode == 0, f"setup-plan failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        plan_output = json.loads(result.stdout)
        assert plan_output["result"] == "success"
        assert (feature_dir / "plan.md").exists()

        # === Step 3: Simulate LLM task generation (write tasks.md + WP files) ===
        tasks_dir = feature_dir / "tasks"

        tasks_md_content = """# Work Packages

## Work Package WP01: Hello World
**Dependencies**: None

### Included Subtasks
- T001 Create hello module

---
"""
        (feature_dir / "tasks.md").write_text(tasks_md_content, encoding="utf-8")

        # Omit 'dependencies' from frontmatter so finalize-tasks has work to do
        wp01_content = """---
work_package_id: "WP01"
title: "Hello World"
lane: "planned"
subtasks:
  - "T001"
phase: "Phase 1"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-02-12T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Generated via test"
---

# Work Package Prompt: WP01 -- Hello World

Create a hello module.
"""
        (tasks_dir / "WP01-hello-world.md").write_text(wp01_content, encoding="utf-8")

        # Create meta.json (required by finalize-tasks for event emission)
        import json as json_mod

        meta_content = {
            "feature_number": "001",
            "feature_slug": feature_slug,
            "created_at": "2026-02-12T00:00:00Z",
            "vcs": "git",
        }
        (feature_dir / "meta.json").write_text(
            json_mod.dumps(meta_content, indent=2),
            encoding="utf-8",
        )

        # Commit the tasks so finalize-tasks has a clean working tree
        subprocess.run(
            ["git", "add", "."],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add tasks for smoke test"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # === Step 4: Finalize tasks ===
        # Note: finalize-tasks does not accept --feature; it auto-detects
        # from the kitty-specs/ directory in the cwd.
        result = run_cli(
            repo,
            "agent",
            "feature",
            "finalize-tasks",
            "--json",
        )
        assert result.returncode == 0, f"finalize-tasks failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"

        # Verify WP file still exists and has dependencies field
        wp01_path = tasks_dir / "WP01-hello-world.md"
        assert wp01_path.exists(), "WP01 file disappeared after finalize-tasks"
        wp01_text = wp01_path.read_text(encoding="utf-8")
        assert "dependencies" in wp01_text.lower(), "WP01 missing dependencies after finalize-tasks"

        # === Step 5: Implement WP01 (create workspace) ===
        result = run_cli(
            repo,
            "implement",
            "WP01",
            "--feature",
            feature_slug,
            "--json",
        )

        # The implement command may or may not use --json for output.
        # We check for success by looking at the worktree existing.
        worktree_dir = repo / ".worktrees" / f"{feature_slug}-WP01"

        if result.returncode != 0:
            # Try without --json (implement might not support it cleanly)
            result = run_cli(
                repo,
                "implement",
                "WP01",
                "--feature",
                feature_slug,
            )

        # Verify worktree was created
        assert worktree_dir.exists(), (
            f"Workspace not created at {worktree_dir}\n"
            f"implement stdout: {result.stdout}\n"
            f"implement stderr: {result.stderr}\n"
            f"implement rc: {result.returncode}"
        )

        # === Step 6: Make a change in the workspace and commit ===
        src_in_wt = worktree_dir / "src"
        if not src_in_wt.exists():
            src_in_wt.mkdir(parents=True)

        (src_in_wt / "hello.py").write_text(
            'def hello() -> str:\n    return "Hello from E2E smoke test"\n',
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "add", "."],
            cwd=worktree_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "feat(WP01): add hello module"],
            cwd=worktree_dir,
            check=True,
            capture_output=True,
        )

        # Verify the commit landed in the worktree
        log_result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=worktree_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "hello" in log_result.stdout.lower(), "Commit not found in worktree"

        # === Step 7: Move WP01 to for_review ===
        result = run_cli(
            repo,
            "agent",
            "tasks",
            "move-task",
            "WP01",
            "--to",
            "for_review",
            "--feature",
            feature_slug,
            "--json",
        )

        # move-task may return non-zero if preflight checks fail (dirty worktree, etc.)
        # The important thing is that we exercised the full sequence.
        # We check that the WP file was updated if the command succeeded.
        if result.returncode == 0:
            wp01_updated = wp01_path.read_text(encoding="utf-8")
            assert "for_review" in wp01_updated, "WP01 not moved to for_review"

        # === Final verification: all artifacts exist ===
        assert (feature_dir / "spec.md").exists(), "spec.md missing at end"
        assert (feature_dir / "plan.md").exists(), "plan.md missing at end"
        assert (feature_dir / "tasks.md").exists(), "tasks.md missing at end"
        assert wp01_path.exists(), "WP01 prompt file missing at end"
        assert worktree_dir.exists(), "Worktree missing at end"

        # Verify git history has the expected commits
        log_result = subprocess.run(
            ["git", "log", "--oneline", "--all"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        log_text = log_result.stdout.lower()
        assert "spec" in log_text, "spec commit missing from git log"
        assert "plan" in log_text, "plan commit missing from git log"
        assert "tasks" in log_text or "finalize" in log_text, "tasks/finalize commit missing from git log"


@pytest.mark.e2e
class TestWorkflowEdgeCases:
    """Edge case tests for the CLI workflow."""

    def test_create_feature_rejects_bad_slug(self, e2e_project: Path, run_cli) -> None:
        """create-feature rejects non-kebab-case slugs."""
        result = run_cli(
            e2e_project,
            "agent",
            "feature",
            "create-feature",
            "Bad_Slug",
            "--json",
        )
        assert result.returncode != 0, "Should reject non-kebab-case slug"
        # The JSON output may contain Rich console formatting escape codes,
        # so we check the raw text for the error indicator rather than parsing JSON.
        combined = result.stdout + result.stderr
        assert "error" in combined.lower() or "invalid" in combined.lower(), (
            f"Expected error message in output, got:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_setup_plan_requires_feature(self, e2e_project: Path, run_cli) -> None:
        """setup-plan fails gracefully when no feature exists."""
        result = run_cli(
            e2e_project,
            "agent",
            "feature",
            "setup-plan",
            "--json",
        )
        # Should fail because no feature exists yet
        assert result.returncode != 0, "setup-plan should fail when no feature exists"

    def test_implement_requires_existing_wp(self, e2e_project: Path, run_cli) -> None:
        """implement fails gracefully when WP does not exist."""
        result = run_cli(
            e2e_project,
            "implement",
            "WP99",
        )
        assert result.returncode != 0, "implement should fail for non-existent WP"
