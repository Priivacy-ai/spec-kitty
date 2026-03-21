"""Unit tests for agent feature CLI commands."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.feature import app

pytestmark = pytest.mark.fast

runner = CliRunner()


class TestBranchContextCommand:
    """Tests for branch-context command."""

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature.is_git_repo")
    @patch("specify_cli.cli.commands.agent.feature.get_current_branch")
    def test_branch_context_json_output(
        self,
        mock_branch: Mock,
        mock_is_git: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ) -> None:
        """Should resolve deterministic branch contract in JSON."""
        mock_locate.return_value = tmp_path
        mock_is_git.return_value = True
        mock_branch.return_value = "2.x"

        result = runner.invoke(
            app,
            ["branch-context", "--json", "--target-branch", "release/2.x"],
        )

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["result"] == "success"
        assert output["repo_root"] == str(tmp_path.resolve())
        assert output["current_branch"] == "2.x"
        assert output["target_branch"] == "release/2.x"
        assert output["planning_base_branch"] == "release/2.x"
        assert output["merge_target_branch"] == "release/2.x"
        assert output["branch_matches_target"] is False
        assert output["target_branch_source"] == "cli_arg"


class TestCreateFeatureCommand:
    """Tests for create-feature command."""

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature.is_git_repo")
    @patch("specify_cli.cli.commands.agent.feature.get_current_branch")
    @patch("specify_cli.cli.commands.agent.feature.get_next_feature_number")
    @patch("specify_cli.cli.commands.agent.feature._commit_to_branch")
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
        assert output["current_branch"] == "main"
        assert output["target_branch"] == "main"
        assert output["base_branch"] == "main"
        assert output["planning_base_branch"] == "main"
        assert output["merge_target_branch"] == "main"
        assert output["branch_matches_target"] is True
        assert "Completed worktree changes must merge into main." in output["branch_strategy_summary"]
        assert output["TARGET_BRANCH"] == "main"
        assert output["BASE_BRANCH"] == "main"

        # Verify feature directory was created
        feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
        assert feature_dir.exists()
        assert (feature_dir / "spec.md").exists()

        # meta.json should exist for all missions (not only documentation)
        meta_path = feature_dir / "meta.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["feature_number"] == "001"
        assert meta["slug"] == "001-test-feature"
        assert meta["feature_slug"] == "001-test-feature"
        assert meta["mission"] == "software-dev"
        assert meta["target_branch"] == "main"
    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature.is_git_repo")
    @patch("specify_cli.cli.commands.agent.feature.get_current_branch")
    @patch("specify_cli.cli.commands.agent.feature.get_next_feature_number")
    @patch("specify_cli.cli.commands.agent.feature._commit_to_branch")
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

    @patch("specify_cli.cli.commands.agent.feature.is_worktree_context")
    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature.Path.cwd")
    def test_blocks_create_feature_from_worktree_with_main_repo_hint(
        self,
        mock_cwd: Mock,
        mock_locate: Mock,
        mock_is_worktree: Mock,
    ) -> None:
        """Should print main repo hint when worktree context is detected."""
        mock_cwd.return_value = Path("/tmp/external-worktree")
        mock_is_worktree.return_value = True
        mock_locate.return_value = Path("/tmp/main-repo")

        result = runner.invoke(app, ["create-feature", "test-feature"])

        assert result.exit_code == 1
        assert "Cannot create features from inside a worktree" in result.stdout
        assert "Run from the main repository instead:" in result.stdout
        assert "cd " in result.stdout
        assert "/main-repo" in result.stdout
        assert "spec-kitty agent create-feature test-feature" in result.stdout

    @patch("specify_cli.cli.commands.agent.feature.is_worktree_context")
    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature.Path.cwd")
    def test_blocks_create_feature_from_worktree_with_worktrees_fallback_hint(
        self,
        mock_cwd: Mock,
        mock_locate: Mock,
        mock_is_worktree: Mock,
    ) -> None:
        """Should fall back to .worktrees path slicing when main repo lookup fails."""
        mock_cwd.return_value = Path("/tmp/main-repo/.worktrees/feature-001")
        mock_is_worktree.return_value = True
        mock_locate.return_value = None

        result = runner.invoke(app, ["create-feature", "test-feature"])

        assert result.exit_code == 1
        assert "Cannot create features from inside a worktree" in result.stdout
        assert "Run from the main repository instead:" in result.stdout
        assert "cd " in result.stdout
        assert "/main-repo" in result.stdout
        assert "spec-kitty agent create-feature test-feature" in result.stdout

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
    @patch("specify_cli.cli.commands.agent.feature.get_next_feature_number")
    @patch("specify_cli.cli.commands.agent.feature._commit_to_branch")
    def test_allows_feature_creation_from_any_branch(
        self, mock_commit: Mock, mock_get_number: Mock, mock_branch: Mock,
        mock_is_git: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should allow feature creation on any branch (records it as target)."""
        # Setup: On non-main branch — should succeed (not block)
        mock_locate.return_value = tmp_path
        mock_is_git.return_value = True
        mock_branch.return_value = "develop"
        mock_get_number.return_value = 1

        # Create necessary directories
        (tmp_path / ".kittify" / "templates").mkdir(parents=True)
        (tmp_path / ".kittify" / "templates" / "spec-template.md").write_text("# Spec Template")

        # Execute
        result = runner.invoke(app, ["create-feature", "test-feature", "--json"])

        # Verify — should succeed, recording "develop" as target_branch
        assert result.exit_code == 0
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert output["result"] == "success"

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature.is_git_repo")
    @patch("specify_cli.cli.commands.agent.feature.get_current_branch")
    @patch("specify_cli.cli.commands.agent.feature.get_next_feature_number")
    @patch("specify_cli.cli.commands.agent.feature._commit_to_branch")
    def test_creates_feature_on_primary_branch(
        self, mock_commit: Mock, mock_get_number: Mock, mock_branch: Mock,
        mock_is_git: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should allow feature creation on the primary branch."""
        # Setup: On primary branch
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
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert output["result"] == "success"


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
        assert output["current_branch"] == "main"
        assert output["target_branch"] == "main"
        assert output["branch_matches_target"] is True

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
        assert output["spec_file"] == paths["spec_file"]
        assert output["current_branch"] == "main"
        assert output["target_branch"] == "main"
        assert output["base_branch"] == "main"
        assert output["branch_matches_target"] is True
        assert output["TARGET_BRANCH"] == "main"
        assert output["BASE_BRANCH"] == "main"
        assert "runtime_vars" in output
        assert "now_utc_iso" in output["runtime_vars"]
        assert output["FEATURE_SPEC"] == paths["spec_file"]
        assert "SPECS_DIR" in output
        assert "spec_kitty_version" in output

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
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature.validate_feature_structure")
    def test_passes_explicit_feature_to_detection(
        self, mock_validate: Mock, mock_find: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should pass --feature to detection with strict context fallback disabled."""
        mock_locate.return_value = tmp_path
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        mock_find.return_value = feature_dir
        mock_validate.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "paths": {"feature_dir": str(feature_dir)},
        }

        result = runner.invoke(
            app,
            [
                "check-prerequisites",
                "--feature",
                "001-test",
                "--json",
                "--paths-only",
                "--include-tasks",
            ],
        )

        assert result.exit_code == 0
        mock_find.assert_called_once()
        args, kwargs = mock_find.call_args
        assert args[0] == tmp_path
        assert isinstance(args[1], Path)
        assert kwargs["explicit_feature"] == "001-test"

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    def test_returns_context_remediation_payload_when_ambiguous(
        self, mock_find: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should return deterministic remediation payload on ambiguous context."""
        mock_locate.return_value = tmp_path
        mock_find.side_effect = ValueError("Multiple features found")

        feature_a = tmp_path / "kitty-specs" / "001-alpha"
        feature_b = tmp_path / "kitty-specs" / "002-beta"
        feature_a.mkdir(parents=True)
        feature_b.mkdir(parents=True)
        (feature_a / "spec.md").write_text("# Alpha", encoding="utf-8")
        (feature_b / "spec.md").write_text("# Beta", encoding="utf-8")

        result = runner.invoke(
            app,
            ["check-prerequisites", "--json", "--paths-only", "--include-tasks"],
        )

        assert result.exit_code == 1
        payload = json.loads(result.stdout.strip().split("\n")[0])
        assert payload["error_code"] == "FEATURE_CONTEXT_UNRESOLVED"
        assert payload["available_features"] == ["001-alpha", "002-beta"]
        assert "check-prerequisites --feature" in payload["example_command"]
        assert payload["remediation"] == "Re-run with --feature <slug>"

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

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    def test_emits_single_json_object_on_detection_error(
        self,
        mock_find: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """Regression guard: detection errors should not emit duplicate JSON payloads."""
        mock_locate.return_value = tmp_path
        mock_find.side_effect = ValueError("Multiple features found")

        result = runner.invoke(app, ["check-prerequisites", "--json"])

        assert result.exit_code == 1
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert payload["error_code"] == "FEATURE_CONTEXT_UNRESOLVED"


class TestGitPreflightEnforcement:
    """Tests for _enforce_git_preflight integration in feature commands."""

    @patch("specify_cli.cli.commands.agent.feature.run_git_preflight")
    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    def test_check_prerequisites_exits_on_preflight_failure_json(
        self, mock_locate: Mock, mock_preflight: Mock, tmp_path: Path
    ):
        """check-prerequisites should emit JSON remediation payload on preflight failure."""
        from specify_cli.core.git_preflight import GitPreflightIssue, GitPreflightResult

        (tmp_path / ".git").mkdir()
        mock_locate.return_value = tmp_path

        failed_result = GitPreflightResult(repo_root=tmp_path)
        failed_result.errors.append(
            GitPreflightIssue(
                code="UNTRUSTED_REPOSITORY",
                check="repository_trust",
                message="Git rejected repository ownership trust (safe.directory).",
                remediation="Mark the repository as trusted.",
                command=f"git config --global --add safe.directory '{tmp_path}'",
            )
        )
        mock_preflight.return_value = failed_result

        result = runner.invoke(app, ["check-prerequisites", "--json"])

        assert result.exit_code == 1
        payload = json.loads(result.stdout.strip().split("\n")[0])
        assert payload["error_code"] == "GIT_PREFLIGHT_FAILED"
        assert isinstance(payload["remediation"], list)
        assert len(payload["remediation"]) >= 1

    @patch("specify_cli.cli.commands.agent.feature.run_git_preflight")
    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    def test_check_prerequisites_exits_on_preflight_failure_human(
        self, mock_locate: Mock, mock_preflight: Mock, tmp_path: Path
    ):
        """check-prerequisites should print human-readable error on preflight failure."""
        from specify_cli.core.git_preflight import GitPreflightIssue, GitPreflightResult

        (tmp_path / ".git").mkdir()
        mock_locate.return_value = tmp_path

        failed_result = GitPreflightResult(repo_root=tmp_path)
        failed_result.errors.append(
            GitPreflightIssue(
                code="UNTRUSTED_REPOSITORY",
                check="repository_trust",
                message="Git rejected repository ownership trust (safe.directory).",
                remediation="Mark the repository as trusted.",
                command="git config --global --add safe.directory /repo",
            )
        )
        mock_preflight.return_value = failed_result

        result = runner.invoke(app, ["check-prerequisites"])

        assert result.exit_code == 1
        assert "Git rejected repository ownership trust" in result.stdout

    @patch("specify_cli.cli.commands.agent.feature.run_git_preflight")
    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    def test_setup_plan_exits_on_preflight_failure_json(
        self, mock_locate: Mock, mock_preflight: Mock, tmp_path: Path
    ):
        """setup-plan should emit JSON remediation payload on preflight failure."""
        from specify_cli.core.git_preflight import GitPreflightIssue, GitPreflightResult

        (tmp_path / ".git").mkdir()
        mock_locate.return_value = tmp_path

        failed_result = GitPreflightResult(repo_root=tmp_path)
        failed_result.errors.append(
            GitPreflightIssue(
                code="UNTRUSTED_REPOSITORY",
                check="repository_trust",
                message="Git rejected repository ownership trust (safe.directory).",
                remediation="Mark the repository as trusted.",
                command="git config --global --add safe.directory /repo",
            )
        )
        mock_preflight.return_value = failed_result

        result = runner.invoke(app, ["setup-plan", "--json"])

        assert result.exit_code == 1
        payload = json.loads(result.stdout.strip().split("\n")[0])
        assert payload["error_code"] == "GIT_PREFLIGHT_FAILED"


class TestFinalizeTasksCommand:
    """Tests for finalize-tasks command."""

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature._show_branch_context")
    def test_passes_explicit_feature_to_detection(
        self,
        mock_show_branch: Mock,
        mock_find: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """Should pass --feature to detection with strict context fallback disabled."""
        mock_locate.return_value = tmp_path
        mock_show_branch.return_value = (tmp_path, "main")
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        mock_find.return_value = feature_dir

        result = runner.invoke(app, ["finalize-tasks", "--feature", "001-test", "--json"])

        # Command exits because tasks/ is missing, but detection should be explicit and strict.
        assert result.exit_code == 1
        mock_find.assert_called_once()
        args, kwargs = mock_find.call_args
        assert args[0] == tmp_path
        assert isinstance(args[1], Path)
        assert kwargs["explicit_feature"] == "001-test"

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    def test_returns_context_remediation_payload_when_ambiguous(
        self, mock_find: Mock, mock_locate: Mock, tmp_path: Path
    ):
        """Should return deterministic remediation payload on ambiguous context."""
        mock_locate.return_value = tmp_path
        mock_find.side_effect = ValueError("Multiple features found")

        feature_a = tmp_path / "kitty-specs" / "001-alpha"
        feature_b = tmp_path / "kitty-specs" / "002-beta"
        feature_a.mkdir(parents=True)
        feature_b.mkdir(parents=True)
        (feature_a / "spec.md").write_text("# Alpha", encoding="utf-8")
        (feature_b / "spec.md").write_text("# Beta", encoding="utf-8")

        result = runner.invoke(app, ["finalize-tasks", "--json"])

        assert result.exit_code == 1
        payload = json.loads(result.stdout.strip().split("\n")[0])
        assert payload["error_code"] == "FEATURE_CONTEXT_UNRESOLVED"
        assert payload["available_features"] == ["001-alpha", "002-beta"]
        assert "finalize-tasks --feature" in payload["example_command"]
        assert payload["remediation"] == "Re-run with --feature <slug>"

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature._show_branch_context", return_value=(None, "main"))
    def test_fails_when_requirement_refs_missing(
        self,
        mock_show_branch: Mock,
        mock_find: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """Should fail with explicit payload when a WP has no requirement refs."""
        mock_locate.return_value = tmp_path

        feature_dir = tmp_path / "kitty-specs" / "001-test"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        mock_find.return_value = feature_dir

        (feature_dir / "spec.md").write_text(
            """# Spec
## Functional Requirements
| ID | Requirement | Acceptance Criteria | Status |
| --- | --- | --- | --- |
| FR-001 | Test requirement | Covered by WP01. | proposed |
""",
            encoding="utf-8",
        )
        (feature_dir / "tasks.md").write_text(
            "## Work Package WP01\n**Dependencies**: None\n",
            encoding="utf-8",
        )
        (tasks_dir / "WP01-test.md").write_text(
            """---
work_package_id: "WP01"
title: "WP01"
---

# WP01
""",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["finalize-tasks", "--json"])
        assert result.exit_code == 1

        payload = json.loads(result.stdout.strip().split("\n")[0])
        assert payload["error"] == "Requirement mapping validation failed"
        assert payload["missing_requirement_refs_wps"] == ["WP01"]

    def test_uses_wp_frontmatter_requirement_refs_when_tasks_md_missing_refs(self, tmp_path: Path):
        """Fallback should parse requirement_refs from WP frontmatter when tasks.md lacks them."""
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        (feature_dir / "spec.md").write_text(
            """# Spec
## Functional Requirements
| ID | Requirement | Acceptance Criteria | Status |
| --- | --- | --- | --- |
| FR-001 | First requirement | Covered by WP01. | proposed |
""",
            encoding="utf-8",
        )
        (feature_dir / "tasks.md").write_text(
            "## Work Package WP01\n**Dependencies**: None\n",
            encoding="utf-8",
        )
        (tasks_dir / "WP01-test.md").write_text(
            """---
work_package_id: "WP01"
title: "WP01"
requirement_refs:
  - FR-001
---

# WP01
""",
            encoding="utf-8",
        )

        with (
            patch(
                "specify_cli.cli.commands.agent.feature.locate_project_root",
                return_value=tmp_path,
            ),
            patch(
                "specify_cli.cli.commands.agent.feature._find_feature_directory",
                return_value=feature_dir,
            ),
            patch(
                "specify_cli.cli.commands.agent.feature._show_branch_context",
                return_value=(None, "main"),
            ),
            patch(
                "specify_cli.cli.commands.agent.feature.safe_commit",
                return_value=True,
            ),
            patch(
                "specify_cli.cli.commands.agent.feature.run_command",
                return_value=(0, "a" * 40, ""),
            ),
        ):
            result = runner.invoke(app, ["finalize-tasks", "--json"])

        assert result.exit_code == 0
        json_lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
        assert json_lines, f"Expected JSON output, got: {result.stdout!r}"
        payload = json.loads(json_lines[-1])
        assert payload["result"] == "success"
        assert payload["requirement_refs_parsed"]["WP01"] == ["FR-001"]
        updated = (tasks_dir / "WP01-test.md").read_text(encoding="utf-8")
        assert 'planning_base_branch: main' in updated
        assert 'merge_target_branch: main' in updated
        assert 'branch_strategy: Planning artifacts for this feature were generated on main.' in updated

class TestSetupPlanCommand:
    """Tests for setup-plan command."""

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature._show_branch_context", return_value=(None, "main"))
    @patch("specify_cli.cli.commands.agent.feature._commit_to_branch")
    def test_scaffolds_plan_template_json(
        self,
        mock_commit: Mock,
        mock_show_branch: Mock,
        mock_find: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """Should scaffold plan template and output JSON format."""
        # Setup
        mock_locate.return_value = tmp_path
        mock_show_branch.return_value = (tmp_path, "main")
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text("# Spec")
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
        assert output["feature_slug"] == "001-test"
        assert "plan_file" in output
        assert "feature_dir" in output
        assert output["spec_file"] == str(feature_dir / "spec.md")
        assert output["current_branch"] == "main"
        assert output["target_branch"] == "main"
        assert output["base_branch"] == "main"
        assert output["planning_base_branch"] == "main"
        assert output["merge_target_branch"] == "main"
        assert output["branch_matches_target"] is True
        assert output["TARGET_BRANCH"] == "main"
        assert output["BASE_BRANCH"] == "main"

        # Verify plan file was created
        plan_file = feature_dir / "plan.md"
        assert plan_file.exists()
        assert plan_file.read_text() == "# Implementation Plan Template"

        # Verify commit was called
        mock_commit.assert_called_once()

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature._show_branch_context", return_value=(None, "main"))
    @patch("specify_cli.cli.commands.agent.feature._commit_to_branch")
    def test_scaffolds_plan_template_human(
        self,
        mock_commit: Mock,
        mock_show_branch: Mock,
        mock_find: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """Should scaffold plan template and output human-readable format."""
        # Setup
        mock_locate.return_value = tmp_path
        mock_show_branch.return_value = (tmp_path, "main")
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text("# Spec")
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
    @patch("specify_cli.cli.commands.agent.feature._show_branch_context", return_value=(None, "main"))
    @patch("specify_cli.cli.commands.agent.feature.files")
    def test_errors_when_template_not_found(
        self,
        mock_files: Mock,
        mock_show_branch: Mock,
        mock_find: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """Should return error when plan template not found."""
        # Setup
        mock_locate.return_value = tmp_path
        mock_show_branch.return_value = (tmp_path, "main")
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text("# Spec")
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
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature._show_branch_context", return_value=(None, "main"))
    def test_errors_when_spec_missing(
        self,
        mock_show_branch: Mock,
        mock_find: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """Should return structured error when feature spec.md is missing."""
        # Setup
        mock_locate.return_value = tmp_path
        mock_show_branch.return_value = (tmp_path, "main")
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        feature_dir.mkdir(parents=True)
        mock_find.return_value = feature_dir

        # Execute
        result = runner.invoke(app, ["setup-plan", "--feature", "001-test", "--json"])

        # Verify
        assert result.exit_code == 1
        first_line = result.stdout.strip().split('\n')[0]
        output = json.loads(first_line)
        assert output["error_code"] == "SPEC_FILE_MISSING"
        assert output["feature_slug"] == "001-test"
        assert output["spec_file"] == str((feature_dir / "spec.md").resolve())
        assert "Restore the missing spec file" in "\n".join(output["remediation"])

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

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    def test_setup_plan_emits_single_json_object_on_detection_error(
        self,
        mock_find: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """Regression guard: setup-plan detection errors should not emit duplicate JSON payloads."""
        mock_locate.return_value = tmp_path
        mock_find.side_effect = ValueError("Multiple features found")

        result = runner.invoke(app, ["setup-plan", "--json"])

        assert result.exit_code == 1
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert payload["error_code"] == "PLAN_CONTEXT_UNRESOLVED"


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
    def test_multiple_features_require_explicit_selection(
        self, mock_is_worktree: Mock, tmp_path: Path
    ):
        """Mutating feature commands should not auto-select among multiple features."""
        from specify_cli.cli.commands.agent.feature import _find_feature_directory

        mock_is_worktree.return_value = False

        # Create main repo structure with multiple features
        kitty_specs = tmp_path / "kitty-specs"
        kitty_specs.mkdir()
        for slug, lane in (
            ("001-feature", "done"),
            ("002-feature", "done"),
            ("003-feature", "planned"),
        ):
            feature_dir = kitty_specs / slug
            tasks_dir = feature_dir / "tasks"
            tasks_dir.mkdir(parents=True)
            (tasks_dir / "WP01.md").write_text(
                f"---\nwork_package_id: WP01\ntitle: Test\nlane: {lane}\n---\n",
                encoding="utf-8",
            )

        with pytest.raises(ValueError, match="Please specify explicitly"):
            _find_feature_directory(tmp_path, tmp_path)

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
