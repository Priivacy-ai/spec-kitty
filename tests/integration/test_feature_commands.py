"""Integration tests for feature lifecycle commands.

These tests verify that feature commands work end-to-end with real git operations.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.feature import app

runner = CliRunner()


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository for testing."""
    repo = tmp_path / "test-repo"
    repo.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create .kittify marker
    kittify = repo / ".kittify"
    kittify.mkdir()
    (kittify / "marker.txt").write_text("marker")

    # Create initial commit
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    return repo


class TestCreateFeatureIntegration:
    """Integration tests for create-feature command."""

    def test_creates_feature_from_main_repo(self, git_repo: Path, monkeypatch):
        """Should create feature directory in main repository."""
        # Setup
        monkeypatch.chdir(git_repo)

        # Create plan template
        template_dir = git_repo / ".kittify" / "templates"
        template_dir.mkdir(parents=True)
        (template_dir / "plan-template.md").write_text("# Plan Template")
        (template_dir / "spec-template.md").write_text("# Spec Template")

        # Create memory directory for symlink/copy
        memory_dir = git_repo / ".kittify" / "memory"
        memory_dir.mkdir(parents=True)
        (memory_dir / "constitution.md").write_text("# Constitution")

        # Create AGENTS.md
        (git_repo / ".kittify" / "AGENTS.md").write_text("# Agents")

        # Execute
        result = runner.invoke(app, ["create-feature", "test-feature", "--json"])

        # Verify command succeeded
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["result"] == "success"
        assert output["feature"] == "001-test-feature"

        # Verify no worktree created (planning happens in main)
        worktrees_dir = git_repo / ".worktrees"
        if worktrees_dir.exists():
            assert not list(worktrees_dir.iterdir()), "Unexpected worktrees created"

        # Verify feature directory structure
        feature_dir = git_repo / "kitty-specs" / "001-test-feature"
        assert feature_dir.exists()
        assert (feature_dir / "spec.md").exists()
        assert (feature_dir / "spec.md").read_text() == "# Spec Template"
        assert (feature_dir / "checklists").is_dir()
        assert (feature_dir / "research").is_dir()
        assert (feature_dir / "tasks").is_dir()
        assert (feature_dir / "tasks" / ".gitkeep").exists()
        assert (feature_dir / "tasks" / "README.md").exists()

        # Verify tasks/README.md contains frontmatter docs
        tasks_readme = (feature_dir / "tasks" / "README.md").read_text()
        assert "YAML frontmatter" in tasks_readme
        assert "lane:" in tasks_readme

        # Verify .kittify is unchanged in main repo
        assert (git_repo / ".kittify").exists()

    def test_creates_feature_with_auto_incrementing_number(
        self, git_repo: Path, monkeypatch
    ):
        """Should auto-increment feature number when creating multiple features."""
        # Setup
        monkeypatch.chdir(git_repo)

        # Create templates
        template_dir = git_repo / ".kittify" / "templates"
        template_dir.mkdir(parents=True)
        (template_dir / "spec-template.md").write_text("# Spec")

        # Create first feature
        result1 = runner.invoke(app, ["create-feature", "feature-one", "--json"])
        assert result1.exit_code == 0
        output1 = json.loads(result1.stdout)
        assert output1["feature"] == "001-feature-one"

        # Create second feature
        result2 = runner.invoke(app, ["create-feature", "feature-two", "--json"])
        assert result2.exit_code == 0
        output2 = json.loads(result2.stdout)
        assert output2["feature"] == "002-feature-two"

        # Verify both feature directories exist in main
        assert (git_repo / "kitty-specs" / "001-feature-one").exists()
        assert (git_repo / "kitty-specs" / "002-feature-two").exists()

    def test_creates_feature_from_existing_worktree(self, git_repo: Path, monkeypatch):
        """Should reject create-feature when run from a worktree branch."""
        monkeypatch.chdir(git_repo)
        template_dir = git_repo / ".kittify" / "templates"
        template_dir.mkdir(parents=True)
        (template_dir / "spec-template.md").write_text("# Spec")

        # Create a worktree to simulate worktree context
        worktree_path = git_repo / ".worktrees" / "001-existing"
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), "-b", "001-existing"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        monkeypatch.chdir(worktree_path)

        # Create feature from worktree should fail (must be in planning repo, not worktree)
        result = runner.invoke(app, ["create-feature", "second-feature", "--json"])
        assert result.exit_code != 0
        error_output = result.stdout + result.stderr
        assert "worktree" in error_output.lower()


