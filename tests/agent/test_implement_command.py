"""Unit tests for lane-only implement command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from specify_cli.cli.commands.implement import (
    _ensure_vcs_in_meta,
    detect_feature_context,
    find_wp_file,
    implement,
)
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import write_lanes_json

pytestmark = pytest.mark.fast


def create_meta_json(feature_dir: Path, vcs: str = "git") -> Path:
    meta_path = feature_dir / "meta.json"
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta_content = {
        "feature_number": feature_dir.name.split("-")[0],
        "mission_slug": feature_dir.name,
        "created_at": "2026-01-17T00:00:00Z",
        "friendly_name": feature_dir.name,
        "mission": "software-dev",
        "slug": feature_dir.name,
        "target_branch": "main",
    }
    if vcs:
        meta_content["vcs"] = vcs
    meta_path.write_text(json.dumps(meta_content, indent=2))
    return meta_path


def create_lanes_json(feature_dir: Path, wp_ids: tuple[str, ...] = ("WP01",)) -> None:
    write_lanes_json(
        feature_dir,
        LanesManifest(
            version=1,
            mission_slug=feature_dir.name,
            mission_id=f"mission-{feature_dir.name}",
            mission_branch=f"kitty/mission-{feature_dir.name}",
            target_branch="main",
            lanes=[
                ExecutionLane(
                    lane_id="lane-a",
                    wp_ids=wp_ids,
                    write_scope=("src/**",),
                    predicted_surfaces=("core",),
                    depends_on_lanes=(),
                    parallel_group=0,
                )
            ],
            computed_at="2026-04-04T10:00:00Z",
            computed_from="test",
        ),
    )


class TestDetectFeatureContext:
    def test_detect_with_explicit_flag(self) -> None:
        number, slug = detect_feature_context("010-lane-only-runtime")
        assert number == "010"
        assert slug == "010-lane-only-runtime"

    def test_detect_failure_no_flag(self) -> None:
        with pytest.raises(typer.Exit):
            detect_feature_context(None)

    def test_detect_invalid_format(self) -> None:
        with pytest.raises(typer.Exit):
            detect_feature_context("lane-only-runtime")


class TestFindWpFile:
    def test_find_wp_file_success(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "kitty-specs" / "010-feature" / "tasks"
        tasks_dir.mkdir(parents=True)
        wp_file = tasks_dir / "WP01-setup.md"
        wp_file.write_text("# WP01")

        result = find_wp_file(tmp_path, "010-feature", "WP01")
        assert result == wp_file

    def test_find_wp_file_not_found(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "kitty-specs" / "010-feature" / "tasks"
        tasks_dir.mkdir(parents=True)
        with pytest.raises(FileNotFoundError, match="WP file not found"):
            find_wp_file(tmp_path, "010-feature", "WP01")


class TestEnsureVcsInMeta:
    def test_existing_vcs_is_preserved(self, tmp_path: Path) -> None:
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        create_meta_json(feature_dir, vcs="git")
        assert _ensure_vcs_in_meta(feature_dir, tmp_path).value == "git"

    def test_missing_meta_errors(self, tmp_path: Path) -> None:
        with pytest.raises(typer.Exit):
            _ensure_vcs_in_meta(tmp_path / "kitty-specs" / "010-feature", tmp_path)


class TestImplementCommand:
    def test_implement_requires_lanes_json(self, tmp_path: Path) -> None:
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        create_meta_json(feature_dir)
        wp_file = feature_dir / "tasks" / "WP01-setup.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text("---\nwork_package_id: WP01\ndependencies: []\n---\n# WP01")

        with patch("specify_cli.cli.commands.implement.find_repo_root", return_value=tmp_path), patch(
            "specify_cli.cli.commands.implement.detect_feature_context",
            return_value=("010", "010-feature"),
        ):
            with pytest.raises(typer.Exit):
                implement("WP01", feature="010-feature", recover=False)

    def test_implement_json_output_is_clean(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        create_meta_json(feature_dir)
        create_lanes_json(feature_dir)
        wp_file = feature_dir / "tasks" / "WP01-setup.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text("---\nwork_package_id: WP01\ndependencies: []\n---\n# WP01")

        with patch("specify_cli.cli.commands.implement.find_repo_root", return_value=tmp_path), patch(
            "specify_cli.cli.commands.implement.detect_feature_context",
            return_value=("010", "010-feature"),
        ), patch(
            "specify_cli.cli.commands.implement.resolve_feature_target_branch",
            return_value="main",
        ), patch(
            "specify_cli.cli.commands.implement._ensure_planning_artifacts_committed_git",
        ), patch(
            "specify_cli.cli.commands.implement._ensure_vcs_in_meta",
        ) as mock_ensure_vcs, patch(
            "specify_cli.cli.commands.implement.create_lane_workspace",
        ) as mock_create_lane_workspace:
            mock_ensure_vcs.return_value = MagicMock(value="git")
            mock_create_lane_workspace.return_value = MagicMock(
                workspace_path=tmp_path / ".worktrees" / "010-feature-lane-a",
                branch_name="kitty/mission-010-feature-lane-a",
                lane_id="lane-a",
                mission_branch="kitty/mission-010-feature",
                is_reuse=False,
            )

            implement("WP01", feature="010-feature", json_output=True, recover=False)

        payload = json.loads(capsys.readouterr().out.strip())
        assert payload["workspace"] == ".worktrees/010-feature-lane-a"
        assert payload["branch"] == "kitty/mission-010-feature-lane-a"
        assert payload["lane_id"] == "lane-a"

    def test_implement_json_error_output_is_clean(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        create_meta_json(feature_dir)
        wp_file = feature_dir / "tasks" / "WP01-setup.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text("---\nwork_package_id: WP01\ndependencies: []\n---\n# WP01")

        with patch("specify_cli.cli.commands.implement.find_repo_root", return_value=tmp_path), patch(
            "specify_cli.cli.commands.implement.detect_feature_context",
            return_value=("010", "010-feature"),
        ), patch(
            "specify_cli.cli.commands.implement.resolve_feature_target_branch",
            return_value="main",
        ), patch(
            "specify_cli.cli.commands.implement._ensure_planning_artifacts_committed_git",
        ):
            with pytest.raises(typer.Exit):
                implement("WP01", feature="010-feature", json_output=True, recover=False)

        payload = json.loads(capsys.readouterr().out.strip())
        assert payload["status"] == "error"
        assert payload["wp_id"] == "WP01"
        assert payload["error"] != "implement command failed"
        assert "lanes.json is required" in payload["error"]

    def test_implement_creates_lane_workspace(self, tmp_path: Path) -> None:
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        create_meta_json(feature_dir)
        create_lanes_json(feature_dir, wp_ids=("WP01", "WP02"))
        wp_file = feature_dir / "tasks" / "WP02-api.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text("---\nwork_package_id: WP02\ndependencies: [WP01]\n---\n# WP02")

        with patch("specify_cli.cli.commands.implement.find_repo_root", return_value=tmp_path), patch(
            "specify_cli.cli.commands.implement.detect_feature_context",
            return_value=("010", "010-feature"),
        ), patch(
            "specify_cli.cli.commands.implement.resolve_feature_target_branch",
            return_value="main",
        ), patch(
            "specify_cli.cli.commands.implement._ensure_planning_artifacts_committed_git",
        ), patch(
            "specify_cli.cli.commands.implement._ensure_vcs_in_meta",
        ) as mock_ensure_vcs, patch(
            "specify_cli.cli.commands.implement.create_lane_workspace",
        ) as mock_create_lane_workspace:
            mock_ensure_vcs.return_value = MagicMock(value="git")
            mock_create_lane_workspace.return_value = MagicMock(
                workspace_path=tmp_path / ".worktrees" / "010-feature-lane-a",
                branch_name="kitty/mission-010-feature-lane-a",
                lane_id="lane-a",
                mission_branch="kitty/mission-010-feature",
                is_reuse=True,
            )

            implement("WP02", feature="010-feature", recover=False)

            kwargs = mock_create_lane_workspace.call_args.kwargs
            assert kwargs["wp_id"] == "WP02"
            assert kwargs["declared_deps"] == ["WP01"]
