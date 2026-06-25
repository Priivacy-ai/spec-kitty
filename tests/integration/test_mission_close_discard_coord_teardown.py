"""Regression: ``mission close --discard`` must tear down a coordination mission.

Reproduces a silent no-op: on a coordination-topology mission whose coordination
worktree is present, ``spec-kitty mission close --discard`` prints
``✓ Mission <slug> discarded`` but leaves the coordination worktree AND branch in
place.

Root cause exercised by this fixture (the split-brain surface layout):

* planning/identity artifacts (``meta.json`` / ``lanes.json``) live on the
  PRIMARY branch's mission dir;
* the coordination branch's mission dir is status-only (``status.events.jsonl`` /
  ``status.json``) — the coordination worktree is a full checkout of that branch;
* ``close_cmd`` resolves ``feature_dir`` via ``resolve_feature_dir_for_mission``
  (the ``tasks``-action context), which returns the coordination worktree's
  status-only dir → ``meta.json`` is absent → ``_read_mission_mid8`` returns
  ``""`` → ``_teardown_coordination_worktree`` early-returns → nothing is torn
  down, yet the command reports success.

This test asserts the CORRECT post-condition (worktree + branch gone). It FAILS
on the current code (the bug); the fix flips it green.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import mission_type
from specify_cli.coordination import CoordinationWorkspace

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

runner = CliRunner()

MISSION_ID = "01J6XW9K000000000000000000"
MID8 = MISSION_ID[:8]
# Mission dir / slug follows the real `<base>-<mid8>` identity convention so the
# coord-surface resolver composes the same mission-dir name on both branches.
SLUG = f"demo-coord-mission-{MID8}"
# Branch + worktree names come from the canonical helpers the runtime uses, so
# the fixture matches exactly what ``CoordinationWorkspace.resolve`` expects.
COORD_BRANCH = CoordinationWorkspace.branch_name(SLUG, MID8)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def coord_mission(tmp_path: Path) -> Path:
    """A coordination mission in the split-brain surface layout.

    Primary branch carries meta.json + lanes.json; the coordination branch's
    mission dir is status-only; a real coordination worktree is materialised.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".kittify").mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")

    fdir = repo / "kitty-specs" / SLUG
    fdir.mkdir(parents=True)
    (fdir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": SLUG,
                "mission_id": MISSION_ID,
                "mid8": MID8,
                "coordination_branch": COORD_BRANCH,
                "mission_branch": COORD_BRANCH,
                "target_branch": "main",
            }
        ),
        encoding="utf-8",
    )
    (fdir / "lanes.json").write_text(
        json.dumps(
            {
                "version": 1,
                "mission_slug": SLUG,
                "mission_id": MISSION_ID,
                "mission_branch": COORD_BRANCH,
                "target_branch": "main",
                "computed_at": "2026-01-01T00:00:00+00:00",
                "computed_from": "test",
                "lanes": [
                    {"lane_id": "lane-a", "wp_ids": ["WP01"], "write_scope": [],
                     "predicted_surfaces": [], "depends_on_lanes": [], "parallel_group": 0},
                ],
            }
        ),
        encoding="utf-8",
    )
    (fdir / "status.events.jsonl").write_text("", encoding="utf-8")
    (fdir / "status.json").write_text("{}", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed primary mission surface")

    # Coordination branch: status-only mission dir (drop planning artifacts).
    _git(repo, "branch", COORD_BRANCH)
    _git(repo, "checkout", "-q", COORD_BRANCH)
    _git(repo, "rm", "-q", f"kitty-specs/{SLUG}/meta.json", f"kitty-specs/{SLUG}/lanes.json")
    _git(repo, "commit", "-q", "-m", "coord: status-only mission surface")
    _git(repo, "checkout", "-q", "main")

    # Materialise the real coordination worktree (full checkout of coord branch).
    CoordinationWorkspace.resolve(repo, SLUG, MID8)
    assert CoordinationWorkspace.is_present(repo, SLUG, MID8)
    return repo


def test_close_discard_tears_down_coordination_worktree_and_branch(
    coord_mission: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = coord_mission
    monkeypatch.chdir(repo)

    result = runner.invoke(
        mission_type.app,
        ["close", "--mission", SLUG, "--discard", "--force"],
        env={"PWD": str(repo)},
    )
    assert result.exit_code == 0, result.output

    # The command must actually tear down what it claims to.
    assert not CoordinationWorkspace.is_present(repo, SLUG, MID8), (
        "coordination worktree still present after `close --discard` "
        f"(command output: {result.output!r})"
    )
    branches = _git(repo, "branch", "--list", COORD_BRANCH).stdout.strip()
    assert branches == "", f"coordination branch leaked after `close --discard`: {branches!r}"
