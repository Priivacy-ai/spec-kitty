"""ATDD: canonical lane reads must resolve the coordination worktree (#1589 facet 3).

On lane-based missions, status writes are committed to the coordination worktree
(`.worktrees/<slug>-<mid8>-coord/kitty-specs/<slug>-<mid8>/`) via the transactional
emit path. But `lane_reader` reads the *primary* checkout's mission dir, which never
receives the lane events — so `get_wp_lane`/`get_all_wp_lanes` see nothing and
`move-task`/`next` raise "no canonical status" despite a fully materialized coord log.

`workflow.py` and `acceptance` already resolve reads via
`missions._read_path_resolver.resolve_mission_read_path`; `lane_reader` was never
updated. These tests reproduce that gap: they fail on the current code (lane_reader
reads the empty primary) and pass once lane_reader resolves the coord worktree.

Legacy missions (no coord worktree) must be unaffected — the resolver returns the
primary checkout, so behavior is identical.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.status.lane_reader import (
    CanonicalStatusNotFoundError,
    get_wp_lane,
)

pytestmark = [pytest.mark.unit]

MID8 = "ABCD1234"
MISSION_ID = "ABCD1234EFGH5678IJKL9012MN"
SLUG = "demo-mission"
MISSION_DIR = f"{SLUG}-{MID8}"


def _planned_event(wp_id: str) -> str:
    return json.dumps(
        {
            "event_id": f"01TEST{wp_id}00000000000000",
            "mission_slug": SLUG,
            "wp_id": wp_id,
            "from_lane": "planned",
            "to_lane": "planned",
            "at": "2026-06-01T00:00:00+00:00",
            "actor": "finalize-tasks",
            "force": True,
            "execution_mode": "worktree",
            "reason": "canonical bootstrap",
            "review_ref": None,
            "evidence": None,
            "policy_metadata": None,
        },
        sort_keys=True,
    )


def _seed_meta(primary: Path) -> None:
    (primary / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": SLUG,
                "mission_id": MISSION_ID,
                "mid8": MID8,
                "coordination_branch": f"kitty/mission-{MISSION_DIR}",
            }
        ),
        encoding="utf-8",
    )


def test_get_wp_lane_resolves_coordination_worktree(tmp_path: Path) -> None:
    repo = tmp_path
    primary = repo / "kitty-specs" / MISSION_DIR
    primary.mkdir(parents=True)
    _seed_meta(primary)
    # Primary checkout has NO event log — exactly the desync state.
    coord = repo / ".worktrees" / f"{MISSION_DIR}-coord" / "kitty-specs" / MISSION_DIR
    coord.mkdir(parents=True)
    (coord / "status.events.jsonl").write_text(_planned_event("WP01") + "\n", encoding="utf-8")

    # ACCEPTANCE: reading the primary feature_dir must resolve the coord worktree.
    lane = get_wp_lane(primary, "WP01")
    assert str(lane) == "planned", f"expected coord status to be read; got {lane!r}"


def test_legacy_mission_without_coord_worktree_unaffected(tmp_path: Path) -> None:
    repo = tmp_path
    primary = repo / "kitty-specs" / MISSION_DIR
    primary.mkdir(parents=True)
    _seed_meta(primary)
    # No coord worktree; the event log lives in the primary checkout (legacy).
    (primary / "status.events.jsonl").write_text(_planned_event("WP01") + "\n", encoding="utf-8")

    lane = get_wp_lane(primary, "WP01")
    assert str(lane) == "planned"


def test_missing_everywhere_still_raises(tmp_path: Path) -> None:
    repo = tmp_path
    primary = repo / "kitty-specs" / MISSION_DIR
    primary.mkdir(parents=True)
    _seed_meta(primary)
    # Neither primary nor coord has an event log.
    with pytest.raises(CanonicalStatusNotFoundError):
        get_wp_lane(primary, "WP01")