class TestCheckPrerequisitesIntegration:
    """Integration tests for check-prerequisites command."""

    def test_validates_complete_feature_structure(self, git_repo: Path, monkeypatch):
        """Should validate feature structure when all files exist."""
        # Setup: Create feature with complete structure
        monkeypatch.chdir(git_repo)
        template_dir = git_repo / ".kittify" / "templates"
        template_dir.mkdir(parents=True)
        (template_dir / "spec-template.md").write_text("# Spec")

        runner.invoke(app, ["create-feature", "test-feature"])

        # Change to feature directory (main repo)
        feature_dir = git_repo / "kitty-specs" / "001-test-feature"
        monkeypatch.chdir(feature_dir)

        # Execute
        result = runner.invoke(app, ["check-prerequisites", "--json"])

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["valid"] is True
        assert output["errors"] == []
        assert "spec_file" in output["paths"]
        assert "checklists_dir" in output["paths"]

    def test_detects_missing_required_files(self, git_repo: Path, monkeypatch):
        """Should detect missing required files."""
        # Setup: Create feature directory without spec.md
        monkeypatch.chdir(git_repo)
        feature_dir = git_repo / "kitty-specs" / "001-incomplete"
        feature_dir.mkdir(parents=True)

        # Execute
        result = runner.invoke(app, ["check-prerequisites", "--json"])

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["valid"] is False
        assert any("spec.md" in error for error in output["errors"])

    def test_validates_from_worktree_root(self, git_repo: Path, monkeypatch):
        """Should correctly identify feature when run from feature directory."""
        # Setup
        monkeypatch.chdir(git_repo)
        template_dir = git_repo / ".kittify" / "templates"
        template_dir.mkdir(parents=True)
        (template_dir / "spec-template.md").write_text("# Spec")

        # Create multiple features
        runner.invoke(app, ["create-feature", "feature-one"])
        runner.invoke(app, ["create-feature", "feature-two"])

        # Change to second feature directory
        feature_dir = git_repo / "kitty-specs" / "002-feature-two"
        monkeypatch.chdir(feature_dir)

        # Execute
        result = runner.invoke(app, ["check-prerequisites", "--json"])

        # Verify it detects the correct feature (002, not 001)
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert "002-feature-two" in output["paths"]["feature_dir"]

    def test_paths_only_flag_integration(self, git_repo: Path, monkeypatch):
        """Should output only paths when --paths-only flag is used."""
        # Setup
        monkeypatch.chdir(git_repo)
        feature_dir = git_repo / "kitty-specs" / "001-test"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text("# Spec")

        # Execute
        result = runner.invoke(app, ["check-prerequisites", "--json", "--paths-only"])

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        # Should only have paths, not valid/errors/warnings
        assert "spec_file" in output
        assert "valid" not in output
        assert "errors" not in output


