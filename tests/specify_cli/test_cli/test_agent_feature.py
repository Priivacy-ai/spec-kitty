"""Unit tests for agent feature CLI commands."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.feature import app

runner = CliRunner()


class TestCreateFeatureCommand:
    """Tests for create-feature command."""

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature.is_git_repo")
    @patch("specify_cli.cli.commands.agent.feature.get_current_branch")
    @patch("specify_cli.cli.commands.agent.feature.get_next_feature_number")
    @patch("specify_cli.cli.commands.agent.feature._commit_to_main")
    def test_creates_feature_with_json_output(
        self, mock_commit: Mock, mock_get_number: Mock, mock_branch: Mock,
        mock_is_git: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should create feature and output JSON format."""
        # Setup
        mock_locate.return_value = tmp_path
        mock_is_git.return_value = True
        mock_branch.return_value = "main"
        mock_get_number.return_value = 1

        # Create necessary directories
        (tmp_path / ".kittify" / "templates").mkdir(parents=True)
        (tmp_path / ".kittify" / "templates" / "spec-template.md").write_text("# Spec Template")

        # Execute
        result = runner.invoke(app, ["create-feature", "test-feature", "--json"])

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["result"] == "success"
        assert output["feature"] == "001-test-feature"
        assert "feature_dir" in output

        # Verify feature directory was created
        feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
        assert feature_dir.exists()
        assert (feature_dir / "spec.md").exists()

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature.is_git_repo")
    @patch("specify_cli.cli.commands.agent.feature.get_current_branch")
    @patch("specify_cli.cli.commands.agent.feature.get_next_feature_number")
    @patch("specify_cli.cli.commands.agent.feature._commit_to_main")
    def test_creates_feature_with_human_output(
        self, mock_commit: Mock, mock_get_number: Mock, mock_branch: Mock,
        mock_is_git: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should create feature and output human-readable format."""
        # Setup
        mock_locate.return_value = tmp_path
        mock_is_git.return_value = True
        mock_branch.return_value = "main"
        mock_get_number.return_value = 1

        # Create necessary directories
        (tmp_path / ".kittify" / "templates").mkdir(parents=True)
        (tmp_path / ".kittify" / "templates" / "spec-template.md").write_text("# Spec Template")

        # Execute
        result = runner.invoke(app, ["create-feature", "test-feature"])

        # Verify
        assert result.exit_code == 0
        assert "Feature created: 001-test-feature" in result.stdout
        assert "Directory:" in result.stdout

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    def test_errors_when_project_root_not_found_json(self, mock_locate: Mock):
        """Should return JSON error when project root not found."""
        # Setup
        mock_locate.return_value = None

        # Execute
        result = runner.invoke(app, ["create-feature", "test-feature", "--json"])

        # Verify
        assert result.exit_code == 1
        # Parse only the first line (JSON output)
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output
        assert "Could not locate project root" in output["error"]

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    def test_errors_when_project_root_not_found_human(self, mock_locate: Mock):
        """Should return human error when project root not found."""
        # Setup
        mock_locate.return_value = None

        # Execute
        result = runner.invoke(app, ["create-feature", "test-feature"])

        # Verify
        assert result.exit_code == 1
        assert "Error:" in result.stdout
        assert "Could not locate project root" in result.stdout

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature.is_git_repo")
    @patch("specify_cli.cli.commands.agent.feature.get_current_branch")
    def test_handles_git_errors(
        self, mock_branch: Mock, mock_is_git: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should handle errors when not in git repo or wrong branch."""
        # Setup: Not in git repo
        mock_locate.return_value = tmp_path
        mock_is_git.return_value = False

        # Execute
        result = runner.invoke(app, ["create-feature", "test-feature", "--json"])

        # Verify
        assert result.exit_code == 1
        # Parse only the first line (JSON output)
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output
        assert "git" in output["error"].lower()

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature.is_git_repo")
    @patch("specify_cli.cli.commands.agent.feature.get_current_branch")
    def test_requires_main_branch(
        self, mock_branch: Mock, mock_is_git: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should require main branch for feature creation."""
        # Setup: On wrong branch
        mock_locate.return_value = tmp_path
        mock_is_git.return_value = True
        mock_branch.return_value = "develop"

        # Execute
        result = runner.invoke(app, ["create-feature", "test-feature", "--json"])

        # Verify
        assert result.exit_code == 1
        # Parse only the first line (JSON output)
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output
        assert "main" in output["error"].lower()


class TestCheckPrerequisitesCommand:
    """Tests for check-prerequisites command."""

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature.validate_feature_structure")
    def test_validates_prerequisites_json_output(
        self, mock_validate: Mock, mock_find: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should validate prerequisites and output JSON format."""
        # Setup
        mock_locate.return_value = tmp_path
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        mock_find.return_value = feature_dir
        mock_validate.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "paths": {"spec_file": str(feature_dir / "spec.md")},
        }

        # Execute
        result = runner.invoke(app, ["check-prerequisites", "--json"])

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["valid"] is True
        assert "errors" in output
        assert "warnings" in output
        assert "paths" in output

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature.validate_feature_structure")
    def test_validates_prerequisites_human_output(
        self, mock_validate: Mock, mock_find: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should validate prerequisites and output human-readable format."""
        # Setup
        mock_locate.return_value = tmp_path
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        feature_dir.mkdir(parents=True)
        mock_find.return_value = feature_dir
        mock_validate.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "paths": {},
        }

        # Execute
        result = runner.invoke(app, ["check-prerequisites"])

        # Verify
        assert result.exit_code == 0
        assert "Prerequisites check passed" in result.stdout
        assert "Feature: 001-test" in result.stdout

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature.validate_feature_structure")
    def test_shows_validation_errors(
        self, mock_validate: Mock, mock_find: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should show validation errors in output."""
        # Setup
        mock_locate.return_value = tmp_path
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        feature_dir.mkdir(parents=True)
        mock_find.return_value = feature_dir
        mock_validate.return_value = {
            "valid": False,
            "errors": ["Missing required file: spec.md"],
            "warnings": [],
            "paths": {},
        }

        # Execute
        result = runner.invoke(app, ["check-prerequisites"])

        # Verify
        assert result.exit_code == 0
        assert "Prerequisites check failed" in result.stdout
        assert "Missing required file: spec.md" in result.stdout

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature.validate_feature_structure")
    def test_shows_validation_warnings(
        self, mock_validate: Mock, mock_find: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should show validation warnings in output."""
        # Setup
        mock_locate.return_value = tmp_path
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        feature_dir.mkdir(parents=True)
        mock_find.return_value = feature_dir
        mock_validate.return_value = {
            "valid": True,
            "errors": [],
            "warnings": ["Missing recommended directory: checklists/"],
            "paths": {},
        }

        # Execute
        result = runner.invoke(app, ["check-prerequisites"])

        # Verify
        assert result.exit_code == 0
        assert "Warnings:" in result.stdout
        assert "Missing recommended directory: checklists/" in result.stdout

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature.validate_feature_structure")
    def test_paths_only_flag_json(
        self, mock_validate: Mock, mock_find: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should output only paths when --paths-only flag is used."""
        # Setup
        mock_locate.return_value = tmp_path
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        mock_find.return_value = feature_dir
        paths = {"spec_file": str(feature_dir / "spec.md")}
        mock_validate.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "paths": paths,
        }

        # Execute
        result = runner.invoke(app, ["check-prerequisites", "--json", "--paths-only"])

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output == paths

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature.validate_feature_structure")
    def test_include_tasks_flag(
        self, mock_validate: Mock, mock_find: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should validate tasks.md when --include-tasks flag is used."""
        # Setup
        mock_locate.return_value = tmp_path
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        mock_find.return_value = feature_dir
        mock_validate.return_value = {
            "valid": False,
            "errors": ["Missing required file: tasks.md"],
            "warnings": [],
            "paths": {},
        }

        # Execute
        result = runner.invoke(app, ["check-prerequisites", "--include-tasks", "--json"])

        # Verify
        assert result.exit_code == 0
        mock_validate.assert_called_once_with(feature_dir, check_tasks=True)
        output = json.loads(result.stdout)
        assert "Missing required file: tasks.md" in output["errors"]

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    def test_errors_when_project_root_not_found(self, mock_locate: Mock):
        """Should return error when project root not found."""
        # Setup
        mock_locate.return_value = None

        # Execute
        result = runner.invoke(app, ["check-prerequisites", "--json"])

        # Verify
        assert result.exit_code == 1
        # Parse only the first line (JSON output)
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output


class TestSetupPlanCommand:
    """Tests for setup-plan command."""

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature._commit_to_main")
    def test_scaffolds_plan_template_json(
        self, mock_commit: Mock, mock_find: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should scaffold plan template and output JSON format."""
        # Setup
        mock_locate.return_value = tmp_path
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        feature_dir.mkdir(parents=True)
        mock_find.return_value = feature_dir

        # Create template
        template_dir = tmp_path / ".kittify" / "templates"
        template_dir.mkdir(parents=True)
        plan_template = template_dir / "plan-template.md"
        plan_template.write_text("# Implementation Plan Template")

        # Execute
        result = runner.invoke(app, ["setup-plan", "--json"])

        # Verify
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["result"] == "success"
        assert "plan_file" in output
        assert "feature_dir" in output

        # Verify plan file was created
        plan_file = feature_dir / "plan.md"
        assert plan_file.exists()
        assert plan_file.read_text() == "# Implementation Plan Template"

        # Verify commit was called
        mock_commit.assert_called_once()

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature._commit_to_main")
    def test_scaffolds_plan_template_human(
        self, mock_commit: Mock, mock_find: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should scaffold plan template and output human-readable format."""
        # Setup
        mock_locate.return_value = tmp_path
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        feature_dir.mkdir(parents=True)
        mock_find.return_value = feature_dir

        # Create template
        template_dir = tmp_path / ".kittify" / "templates"
        template_dir.mkdir(parents=True)
        plan_template = template_dir / "plan-template.md"
        plan_template.write_text("# Implementation Plan Template")

        # Execute
        result = runner.invoke(app, ["setup-plan"])

        # Verify
        assert result.exit_code == 0
        assert "Plan scaffolded:" in result.stdout

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature.files")
    def test_errors_when_template_not_found(
        self, mock_files: Mock, mock_find: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should return error when plan template not found."""
        # Setup
        mock_locate.return_value = tmp_path
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        feature_dir.mkdir(parents=True)
        mock_find.return_value = feature_dir

        # No template created and package template unavailable
        package_templates = Mock()
        package_template = Mock()
        package_template.exists.return_value = False
        package_templates.joinpath.return_value = package_template
        mock_files.return_value = package_templates

        # Execute
        result = runner.invoke(app, ["setup-plan", "--json"])

        # Verify
        assert result.exit_code == 1
        output = json.loads(result.stdout)
        assert "error" in output
        assert "Plan template not found" in output["error"]

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    def test_errors_when_project_root_not_found(self, mock_locate: Mock):
        """Should return error when project root not found."""
        # Setup
        mock_locate.return_value = None

        # Execute
        result = runner.invoke(app, ["setup-plan", "--json"])

        # Verify
        assert result.exit_code == 1
        # Parse only the first line (JSON output)
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert "error" in output


class TestFindFeatureDirectory:
    """Tests for _find_feature_directory helper function."""

    @patch("specify_cli.cli.commands.agent.feature.is_worktree_context")
    @patch("specify_cli.cli.commands.agent.feature.subprocess.run")
    def test_finds_feature_in_worktree_by_branch_name(
        self, mock_subprocess: Mock, mock_is_worktree: Mock, tmp_path: Path
    ):
        """Should find feature directory matching branch name in worktree."""
        # Setup
        from specify_cli.cli.commands.agent.feature import _find_feature_directory

        mock_is_worktree.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stdout="001-test-feature\n")

        # Create worktree structure
        kitty_specs = tmp_path / "kitty-specs"
        kitty_specs.mkdir()
        (kitty_specs / "001-test-feature").mkdir()
        (kitty_specs / "002-other-feature").mkdir()

        # Execute
        result = _find_feature_directory(tmp_path, tmp_path)

        # Verify
        assert result == kitty_specs / "001-test-feature"

    @patch("specify_cli.cli.commands.agent.feature.is_worktree_context")
    def test_finds_latest_feature_in_main_repo(
        self, mock_is_worktree: Mock, tmp_path: Path
    ):
        """Should find highest numbered feature in main repo."""
        # Setup
        from specify_cli.cli.commands.agent.feature import _find_feature_directory

        mock_is_worktree.return_value = False

        # Create main repo structure
        kitty_specs = tmp_path / "kitty-specs"
        kitty_specs.mkdir()
        (kitty_specs / "001-feature").mkdir()
        (kitty_specs / "003-feature").mkdir()
        (kitty_specs / "002-feature").mkdir()

        # Execute
        result = _find_feature_directory(tmp_path, tmp_path)

        # Verify
        assert result == kitty_specs / "003-feature"

    @patch("specify_cli.cli.commands.agent.feature.is_worktree_context")
    def test_raises_error_when_no_features_in_main_repo(
        self, mock_is_worktree: Mock, tmp_path: Path
    ):
        """Should raise error when no features exist in main repo."""
        # Setup
        from specify_cli.cli.commands.agent.feature import _find_feature_directory

        mock_is_worktree.return_value = False

        # Create empty kitty-specs
        kitty_specs = tmp_path / "kitty-specs"
        kitty_specs.mkdir()

        # Execute & Verify (updated to match centralized error message)
        with pytest.raises(ValueError, match="No features found"):
            _find_feature_directory(tmp_path, tmp_path)

    @patch("specify_cli.cli.commands.agent.feature.is_worktree_context")
    @patch("specify_cli.cli.commands.agent.feature.subprocess.run")
    def test_falls_back_when_branch_name_unavailable(
        self, mock_subprocess: Mock, mock_is_worktree: Mock, tmp_path: Path
    ):
        """Should fallback to any feature when git command fails."""
        # Setup
        from specify_cli.cli.commands.agent.feature import _find_feature_directory

        mock_is_worktree.return_value = True
        # Simulate git command failure
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git")

        # Create worktree structure
        kitty_specs = tmp_path / "kitty-specs"
        kitty_specs.mkdir()
        (kitty_specs / "001-test-feature").mkdir()

        # Execute
        result = _find_feature_directory(tmp_path, tmp_path)

        # Verify - should still find the feature via fallback
        assert result == kitty_specs / "001-test-feature"

    @patch("specify_cli.cli.commands.agent.feature.is_worktree_context")
    @patch("specify_cli.cli.commands.agent.feature.subprocess.run")
    def test_raises_error_when_kitty_specs_not_found_in_worktree(
        self, mock_subprocess: Mock, mock_is_worktree: Mock, tmp_path: Path
    ):
        """Should raise error when kitty-specs not found in worktree."""
        # Setup
        from specify_cli.cli.commands.agent.feature import _find_feature_directory

        mock_is_worktree.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stdout="001-test\n")

        # No kitty-specs directory created

        # Execute & Verify (updated to match centralized error message)
        with pytest.raises(ValueError, match="Feature directory not found"):
            _find_feature_directory(tmp_path, tmp_path / "nested")
