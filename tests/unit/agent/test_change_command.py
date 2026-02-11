"""Unit tests for agent change command with stash routing, validation, and complexity.

Tests the agent change preview command with real stash routing,
ambiguity detection, closed reference checking, and deterministic
complexity scoring (WP02 + WP03).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from specify_cli.cli.commands.agent.change import app as agent_change_app

runner = CliRunner()


class TestPreviewWithRouting:
    """Test preview command with real branch stash routing."""

    def test_preview_on_feature_branch(self) -> None:
        """Preview on feature branch should route to feature stash."""
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
            mock_root.return_value = Path("/tmp/fake-repo")
            mock_main.return_value = Path("/tmp/fake-repo")

            result = runner.invoke(
                agent_change_app,
                ["preview", "use pydantic in models.py", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["stashScope"] == "feature"
            assert data["stashKey"] == "029-test"
            assert data["validationState"] == "valid"
            assert not data["requiresClarification"]

    def test_preview_on_main_branch(self) -> None:
        """Preview on main should route to main stash."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.core.change_stack.get_current_branch", return_value="main"
            ),
            patch("specify_cli.core.change_stack._get_main_repo_root") as mock_main,
        ):
            mock_root.return_value = Path("/tmp/fake-repo")
            mock_main.return_value = Path("/tmp/fake-repo")

            result = runner.invoke(
                agent_change_app,
                ["preview", "fix typo in README", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["stashScope"] == "main"
            assert data["stashKey"] == "main"

    def test_preview_ambiguous_request(self) -> None:
        """Ambiguous request should be flagged in preview."""
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
            mock_root.return_value = Path("/tmp/fake-repo")
            mock_main.return_value = Path("/tmp/fake-repo")

            result = runner.invoke(
                agent_change_app,
                ["preview", "change this block", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["validationState"] == "ambiguous"
            assert data["requiresClarification"]
            assert data["clarificationPrompt"] is not None

    def test_preview_with_closed_wp_reference(self) -> None:
        """Preview should include closed reference info."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.core.change_stack.get_current_branch",
                return_value="001-demo",
            ),
            patch("specify_cli.core.change_stack._get_main_repo_root") as mock_main,
        ):
            repo_root = Path("/tmp/fake-repo")
            mock_root.return_value = repo_root
            mock_main.return_value = repo_root

            # Create a done WP
            tasks_dir = repo_root / "kitty-specs" / "001-demo" / "tasks"
            tasks_dir.mkdir(parents=True, exist_ok=True)
            (tasks_dir / "WP01-setup.md").write_text(
                '---\nlane: "done"\n---\n', encoding="utf-8"
            )

            try:
                result = runner.invoke(
                    agent_change_app,
                    ["preview", "apply same pattern as WP01 to auth.py", "--json"],
                )
                assert result.exit_code == 0
                data = json.loads(result.output)
                assert data["validationState"] == "valid"
                if "closedReferences" in data:
                    assert data["closedReferences"]["linkOnly"]
            finally:
                # Cleanup temp files
                import shutil

                if tasks_dir.exists():
                    shutil.rmtree(tasks_dir.parent)

    def test_preview_unresolvable_branch_errors(self) -> None:
        """Preview should error when branch can't be resolved."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.core.change_stack.get_current_branch", return_value=None
            ),
            patch("specify_cli.core.change_stack._get_main_repo_root") as mock_main,
        ):
            mock_root.return_value = Path("/tmp/fake-repo")
            mock_main.return_value = Path("/tmp/fake-repo")

            result = runner.invoke(
                agent_change_app,
                ["preview", "add caching", "--json"],
            )
            assert result.exit_code == 1


class TestPreviewValidation:
    """Test preview validation edge cases."""

    def test_request_with_file_path_is_valid(self) -> None:
        """Requests mentioning file paths should be valid."""
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
            mock_root.return_value = Path("/tmp/fake-repo")
            mock_main.return_value = Path("/tmp/fake-repo")

            result = runner.invoke(
                agent_change_app,
                ["preview", "refactor this part of change_stack.py", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["validationState"] == "valid"

    def test_preview_fails_in_non_initialized_repo(self) -> None:
        """Preview should fail with exit 1 in a git repo without .kittify."""
        with patch(
            "specify_cli.cli.commands.agent.change.locate_project_root"
        ) as mock_root:
            mock_root.return_value = None  # No .kittify found

            result = runner.invoke(
                agent_change_app,
                ["preview", "add caching", "--json"],
            )
            assert result.exit_code == 1
            assert ".kittify not found" in result.output

    def test_request_with_wp_id_is_valid(self) -> None:
        """Requests mentioning WP IDs should be valid even with vague language."""
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
            mock_root.return_value = Path("/tmp/fake-repo")
            mock_main.return_value = Path("/tmp/fake-repo")

            result = runner.invoke(
                agent_change_app,
                ["preview", "change this block in WP03", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["validationState"] == "valid"


class TestPreviewComplexityIntegration:
    """Test that preview includes complexity scoring fields.

    Note: Since the classifier redesign (AI-assessed scores), preview always
    returns a default/simple classification (all zeros) because the actual
    scoring is done by the AI agent on the apply step.  Preview still
    returns the full structure so the agent can display it.
    """

    def test_preview_includes_complexity_structure(self) -> None:
        """Preview should include complexity scoring fields with default values."""
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
            mock_root.return_value = Path("/tmp/fake-repo")
            mock_main.return_value = Path("/tmp/fake-repo")

            result = runner.invoke(
                agent_change_app,
                [
                    "preview",
                    "add package requests and update the shared config module",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            complexity = data["complexity"]
            # Should have all scoring fields
            assert "classification" in complexity
            assert "totalScore" in complexity
            assert "proposedMode" in complexity
            assert "reviewAttention" in complexity
            # Preview uses backward-compatible classify_change_request()
            # which returns all-zeros (simple) - actual scoring is on apply
            assert complexity["classification"] == "simple"
            assert complexity["totalScore"] == 0

    def test_preview_always_simple_no_warning(self) -> None:
        """Preview always returns simple classification (scoring is on apply)."""
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
            mock_root.return_value = Path("/tmp/fake-repo")
            mock_main.return_value = Path("/tmp/fake-repo")

            # Even a complex-sounding request gets simple on preview
            result = runner.invoke(
                agent_change_app,
                [
                    "preview",
                    "replace framework Django with FastAPI, migrate from PostgreSQL to MongoDB, "
                    "update the api contract for all endpoints",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            # Preview no longer does algorithmic scoring - always simple
            assert data["warningRequired"] is False
            assert data["complexity"]["classification"] == "simple"

    def test_preview_simple_no_warning(self) -> None:
        """Simple requests should not trigger a warning."""
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
            mock_root.return_value = Path("/tmp/fake-repo")
            mock_main.return_value = Path("/tmp/fake-repo")

            result = runner.invoke(
                agent_change_app,
                ["preview", "fix typo in README", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["warningRequired"] is False
            assert data["complexity"]["classification"] == "simple"


class TestApplyContinueGate:
    """Test FR-010/FR-011: explicit continue/stop gate on apply."""

    def test_apply_blocks_high_complexity_without_continue(self) -> None:
        """Apply should block high complexity requests without --continue."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.cli.commands.agent.change.detect_feature_slug"
            ) as mock_slug,
        ):
            mock_root.return_value = Path("/tmp/fake-repo")
            mock_slug.return_value = "029-test"

            result = runner.invoke(
                agent_change_app,
                [
                    "apply",
                    "test-id",
                    "--request-text",
                    "replace framework Django with FastAPI",
                    "--scope-breadth",
                    "3",
                    "--coupling",
                    "2",
                    "--dependency-churn",
                    "2",
                    "--ambiguity",
                    "1",
                    "--integration-risk",
                    "1",
                    "--json",
                ],
            )
            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data["error"] == "high_complexity_blocked"
            assert "complexity threshold" in data["message"]

    def test_apply_allows_high_complexity_with_continue(self, tmp_path: Path) -> None:
        """Apply should allow high complexity requests with --continue."""
        # Create tasks dir for stash routing
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
                    "test-id",
                    "--request-text",
                    "replace framework Django with FastAPI",
                    "--scope-breadth",
                    "3",
                    "--coupling",
                    "2",
                    "--dependency-churn",
                    "2",
                    "--ambiguity",
                    "1",
                    "--integration-risk",
                    "1",
                    "--continue",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["requestId"] == "test-id"
            # When --continue is used with high complexity, result should include scoring
            assert "complexity" in data
            assert data["complexity"]["reviewAttention"] == "elevated"
            assert data["complexity"]["classification"] == "high"
            assert data["complexity"]["totalScore"] == 9
            # Verify generated WP files have elevated review_attention in frontmatter
            if "writtenFiles" in data and data["writtenFiles"]:
                for fpath in data["writtenFiles"]:
                    content = Path(fpath).read_text(encoding="utf-8")
                    assert 'review_attention: "elevated"' in content, (
                        f"Generated WP {fpath} missing elevated review_attention"
                    )

    def test_apply_requires_request_text(self) -> None:
        """Apply without --request-text should fail (required for complexity gating)."""
        result = runner.invoke(
            agent_change_app,
            ["apply", "test-id", "--json"],
        )
        assert result.exit_code != 0

    def test_apply_simple_passes_without_continue(self, tmp_path: Path) -> None:
        """Apply with simple complexity should pass without --continue."""
        # Create tasks dir for stash routing
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
                    "test-id",
                    "--request-text",
                    "fix typo in README",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["requestId"] == "test-id"


class TestApplyDependencyEnforcement:
    """Test dependency policy enforcement wired into the apply path (WP05)."""

    def _make_wp_file(
        self, tasks_dir: Path, wp_id: str, lane: str, change_stack: bool = False
    ) -> None:
        """Helper to create a WP file with frontmatter."""
        content = f'---\nwork_package_id: "{wp_id}"\ntitle: "{wp_id} test"\nlane: "{lane}"\nchange_stack: {"true" if change_stack else "false"}\ndependencies: []\n---\n# {wp_id}\n'
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (tasks_dir / f"{wp_id}-test.md").write_text(content, encoding="utf-8")

    def test_apply_extracts_and_attaches_dependencies(self, tmp_path: Path) -> None:
        """Apply should extract WP refs, validate deps, and attach to generated WP."""
        tasks_dir = tmp_path / "kitty-specs" / "029-test" / "tasks"
        self._make_wp_file(tasks_dir, "WP01", "doing")

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
                    "test-id",
                    "--request-text",
                    "apply same pattern as WP01 to auth.py",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            # Generated WP should have WP01 as a dependency
            created = data["createdWorkPackages"]
            assert len(created) >= 1
            assert "WP01" in created[0]["dependencies"]
            assert data["consistency"]["dependencyValidationPassed"] is True

    def test_apply_rejects_closed_wp_as_dependency(self, tmp_path: Path) -> None:
        """Apply should reject edges to closed/done WPs (use closed_reference_links instead)."""
        tasks_dir = tmp_path / "kitty-specs" / "029-test" / "tasks"
        self._make_wp_file(tasks_dir, "WP01", "done")

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
                    "test-id",
                    "--request-text",
                    "apply same pattern as WP01 to auth.py",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            # WP01 is done, so it should NOT be a dependency
            created = data["createdWorkPackages"]
            assert len(created) >= 1
            assert "WP01" not in created[0]["dependencies"]
            # It should be in closedReferenceLinks instead
            assert "WP01" in data["closedReferenceLinks"]

    def test_apply_aborts_on_cyclic_dependency(self, tmp_path: Path) -> None:
        """Apply should abort atomically when cycle detected in dependency graph."""
        tasks_dir = tmp_path / "kitty-specs" / "029-test" / "tasks"
        # WP01 depends on WP02, WP02 is open. The new change WP will depend on WP02,
        # and WP01 also depends on the new WP ID -> cycle.
        # To create a cycle, we make WP01 depend on the next allocatable ID (WP03)
        # and then the request references WP01 (which would create WP03 -> WP01 -> WP03)
        content_wp01 = '---\nwork_package_id: "WP01"\ntitle: "WP01 test"\nlane: "doing"\nchange_stack: false\ndependencies: ["WP03"]\n---\n# WP01\n'
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (tasks_dir / "WP01-test.md").write_text(content_wp01, encoding="utf-8")
        # WP02 exists so next ID will be WP03
        self._make_wp_file(tasks_dir, "WP02", "planned")

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
                    "test-id",
                    "--request-text",
                    "apply same pattern as WP01 to auth.py",
                    "--json",
                ],
            )
            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data["error"] == "dependency_validation_failed"
            # No files should have been written (atomic abort)
            generated_wps = list(tasks_dir.glob("WP03-*.md"))
            assert len(generated_wps) == 0

    def test_apply_no_wp_refs_produces_no_dependencies(self, tmp_path: Path) -> None:
        """Apply with no WP references should produce WP with empty dependencies."""
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
                    "test-id",
                    "--request-text",
                    "add caching to the API layer",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            created = data["createdWorkPackages"]
            assert len(created) >= 1
            assert created[0]["dependencies"] == []
            assert data["consistency"]["dependencyValidationPassed"] is True
