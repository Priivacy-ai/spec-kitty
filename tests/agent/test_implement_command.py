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


@pytest.fixture(autouse=True)
def _bypass_charter_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass the charter preflight gate for these implement-flow tests.

    None of these fixtures stage a charter; without the bypass the gate
    returns ``Error: charter_source missing`` before reaching the
    lane-workspace creation / JSON-output paths the tests exercise.
    Patch the hook boundary directly instead of relying on a production
    environment bypass.
    """
    from specify_cli.charter_runtime.preflight.result import CharterPreflightResult

    result = CharterPreflightResult(passed=True, checks=[])
    monkeypatch.setenv("SPEC_KITTY_TEST_MODE", "1")
    monkeypatch.setattr(
        "specify_cli.charter_runtime.preflight.hook.run_preflight_or_abort",
        lambda *_args, **_kwargs: result,
    )


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
        number, slug = detect_feature_context("lane-only-runtime")
        assert number is None
        assert slug == "lane-only-runtime"


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
        wp_file.write_text(
            "---\n"
            "work_package_id: WP01\n"
            "dependencies: []\n"
            "execution_mode: code_change\n"
            "owned_files:\n  - src/wp01/**\n"
            "authoritative_surface: src/wp01/\n"
            "---\n# WP01",
            encoding="utf-8",
        )

        with (
            patch("specify_cli.cli.commands.implement.find_repo_root", return_value=tmp_path),
            patch(
                "specify_cli.cli.commands.implement.detect_feature_context",
                return_value=("010", "010-feature"),
            ),
        ):
            with pytest.raises(typer.Exit):
                implement("WP01", feature="010-feature", recover=False)

    def test_implement_json_output_is_clean(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        create_meta_json(feature_dir)
        create_lanes_json(feature_dir)
        wp_file = feature_dir / "tasks" / "WP01-setup.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            "---\n"
            "work_package_id: WP01\n"
            "dependencies: []\n"
            "execution_mode: code_change\n"
            "owned_files:\n  - src/wp01/**\n"
            "authoritative_surface: src/wp01/\n"
            "---\n# WP01",
            encoding="utf-8",
        )

        with (
            patch("specify_cli.cli.commands.implement.find_repo_root", return_value=tmp_path),
            patch(
                "specify_cli.cli.commands.implement.detect_feature_context",
                return_value=("010", "010-feature"),
            ),
            patch(
                "specify_cli.cli.commands.implement.resolve_feature_target_branch",
                return_value="main",
            ),
            patch(
                "specify_cli.cli.commands.implement._ensure_planning_artifacts_committed_git",
            ),
            patch(
                "specify_cli.cli.commands.implement._ensure_vcs_in_meta",
            ) as mock_ensure_vcs,
            patch(
                "specify_cli.cli.commands.implement.create_lane_workspace",
            ) as mock_create_lane_workspace,
        ):
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
        assert payload["mission_slug"] == "010-feature"
        assert payload["mission_number"] is None
        assert payload["mission_type"] == "software-dev"

    def test_implement_json_error_output_is_clean(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        create_meta_json(feature_dir)
        wp_file = feature_dir / "tasks" / "WP01-setup.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            "---\n"
            "work_package_id: WP01\n"
            "dependencies: []\n"
            "execution_mode: code_change\n"
            "owned_files:\n  - src/wp01/**\n"
            "authoritative_surface: src/wp01/\n"
            "---\n# WP01",
            encoding="utf-8",
        )

        with (
            patch("specify_cli.cli.commands.implement.find_repo_root", return_value=tmp_path),
            patch(
                "specify_cli.cli.commands.implement.detect_feature_context",
                return_value=("010", "010-feature"),
            ),
            patch(
                "specify_cli.cli.commands.implement.resolve_feature_target_branch",
                return_value="main",
            ),
            patch(
                "specify_cli.cli.commands.implement._ensure_planning_artifacts_committed_git",
            ),
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
        wp_file.write_text(
            "---\n"
            "work_package_id: WP02\n"
            "dependencies: [WP01]\n"
            "execution_mode: code_change\n"
            "owned_files:\n  - src/wp02/**\n"
            "authoritative_surface: src/wp02/\n"
            "---\n# WP02",
            encoding="utf-8",
        )

        with (
            patch("specify_cli.cli.commands.implement.find_repo_root", return_value=tmp_path),
            patch(
                "specify_cli.cli.commands.implement.detect_feature_context",
                return_value=("010", "010-feature"),
            ),
            patch(
                "specify_cli.cli.commands.implement.resolve_feature_target_branch",
                return_value="main",
            ),
            patch(
                "specify_cli.cli.commands.implement._ensure_planning_artifacts_committed_git",
            ),
            patch(
                "specify_cli.cli.commands.implement._ensure_vcs_in_meta",
            ) as mock_ensure_vcs,
            patch(
                "specify_cli.cli.commands.implement.create_lane_workspace",
            ) as mock_create_lane_workspace,
        ):
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

    def test_implement_auto_commit_allows_safe_coordination_branch_when_target_is_protected(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("SPEC_KITTY_TEST_MODE", raising=False)
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        create_meta_json(feature_dir)
        create_lanes_json(feature_dir)
        wp_file = feature_dir / "tasks" / "WP01-setup.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            "---\n"
            "work_package_id: WP01\n"
            "dependencies: []\n"
            "execution_mode: code_change\n"
            "owned_files:\n  - src/wp01/**\n"
            "authoritative_surface: src/wp01/\n"
            "---\n# WP01",
            encoding="utf-8",
        )

        with (
            patch("specify_cli.cli.commands.implement.find_repo_root", return_value=tmp_path),
            patch(
                "specify_cli.cli.commands.implement.detect_feature_context",
                return_value=("010", "010-feature"),
            ),
            patch(
                "specify_cli.cli.commands.implement.resolve_feature_target_branch",
                return_value="main",
            ),
            patch(
                "specify_cli.cli.commands.implement.get_current_branch",
                return_value="kitty/mission-010-feature-01ABCDEF",
            ),
            patch(
                "specify_cli.cli.commands.implement.protected_branches",
                return_value=frozenset({"main"}),
            ),
            patch(
                "specify_cli.cli.commands.implement._ensure_planning_artifacts_committed_git",
            ) as mock_commit_planning,
            patch(
                "specify_cli.cli.commands.implement._ensure_vcs_in_meta",
            ) as mock_ensure_vcs,
            patch(
                "specify_cli.cli.commands.implement.resolve_workspace_for_wp",
            ) as mock_resolve_workspace,
            patch(
                "specify_cli.cli.commands.implement.create_lane_workspace",
            ) as mock_create_lane_workspace,
            patch(
                "specify_cli.cli.commands.implement.start_implementation_status",
                return_value=MagicMock(status_changed=False),
            ),
            patch(
                "specify_cli.bulk_edit.gate.ensure_occurrence_classification_ready",
                return_value=MagicMock(passed=True, change_mode="code_change"),
            ),
        ):
            mock_ensure_vcs.return_value = MagicMock(value="git")
            mock_resolve_workspace.return_value = MagicMock(
                execution_mode="code_change",
                worktree_path=tmp_path / ".worktrees" / "010-feature-lane-a",
                workspace_name="010-feature-lane-a",
                branch_name="kitty/mission-010-feature-lane-a",
                lane_id="lane-a",
                lane_wp_ids=["WP01"],
                resolution_kind="lane_workspace",
                exists=True,
            )
            mock_create_lane_workspace.return_value = MagicMock(
                workspace_path=tmp_path / ".worktrees" / "010-feature-lane-a",
                branch_name="kitty/mission-010-feature-lane-a",
                lane_id="lane-a",
                mission_branch="kitty/mission-010-feature",
                is_reuse=False,
                execution_mode="code_change",
                resolution_kind="lane_workspace",
            )

            implement("WP01", feature="010-feature", auto_commit=True, recover=False)

        mock_commit_planning.assert_called_once()

    def test_implement_status_emit_uses_transport_execution_mode(self, tmp_path: Path) -> None:
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        create_meta_json(feature_dir)
        create_lanes_json(feature_dir)
        wp_file = feature_dir / "tasks" / "WP01-setup.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            "---\n"
            "work_package_id: WP01\n"
            "dependencies: []\n"
            "execution_mode: code_change\n"
            "owned_files:\n  - src/wp01/**\n"
            "authoritative_surface: src/wp01/\n"
            "---\n# WP01",
            encoding="utf-8",
        )

        captured: dict[str, str] = {}

        def fake_start_status(**kwargs: object) -> MagicMock:
            captured["execution_mode"] = str(kwargs["execution_mode"])
            captured["workspace_context"] = str(kwargs["workspace_context"])
            return MagicMock(status_changed=False)

        with (
            patch("specify_cli.cli.commands.implement.find_repo_root", return_value=tmp_path),
            patch(
                "specify_cli.cli.commands.implement.detect_feature_context",
                return_value=("010", "010-feature"),
            ),
            patch(
                "specify_cli.cli.commands.implement.resolve_feature_target_branch",
                return_value="main",
            ),
            patch(
                "specify_cli.cli.commands.implement._ensure_planning_artifacts_committed_git",
            ),
            patch(
                "specify_cli.cli.commands.implement._ensure_vcs_in_meta",
            ) as mock_ensure_vcs,
            patch(
                "specify_cli.cli.commands.implement.create_lane_workspace",
            ) as mock_create_lane_workspace,
            patch(
                "specify_cli.cli.commands.implement.start_implementation_status",
                side_effect=fake_start_status,
            ),
        ):
            mock_ensure_vcs.return_value = MagicMock(value="git")
            mock_create_lane_workspace.return_value = MagicMock(
                workspace_path=tmp_path / ".worktrees" / "010-feature-lane-a",
                branch_name="kitty/mission-010-feature-lane-a",
                lane_id="lane-a",
                mission_branch="kitty/mission-010-feature",
                is_reuse=False,
                execution_mode="code_change",
                resolution_kind="lane_workspace",
            )

            implement("WP01", feature="010-feature", auto_commit=False, recover=False)

        assert captured["execution_mode"] == "worktree"
        assert captured["workspace_context"].startswith("worktree:")

    def test_implement_allows_planning_artifact_in_lane_planning(self, tmp_path: Path) -> None:
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        create_meta_json(feature_dir)
        wp_file = feature_dir / "tasks" / "WP02-plan.md"
        wp_file.parent.mkdir(parents=True)
        wp_file.write_text(
            "---\n"
            "work_package_id: WP02\n"
            "dependencies: []\n"
            "execution_mode: planning_artifact\n"
            "owned_files:\n"
            "  - kitty-specs/010-feature/**\n"
            "authoritative_surface: kitty-specs/010-feature/\n"
            "---\n"
            "# WP02\n"
        )

        with (
            patch("specify_cli.cli.commands.implement.find_repo_root", return_value=tmp_path),
            patch(
                "specify_cli.cli.commands.implement.detect_feature_context",
                return_value=("010", "010-feature"),
            ),
            patch(
                "specify_cli.cli.commands.implement.resolve_feature_target_branch",
                return_value="main",
            ),
            patch(
                "specify_cli.cli.commands.implement._ensure_planning_artifacts_committed_git",
            ),
            patch(
                "specify_cli.cli.commands.implement._ensure_vcs_in_meta",
            ) as mock_ensure_vcs,
            patch(
                "specify_cli.cli.commands.implement.resolve_workspace_for_wp",
            ) as mock_resolve_workspace,
            patch(
                "specify_cli.cli.commands.implement.create_lane_workspace",
            ) as mock_create_lane_workspace,
        ):
            mock_ensure_vcs.return_value = MagicMock(value="git")
            from specify_cli.lanes.compute import PLANNING_LANE_ID
            mock_resolve_workspace.return_value = MagicMock(
                execution_mode="planning_artifact",
                worktree_path=tmp_path,
                workspace_name=f"010-feature-{PLANNING_LANE_ID}",
                branch_name="main",
                lane_id=PLANNING_LANE_ID,
                lane_wp_ids=["WP02"],
                resolution_kind="repo_root",
                exists=True,
            )
            mock_create_lane_workspace.return_value = MagicMock(
                workspace_path=tmp_path,
                branch_name=None,
                workspace_name=f"010-feature-{PLANNING_LANE_ID}",
                lane_id=PLANNING_LANE_ID,
                mission_branch=None,
                is_reuse=False,
                execution_mode="planning_artifact",
                resolution_kind="repo_root",
            )

            implement("WP02", feature="010-feature", auto_commit=False, recover=False)

            kwargs = mock_create_lane_workspace.call_args.kwargs
            assert kwargs["lanes_manifest"] is None
            assert kwargs["resolved_workspace"].execution_mode == "planning_artifact"
