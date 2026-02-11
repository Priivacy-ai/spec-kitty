"""Integration tests for change command main stash flow (WP06).

Tests end-to-end reconciliation and merge coordination through the
CLI apply and reconcile commands using real stash routing.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from specify_cli.cli.commands.agent.change import app as agent_change_app
from typer.testing import CliRunner

runner = CliRunner()


def _create_wp_file(
    tasks_dir: Path, wp_id: str, lane: str = "planned", change_stack: bool = False
) -> None:
    """Helper to create a WP file."""
    tasks_dir.mkdir(parents=True, exist_ok=True)
    cs = "true" if change_stack else "false"
    content = (
        f'---\nwork_package_id: "{wp_id}"\ntitle: "{wp_id} task"\n'
        f'lane: "{lane}"\nchange_stack: {cs}\ndependencies: []\n---\n# {wp_id}\n'
    )
    (tasks_dir / f"{wp_id}-task.md").write_text(content, encoding="utf-8")


class TestApplyReconciliation:
    """Test that apply triggers reconciliation and produces consistency report."""

    def test_apply_reconciles_tasks_doc(self, tmp_path: Path) -> None:
        """Apply should reconcile tasks.md and report consistency."""
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

            # Consistency report should be present and valid
            consistency = data["consistency"]
            assert "updatedTasksDoc" in consistency
            assert "dependencyValidationPassed" in consistency
            assert "brokenLinksFixed" in consistency
            assert isinstance(consistency["issues"], list)

    def test_apply_with_open_wp_ref_produces_deps_and_consistency(
        self, tmp_path: Path
    ) -> None:
        """Apply referencing an open WP should validate deps and reconcile."""
        tasks_dir = tmp_path / "kitty-specs" / "029-test" / "tasks"
        _create_wp_file(tasks_dir, "WP01", "doing")

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

            # Dependencies extracted
            created = data["createdWorkPackages"]
            assert len(created) >= 1
            assert "WP01" in created[0]["dependencies"]

            # Consistency should pass
            assert data["consistency"]["dependencyValidationPassed"] is True

    def test_apply_creates_tasks_md_with_wp_section(self, tmp_path: Path) -> None:
        """Apply should create or update tasks.md with the generated WP section."""
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

            # tasks.md should exist and contain the generated WP
            feature_dir = tmp_path / "kitty-specs" / "029-test"
            tasks_md = feature_dir / "tasks.md"
            assert tasks_md.exists()
            content = tasks_md.read_text(encoding="utf-8")
            assert "Change Stack" in content

    def test_apply_broken_links_are_fixed_in_file(self, tmp_path: Path) -> None:
        """Apply should actually remove broken prompt links from tasks.md."""
        tasks_dir = tmp_path / "kitty-specs" / "029-test" / "tasks"
        tasks_dir.mkdir(parents=True)
        feature_dir = tmp_path / "kitty-specs" / "029-test"

        # Pre-populate tasks.md with a broken link
        (feature_dir / "tasks.md").write_text(
            "# Tasks\n\n**Prompt**: `tasks/WP99-nonexistent.md`\n\nKeep this\n",
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

            result = runner.invoke(
                agent_change_app,
                [
                    "apply",
                    "test-id",
                    "--request-text",
                    "add caching to API",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["consistency"]["brokenLinksFixed"] >= 1

            # Verify the broken link was removed from the actual file
            content = (feature_dir / "tasks.md").read_text(encoding="utf-8")
            assert "`tasks/WP99-nonexistent.md`" not in content
            assert "Keep this" in content


class TestReconcileEndpoint:
    """Test the reconcile CLI endpoint for consistency reporting."""

    def test_reconcile_returns_consistency_report(self, tmp_path: Path) -> None:
        """Reconcile should return a complete consistency report."""
        tasks_dir = tmp_path / "kitty-specs" / "029-test" / "tasks"
        tasks_dir.mkdir(parents=True)
        _create_wp_file(tasks_dir, "WP01", "doing")

        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.cli.commands.agent.change.detect_feature_slug"
            ) as mock_slug,
        ):
            mock_root.return_value = tmp_path
            mock_slug.return_value = "029-test"

            result = runner.invoke(
                agent_change_app,
                ["reconcile", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "consistency" in data
            consistency = data["consistency"]
            assert "dependencyValidationPassed" in consistency
            assert "brokenLinksFixed" in consistency

    def test_reconcile_zero_issues_when_clean(self, tmp_path: Path) -> None:
        """Reconcile on a clean setup should have zero issues."""
        tasks_dir = tmp_path / "kitty-specs" / "029-test" / "tasks"
        _create_wp_file(tasks_dir, "WP01", "done")
        _create_wp_file(tasks_dir, "WP02", "planned")

        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.cli.commands.agent.change.detect_feature_slug"
            ) as mock_slug,
        ):
            mock_root.return_value = tmp_path
            mock_slug.return_value = "029-test"

            result = runner.invoke(
                agent_change_app,
                ["reconcile", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["consistency"]["dependencyValidationPassed"] is True
            assert data["consistency"]["issues"] == []
