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

    def test_find_with_explicit_slug(self, tmp_path: Path):
        """_find_feature_slug returns explicit slug when provided.

        After WP02 removed heuristic detection, _find_feature_slug requires
        an explicit slug.  No cwd scanning or git branch parsing is performed.
        """
        from specify_cli.cli.commands.agent.tasks import _find_feature_slug

        slug = _find_feature_slug(explicit_feature="008-test-feature")
        assert slug == "008-test-feature"

    def test_find_raises_on_missing_slug(self):
        """_find_feature_slug raises typer.Exit when no explicit slug is given."""
        from specify_cli.cli.commands.agent.tasks import _find_feature_slug
        from click.exceptions import Exit

        with pytest.raises(Exit):
            _find_feature_slug(explicit_feature=None)


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
