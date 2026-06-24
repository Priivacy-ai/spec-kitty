"""Contract: ``append-history`` commits the WP prompt file to the PRIMARY surface.

write-surface-coherence WP03 (FR-003 / T013): a WP prompt file is a
``WORK_PACKAGE_TASK`` — a PRIMARY artifact kind. So ``append-history`` commits it
to the mission's primary ``target_branch`` for every topology, directly from the
primary checkout — NOT through the coordination worktree (the planning→coord
transit is removed, C-005). This re-pins the prior regression (which asserted the
removed coord-transit contract) onto the primary surface.

Uses git (unlike ``test_orchestrator_commands_integration.py``, which is git-free).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.orchestrator_api.commands import app

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

runner = CliRunner()

MISSION_SLUG = "hist-coord"
MID8 = "01KHIST0"
MISSION_ID = "01KHIST0000000000000000000"
MISSION_DIRNAME = f"{MISSION_SLUG}-{MID8}"
COORD_BRANCH = f"kitty/mission-{MISSION_DIRNAME}"
# The mission's primary feature target_branch. Planning/WP-prompt commits land
# here (FR-003), so it is a NON-protected feature branch the operator is on.
TARGET_BRANCH = "feat/hist-target"

_WP_FILE = (
    "---\n"
    "work_package_id: WP01\n"
    "title: Test WP01\n"
    "dependencies: []\n"
    "---\n\n"
    "# WP01\n\n"
    "## Activity Log\n"
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )


@pytest.fixture
def coord_repo(tmp_path: Path) -> Path:
    """A git repo with a coordination-topology mission and a live coord worktree."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")

    feature_dir = repo / "kitty-specs" / MISSION_DIRNAME
    (feature_dir / "tasks").mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": MISSION_SLUG,
                "mission_id": MISSION_ID,
                "mid8": MID8,
                "coordination_branch": COORD_BRANCH,
                "target_branch": TARGET_BRANCH,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks" / "WP01.md").write_text(_WP_FILE, encoding="utf-8")
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", "seed mission")
    _git(repo, "branch", COORD_BRANCH)

    # The WP prompt file is a primary kind → lands on the primary feature
    # target_branch (FR-003 / T013). The operator is ON that feature branch (D-3),
    # so check it out as HEAD; the commit lands there directly with no coord
    # transit. The coordination worktree still exists (status routes there).
    _git(repo, "checkout", "-q", "-b", TARGET_BRANCH)
    coord_worktree = CoordinationWorkspace.worktree_path(repo, MISSION_SLUG, MID8)
    _git(repo, "worktree", "add", "-q", str(coord_worktree), COORD_BRANCH)
    return repo


def _invoke_append_history(repo: Path) -> object:
    with patch(
        "specify_cli.orchestrator_api.commands._get_main_repo_root",
        return_value=repo,
    ):
        return runner.invoke(
            app,
            [
                "append-history",
                "--mission",
                MISSION_DIRNAME,
                "--wp",
                "WP01",
                "--actor",
                "claude",
                "--note",
                "Starting implementation",
            ],
        )


def test_append_history_commits_to_primary_target_branch(coord_repo: Path) -> None:
    result = _invoke_append_history(coord_repo)

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["data"]["wp_id"] == "WP01"

    # FR-003 / T013: the WP-prompt edit (WORK_PACKAGE_TASK, a primary kind) is
    # committed on the PRIMARY feature target_branch, with the note.
    committed = _git(
        coord_repo,
        "show",
        f"{TARGET_BRANCH}:kitty-specs/{MISSION_DIRNAME}/tasks/WP01.md",
    )
    assert "Starting implementation" in committed.stdout

    # And the coordination branch carries NO such commit — the planning→coord
    # transit is removed (C-005). The WP edit never touches the coord branch.
    coord_show = subprocess.run(
        ["git", "show", f"{COORD_BRANCH}:kitty-specs/{MISSION_DIRNAME}/tasks/WP01.md"],
        cwd=coord_repo,
        capture_output=True,
        text=True,
    )
    assert "Starting implementation" not in coord_show.stdout, (
        "WP-prompt edit leaked onto the coordination branch — planning→coord "
        "transit was not removed (FR-003 / C-005)."
    )
