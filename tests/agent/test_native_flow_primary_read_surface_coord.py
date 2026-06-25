"""Regression: native-flow commands read PRIMARY artifacts off the primary surface
under coordination topology (#2115).

The orchestrator-api fix (#2128) covered the orchestrate path; this covers the
NATIVE commands that hit the SAME coord/feat split next:

- ``spec-kitty merge`` read ``lanes.json`` (LANE_STATE) off the coordination
  worktree → ``lanes.json is required for …/<slug>-coord/…`` hard-block.
- ``spec-kitty agent tasks status`` read WP ``tasks/`` (WORK_PACKAGE_TASK) off the
  coordination worktree → ``Tasks directory not found``.

Both PRIMARY-partition reads now resolve through the kind-aware
``resolve_planning_read_dir`` seam (primary surface for every topology), matching
where ``finalize-tasks`` writes them. STATUS reads (event log) stay on the coord
worktree.

The fixture reproduces the genuine split: ``lanes.json`` + ``tasks/`` + ``meta.json``
live ONLY on the target branch; the coordination worktree carries only the status
event log.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from mission_runtime import MissionArtifactKind
from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.missions._read_path_resolver import (
    candidate_feature_dir_for_mission,
    primary_feature_dir_for_mission,
    resolve_planning_read_dir,
)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

runner = CliRunner()

MISSION_SLUG = "nativesplit"
MID8 = "01KNAT0V"
MISSION_ID = "01KNAT0V000000000000000000"
MISSION_DIRNAME = f"{MISSION_SLUG}-{MID8}"
COORD_BRANCH = f"kitty/mission-{MISSION_DIRNAME}"
TARGET_BRANCH = "feat/nativesplit-target"


def _wp(wp_id: str, deps: str = "[]") -> str:
    return (
        f"---\nwork_package_id: {wp_id}\ntitle: {wp_id}\ndependencies: {deps}\n"
        f"lane: planned\n---\n\n# {wp_id}\n"
    )


_LANES_JSON = {
    "version": 1,
    "feature_slug": MISSION_DIRNAME,
    "target_branch": TARGET_BRANCH,
    "mission_branch": COORD_BRANCH,
    "lanes": [{"lane_id": "lane-a", "wp_ids": ["WP01", "WP02"]}],
}


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )


@pytest.fixture
def split_repo(tmp_path: Path) -> Path:
    """Coord mission whose planning artifacts live ONLY on the target branch."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")

    feature_dir = repo / "kitty-specs" / MISSION_DIRNAME
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": MISSION_SLUG,
                "mission_id": MISSION_ID,
                "mid8": MID8,
                "topology": "coord",
                "coordination_branch": COORD_BRANCH,
                "target_branch": TARGET_BRANCH,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    # Seed meta only on main, branch coord from it (coord lacks lanes.json/tasks/).
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", "seed meta")
    _git(repo, "branch", COORD_BRANCH)

    # Planning artifacts (lanes.json + WP tasks/) land on the writable target branch.
    _git(repo, "checkout", "-q", "-b", TARGET_BRANCH)
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01.md").write_text(_wp("WP01"), encoding="utf-8")
    (tasks_dir / "WP02.md").write_text(_wp("WP02", "[WP01]"), encoding="utf-8")
    (feature_dir / "lanes.json").write_text(
        json.dumps(_LANES_JSON) + "\n", encoding="utf-8"
    )
    (feature_dir / "tasks.md").write_text("# Tasks\n\n- WP01\n- WP02\n", encoding="utf-8")
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", "planning artifacts on target")

    coord_worktree = CoordinationWorkspace.worktree_path(repo, MISSION_SLUG, MID8)
    _git(repo, "worktree", "add", "-q", str(coord_worktree), COORD_BRANCH)
    return repo


def _coord_feature_dir(repo: Path) -> Path:
    return (
        CoordinationWorkspace.worktree_path(repo, MISSION_SLUG, MID8)
        / "kitty-specs"
        / MISSION_DIRNAME
    )


def test_primary_planning_reads_diverge_from_coord_worktree(split_repo: Path) -> None:
    """The PRIMARY surface (where merge/tasks now read) carries lanes.json + tasks/;
    the coord worktree (where they used to read) does not — non-vacuity guard."""
    # merge reads lanes.json via primary_feature_dir_for_mission ...
    primary = primary_feature_dir_for_mission(split_repo, MISSION_DIRNAME)
    assert (primary / "lanes.json").exists()
    assert (primary / "tasks" / "WP01.md").exists()

    # ... and tasks status reads tasks/ via the kind-aware seam → same primary dir.
    seam = resolve_planning_read_dir(
        split_repo, MISSION_DIRNAME, kind=MissionArtifactKind.WORK_PACKAGE_TASK
    )
    assert seam == primary

    # The OLD read surface (coord-aware) is the coord worktree, which has neither —
    # exactly the split that produced "lanes.json is required" / "Tasks directory
    # not found" before the fix.
    coord_aware = candidate_feature_dir_for_mission(split_repo, MISSION_DIRNAME)
    assert coord_aware == _coord_feature_dir(split_repo)
    assert not (coord_aware / "lanes.json").exists()
    assert not (coord_aware / "tasks").exists()


