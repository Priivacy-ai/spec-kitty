"""Tests for lane-based merge operations."""

import subprocess

import pytest

from specify_cli.lanes.merge import (
    LaneMergeResult,
    MissionMergeResult,
    merge_lane_to_mission,
    merge_mission_to_target,
)
from specify_cli.lanes.models import ExecutionLane, LanesManifest


def _run(cmd, cwd):
    subprocess.run(cmd, cwd=str(cwd), capture_output=True, check=True)


def _commit(repo, filename, content, message):
    (repo / filename).parent.mkdir(parents=True, exist_ok=True)
    (repo / filename).write_text(content)
    _run(["git", "add", filename], repo)
    _run(["git", "commit", "-m", message], repo)


def _make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", str(repo)], tmp_path)
    _run(["git", "config", "user.email", "test@test.com"], repo)
    _run(["git", "config", "user.name", "Test"], repo)
    _commit(repo, "README.md", "init\n", "init")
    _run(["git", "branch", "-M", "main"], repo)
    return repo


def _make_manifest(mission_slug="010-feat", *, target_branch="main", lanes=None):
    return LanesManifest(
        version=1,
        mission_slug=mission_slug,
        mission_id=mission_slug,
        mission_branch=f"kitty/mission-{mission_slug}",
        target_branch=target_branch,
        lanes=lanes
        or [
            ExecutionLane(
                lane_id="lane-a",
                wp_ids=("WP01", "WP02"),
                write_scope=("src/**",),
                predicted_surfaces=(),
                depends_on_lanes=(),
                parallel_group=0,
            ),
        ],
        computed_at="2026-04-03T12:00:00+00:00",
        computed_from="test",
    )


class TestMergeLaneToMission:
    def test_successful_lane_merge(self, tmp_path):
        repo = _make_repo(tmp_path)
        manifest = _make_manifest()

        # Create mission and lane branches
        _run(["git", "branch", "kitty/mission-010-feat"], repo)
        _run(["git", "branch", "kitty/mission-010-feat-lane-a"], repo)

        # Add a commit on the lane branch
        _run(["git", "checkout", "kitty/mission-010-feat-lane-a"], repo)
        _commit(repo, "src/new.py", "lane work\n", "lane commit")
        _run(["git", "checkout", "main"], repo)

        result = merge_lane_to_mission(repo, "010-feat", "lane-a", manifest)

        assert result.success is True
        assert result.lane_id == "lane-a"
        assert result.merged_into == "kitty/mission-010-feat"

    def test_stale_lane_blocked(self, tmp_path):
        repo = _make_repo(tmp_path)
        manifest = _make_manifest()

        _run(["git", "branch", "kitty/mission-010-feat"], repo)
        _run(["git", "branch", "kitty/mission-010-feat-lane-a"], repo)

        # Both mission and lane change the same file
        _run(["git", "checkout", "kitty/mission-010-feat"], repo)
        _commit(repo, "src/views.py", "mission\n", "mission change")

        _run(["git", "checkout", "kitty/mission-010-feat-lane-a"], repo)
        _commit(repo, "src/views.py", "lane\n", "lane change")
        _run(["git", "checkout", "main"], repo)

        result = merge_lane_to_mission(repo, "010-feat", "lane-a", manifest)

        assert result.success is False
        assert result.stale_check is not None
        assert result.stale_check.is_stale is True

    def test_nonexistent_lane_branch(self, tmp_path):
        repo = _make_repo(tmp_path)
        manifest = _make_manifest()
        _run(["git", "branch", "kitty/mission-010-feat"], repo)

        result = merge_lane_to_mission(repo, "010-feat", "lane-a", manifest)

        assert result.success is False
        assert "does not exist" in result.errors[0]

    def test_unknown_lane_id(self, tmp_path):
        repo = _make_repo(tmp_path)
        manifest = _make_manifest()

        result = merge_lane_to_mission(repo, "010-feat", "lane-z", manifest)

        assert result.success is False
        assert "not found" in result.errors[0]

    def test_planning_lane_uses_target_branch_not_main(self, tmp_path):
        repo = _make_repo(tmp_path)
        _run(["git", "checkout", "-b", "release/3.1.1"], repo)
        _commit(repo, "docs/release-note.md", "planning update\n", "planning base")
        _run(["git", "checkout", "main"], repo)
        _run(["git", "branch", "kitty/mission-010-feat", "release/3.1.1"], repo)

        manifest = _make_manifest(
            target_branch="release/3.1.1",
            lanes=[
                ExecutionLane(
                    lane_id="lane-planning",
                    wp_ids=("WP00",),
                    write_scope=("kitty-specs/**",),
                    predicted_surfaces=(),
                    depends_on_lanes=(),
                    parallel_group=0,
                )
            ],
        )

        result = merge_lane_to_mission(repo, "010-feat", "lane-planning", manifest)

        assert result.success is True
        assert result.lane_id == "lane-planning"
        assert result.merged_into == "kitty/mission-010-feat"


class TestMergeMissionToTarget:
    def test_successful_mission_merge(self, tmp_path):
        repo = _make_repo(tmp_path)
        manifest = _make_manifest()

        # Create mission branch with a commit
        _run(["git", "branch", "kitty/mission-010-feat"], repo)
        _run(["git", "checkout", "kitty/mission-010-feat"], repo)
        _commit(repo, "src/feature.py", "feature\n", "feature work")
        _run(["git", "checkout", "main"], repo)

        result = merge_mission_to_target(repo, "010-feat", manifest)

        assert result.success is True
        assert result.commit is not None
        assert result.target_branch == "main"

    def test_merge_self_heals_event_log_merge_driver_config(self, tmp_path):
        repo = _make_repo(tmp_path)
        manifest = _make_manifest()

        _run(["git", "branch", "kitty/mission-010-feat"], repo)
        _run(["git", "checkout", "kitty/mission-010-feat"], repo)
        _commit(repo, "src/feature.py", "feature\n", "feature work")
        _run(["git", "checkout", "main"], repo)

        assert (
            subprocess.run(
                ["git", "config", "--local", "--get", "merge.spec-kitty-event-log.driver"],
                cwd=str(repo),
                capture_output=True,
                text=True,
            ).returncode
            != 0
        )

        result = merge_mission_to_target(repo, "010-feat", manifest)

        assert result.success is True
        driver = subprocess.run(
            ["git", "config", "--local", "--get", "merge.spec-kitty-event-log.driver"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert driver == "spec-kitty merge-driver-event-log %O %A %B"

    def test_nonexistent_mission_branch(self, tmp_path):
        repo = _make_repo(tmp_path)
        manifest = _make_manifest()

        result = merge_mission_to_target(repo, "010-feat", manifest)

        assert result.success is False
        assert "does not exist" in result.errors[0]
