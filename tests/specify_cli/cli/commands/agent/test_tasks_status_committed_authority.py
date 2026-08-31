"""Board regression: ``agent tasks status`` must read committed lanes for a
merged mission, not a stale coordination checkout (WP01 T001, #2947).

Mission next-committed-state-authority-01M1CA8W. Before the fix, the board's
lane rollup reads WP lanes from the (possibly stale) topology-resolved
``feature_dir`` — for a merged mission whose coordination worktree has not
been cleaned up, that surface still shows the pre-merge ``planned`` lanes even
though the PRIMARY checkout carries the committed ``accepted`` truth
(``tasks_status_cmd.py`` :193 already reads ``tasks/`` from PRIMARY; the lane
read did not, until this fix).

The fixture below builds TWO DISTINCT on-disk surfaces on purpose (a
single-dir fixture would not exercise the bug): a committed PRIMARY (accepted)
and a stale COORD checkout (still planned). An explicit assertion proves the
two surfaces diverge before asserting the board's committed-lane output.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event, read_events
from tests.mocked_env import setup_mocked_env

pytestmark = pytest.mark.fast

runner = CliRunner()

_SLUG = "committed-board-01KZCD"


def _write_wp_file(tasks_dir: Path, wp_id: str) -> None:
    (tasks_dir / f"{wp_id}-test.md").write_text(
        "---\n"
        f"work_package_id: {wp_id}\n"
        f"title: Test {wp_id}\n"
        "execution_mode: code_change\n"
        "---\n"
        f"# {wp_id}\n",
        encoding="utf-8",
    )


def _seed_lane(feature_dir: Path, wp_id: str, *, from_lane: Lane, to_lane: Lane) -> None:
    append_event(
        feature_dir,
        StatusEvent(
            event_id=f"test-{feature_dir.name}-{wp_id}-{to_lane}",
            mission_slug=_SLUG,
            wp_id=wp_id,
            from_lane=from_lane,
            to_lane=to_lane,
            at="2026-01-01T00:00:00+00:00",
            actor="test",
            force=True,
            execution_mode="worktree",
        ),
    )


def _build_two_surface_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """Build a committed PRIMARY (accepted) + a stale COORD checkout (planned)."""
    primary = tmp_path / "kitty-specs" / _SLUG
    tasks_dir = primary / "tasks"
    tasks_dir.mkdir(parents=True)
    _write_wp_file(tasks_dir, "WP01")
    _write_wp_file(tasks_dir, "WP02")
    (primary / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": _SLUG,
                "mission_id": "01KZCD00000000000000000AB",
                "mission_number": 99,
                "mission_type": "software-dev",
                "coordination_branch": f"kitty/mission-{_SLUG}",
            }
        ),
        encoding="utf-8",
    )
    _seed_lane(primary, "WP01", from_lane=Lane.IN_REVIEW, to_lane=Lane.APPROVED)
    _seed_lane(primary, "WP02", from_lane=Lane.APPROVED, to_lane=Lane.DONE)

    coord = tmp_path / ".worktrees" / f"{_SLUG}-coord" / "kitty-specs" / _SLUG
    coord.mkdir(parents=True)
    _seed_lane(coord, "WP01", from_lane=Lane.GENESIS, to_lane=Lane.PLANNED)
    _seed_lane(coord, "WP02", from_lane=Lane.GENESIS, to_lane=Lane.PLANNED)

    return primary, coord


@pytest.mark.regression
def test_status_board_reports_committed_lanes_for_merged_mission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#2947: a merged mission's board must show committed (accepted) lanes,
    never the stale coordination checkout's pre-merge ``planned`` lanes."""
    primary, coord = _build_two_surface_fixture(tmp_path)

    # The two on-disk surfaces genuinely diverge -- proves the stale-coord leg
    # is under test, not a same-dir no-op (SHOULD-FIX-6).
    primary_events = read_events(primary)
    coord_events = read_events(coord)
    assert {e.to_lane for e in primary_events} == {Lane.APPROVED, Lane.DONE}
    assert {e.to_lane for e in coord_events} == {Lane.PLANNED}

    workspace = SimpleNamespace(execution_mode="code_change", resolution_kind="lane_workspace")
    monkeypatch.chdir(tmp_path)

    with (
        setup_mocked_env(tmp_path, mission_slug=_SLUG, workspace_resolution=workspace),
        # Simulate the real topology resolver landing on the still-present
        # (stale) coordination checkout -- exactly what a merged mission whose
        # coord worktree was never cleaned up produces (D1/D7: the resolver is
        # existence-gated and freshness-blind).
        patch(
            "specify_cli.missions._read_path_resolver.resolve_handle_to_read_path",
            return_value=coord,
        ),
    ):
        result = runner.invoke(app, ["status", "--mission", _SLUG, "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    lanes_by_id = {wp["id"]: wp["lane"] for wp in payload["work_packages"]}

    # Before the fix: {"WP01": "planned", "WP02": "planned"} (the stale coord
    # rollup). After the fix: the committed PRIMARY lanes.
    assert lanes_by_id == {"WP01": "approved", "WP02": "done"}
    assert payload["by_lane"].get("planned", 0) == 0
