"""Regression tests for `merge --dry-run` review-artifact consistency parity (issue #991).

The real merge path runs the review-artifact consistency gate and emits
``REJECTED_REVIEW_ARTIFACT_CONFLICT`` when an approved/done WP still has a
rejected latest review-cycle artifact. Prior to this fix, ``merge --dry-run``
skipped that gate and returned a clean preview, weakening dry-run as a
readiness signal. These tests lock the new behavior:

* The shared preflight helper detects the same conflict the real gate detects.
* Dry-run surfaces ``REJECTED_REVIEW_ARTIFACT_CONFLICT`` in JSON output.
* Dry-run surfaces ``REJECTED_REVIEW_ARTIFACT_CONFLICT`` in human output.
* Dry-run surfaces malformed review-cycle schema diagnostics in human output.
* Dry-run success path is unchanged on a clean mission.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from specify_cli.post_merge.review_artifact_consistency import (
    REJECTED_REVIEW_ARTIFACT_CONFLICT,
    REVIEW_ARTIFACT_SCHEMA_INVALID,
    ReviewArtifactPreflightResult,
    run_review_artifact_consistency_preflight,
)
from specify_cli.review.artifacts import ReviewCycleArtifact
from specify_cli.status.models import Lane
from tests.reliability.fixtures import (
    WorkPackageSpec,
    append_status_event,
    create_mission_fixture,
    write_work_package,
)

pytestmark = pytest.mark.fast


def _write_review_artifact(
    artifact_dir: Path,
    *,
    cycle_number: int,
    verdict: str,
    mission_slug: str,
) -> Path:
    artifact = ReviewCycleArtifact(
        cycle_number=cycle_number,
        wp_id="WP01",
        mission_slug=mission_slug,
        reviewer_agent="reviewer-renata",
        verdict=verdict,
        reviewed_at="2026-05-14T12:00:00+00:00",
        body=f"# Review\n\nVerdict: {verdict}\n",
    )
    path = artifact_dir / f"review-cycle-{cycle_number}.md"
    artifact.write(path)
    return path


def _write_malformed_review_artifact(artifact_dir: Path) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / "review-cycle-1.md"
    path.write_text(
        "---\n"
        "affected_files:\n"
        "  - src/foo.py\n"
        "cycle_number: 1\n"
        "mission_slug: release-320-workflow-reliability-01KQKV85\n"
        "reviewed_at: '2026-05-14T12:00:00+00:00'\n"
        "reviewer_agent: reviewer-renata\n"
        "verdict: approved\n"
        "wp_id: WP01\n"
        "---\n"
        "\n"
        "# Review\n",
        encoding="utf-8",
    )
    return path


def _write_lanes_json(mission: object) -> None:
    lanes_json = mission.mission_dir / "lanes.json"
    lanes_json.write_text(
        json.dumps(
            {
                "version": 1,
                "mission_slug": mission.mission_slug,
                "mission_id": mission.mission_id,
                "mission_branch": f"kitty/mission-{mission.mission_slug}",
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


def _patch_dry_run_git_boundaries(monkeypatch: pytest.MonkeyPatch, mission: object) -> None:
    monkeypatch.setattr(
        "specify_cli.cli.commands.merge._enforce_git_preflight", lambda *a, **kw: None
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.merge.find_repo_root", lambda: mission.repo_root
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.merge.get_main_repo_root",
        lambda _repo: mission.repo_root,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.merge._validate_target_branch",
        lambda *a, **kw: None,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.merge._resolve_target_branch",
        lambda *a, **kw: ("main", "cli"),
    )


def test_preflight_detects_rejected_review_artifact_on_approved_wp(
    tmp_path: Path,
) -> None:
    """The shared preflight helper detects the same conflict the real gate detects."""
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission,
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.APPROVED,
        event_id="01KRKTT5APPROVED00000001",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    _write_review_artifact(
        artifact_dir,
        cycle_number=1,
        verdict="rejected",
        mission_slug=mission.mission_slug,
    )

    result = run_review_artifact_consistency_preflight(
        mission.mission_dir,
        wp_ids=["WP01"],
    )

    assert isinstance(result, ReviewArtifactPreflightResult)
    assert not result.passed
    assert len(result.findings) == 1
    assert result.findings[0].wp_id == "WP01"
    assert result.findings[0].verdict == "rejected"

    diagnostics = result.diagnostics(repo_root=mission.repo_root)
    assert len(diagnostics) == 1
    assert diagnostics[0]["diagnostic_code"] == REJECTED_REVIEW_ARTIFACT_CONFLICT
    assert diagnostics[0]["branch_or_work_package"] == "WP01"
    assert diagnostics[0]["latest_review_cycle_verdict"] == "rejected"


def test_preflight_passes_on_clean_mission(tmp_path: Path) -> None:
    """The preflight returns ``passed=True`` when no conflicts exist (dry-run success path stays clean)."""
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission,
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.APPROVED,
        event_id="01KRKTT5APPROVED00000002",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    _write_review_artifact(
        artifact_dir,
        cycle_number=1,
        verdict="approved",
        mission_slug=mission.mission_slug,
    )

    result = run_review_artifact_consistency_preflight(
        mission.mission_dir,
        wp_ids=["WP01"],
    )

    assert result.passed
    assert result.findings == ()
    assert result.diagnostics(repo_root=mission.repo_root) == []


def test_dry_run_emits_rejected_review_artifact_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``merge --dry-run --json`` exits non-zero and emits REJECTED_REVIEW_ARTIFACT_CONFLICT."""
    import typer
    from typer.testing import CliRunner

    from specify_cli.cli.commands.merge import merge

    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission,
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.APPROVED,
        event_id="01KRKTT5APPROVED00000003",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    _write_review_artifact(
        artifact_dir,
        cycle_number=1,
        verdict="rejected",
        mission_slug=mission.mission_slug,
    )

    _write_lanes_json(mission)

    monkeypatch.chdir(mission.repo_root)

    app = typer.Typer()
    app.command()(merge)
    runner = CliRunner()

    # Avoid the git preflight, which would fail in a non-git tmp dir.
    _patch_dry_run_git_boundaries(monkeypatch, mission)

    result = runner.invoke(
        app,
        ["--mission", mission.mission_slug, "--dry-run", "--json"],
    )

    assert result.exit_code == 1, (
        f"Expected exit 1, got {result.exit_code}\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["blocked"] is True
    assert payload["diagnostic_code"] == REJECTED_REVIEW_ARTIFACT_CONFLICT
    assert payload["blockers"]
    assert payload["blockers"][0]["diagnostic_code"] == REJECTED_REVIEW_ARTIFACT_CONFLICT
    assert payload["blockers"][0]["branch_or_work_package"] == "WP01"


def test_dry_run_emits_review_artifact_schema_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``merge --dry-run --json`` reports malformed review-cycle frontmatter."""
    import typer
    from typer.testing import CliRunner

    from specify_cli.cli.commands.merge import merge

    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission,
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.APPROVED,
        event_id="01KRKTT5APPROVED00000006",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    _write_malformed_review_artifact(artifact_dir)
    _write_lanes_json(mission)

    monkeypatch.chdir(mission.repo_root)

    app = typer.Typer()
    app.command()(merge)
    runner = CliRunner()

    _patch_dry_run_git_boundaries(monkeypatch, mission)

    result = runner.invoke(
        app,
        ["--mission", mission.mission_slug, "--dry-run", "--json"],
    )

    assert result.exit_code == 1, (
        f"Expected exit 1, got {result.exit_code}\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["blocked"] is True
    assert payload["diagnostic_code"] == REVIEW_ARTIFACT_SCHEMA_INVALID
    assert payload["blockers"][0]["diagnostic_code"] == REVIEW_ARTIFACT_SCHEMA_INVALID
    assert payload["blockers"][0]["branch_or_work_package"] == "WP01"
    assert (
        payload["blockers"][0]["violated_invariant"]
        == "review_cycle_frontmatter_must_match_schema"
    )
    assert "affected_files entries must be mappings" in payload["blockers"][0]["schema_error"]


def test_dry_run_human_emits_rejected_review_artifact_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``merge --dry-run`` without --json prints a labelled REJECTED_REVIEW_ARTIFACT_CONFLICT block."""
    import typer
    from typer.testing import CliRunner

    from specify_cli.cli.commands.merge import merge

    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission,
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.APPROVED,
        event_id="01KRKTT5APPROVED00000004",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    _write_review_artifact(
        artifact_dir,
        cycle_number=1,
        verdict="rejected",
        mission_slug=mission.mission_slug,
    )

    _write_lanes_json(mission)

    monkeypatch.chdir(mission.repo_root)

    app = typer.Typer()
    app.command()(merge)
    runner = CliRunner()

    _patch_dry_run_git_boundaries(monkeypatch, mission)

    result = runner.invoke(app, ["--mission", mission.mission_slug, "--dry-run"])

    assert result.exit_code == 1
    output = result.stdout
    assert REJECTED_REVIEW_ARTIFACT_CONFLICT in output
    assert "WP01" in output


def test_dry_run_human_emits_review_artifact_schema_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``merge --dry-run`` prints labelled schema diagnostics without a traceback."""
    import typer
    from typer.testing import CliRunner

    from specify_cli.cli.commands.merge import merge

    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission,
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.APPROVED,
        event_id="01KRKTT5APPROVED00000007",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    review_path = _write_malformed_review_artifact(artifact_dir)
    _write_lanes_json(mission)

    monkeypatch.chdir(mission.repo_root)

    app = typer.Typer()
    app.command()(merge)
    runner = CliRunner()

    _patch_dry_run_git_boundaries(monkeypatch, mission)

    result = runner.invoke(app, ["--mission", mission.mission_slug, "--dry-run"])

    assert result.exit_code == 1
    output = result.stdout
    unwrapped_output = output.replace("\n", "")
    review_path_text = str(review_path.relative_to(mission.repo_root))
    assert REVIEW_ARTIFACT_SCHEMA_INVALID in output
    assert "branch_or_work_package: WP01" in output
    assert (
        "violated_invariant: review_cycle_frontmatter_must_match_schema" in output
    )
    assert f"latest_review_cycle_path: {review_path_text}" in unwrapped_output
    assert "schema_error: affected_files entries must be mappings" in output
    assert "affected_files entries must be mappings" in unwrapped_output
    assert "Traceback" not in output


def test_real_merge_schema_preflight_does_not_write_merge_state(
    tmp_path: Path,
) -> None:
    """Schema-invalid review artifacts must fail before merge-state mutation."""
    import typer

    from specify_cli.cli.commands.merge import _run_lane_based_merge_locked
    from specify_cli.merge.state import get_state_path

    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission,
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.APPROVED,
        event_id="01KRKTT5APPROVED00000008",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    _write_malformed_review_artifact(artifact_dir)
    lanes_manifest = SimpleNamespace(
        lanes=[SimpleNamespace(lane_id="lane-a", wp_ids=["WP01"])],
        mission_branch=f"kitty/mission-{mission.mission_slug}",
        target_branch="main",
    )

    with pytest.raises(typer.Exit) as exc_info:
        _run_lane_based_merge_locked(
            mission.repo_root,
            mission.mission_slug,
            mission.mission_id,  # canonical_id (path handle)
            mission.mission_id,  # canonical_mission_id (ULID for event fields)
            mission.mission_dir,
            lanes_manifest,
            push=False,
            delete_branch=False,
            remove_worktree=False,
        )

    assert exc_info.value.exit_code == 1
    assert not get_state_path(mission.repo_root, mission.mission_id).exists()
