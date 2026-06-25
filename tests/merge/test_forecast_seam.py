"""Seam test for ``specify_cli.merge.forecast`` (mission #2057, WP06).

Locks the ``merge --dry-run`` forecast contract at the seam: the exact JSON key
set (cli-surface-contract.md §2), the REJECTED_REVIEW_ARTIFACT_CONFLICT gate
preview (human + JSON), unresolved-slug / missing-lanes errors, and the
would_assign_mission_number scan. One-way import enforced (INV-2).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from specify_cli import __version__ as SPEC_KITTY_VERSION
from specify_cli.merge import forecast
from specify_cli.merge.config import MergeStrategy
from specify_cli.post_merge.review_artifact_consistency import (
    REJECTED_REVIEW_ARTIFACT_CONFLICT,
)
from specify_cli.status.models import Lane
from tests.reliability.fixtures import (
    WorkPackageSpec,
    append_status_event,
    create_mission_fixture,
    write_work_package,
)

pytestmark = pytest.mark.fast


EXPECTED_DRY_RUN_PAYLOAD_KEYS = frozenset(
    {
        "spec_kitty_version",
        "mission_slug",
        "target_branch",
        "strategy",
        "delete_branch",
        "remove_worktree",
        "push",
        "mission_branch",
        "lanes",
        "would_assign_mission_number",
    }
)


def test_forecast_does_not_import_command_shim() -> None:
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(forecast))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    assert not any(
        m.startswith("specify_cli.cli.commands.merge") for m in modules
    ), sorted(modules)


def test_unresolved_slug_raises_exit_1(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(typer.Exit) as exc:
        forecast.run_dry_run_forecast(
            repo_root=Path("/r"),
            resolved_feature=None,
            resolved_target_branch="main",
            resolved_strategy=MergeStrategy.SQUASH,
            delete_branch=True,
            remove_worktree=True,
            push=False,
            json_output=True,
        )
    assert exc.value.exit_code == 1
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["error"] == "Mission slug could not be resolved. Use --mission <slug>."


def _lanes_json_for(mission: object) -> None:
    (mission.mission_dir / "lanes.json").write_text(  # type: ignore[attr-defined]
        json.dumps(
            {
                "version": 1,
                "mission_slug": mission.mission_slug,  # type: ignore[attr-defined]
                "mission_id": mission.mission_id,  # type: ignore[attr-defined]
                "mission_branch": f"kitty/mission-{mission.mission_slug}",  # type: ignore[attr-defined]
                "target_branch": "main",
                "lanes": [
                    {
                        "lane_id": "lane-a",
                        "wp_ids": ["WP01"],
                        "write_scope": [],
                        "predicted_surfaces": [],
                        "depends_on_lanes": [],
                        "parallel_group": 0,
                    }
                ],
                "computed_at": "2026-05-14T12:00:00+00:00",
                "computed_from": "dependency_graph+ownership",
                "planning_artifact_wps": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_clean_forecast_json_payload_key_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission, from_lane=Lane.FOR_REVIEW, to_lane=Lane.APPROVED,
        event_id="01KVXHDKFORECAST00000001",
    )
    _lanes_json_for(mission)
    monkeypatch.setattr(
        "specify_cli.merge.forecast.get_main_repo_root", lambda _r: mission.repo_root
    )

    # On a clean mission the forecast prints the payload and returns (no Exit).
    forecast.run_dry_run_forecast(
        repo_root=mission.repo_root,
        resolved_feature=mission.mission_slug,
        resolved_target_branch="main",
        resolved_strategy=MergeStrategy.SQUASH,
        delete_branch=True,
        remove_worktree=True,
        push=False,
        json_output=True,
    )
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert frozenset(payload) == EXPECTED_DRY_RUN_PAYLOAD_KEYS
    assert payload["spec_kitty_version"] == SPEC_KITTY_VERSION
    assert payload["mission_slug"] == mission.mission_slug
    assert payload["strategy"] == "squash"
    assert payload["push"] is False


def test_review_artifact_conflict_blocks_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from specify_cli.review.artifacts import ReviewCycleArtifact

    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission, from_lane=Lane.FOR_REVIEW, to_lane=Lane.APPROVED,
        event_id="01KVXHDKFORECAST00000002",
    )
    artifact = ReviewCycleArtifact(
        cycle_number=1, wp_id="WP01", mission_slug=mission.mission_slug,
        reviewer_agent="reviewer-renata", verdict="rejected",
        reviewed_at="2026-05-14T12:00:00+00:00", body="# Review\n\nVerdict: rejected\n",
    )
    artifact.write(mission.tasks_dir / "WP01-regression-harness" / "review-cycle-1.md")
    _lanes_json_for(mission)
    monkeypatch.setattr(
        "specify_cli.merge.forecast.get_main_repo_root", lambda _r: mission.repo_root
    )

    with pytest.raises(typer.Exit) as exc:
        forecast.run_dry_run_forecast(
            repo_root=mission.repo_root,
            resolved_feature=mission.mission_slug,
            resolved_target_branch="main",
            resolved_strategy=MergeStrategy.SQUASH,
            delete_branch=True,
            remove_worktree=True,
            push=False,
            json_output=True,
        )
    assert exc.value.exit_code == 1
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["blocked"] is True
    assert payload["diagnostic_code"] == REJECTED_REVIEW_ARTIFACT_CONFLICT


def test_missing_lanes_raises_exit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    mission = create_mission_fixture(tmp_path)
    monkeypatch.setattr(
        "specify_cli.merge.forecast.get_main_repo_root", lambda _r: mission.repo_root
    )
    with pytest.raises(typer.Exit) as exc:
        forecast.run_dry_run_forecast(
            repo_root=mission.repo_root,
            resolved_feature=mission.mission_slug,
            resolved_target_branch="main",
            resolved_strategy=MergeStrategy.SQUASH,
            delete_branch=True,
            remove_worktree=True,
            push=False,
            json_output=True,
        )
    assert exc.value.exit_code == 1
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert "lanes.json is required" in payload["error"]


def test_scan_would_assign_mission_number_handles_failure(tmp_path: Path) -> None:
    with (
        patch.object(forecast, "needs_number_assignment", return_value=True),
        patch.object(forecast, "assign_next_mission_number", side_effect=RuntimeError("boom")),
        patch.object(forecast, "get_main_repo_root", lambda _r: tmp_path),
    ):
        assert forecast._scan_would_assign_mission_number(tmp_path, tmp_path) is None

    with patch.object(forecast, "needs_number_assignment", return_value=False):
        assert forecast._scan_would_assign_mission_number(tmp_path, tmp_path) is None


def test_scan_would_assign_mission_number_returns_value(tmp_path: Path) -> None:
    with (
        patch.object(forecast, "needs_number_assignment", return_value=True),
        patch.object(forecast, "assign_next_mission_number", return_value=7),
        patch.object(forecast, "get_main_repo_root", lambda _r: tmp_path),
    ):
        assert forecast._scan_would_assign_mission_number(tmp_path, tmp_path) == 7


# --- human-output (non-JSON) branches: NFR-002 coverage of console paths -----


def test_emit_dry_run_error_human_channel(capsys: pytest.CaptureFixture[str]) -> None:
    forecast._emit_dry_run_error(error_msg="boom happened", json_output=False)
    out = capsys.readouterr().out
    assert "Error:" in out
    assert "boom happened" in out


def test_unresolved_slug_human_channel_prints_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(typer.Exit) as exc:
        forecast.run_dry_run_forecast(
            repo_root=Path("/r"),
            resolved_feature=None,
            resolved_target_branch="main",
            resolved_strategy=MergeStrategy.SQUASH,
            delete_branch=True,
            remove_worktree=True,
            push=False,
            json_output=False,
        )
    assert exc.value.exit_code == 1
    out = capsys.readouterr().out
    assert "Mission slug could not be resolved" in out


def test_review_artifact_block_human_channel(capsys: pytest.CaptureFixture[str]) -> None:
    """Drive the human-output review-artifact gate printing (lines 84-108)."""
    from specify_cli.post_merge.review_artifact_consistency import (
        RejectedReviewArtifactFinding,
        ReviewArtifactPreflightResult,
    )

    finding = RejectedReviewArtifactFinding(
        wp_id="WP01",
        lane="approved",
        artifact_path=Path("/repo/kitty-specs/m/tasks/WP01/review-cycle-1.md"),
        cycle_number=1,
        verdict="rejected",
    )
    preflight = ReviewArtifactPreflightResult(findings=(finding,))

    forecast._emit_review_artifact_block(
        preflight,
        main_repo_for_diag=Path("/repo"),
        resolved_feature="m",
        resolved_target_branch="main",
        json_output=False,
    )
    out = capsys.readouterr().out
    assert "Review artifact consistency gate failed" in out
    assert "diagnostic_code:" in out
    assert "latest_review_cycle_verdict:" in out
    assert "Mission: m" in out


def test_review_artifact_block_schema_finding_human_channel(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A schema finding exercises the schema_error human branch (line 102)."""
    from specify_cli.post_merge.review_artifact_consistency import (
        ReviewArtifactPreflightResult,
        ReviewArtifactSchemaFinding,
    )

    finding = ReviewArtifactSchemaFinding(
        wp_id="WP02",
        lane="done",
        artifact_path=Path("/repo/kitty-specs/m/tasks/WP02/review-cycle-1.md"),
        schema_error="affected_files must be a list",
    )
    preflight = ReviewArtifactPreflightResult(findings=(finding,))

    forecast._emit_review_artifact_block(
        preflight,
        main_repo_for_diag=Path("/repo"),
        resolved_feature="m",
        resolved_target_branch="main",
        json_output=False,
    )
    out = capsys.readouterr().out
    assert "schema_error:" in out


def test_clean_forecast_human_channel_prints_would_assign(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Human-output clean forecast with a would-assign number (line 201 + 207)."""
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission, from_lane=Lane.FOR_REVIEW, to_lane=Lane.APPROVED,
        event_id="01KVXHDKFORECAST00000003",
    )
    _lanes_json_for(mission)
    monkeypatch.setattr(
        "specify_cli.merge.forecast.get_main_repo_root", lambda _r: mission.repo_root
    )
    with patch.object(forecast, "_scan_would_assign_mission_number", return_value=42):
        forecast.run_dry_run_forecast(
            repo_root=mission.repo_root,
            resolved_feature=mission.mission_slug,
            resolved_target_branch="main",
            resolved_strategy=MergeStrategy.SQUASH,
            delete_branch=True,
            remove_worktree=True,
            push=False,
            json_output=False,
        )
    out = capsys.readouterr().out
    assert "would assign" in out
    assert "mission_number=42" in out
