"""Tests for stale-lane merge blocker.

Uses real git repos to test file-level overlap detection.
"""

import subprocess

import pytest

from specify_cli.lanes.models import ExecutionLane
from specify_cli.lanes.stale_check import check_lane_staleness

pytestmark = pytest.mark.git_repo


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


def _lane(lane_id="lane-a", wp_ids=("WP01",)):
    return ExecutionLane(
        lane_id=lane_id,
        wp_ids=wp_ids,
        write_scope=("src/**",),
        predicted_surfaces=(),
        depends_on_lanes=(),
        parallel_group=0,
    )


class TestCheckLaneStaleness:
    def test_not_stale_when_mission_unchanged(self, tmp_path):
        repo = _make_repo(tmp_path)
        # Create mission and lane branches from same point
        _run(["git", "branch", "kitty/mission-feat"], repo)
        _run(["git", "branch", "kitty/mission-feat-lane-a"], repo)

        result = check_lane_staleness(
            _lane(),
            "kitty/mission-feat-lane-a",
            "kitty/mission-feat",
            repo,
        )
        assert result.is_stale is False

    def test_not_stale_when_no_file_overlap(self, tmp_path):
        repo = _make_repo(tmp_path)
        _run(["git", "branch", "kitty/mission-feat"], repo)
        _run(["git", "branch", "kitty/mission-feat-lane-a"], repo)

        # Mission changes file A
        _run(["git", "checkout", "kitty/mission-feat"], repo)
        _commit(repo, "src/a.py", "mission\n", "mission change")

        # Lane changes file B
        _run(["git", "checkout", "kitty/mission-feat-lane-a"], repo)
        _commit(repo, "src/b.py", "lane\n", "lane change")

        _run(["git", "checkout", "main"], repo)

        result = check_lane_staleness(
            _lane(),
            "kitty/mission-feat-lane-a",
            "kitty/mission-feat",
            repo,
        )
        assert result.is_stale is False

    def test_stale_when_overlapping_files(self, tmp_path):
        repo = _make_repo(tmp_path)
        _run(["git", "branch", "kitty/mission-feat"], repo)
        _run(["git", "branch", "kitty/mission-feat-lane-a"], repo)

        # Mission changes src/views.py
        _run(["git", "checkout", "kitty/mission-feat"], repo)
        _commit(repo, "src/views.py", "mission version\n", "mission change")

        # Lane also changes src/views.py
        _run(["git", "checkout", "kitty/mission-feat-lane-a"], repo)
        _commit(repo, "src/views.py", "lane version\n", "lane change")

        _run(["git", "checkout", "main"], repo)

        result = check_lane_staleness(
            _lane(),
            "kitty/mission-feat-lane-a",
            "kitty/mission-feat",
            repo,
        )
        assert result.is_stale is True
        assert "src/views.py" in result.stale_files
        assert result.remediation is not None
        assert "git merge" in result.remediation

    def test_stale_reports_only_overlapping_files(self, tmp_path):
        repo = _make_repo(tmp_path)
        _run(["git", "branch", "kitty/mission-feat"], repo)
        _run(["git", "branch", "kitty/mission-feat-lane-a"], repo)

        # Mission changes two files
        _run(["git", "checkout", "kitty/mission-feat"], repo)
        _commit(repo, "src/a.py", "m\n", "m1")
        _commit(repo, "src/b.py", "m\n", "m2")

        # Lane changes one overlapping + one unique
        _run(["git", "checkout", "kitty/mission-feat-lane-a"], repo)
        _commit(repo, "src/a.py", "l\n", "l1")
        _commit(repo, "src/c.py", "l\n", "l2")

        _run(["git", "checkout", "main"], repo)

        result = check_lane_staleness(
            _lane(),
            "kitty/mission-feat-lane-a",
            "kitty/mission-feat",
            repo,
        )
        assert result.is_stale is True
        assert result.stale_files == ["src/a.py"]
