"""Unit tests for agent task helper functions (2.x contract).

Extracted from test_tasks.py during test-detection-remediation.
These test active 2.x helpers: _find_feature_slug and status lane alias resolution.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app

runner = CliRunner()


class TestFindFeatureSlug:
    """Tests for _find_feature_slug helper."""

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks.Path.cwd")
    def test_find_from_cwd_with_kitty_specs(self, mock_cwd: Mock, mock_root: Mock, tmp_path: Path):
        """Should extract feature slug from cwd containing kitty-specs."""
        from specify_cli.cli.commands.agent.tasks import _find_feature_slug

        # Setup: cwd is in kitty-specs/feature-slug directory
        feature_dir = tmp_path / "kitty-specs" / "008-test-feature"
        feature_dir.mkdir(parents=True)

        mock_cwd.return_value = feature_dir
        mock_root.return_value = tmp_path

        with patch("specify_cli.core.feature_detection._get_main_repo_root") as mock_main:
            mock_main.return_value = tmp_path

            slug = _find_feature_slug()
            assert slug == "008-test-feature"

    @patch("subprocess.run")
    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks.Path.cwd")
    def test_find_from_git_branch(self, mock_cwd: Mock, mock_root: Mock, mock_subprocess: Mock, tmp_path: Path):
        """Should extract feature slug from git branch name."""
        from specify_cli.cli.commands.agent.tasks import _find_feature_slug

        mock_cwd.return_value = Path("/repo")
        mock_root.return_value = tmp_path
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="008-test-feature\n"
        )

        # Create kitty-specs directory to validate the slug
        (tmp_path / "kitty-specs" / "008-test-feature").mkdir(parents=True)

        slug = _find_feature_slug()
        assert slug == "008-test-feature"

    @patch("subprocess.run")
    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks.Path.cwd")
    def test_find_raises_on_failure(self, mock_cwd: Mock, mock_repo: Mock, mock_subprocess: Mock):
        """Should raise typer.Exit when slug cannot be determined."""
        from specify_cli.cli.commands.agent.tasks import _find_feature_slug
        import subprocess
        from click.exceptions import Exit

        mock_cwd.return_value = Path("/repo")
        mock_repo.return_value = None
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(Exit):
            _find_feature_slug()


class TestStatusInProgressLane:
    """Tests for status subcommand lane alias resolution (issue #204).

    The 7-lane model persists 'in_progress' as the canonical lane name,
    but the status subcommand previously used 'doing' as the dict key,
    causing WPs with lane: in_progress to fall through to 'other'.
    """

    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_in_progress_wp_appears_in_json_output(
        self, mock_slug: Mock, mock_root: Mock, mock_branch: Mock, tmp_path: Path
    ):
        """WP with lane: in_progress must appear in by_lane count, not vanish."""
        repo_root = tmp_path
        (repo_root / ".kittify").mkdir()
        tasks_dir = repo_root / "kitty-specs" / "042-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        # WP with canonical 'in_progress' lane (as persisted by 7-lane model)
        (tasks_dir / "WP01-alpha.md").write_text(
            '---\nwork_package_id: "WP01"\ntitle: "Alpha"\nlane: "in_progress"\n---\nContent\n'
        )
        # WP with legacy alias 'doing'
        (tasks_dir / "WP02-beta.md").write_text(
            '---\nwork_package_id: "WP02"\ntitle: "Beta"\nlane: "doing"\n---\nContent\n'
        )
        # WP already planned
        (tasks_dir / "WP03-gamma.md").write_text(
            '---\nwork_package_id: "WP03"\ntitle: "Gamma"\nlane: "planned"\n---\nContent\n'
        )

        mock_root.return_value = repo_root
        mock_slug.return_value = "042-test"
        mock_branch.return_value = (repo_root, "main")

        with patch(
            "specify_cli.core.stale_detection.check_doing_wps_for_staleness",
            return_value={},
        ):
            result = runner.invoke(app, ["status", "--feature", "042-test", "--json"])

        assert result.exit_code == 0, f"stdout: {result.stdout}"
        output = json.loads(result.stdout)

        # Both WP01 (in_progress) and WP02 (doing alias) should be counted
        # under the canonical 'in_progress' key
        assert output["by_lane"].get("in_progress", 0) == 2, (
            f"Expected 2 in_progress WPs, got by_lane: {output['by_lane']}"
        )
        assert output["by_lane"].get("planned", 0) == 1

        # Verify individual WP lane values are canonicalized
        wp_lanes = {wp["id"]: wp["lane"] for wp in output["work_packages"]}
        assert wp_lanes["WP01"] == "in_progress"
        assert wp_lanes["WP02"] == "in_progress"  # 'doing' resolved to 'in_progress'

    @patch("specify_cli.core.stale_detection.check_doing_wps_for_staleness", return_value={})
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    def test_in_progress_wp_appears_in_rich_output(
        self, mock_slug: Mock, mock_root: Mock, mock_branch: Mock,
        mock_stale: Mock, tmp_path: Path
    ):
        """WP with lane: in_progress must appear in the Doing column of the kanban board."""
        repo_root = tmp_path
        (repo_root / ".kittify").mkdir()
        tasks_dir = repo_root / "kitty-specs" / "042-test" / "tasks"
        tasks_dir.mkdir(parents=True)

        (tasks_dir / "WP01-alpha.md").write_text(
            '---\nwork_package_id: "WP01"\ntitle: "Alpha Task"\nlane: "in_progress"\n---\nContent\n'
        )

        mock_root.return_value = repo_root
        mock_slug.return_value = "042-test"
        mock_branch.return_value = (repo_root, "main")

        result = runner.invoke(app, ["status", "--feature", "042-test"])

        assert result.exit_code == 0, f"stdout: {result.stdout}"
        # The WP should appear in the output (not silently dropped)
        assert "WP01" in result.stdout
        assert "In Progress" in result.stdout or "Doing" in result.stdout