def test_tasks_status_lists_wps_under_coord_split(split_repo: Path) -> None:
    """``agent tasks status`` enumerates WPs from the primary ``tasks/`` even though
    its status surface (the coord worktree) has no ``tasks/`` dir (#2115)."""
    from specify_cli.cli.commands.agent.tasks import app

    with (
        patch(
            "specify_cli.cli.commands.agent.tasks.get_main_repo_root",
            return_value=split_repo,
        ),
        patch(
            "specify_cli.cli.commands.agent.tasks.get_status_read_root",
            return_value=split_repo,
        ),
        patch(
            "specify_cli.cli.commands.agent.tasks.locate_project_root",
            return_value=split_repo,
        ),
        patch(
            "specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out",
            return_value=(split_repo, TARGET_BRANCH),
        ),
        patch(
            "specify_cli.core.stale_detection.check_doing_wps_for_staleness",
            return_value={},
        ),
    ):
        result = runner.invoke(app, ["status", "--mission", MISSION_DIRNAME, "--json"])

    assert result.exit_code == 0, result.stdout
    output = json.loads(result.stdout)
    wp_ids = {wp["id"] for wp in output["work_packages"]}
    assert {"WP01", "WP02"} <= wp_ids, (
        f"WPs not found via the primary surface (got {wp_ids}); the status command "
        "read tasks/ off the coord worktree (#2115)."
    )


def test_preview_claimable_wp_reads_lanes_off_status_dir(tmp_path: Path) -> None:
    """``preview_claimable_wp`` reads tasks/deps from the PRIMARY dir and lanes from
    a separate ``status_dir`` — so a coord mission's tasks/ aren't read off the
    status-only coord surface (#2115)."""
    from specify_cli.status.store import append_event
    from specify_cli.status.models import StatusEvent, Lane as _Lane
    from runtime.next.discovery import preview_claimable_wp

    planning = tmp_path / "primary" / "kitty-specs" / "m"
    (planning / "tasks").mkdir(parents=True)
    (planning / "tasks" / "WP01.md").write_text(_wp("WP01"), encoding="utf-8")
    status = tmp_path / "coord" / "kitty-specs" / "m"
    status.mkdir(parents=True)
    # Status event log lives on the (separate) status surface only.
    append_event(
        status,
        StatusEvent(
            event_id="ev-wp01-planned",
            mission_slug="m",
            wp_id="WP01",
            from_lane=_Lane.GENESIS,
            to_lane=_Lane.PLANNED,
            at="2026-01-01T00:00:00+00:00",
            actor="test",
            force=True,
            execution_mode="worktree",
        ),
    )

    # With the split: tasks from planning, lanes from status → WP01 is claimable.
    preview = preview_claimable_wp(planning, status_dir=status)
    assert preview.wp_id == "WP01"

    # Backward-compat: passing only the status dir (no tasks/) yields no candidate —
    # proving tasks are read from the first arg, not the status surface.
    assert preview_claimable_wp(status).wp_id is None


def test_mission_number_bakes_onto_target_when_coord_branch_lacks_meta(
    tmp_path: Path,
) -> None:
    """`mission_number` baking falls back to the target branch (where meta.json
    lives post-#2090) when the mission/coordination branch has no meta.json (#2115).
    Pre-fix this warned and left mission_number null."""
    from specify_cli.cli.commands.merge import _bake_mission_number_into_mission_branch

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    # Empty initial commit on main, then branch the mission branch from it — so the
    # mission branch carries NO meta.json (planning is PRIMARY → target only).
    _git(repo, "commit", "-q", "--allow-empty", "-m", "root")
    mission_branch = COORD_BRANCH
    _git(repo, "branch", mission_branch)

    # Target branch carries meta.json (mission_number null) — the PRIMARY surface.
    _git(repo, "checkout", "-q", "-b", TARGET_BRANCH)
    fdir = repo / "kitty-specs" / MISSION_DIRNAME
    fdir.mkdir(parents=True)
    (fdir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": MISSION_SLUG,
                "mission_id": MISSION_ID,
                "mid8": MID8,
                "topology": "coord",
                "coordination_branch": COORD_BRANCH,
                "target_branch": TARGET_BRANCH,
                "mission_number": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", "mission meta on target")

    assigned = _bake_mission_number_into_mission_branch(
        main_repo=repo,
        mission_slug=MISSION_DIRNAME,
        mission_branch=mission_branch,
        target_branch=TARGET_BRANCH,
        dry_run=False,
        merge_state=None,
    )

    assert assigned == 1, "first mission on the target should get number 1"
    # The number landed on the TARGET branch's meta.json (not lost to the
    # meta-less mission branch).
    baked = _git(repo, "show", f"{TARGET_BRANCH}:kitty-specs/{MISSION_DIRNAME}/meta.json")
    assert json.loads(baked.stdout)["mission_number"] == 1
