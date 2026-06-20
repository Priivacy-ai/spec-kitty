"""Regression: ``append-history`` must commit through the coordination worktree.

On a coordination-topology mission the WP prompt file lives in the coordination
worktree (``.worktrees/<mission>-coord/...``). The handler used to commit it with
``worktree_root`` set to the primary checkout, which ``safe_commit`` rejects with
``SAFE_COMMIT_PATH_POLICY`` ("Planning artifacts must be committed from the
coordination worktree"). This exercises the real CLI command against a real git
repo with a materialized coordination worktree.

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
                "target_branch": "main",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks" / "WP01.md").write_text(_WP_FILE, encoding="utf-8")
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", "seed mission")
    _git(repo, "branch", COORD_BRANCH)

    # Materialize the coordination worktree (it exists by the time the orchestrate
    # loop reaches append-history), so the WP file resolves inside it.
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


def test_append_history_commits_through_coordination_worktree(coord_repo: Path) -> None:
    result = _invoke_append_history(coord_repo)

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["data"]["wp_id"] == "WP01"

    # The activity-log edit is committed on the coordination branch, with the note.
    committed = _git(
        coord_repo,
        "show",
        f"{COORD_BRANCH}:kitty-specs/{MISSION_DIRNAME}/tasks/WP01.md",
    )
    assert "Starting implementation" in committed.stdout

    # And the primary checkout's branch carries no such commit (it lives only on
    # the coordination branch — the whole point of coord topology).
    main_log = _git(coord_repo, "log", "--oneline", "main")
    assert "append activity log" not in main_log.stdout
