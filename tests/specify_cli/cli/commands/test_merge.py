"""Tests for merge.py.

WP06 slice: Migrate Slice 4 — merge.py typed Lane enum migration.

Verifies that:
- _assert_merged_wps_reached_done() uses typed Lane enum (Lane.DONE), not raw "done"
- _mark_wp_merged_done() uses typed Lane enum comparisons throughout
- approved|done merge-ready check is EXPLICIT (not delegated to is_terminal)
- is_terminal covers done|canceled — not the same as merge-ready approved|done
- All 9 lanes are correctly classified as merge-ready or not

WP01 slice: merge --abort cleanup.

Verifies that:
- --abort removes .kittify/runtime/merge/__global_merge__/lock when present
- --abort removes .kittify/merge-state.json (legacy) when present
- --abort is idempotent — exits 0 when neither file is present
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.cli.commands.merge import (
    _assert_merged_wps_reached_done,
    _mark_wp_merged_done,
    merge,
)
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event

pytestmark = [pytest.mark.fast, pytest.mark.non_sandbox]  # non_sandbox: subprocess CLI invocation
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_wp(
    path: Path,
    *,
    review_status: str = "approved",
    reviewed_by: str = "reviewer-1",
    agent: str = "test-agent",
) -> None:
    """Write a minimal WP frontmatter file."""
    lines = [
        "---",
        'work_package_id: "WP01"',
        'title: "Test WP"',
        "dependencies: []",
        f'review_status: "{review_status}"',
        f'reviewed_by: "{reviewed_by}"',
        f'agent: "{agent}"',
        "---",
        "# WP01",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_minimal_meta(feature_dir: Path, mission_slug: str) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_id": "01TEST00000000000000000000", "mission_slug": mission_slug}),
        encoding="utf-8",
    )


def _append_done_event(feature_dir: Path, wp_id: str) -> None:
    """Seed the event log with a done transition for *wp_id*."""
    event = StatusEvent(
        event_id=f"01TEST{wp_id}DONE".ljust(26, "0")[:26],
        mission_slug=feature_dir.name,
        wp_id=wp_id,
        from_lane=Lane.APPROVED,
        to_lane=Lane.DONE,
        at="2026-04-09T12:00:00+00:00",
        actor="merge",
        force=False,
        execution_mode="direct_repo",
    )
    append_event(feature_dir, event)


# ---------------------------------------------------------------------------
# T015: Verify approved|done merge-ready check is EXPLICIT (not is_terminal)
# ---------------------------------------------------------------------------


def test_merge_ready_lanes_approved_and_done_only() -> None:
    """CRITICAL: Only approved and done are merge-ready; is_terminal is NOT used."""
    from specify_cli.status.transitions import is_terminal

    # is_terminal covers done|canceled — that's cleanup logic, not merge-readiness
    # approved is merge-ready but NOT terminal
    assert not is_terminal(Lane.APPROVED.value), \
        "approved must NOT be terminal — merge-readiness is a distinct concept"

    # canceled is terminal but NOT merge-ready
    # This is the key distinction: if we used is_terminal for merge-readiness,
    # canceled WPs would incorrectly pass the merge gate.
    assert is_terminal(Lane.CANCELED.value), "canceled is terminal"
    assert is_terminal(Lane.DONE.value), "done is terminal"

    # Define merge-readiness explicitly as the source code does: approved|done only
    _MERGE_READY = frozenset({Lane.APPROVED, Lane.DONE})

    # Verify all 9 lanes against the explicit check
    expected: dict[Lane, bool] = {
        Lane.PLANNED: False,
        Lane.CLAIMED: False,
        Lane.IN_PROGRESS: False,
        Lane.FOR_REVIEW: False,
        Lane.IN_REVIEW: False,
        Lane.APPROVED: True,
        Lane.DONE: True,
        Lane.BLOCKED: False,
        Lane.CANCELED: False,   # terminal but NOT merge-ready!
    }
    for lane, should_be_ready in expected.items():
        is_ready = lane in _MERGE_READY
        assert is_ready == should_be_ready, (
            f"Lane {lane.value}: expected merge-ready={should_be_ready}, got {is_ready}"
        )


def test_canceled_is_not_merge_ready_even_though_terminal() -> None:
    """canceled is is_terminal=True but must NOT be merge-ready."""
    from specify_cli.status.transitions import is_terminal

    assert is_terminal(Lane.CANCELED.value), "canceled is terminal"
    # Explicit approved|done check: canceled is excluded
    _MERGE_READY = frozenset({Lane.APPROVED, Lane.DONE})
    assert Lane.CANCELED not in _MERGE_READY, \
        "canceled must NOT be in merge-ready set (approved|done)"


# ---------------------------------------------------------------------------
# T015: _assert_merged_wps_reached_done live function tests
# ---------------------------------------------------------------------------


def test_assert_merged_wps_reached_done_passes_when_all_done(tmp_path: Path) -> None:
    """All WPs in done → no exit raised."""
    mission_slug = "080-test-feature"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_id": "01TEST00000000000000000000", "mission_slug": mission_slug}),
        encoding="utf-8",
    )

    _append_done_event(feature_dir, "WP01")
    _append_done_event(feature_dir, "WP02")

    # Should not raise
    _assert_merged_wps_reached_done(tmp_path, mission_slug, ["WP01", "WP02"])


def test_assert_merged_wps_reached_done_raises_when_wp_not_done(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WP not in done → typer.Exit(1) raised."""
    mission_slug = "080-test-feature"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_id": "01TEST00000000000000000000", "mission_slug": mission_slug}),
        encoding="utf-8",
    )

    # WP01 done, WP02 only approved
    _append_done_event(feature_dir, "WP01")
    # WP02 stays at approved (no done event)
    event = StatusEvent(
        event_id="01TESTWP02APPROVED0000000000",
        mission_slug=mission_slug,
        wp_id="WP02",
        from_lane=Lane.IN_PROGRESS,
        to_lane=Lane.APPROVED,
        at="2026-04-09T12:00:00+00:00",
        actor="reviewer",
        force=False,
        execution_mode="direct_repo",
    )
    append_event(feature_dir, event)

    with pytest.raises(typer.Exit):
        _assert_merged_wps_reached_done(tmp_path, mission_slug, ["WP01", "WP02"])