class TestSetupPlanIntegration:
    """Integration tests for setup-plan command."""

    def test_scaffolds_plan_from_template(self, git_repo: Path, monkeypatch):
        """Should scaffold plan.md from template."""
        # Setup
        monkeypatch.chdir(git_repo)

        # Create feature structure
        feature_dir = git_repo / "kitty-specs" / "001-test"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text("# Spec")

        # Create plan template
        template_dir = git_repo / ".kittify" / "templates"
        template_dir.mkdir(parents=True)
        plan_template_content = "# Implementation Plan\n\n## Phase 1\nTask description"
        (template_dir / "plan-template.md").write_text(plan_template_content)

        # Execute
        result = runner.invoke(app, ["setup-plan", "--json"])

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["result"] == "success"

        # Verify plan file was created with template content
        plan_file = feature_dir / "plan.md"
        assert plan_file.exists()
        assert plan_file.read_text() == plan_template_content

    def test_scaffolds_plan_from_worktree(self, git_repo: Path, monkeypatch):
        """Should scaffold plan when run from feature directory."""
        # Setup
        monkeypatch.chdir(git_repo)
        template_dir = git_repo / ".kittify" / "templates"
        template_dir.mkdir(parents=True)
        (template_dir / "spec-template.md").write_text("# Spec")
        (template_dir / "plan-template.md").write_text("# Plan Template")

        # Create feature
        runner.invoke(app, ["create-feature", "test-feature"])

        # Change to feature directory
        feature_dir = git_repo / "kitty-specs" / "001-test-feature"
        monkeypatch.chdir(feature_dir)

        # Remove plan.md if it exists
        plan_file = feature_dir / "plan.md"
        if plan_file.exists():
            plan_file.unlink()

        # Execute
        result = runner.invoke(app, ["setup-plan", "--json"])

        # Verify
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert plan_file.exists()
        assert plan_file.read_text() == "# Plan Template"

    def test_falls_back_to_package_template(self, git_repo: Path, monkeypatch):
        """Should use packaged plan template when repo templates are missing."""
        # Setup
        monkeypatch.chdir(git_repo)
        feature_dir = git_repo / "kitty-specs" / "001-test"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text("# Spec")
        plan_file = feature_dir / "plan.md"

        # Ensure no repo-local templates exist
        assert not (git_repo / ".kittify" / "templates" / "plan-template.md").exists()

        # Execute
        result = runner.invoke(app, ["setup-plan", "--json"])

        # Verify
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert plan_file.exists()
        assert plan_file.read_text().startswith("# Implementation Plan:")


class TestEndToEndFeatureWorkflow:
    """End-to-end tests for complete feature lifecycle."""

    def test_complete_feature_creation_workflow(self, git_repo: Path, monkeypatch):
        """Should support complete feature creation workflow."""
        # Setup
        monkeypatch.chdir(git_repo)

        # Create templates
        template_dir = git_repo / ".kittify" / "templates"
        template_dir.mkdir(parents=True)
        (template_dir / "spec-template.md").write_text("# Specification")
        (template_dir / "plan-template.md").write_text("# Plan")

        # Step 1: Create feature
        result1 = runner.invoke(app, ["create-feature", "new-feature", "--json"])
        assert result1.exit_code == 0
        output1 = json.loads(result1.stdout)
        feature_dir = Path(output1["feature_dir"])

        # Step 2: Check prerequisites from feature directory
        monkeypatch.chdir(feature_dir)
        result2 = runner.invoke(app, ["check-prerequisites", "--json"])
        assert result2.exit_code == 0
        output2 = json.loads(result2.stdout)
        assert output2["valid"] is True

        # Step 3: Setup plan (if not already created)
        plan_file = feature_dir / "plan.md"
        if plan_file.exists():
            plan_file.unlink()

        result3 = runner.invoke(app, ["setup-plan", "--json"])
        assert result3.exit_code == 0, f"Setup plan failed: {result3.stdout}"

        # Verify final state
        assert plan_file.exists()
        assert plan_file.read_text() == "# Plan"

        # Verify we can check prerequisites with tasks
        (feature_dir / "tasks.md").write_text("# Tasks")
        result4 = runner.invoke(app, ["check-prerequisites", "--include-tasks", "--json"])
        assert result4.exit_code == 0
        output4 = json.loads(result4.stdout)
        assert output4["valid"] is True
        assert "tasks_file" in output4["paths"]
