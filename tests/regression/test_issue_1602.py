"""Regression for issue #1602 — coordination commit clobbers the canonical log.

On lane-based missions the canonical lane transitions live ONLY on the
coordination branch (the emit pipeline appends them straight to the coord
worktree). The workflow commit (``_commit_via_coordination_transaction``,
reached from ``agent action review`` / ``move-task``) re-committed the
*main-checkout* copy of ``status.events.jsonl`` to the coordination branch.
That copy carries only the bootstrap + lifecycle/decision *envelope* events
(``event_type``/``schema_version`` records the reducer skips) — NOT the lane
transitions. Overwriting the coord copy with it wiped the lane history, so
``read_events()`` returned 0 and the implement/review loop wedged with
"WP has no canonical status".

This test reproduces the clobber through the real coordination-commit code
path and pins the append-only fix: the coordination branch's event log must
never lose an event it already has.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.cli.commands.agent.workflow import _commit_via_coordination_transaction
from specify_cli.coordination.transaction import BookkeepingTransaction
from specify_cli.status.emit import build_status_event
from specify_cli.status.reducer import reduce
from specify_cli.status.store import read_events

pytestmark = [pytest.mark.regression, pytest.mark.git_repo]

MISSION_SLUG = "regression-1602"
MID8 = "01J6CLB16"
MISSION_ID = "01J6CLB1600000000000000000"
COORD_BRANCH = f"kitty/mission-{MISSION_SLUG}-{MID8}"
FEATURE_DIRNAME = f"{MISSION_SLUG}-{MID8}"

import subprocess  # noqa: E402


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )


def _init_coord_mission(repo: Path) -> Path:
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "regression@example.invalid")
    _git(repo, "config", "user.name", "Regression-1602")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "initial")
    _git(repo, "branch", COORD_BRANCH)

    feature_dir = repo / "kitty-specs" / FEATURE_DIRNAME
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": MISSION_ID,
                "mission_slug": MISSION_SLUG,
                "mid8": MID8,
                "mission_type": "software-dev",
                "target_branch": "main",
                "coordination_branch": COORD_BRANCH,
                "created_at": "2026-06-01T00:00:00+00:00",
                "friendly_name": "Issue #1602 regression mission",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", "seed mission scaffold")
    return feature_dir


def _coord_feature_dir(repo: Path) -> Path:
    return repo / ".worktrees" / f"{FEATURE_DIRNAME}-coord" / "kitty-specs" / FEATURE_DIRNAME


def _seed_coord_lane_history(repo: Path) -> None:
    """Append planned→claimed→in_progress for WP01 to the coordination branch.

    Uses the real BookkeepingTransaction (same path the emit pipeline takes), so
    the coord worktree is created and the canonical lane log committed authentically.
    """
    events = [
        build_status_event(
            mission_slug=MISSION_SLUG, mission_id=MISSION_ID, wp_id="WP01",
            from_lane="planned", to_lane="claimed", actor="implementer-ivan",
        ),
        build_status_event(
            mission_slug=MISSION_SLUG, mission_id=MISSION_ID, wp_id="WP01",
            from_lane="claimed", to_lane="in_progress", actor="implementer-ivan",
        ),
    ]
    with BookkeepingTransaction.acquire(
        repo_root=repo,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MID8,
        destination_ref=COORD_BRANCH,
        operation="seed-1602-lane-history",
    ) as txn:
        for event in events:
            txn.append_event(event)
        txn.commit("status: WP01 lane history")


def _write_clobbering_main_copy(feature_dir: Path) -> Path:
    """Main-checkout status.events.jsonl with ONLY an envelope event (no lanes)."""
    path = feature_dir / "status.events.jsonl"
    path.write_text(
        json.dumps(
            {
                "aggregate_id": MISSION_SLUG,
                "aggregate_type": "Mission",
                "event_id": "01ENV160200000000000000001",
                "event_type": "TasksStarted",
                "payload": {"at": "2026-06-01T00:00:00Z"},
                "schema_version": "5.0.0",
                "timestamp": "2026-06-01T00:00:00+00:00",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_review_commit_does_not_clobber_coordination_lane_history(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    main_feature_dir = _init_coord_mission(repo)

    # 1) Canonical lane history lives on the coordination branch.
    _seed_coord_lane_history(repo)
    coord_feature_dir = _coord_feature_dir(repo)
    before = reduce(read_events(coord_feature_dir))
    assert before.work_packages["WP01"]["lane"] == "in_progress"

    # 2) The main checkout's copy carries only an envelope event — exactly the
    #    state that previously clobbered coord when committed back to it.
    main_events = _write_clobbering_main_copy(main_feature_dir)

    # 3) Drive the real review/move-task coordination commit with that copy.
    _commit_via_coordination_transaction(
        coord_branch=COORD_BRANCH,
        repo_root=repo,
        mission_slug=MISSION_SLUG,
        paths=[main_events],
        message="chore: Start WP01 review [reviewer]",
        operation="for_review -> in_review for WP01",
        mission_id=MISSION_ID,
        mid8=MID8,
        wp_id="WP01",
    )

    # 4) The coordination branch's lane history MUST survive (no clobber): the
    #    reducer still sees WP01 in_progress, and the envelope event is carried.
    after = reduce(read_events(coord_feature_dir))
    assert after.work_packages["WP01"]["lane"] == "in_progress", (
        "coordination lane history was clobbered by the main-checkout copy (#1602)"
    )
    raw_ids = [
        json.loads(line)["event_id"]
        for line in (coord_feature_dir / "status.events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert "01ENV160200000000000000001" in raw_ids  # new envelope event carried