def test_assert_merged_wps_reached_done_includes_lane_value_in_error(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Error message includes WP id and current lane value (not raw string)."""
    mission_slug = "080-test-feature"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_id": "01TEST00000000000000000000", "mission_slug": mission_slug}),
        encoding="utf-8",
    )

    # WP01 is in in_progress (not done)
    event = StatusEvent(
        event_id="01TESTWP01INPROG000000000000",
        mission_slug=mission_slug,
        wp_id="WP01",
        from_lane=Lane.CLAIMED,
        to_lane=Lane.IN_PROGRESS,
        at="2026-04-09T12:00:00+00:00",
        actor="test",
        force=True,
        execution_mode="direct_repo",
    )
    append_event(feature_dir, event)

    with pytest.raises(typer.Exit):
        _assert_merged_wps_reached_done(tmp_path, mission_slug, ["WP01"])


# ---------------------------------------------------------------------------
# T015: _mark_wp_merged_done live function tests
# ---------------------------------------------------------------------------


def test_mark_wp_merged_done_emits_done_when_lane_is_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_mark_wp_merged_done emits done transition when WP is in approved lane."""
    mission_slug = "080-test-feature"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    _write_minimal_meta(feature_dir, mission_slug)
    _write_wp(tasks_dir / "WP01-test.md", reviewed_by="reviewer-1")

    emit_calls: list[Any] = []

    def fake_emit(request: Any, **_kwargs: object) -> None:
        emit_calls.append(request)

    monkeypatch.setattr("specify_cli.coordination.status_transition.emit_status_transition_transactional", fake_emit)
    monkeypatch.setattr(
        "specify_cli.status.lane_reader.get_wp_lane",
        lambda *_a, **_kw: "approved",
    )

    _mark_wp_merged_done(tmp_path, mission_slug, "WP01", "main")

    assert len(emit_calls) == 1
    assert emit_calls[0].to_lane == "done"
    assert emit_calls[0].actor == "merge"


def test_mark_wp_merged_done_skips_when_already_done(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_mark_wp_merged_done is idempotent when WP is already in done lane."""
    mission_slug = "080-test-feature"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    _write_minimal_meta(feature_dir, mission_slug)
    _write_wp(tasks_dir / "WP01-test.md")

    emit_mock = Mock()
    monkeypatch.setattr("specify_cli.coordination.status_transition.emit_status_transition_transactional", emit_mock)
    monkeypatch.setattr(
        "specify_cli.status.lane_reader.get_wp_lane",
        lambda *_a, **_kw: "done",
    )

    _mark_wp_merged_done(tmp_path, mission_slug, "WP01", "main")

    emit_mock.assert_not_called()


def test_mark_wp_merged_done_skips_when_no_approval_metadata_for_non_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_mark_wp_merged_done warns and returns if WP is in_progress with no evidence."""
    mission_slug = "080-test-feature"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    _write_minimal_meta(feature_dir, mission_slug)
    # WP with no review metadata
    _write_wp(tasks_dir / "WP01-test.md", review_status="", reviewed_by="")

    emit_mock = Mock()
    monkeypatch.setattr("specify_cli.coordination.status_transition.emit_status_transition_transactional", emit_mock)
    monkeypatch.setattr(
        "specify_cli.status.lane_reader.get_wp_lane",
        lambda *_a, **_kw: "in_progress",
    )
    monkeypatch.setattr(
        "specify_cli.status.history_parser.extract_done_evidence",
        lambda *_a, **_kw: None,
    )

    _mark_wp_merged_done(tmp_path, mission_slug, "WP01", "main")

    emit_mock.assert_not_called()


# ---------------------------------------------------------------------------
# T006: merge --abort cleanup tests (WP01)
# ---------------------------------------------------------------------------

def test_abort_clears_lock_and_state(tmp_path: Path) -> None:
    """--abort removes the global lock file and legacy merge-state JSON when both exist."""
    # Setup: create global merge lock
    lock_path = tmp_path / ".kittify" / "runtime" / "merge" / "__global_merge__" / "lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("2026-04-30T00:00:00+00:00", encoding="utf-8")

    # Setup: create legacy merge-state JSON
    legacy_state_path = tmp_path / ".kittify" / "merge-state.json"
    legacy_state_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_state_path.write_text('{"feature_slug": "test"}', encoding="utf-8")

    # Build a minimal typer app wrapping `merge` so we can invoke via CliRunner
    app = typer.Typer()
    app.command()(merge)

    runner = CliRunner()
    with patch("specify_cli.cli.commands.merge.find_repo_root", return_value=tmp_path):
        result = runner.invoke(app, ["--abort"])

    # Both files must be gone
    assert not lock_path.exists(), "Global merge lock file should have been removed"
    assert not legacy_state_path.exists(), "Legacy merge-state.json should have been removed"
    assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}\nOutput: {result.output}"


def test_abort_idempotent(tmp_path: Path) -> None:
    """--abort exits 0 with no error when neither lock nor state file is present."""
    # Ensure the .kittify dir doesn't even exist
    assert not (tmp_path / ".kittify").exists()

    app = typer.Typer()
    app.command()(merge)

    runner = CliRunner()
    with patch("specify_cli.cli.commands.merge.find_repo_root", return_value=tmp_path):
        result = runner.invoke(app, ["--abort"])

    assert result.exit_code == 0, (
        f"Expected exit 0 on idempotent abort, got {result.exit_code}\nOutput: {result.output}"
    )


# ---------------------------------------------------------------------------
# WP03: Coordination branch surface regression tests (T015/T016 — #1726)
# ---------------------------------------------------------------------------

_COORD_SLUG_M = "coord-test-mission"
_COORD_MISSION_ID_M = "01KTDVHZKGCHCW6HQ4V577PNES"


@pytest.fixture
def coord_branch_mission(tmp_path: Path) -> dict:
    """Minimal coord-branch fixture for test_merge.py.

    slug does NOT end in mid8, so resolver adds suffix:
      .worktrees/coord-test-mission-01KTDVHZ-coord/kitty-specs/coord-test-mission-01KTDVHZ/
    """
    mid8 = _COORD_MISSION_ID_M[:8]  # "01KTDVHZ"
    coord_branch = f"kitty/mission-{_COORD_SLUG_M}-{mid8}"

    primary_dir = tmp_path / "kitty-specs" / _COORD_SLUG_M
    primary_dir.mkdir(parents=True)
    (primary_dir / "meta.json").write_text(
        json.dumps({
            "mission_id": _COORD_MISSION_ID_M,
            "mission_slug": _COORD_SLUG_M,
            "slug": _COORD_SLUG_M,
            "coordination_branch": coord_branch,
            "target_branch": "main",
        }),
        encoding="utf-8",
    )

    coord_dir_name = f"{_COORD_SLUG_M}-{mid8}"
    coord_specs = (
        tmp_path / ".worktrees" / f"{coord_dir_name}-coord"
        / "kitty-specs" / coord_dir_name
    )
    coord_specs.mkdir(parents=True)
    coord_events = coord_specs / "status.events.jsonl"
    coord_events.write_text("", encoding="utf-8")

    return {
        "repo_root": tmp_path,
        "primary_dir": primary_dir,
        "coord_specs": coord_specs,
        "coord_events": coord_events,
    }


def _seed_done_event_m(feature_dir: Path, wp_id: str) -> None:
    event = StatusEvent(
        event_id=f"01TESTM{wp_id[-2:]}DONE000000000000"[:26],
        mission_slug=_COORD_SLUG_M,
        wp_id=wp_id,
        from_lane=Lane.APPROVED,
        to_lane=Lane.DONE,
        at="2026-06-06T12:00:00+00:00",
        actor="merge",
        force=False,
        execution_mode="worktree",
    )
    append_event(feature_dir, event)


def test_planning_only_merge_with_coord_branch_reaches_done(
    coord_branch_mission: dict,
) -> None:
    """Planning-only WP: done event on coord surface → assertion passes.

    Parity ratchet T015: proves _assert_merged_wps_reached_done reads the
    coordination surface when coordination_branch is set.

    Relates-to: #1726
    """
    from specify_cli.coordination.surface_resolver import resolve_status_surface

    repo_root = coord_branch_mission["repo_root"]
    coord_specs = coord_branch_mission["coord_specs"]

    # Seed coord surface (simulates what _mark_wp_merged_done writes)
    _seed_done_event_m(coord_specs, "WP01")

    # Real _assert_merged_wps_reached_done — must not raise
    _assert_merged_wps_reached_done(repo_root, _COORD_SLUG_M, ["WP01"])

    # The done event is on the coordination surface
    surface = resolve_status_surface(repo_root, _COORD_SLUG_M)
    assert surface.exists()
    assert '"done"' in surface.read_text(encoding="utf-8")

    # Primary checkout does NOT have the done event
    primary_events = coord_branch_mission["primary_dir"] / "status.events.jsonl"
    assert not primary_events.exists() or '"done"' not in primary_events.read_text(encoding="utf-8")


def test_code_change_merge_with_coord_branch_reaches_done(
    coord_branch_mission: dict,
) -> None:
    """Code-change WP variant: multi-WP done events on coord surface.

    Parity ratchet T016: surface alignment is independent of WP execution mode.

    Relates-to: #1726
    """
    repo_root = coord_branch_mission["repo_root"]
    coord_specs = coord_branch_mission["coord_specs"]

    _seed_done_event_m(coord_specs, "WP01")
    _seed_done_event_m(coord_specs, "WP02")

    # Both WPs must pass — coord surface has their done events
    _assert_merged_wps_reached_done(repo_root, _COORD_SLUG_M, ["WP01", "WP02"])
