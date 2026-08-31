"""Composition coverage for the coordination-less protected-branch remedy."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from specify_cli.coordination.transaction import BookkeepingTransaction
from specify_cli.coordination.transaction_errors import BookkeepingPolicyRefused
from specify_cli.coordination.types import PROTECTED_BRANCH_REFUSED

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_HATCH_ENV = "SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def repo_root(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "seed")
    return repo


def _make_single_branch_mission(repo_root: Path) -> dict[str, Any]:
    mission_slug = "no-coord-remedy-compose"
    mission_id = "01M3536COMPOSEZZZZZZZZZZZZ"
    mid8 = mission_id[:8]
    feature_dir = repo_root / "kitty-specs" / f"{mission_slug}-{mid8}"
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, Any] = {
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "mid8": mid8,
        "mission_type": "research",
        "target_branch": "main",
        "topology": "single_branch",
        "created_at": "2026-01-01T00:00:00+00:00",
        "friendly_name": "Issue 851 acquire-composition mission",
    }
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2),
        encoding="utf-8",
    )
    _git(repo_root, "add", "kitty-specs")
    _git(repo_root, "commit", "-q", "-m", "seed mission scaffold")
    lane_branch = f"kitty/mission-{mission_slug}-{mid8}-lane-a"
    _git(repo_root, "branch", lane_branch, "main")
    lane_worktree = repo_root / ".worktrees" / f"{mission_slug}-{mid8}-lane-a"
    lane_worktree.parent.mkdir(parents=True, exist_ok=True)
    _git(repo_root, "worktree", "add", str(lane_worktree), lane_branch)
    return {
        "mission_slug": mission_slug,
        "mission_id": mission_id,
        "mid8": mid8,
    }


def test_acquire_composes_no_coord_remedy_for_single_branch_mission(
    repo_root: Path,
) -> None:
    mission = _make_single_branch_mission(repo_root)

    with pytest.raises(BookkeepingPolicyRefused) as excinfo:
        BookkeepingTransaction.acquire(
            repo_root=repo_root,
            mission_id=mission["mission_id"],
            mission_slug=mission["mission_slug"],
            mid8=mission["mid8"],
            destination_ref="main",
            operation="emit_status_transition",
        )

    verdict = excinfo.value.verdict
    assert verdict.error_code == PROTECTED_BRANCH_REFUSED
    assert _HATCH_ENV in verdict.next_step
    assert "coordination branch" not in verdict.next_step.lower()
