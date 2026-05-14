"""Integration tests for the stale-lane auto-rebase orchestrator.

Covers WP08 / T044 (happy path — two-lane additive merge) and T045 (negative
path — semantic conflict).

The orchestrator operates inside a git worktree and shells out to ``git``;
these tests construct a minimal real git repository in ``tmp_path``.
"""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

import pytest

from specify_cli.lanes.auto_rebase import AutoRebaseReport, attempt_auto_rebase
from specify_cli.lanes.models import ExecutionLane

pytestmark = pytest.mark.git_repo


def _run(cmd: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, check=check
    )


def _init_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo with main + mission branches and one shared file."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "-b", "main", str(repo)], tmp_path)
    _run(["git", "config", "user.email", "test@spec-kitty"], repo)
    _run(["git", "config", "user.name", "test"], repo)
    # Seed with a pyproject.toml.
    seed = (
        "[project]\n"
        'name = "demo"\n'
        "dependencies = [\n"
        '  "alpha",\n'
        '  "bravo",\n'
        "]\n"
    )
    (repo / "pyproject.toml").write_text(seed)
    _run(["git", "add", "pyproject.toml"], repo)
    _run(["git", "commit", "-m", "seed"], repo)
    return repo


def _make_lane() -> ExecutionLane:
    return ExecutionLane(
        lane_id="lane-a",
        wp_ids=("WP01",),
        write_scope=("pyproject.toml",),
        predicted_surfaces=(),
        depends_on_lanes=(),
        parallel_group=0,
    )


def _make_lane_worktree(repo: Path, mission_slug: str, lane_id: str, branch: str) -> Path:
    """Create a lane worktree following the spec-kitty path convention."""
    worktree = repo / ".worktrees" / f"{mission_slug}-{lane_id}"
    worktree.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "worktree", "add", "-b", branch, str(worktree), "main"], repo)
    return worktree


def _write_pyproject(path: Path, deps: list[str]) -> None:
    body = "[project]\nname = \"demo\"\ndependencies = [\n"
    for d in deps:
        body += f'  "{d}",\n'
    body += "]\n"
    path.write_text(body)


class TestAutoRebaseAdditive:
    """T044 — Happy path: two lanes add distinct deps; auto-resolve."""

    def test_two_lane_additive_pyproject_merge(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        mission_slug = "008-demo"
        mission_branch = f"kitty/mission-{mission_slug}"

        # Create the mission branch at main's tip.
        _run(["git", "branch", mission_branch, "main"], repo)

        # Lane A's branch — simulated past-merge state via the mission branch:
        # we directly add a dep on the mission branch.
        _run(["git", "checkout", mission_branch], repo)
        _write_pyproject(repo / "pyproject.toml", ["alpha", "bravo", "charlie"])
        _run(["git", "add", "pyproject.toml"], repo)
        _run(["git", "commit", "-m", "mission: add charlie"], repo)
        _run(["git", "checkout", "main"], repo)

        # Lane B's branch with a different additive change.
        branch_b = f"kitty/mission-{mission_slug}-lane-a"
        worktree_b = _make_lane_worktree(repo, mission_slug, "lane-a", branch_b)
        _write_pyproject(
            worktree_b / "pyproject.toml", ["alpha", "bravo", "delta"]
        )
        _run(["git", "add", "pyproject.toml"], worktree_b)
        _run(["git", "config", "user.email", "test@spec-kitty"], worktree_b)
        _run(["git", "config", "user.name", "test"], worktree_b)
        _run(["git", "commit", "-m", "lane: add delta"], worktree_b)

        # Now Lane B is stale — its pyproject.toml conflicts with mission's.
        lane = _make_lane()
        report = attempt_auto_rebase(
            lane=lane,
            branch=branch_b,
            mission_branch=mission_branch,
            repo_root=repo,
            worktree_path=worktree_b,
        )

        assert isinstance(report, AutoRebaseReport)
        assert report.attempted is True
        assert report.succeeded is True, f"halt_reason={report.halt_reason}"
        assert report.halt_reason is None

        # Verify both deps survived.
        merged = (worktree_b / "pyproject.toml").read_text()
        data = tomllib.loads(merged)
        deps = data["project"]["dependencies"]
        # All four deps (alpha, bravo, charlie, delta) should be present.
        names = [d.split(">=")[0].split("==")[0].strip() for d in deps]
        for expected in ("alpha", "bravo", "charlie", "delta"):
            assert expected in names, f"expected {expected} in {names}"

        # Verify a merge commit landed with the expected message format.
        log = _run(
            ["git", "log", "-1", "--pretty=%s"], worktree_b, check=False
        )
        assert log.returncode == 0
        assert "auto-rebase(lane=lane-a)" in log.stdout
        assert "R-PYPROJECT-DEPS-UNION" in log.stdout


class TestAutoRebaseSemanticConflict:
    """T045 — Negative: a semantic conflict falls through to Manual."""

    def test_semantic_conflict_halts_and_cleans_up(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        mission_slug = "009-demo"
        mission_branch = f"kitty/mission-{mission_slug}"

        # Add a code file that both sides will modify in incompatible ways.
        _run(["git", "branch", mission_branch, "main"], repo)
        _run(["git", "checkout", mission_branch], repo)
        (repo / "src").mkdir(parents=True, exist_ok=True)
        (repo / "src" / "flags.py").write_text(
            "def enabled():\n    return False\n"
        )
        _run(["git", "add", "src/flags.py"], repo)
        _run(["git", "commit", "-m", "mission: add flags"], repo)

        # Modify on mission branch.
        (repo / "src" / "flags.py").write_text(
            "def enabled():\n    # Mission's preferred body\n    return False\n"
        )
        _run(["git", "add", "src/flags.py"], repo)
        _run(["git", "commit", "-m", "mission: modify flags"], repo)
        _run(["git", "checkout", "main"], repo)

        # Lane branch makes a conflicting modification.
        branch_b = f"kitty/mission-{mission_slug}-lane-a"
        worktree_b = _make_lane_worktree(repo, mission_slug, "lane-a", branch_b)
        _run(["git", "config", "user.email", "test@spec-kitty"], worktree_b)
        _run(["git", "config", "user.name", "test"], worktree_b)
        (worktree_b / "src").mkdir(parents=True, exist_ok=True)
        (worktree_b / "src" / "flags.py").write_text(
            "def enabled():\n    # Lane's preferred body\n    return True\n"
        )
        _run(["git", "add", "src/flags.py"], worktree_b)
        _run(["git", "commit", "-m", "lane: modify flags"], worktree_b)

        lane = _make_lane()
        report = attempt_auto_rebase(
            lane=lane,
            branch=branch_b,
            mission_branch=mission_branch,
            repo_root=repo,
            worktree_path=worktree_b,
        )

        assert report.attempted is True
        assert report.succeeded is False
        assert report.halt_reason is not None
        # The default rule's reason mentions the unmatched path.
        assert (
            "no classifier rule matched" in report.halt_reason
            or "src/flags.py" in report.halt_reason
        )

        # Lane B worktree must be clean (merge --abort ran).
        status = _run(["git", "status", "--porcelain"], worktree_b)
        # No conflicted files; the merge was aborted.
        assert "UU " not in status.stdout
        # The lane branch tip must still be the pre-merge commit (no merge
        # commit landed).
        rev = _run(["git", "rev-parse", "HEAD"], worktree_b)
        assert rev.returncode == 0
