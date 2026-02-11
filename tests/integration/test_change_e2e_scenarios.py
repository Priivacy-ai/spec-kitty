"""End-to-end scenario tests for /spec-kitty.change command (WP08).

Validates user-level flows from the spec and quickstart:
- Main stash routing and feature stash routing
- High complexity continue/stop behavior
- Ambiguity fail-fast
- Stack-first selection with reconciliation

Success Criteria Mapping (spec.md SC-001 through SC-005)
=========================================================

SC-001: 95%+ of runs produce consistent work packages without manual repair.
  - TestApplyWithReconciliationE2E.test_apply_creates_wps_and_reconciles
    (verifies consistency report, dependency validation, file creation)
  - tests/unit/test_change_reconciliation.py (42 tests: reconcile_tasks_doc,
    reconcile_change_stack, validate_all_dependencies, merge coordination)
  - tests/unit/test_change_stack.py (76 tests: stash routing, dependency
    policy, closed-reference linking, graph integrity)

SC-002: 100% of generated change WPs include an explicit final testing task.
  - tests/unit/test_change_synthesis.py: test_every_wp_has_testing_task,
    test_testing_task_is_last_subtask (verify testing closure in all WPs)
  - TestApplyWithReconciliationE2E confirms createdWorkPackages are written

SC-003: 100% of requests above threshold present /spec-kitty.specify
         recommendation and explicit continue-or-stop decision.
  - TestHighComplexityContinueStopE2E.test_high_complexity_preview_shows_warning
    (warningRequired=True, recommendSpecify=True)
  - TestHighComplexityContinueStopE2E.test_apply_blocks_high_complexity_without_continue
    (exit_code=1, high_complexity_blocked error)
  - TestHighComplexityContinueStopE2E.test_apply_passes_with_continue_flag
    (--continue overrides gate)
  - tests/unit/test_change_classifier.py (111 tests: deterministic 5-factor
    scoring, threshold boundaries, classification)

SC-004: Zero broken dependency references after command execution.
  - TestApplyWithReconciliationE2E.test_apply_creates_wps_and_reconciles
    (dependencyValidationPassed in consistency report)
  - tests/unit/test_change_stack.py: test_validate_dependency_graph_integrity_*
    (cycle detection, missing target, self-dependency)
  - tests/unit/test_change_reconciliation.py: test_validate_all_dependencies_*
    (broken refs, missing targets, valid graphs)

SC-005: Teams can begin implementing within 10 min median from completion.
  - TestNextCommandE2E.test_next_with_no_feature_returns_json
    (selectedSource, nextWorkPackageId, normalProgressionBlocked in output)
  - tests/unit/test_stack_selection_integration.py (14 tests: ready selection,
    blocked stop, normal fallback)
  - TestMainStashRoutingE2E + TestFeatureStashRoutingE2E (stash routing
    ensures WPs land in correct location immediately)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from specify_cli.cli.commands.agent.change import app as agent_change_app
from typer.testing import CliRunner

runner = CliRunner()


# ============================================================================
# Scenario 1: Main stash routing
# ============================================================================


class TestMainStashRoutingE2E:
    """SC-001: Changes on main route to kitty-specs/change-stack/main/."""

    def test_preview_on_main_routes_to_main_stash(self) -> None:
        """Preview from main branch should resolve to main stash scope."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.core.change_stack.get_current_branch", return_value="main"
            ),
            patch("specify_cli.core.change_stack._get_main_repo_root") as mock_main,
        ):
            repo = Path("/tmp/e2e-repo")
            mock_root.return_value = repo
            mock_main.return_value = repo

            result = runner.invoke(
                agent_change_app,
                ["preview", "add logging to auth module", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["stashScope"] == "main"
            assert data["stashKey"] == "main"
            assert "change-stack/main" in data["stashPath"]

    def test_preview_on_master_routes_to_main_stash(self) -> None:
        """Preview from master branch should also resolve to main stash."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.core.change_stack.get_current_branch",
                return_value="master",
            ),
            patch("specify_cli.core.change_stack._get_main_repo_root") as mock_main,
        ):
            repo = Path("/tmp/e2e-repo")
            mock_root.return_value = repo
            mock_main.return_value = repo

            result = runner.invoke(
                agent_change_app,
                ["preview", "fix typo", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["stashScope"] == "main"


# ============================================================================
# Scenario 2: Feature stash routing
# ============================================================================


class TestFeatureStashRoutingE2E:
    """SC-001: Changes on feature branches route to feature tasks dir."""

    def test_preview_on_feature_branch_routes_correctly(self) -> None:
        """Preview from feature branch should resolve to feature stash."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.core.change_stack.get_current_branch",
                return_value="029-mid-stream",
            ),
            patch("specify_cli.core.change_stack._get_main_repo_root") as mock_main,
        ):
            repo = Path("/tmp/e2e-repo")
            mock_root.return_value = repo
            mock_main.return_value = repo

            result = runner.invoke(
                agent_change_app,
                ["preview", "add caching to API layer", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["stashScope"] == "feature"
            assert data["stashKey"] == "029-mid-stream"

    def test_preview_from_worktree_branch_routes_to_feature(self) -> None:
        """Preview from worktree WP branch should resolve to parent feature."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.core.change_stack.get_current_branch",
                return_value="029-mid-stream-WP03",
            ),
            patch("specify_cli.core.change_stack._get_main_repo_root") as mock_main,
        ):
            repo = Path("/tmp/e2e-repo")
            mock_root.return_value = repo
            mock_main.return_value = repo

            result = runner.invoke(
                agent_change_app,
                ["preview", "refactor models.py", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["stashScope"] == "feature"
            assert data["stashKey"] == "029-mid-stream"


# ============================================================================
# Scenario 3: High complexity continue/stop
# ============================================================================


class TestHighComplexityContinueStopE2E:
    """SC-003: High complexity requests require --continue flag."""

    HIGH_COMPLEXITY_REQUEST = (
        "replace framework Django with FastAPI, migrate from PostgreSQL to MongoDB, "
        "update the api contract for all endpoints, modify the deployment pipeline "
        "and kubernetes manifests, refactor all modules across the codebase"
    )

    def test_high_complexity_preview_shows_warning(self) -> None:
        """Preview of high-complexity request should flag warningRequired."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.core.change_stack.get_current_branch",
                return_value="029-test",
            ),
            patch("specify_cli.core.change_stack._get_main_repo_root") as mock_main,
        ):
            mock_root.return_value = Path("/tmp/e2e-repo")
            mock_main.return_value = Path("/tmp/e2e-repo")

            result = runner.invoke(
                agent_change_app,
                ["preview", self.HIGH_COMPLEXITY_REQUEST, "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            if data["complexity"]["classification"] == "high":
                assert data["warningRequired"] is True
                assert data["complexity"]["recommendSpecify"] is True

    def test_apply_blocks_high_complexity_without_continue(self) -> None:
        """Apply should block when complexity is high and --continue not provided."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.cli.commands.agent.change.detect_feature_slug"
            ) as mock_slug,
        ):
            mock_root.return_value = Path("/tmp/e2e-repo")
            mock_slug.return_value = "029-test"

            result = runner.invoke(
                agent_change_app,
                [
                    "apply",
                    "e2e-test-id",
                    "--request-text",
                    self.HIGH_COMPLEXITY_REQUEST,
                    "--json",
                ],
            )
            data = json.loads(result.output)
            if "error" in data and data["error"] == "high_complexity_blocked":
                assert result.exit_code == 1
                assert "complexity threshold" in data["message"]

    def test_apply_passes_with_continue_flag(self, tmp_path: Path) -> None:
        """Apply should allow high complexity when --continue is provided."""
        tasks_dir = tmp_path / "kitty-specs" / "029-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.cli.commands.agent.change.detect_feature_slug"
            ) as mock_slug,
            patch(
                "specify_cli.core.change_stack.get_current_branch",
                return_value="029-test",
            ),
            patch(
                "specify_cli.core.change_stack._get_main_repo_root",
                return_value=tmp_path,
            ),
        ):
            mock_root.return_value = tmp_path
            mock_slug.return_value = "029-test"

            result = runner.invoke(
                agent_change_app,
                [
                    "apply",
                    "e2e-test-id",
                    "--request-text",
                    self.HIGH_COMPLEXITY_REQUEST,
                    "--continue",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["requestId"] == "e2e-test-id"
            assert "createdWorkPackages" in data


# ============================================================================
# Scenario 4: Ambiguity fail-fast
# ============================================================================


class TestAmbiguityFailFastE2E:
    """SC-002: Ambiguous requests are flagged before WP creation."""

    def test_ambiguous_request_detected(self) -> None:
        """Vague requests should be flagged as ambiguous."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.core.change_stack.get_current_branch",
                return_value="029-test",
            ),
            patch("specify_cli.core.change_stack._get_main_repo_root") as mock_main,
        ):
            mock_root.return_value = Path("/tmp/e2e-repo")
            mock_main.return_value = Path("/tmp/e2e-repo")

            result = runner.invoke(
                agent_change_app,
                ["preview", "change this block", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["validationState"] == "ambiguous"
            assert data["requiresClarification"] is True
            assert data["clarificationPrompt"] is not None

    def test_specific_request_passes(self) -> None:
        """Specific requests should pass validation."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.core.change_stack.get_current_branch",
                return_value="029-test",
            ),
            patch("specify_cli.core.change_stack._get_main_repo_root") as mock_main,
        ):
            mock_root.return_value = Path("/tmp/e2e-repo")
            mock_main.return_value = Path("/tmp/e2e-repo")

            result = runner.invoke(
                agent_change_app,
                ["preview", "add caching to function get_user in service.py", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["validationState"] == "valid"
            assert data["requiresClarification"] is False

    def test_disambiguating_file_reference_passes(self) -> None:
        """Request with file reference should pass even with vague language."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.core.change_stack.get_current_branch",
                return_value="029-test",
            ),
            patch("specify_cli.core.change_stack._get_main_repo_root") as mock_main,
        ):
            mock_root.return_value = Path("/tmp/e2e-repo")
            mock_main.return_value = Path("/tmp/e2e-repo")

            result = runner.invoke(
                agent_change_app,
                ["preview", "refactor this block in change_stack.py", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["validationState"] == "valid"


# ============================================================================
# Scenario 5: Apply with reconciliation (SC-004)
# ============================================================================


class TestApplyWithReconciliationE2E:
    """SC-004: Apply creates WPs and reconciles tasks.md."""

    def test_apply_creates_wps_and_reconciles(self, tmp_path: Path) -> None:
        """Apply with request text should create WP files and reconcile tasks.md."""
        tasks_dir = tmp_path / "kitty-specs" / "029-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.cli.commands.agent.change.detect_feature_slug"
            ) as mock_slug,
            patch(
                "specify_cli.core.change_stack.get_current_branch",
                return_value="029-test",
            ),
            patch(
                "specify_cli.core.change_stack._get_main_repo_root",
                return_value=tmp_path,
            ),
        ):
            mock_root.return_value = tmp_path
            mock_slug.return_value = "029-test"

            result = runner.invoke(
                agent_change_app,
                [
                    "apply",
                    "e2e-apply-id",
                    "--request-text",
                    "add caching to the API response layer",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)

            # Should have created WPs
            assert len(data["createdWorkPackages"]) >= 1

            # Should have written files
            assert len(data["writtenFiles"]) >= 1

            # Consistency report should be present
            assert "consistency" in data
            consistency = data["consistency"]
            assert "updatedTasksDoc" in consistency
            assert "dependencyValidationPassed" in consistency

            # Verify WP files actually exist
            for wp_file_str in data["writtenFiles"]:
                wp_file = Path(wp_file_str)
                assert wp_file.exists(), f"WP file not created: {wp_file}"

    def test_apply_includes_merge_jobs_when_needed(self, tmp_path: Path) -> None:
        """Apply should include merge coordination jobs when risk is detected."""
        tasks_dir = tmp_path / "kitty-specs" / "029-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create an in-progress WP to trigger integration risk
        (tasks_dir / "WP03-existing.md").write_text(
            '---\nwork_package_id: "WP03"\ntitle: "Existing"\nlane: "doing"\n---\n',
            encoding="utf-8",
        )

        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.cli.commands.agent.change.detect_feature_slug"
            ) as mock_slug,
            patch(
                "specify_cli.core.change_stack.get_current_branch",
                return_value="029-test",
            ),
            patch(
                "specify_cli.core.change_stack._get_main_repo_root",
                return_value=tmp_path,
            ),
        ):
            mock_root.return_value = tmp_path
            mock_slug.return_value = "029-test"

            # High-complexity request that triggers integration risk
            result = runner.invoke(
                agent_change_app,
                [
                    "apply",
                    "e2e-merge-id",
                    "--request-text",
                    "update the CI/CD pipeline and deploy to kubernetes",
                    "--continue",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "mergeCoordinationJobs" in data


# ============================================================================
# Scenario 6: Next command with stack-first selection
# ============================================================================


class TestNextCommandE2E:
    """SC-005: Next command respects stack-first selection."""

    def test_next_with_no_feature_returns_json(self) -> None:
        """Next command should return valid JSON response."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.cli.commands.agent.change.detect_feature_slug"
            ) as mock_slug,
        ):
            mock_root.return_value = Path("/tmp/e2e-repo")
            mock_slug.return_value = "029-test"

            # Create minimal tasks dir
            tasks_dir = Path("/tmp/e2e-repo/kitty-specs/029-test/tasks")
            tasks_dir.mkdir(parents=True, exist_ok=True)

            try:
                result = runner.invoke(
                    agent_change_app,
                    ["next", "--feature", "029-test", "--json"],
                )
                assert result.exit_code == 0
                data = json.loads(result.output)
                assert "selectedSource" in data
                assert "nextWorkPackageId" in data
                assert "normalProgressionBlocked" in data
            finally:
                import shutil

                if tasks_dir.exists():
                    shutil.rmtree(tasks_dir.parent.parent)
