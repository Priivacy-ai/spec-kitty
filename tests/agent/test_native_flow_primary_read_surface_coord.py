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
