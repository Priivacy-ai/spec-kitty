"""Integration tests for change stack priority and merge coordination (WP06).

Tests merge coordination job triggers, no-trigger paths, and
consistency report fields through the CLI commands.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from specify_cli.cli.commands.agent.change import app as agent_change_app
from typer.testing import CliRunner

runner = CliRunner()


def _create_wp_file(
    tasks_dir: Path,
    wp_id: str,
    lane: str = "planned",
    change_stack: bool = False,
    dependencies: list[str] | None = None,
) -> None:
    """Helper to create a WP file."""
    tasks_dir.mkdir(parents=True, exist_ok=True)
    cs = "true" if change_stack else "false"
    deps = dependencies or []
    deps_yaml = "\n".join(f'  - "{d}"' for d in deps) if deps else ""
    dep_section = f"dependencies:\n{deps_yaml}" if deps else "dependencies: []"
    content = (
        f'---\nwork_package_id: "{wp_id}"\ntitle: "{wp_id} task"\n'
        f'lane: "{lane}"\nchange_stack: {cs}\n{dep_section}\n---\n# {wp_id}\n'
    )
    (tasks_dir / f"{wp_id}-task.md").write_text(content, encoding="utf-8")


class TestMergeCoordinationJobTrigger:
    """Test that merge coordination jobs appear when conditions are met."""

    def test_apply_with_active_dep_triggers_cross_dependency_job(
        self, tmp_path: Path
    ) -> None:
        """Apply referencing a doing WP should trigger a cross-dependency merge job."""
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

            # Should have a cross-dependency merge job
            merge_jobs = data["mergeCoordinationJobs"]
            cross_jobs = [
                j for j in merge_jobs if j.get("riskIndicator") == "cross_dependency"
            ]
            assert len(cross_jobs) >= 1
            assert "WP01" in cross_jobs[0]["targetWPs"]

    def test_apply_no_merge_jobs_when_no_risk(self, tmp_path: Path) -> None:
        """Apply with no risk indicators should produce no merge jobs."""
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
            assert data["mergeCoordinationJobs"] == []

    def test_apply_persists_merge_jobs_artifact(self, tmp_path: Path) -> None:
        """Apply with merge jobs should persist them to change-merge-jobs.json."""
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

            # If merge jobs were generated, artifact file should exist
            if data["mergeCoordinationJobs"]:
                feature_dir = tmp_path / "kitty-specs" / "029-test"
                jobs_file = feature_dir / "change-merge-jobs.json"
                assert jobs_file.exists()
                jobs_data = json.loads(jobs_file.read_text(encoding="utf-8"))
                assert jobs_data["jobCount"] >= 1


class TestReconcileMergeJobs:
    """Test reconcile endpoint merge job reporting."""

    def test_reconcile_includes_persisted_merge_jobs(self, tmp_path: Path) -> None:
        """Reconcile should include merge jobs from persisted artifact."""
        feature_dir = tmp_path / "kitty-specs" / "029-test"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Pre-create a merge jobs artifact
        jobs_file = feature_dir / "change-merge-jobs.json"
        jobs_file.write_text(
            json.dumps(
                {
                    "version": 1,
                    "featureDir": str(feature_dir),
                    "jobCount": 1,
                    "jobs": [
                        {
                            "jobId": "mcj-test",
                            "reason": "Test job",
                            "sourceWP": "WP09",
                            "targetWPs": ["WP03"],
                            "riskIndicator": "cross_dependency",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

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
            assert len(data["mergeCoordinationJobs"]) == 1
            assert data["mergeCoordinationJobs"][0]["jobId"] == "mcj-test"

    def test_reconcile_no_merge_jobs_when_none_exist(self, tmp_path: Path) -> None:
        """Reconcile without a jobs artifact should return empty list."""
        tasks_dir = tmp_path / "kitty-specs" / "029-test" / "tasks"
        tasks_dir.mkdir(parents=True)

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
            assert data["mergeCoordinationJobs"] == []


class TestConsistencyReportFields:
    """Test that consistency report has all required fields and correct values."""

    def test_consistency_report_has_all_fields(self, tmp_path: Path) -> None:
        """Consistency report should include all spec'd fields."""
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
                    "add caching",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            consistency = data["consistency"]

            # All required fields
            assert "updatedTasksDoc" in consistency
            assert "dependencyValidationPassed" in consistency
            assert "brokenLinksFixed" in consistency
            assert "issues" in consistency
            assert "wpSectionsAdded" in consistency
            assert "wpSectionsUpdated" in consistency

            # Types
            assert isinstance(consistency["updatedTasksDoc"], bool)
            assert isinstance(consistency["dependencyValidationPassed"], bool)
            assert isinstance(consistency["brokenLinksFixed"], int)
            assert isinstance(consistency["issues"], list)
            assert isinstance(consistency["wpSectionsAdded"], int)
            assert isinstance(consistency["wpSectionsUpdated"], int)
