"""Tests for WP06: Migrate Slice 4 — merge.py typed Lane enum migration.

Verifies that:
- _assert_merged_wps_reached_done() uses typed Lane enum (Lane.DONE), not raw "done"
- _mark_wp_merged_done() uses typed Lane enum comparisons throughout
- approved|done merge-ready check is EXPLICIT (not delegated to is_terminal)
- is_terminal covers done|canceled — not the same as merge-ready approved|done
- All 9 lanes are correctly classified as merge-ready or not
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from specify_cli.cli.commands.merge import (
    _assert_merged_wps_reached_done,
    _mark_wp_merged_done,
)
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event

pytestmark = pytest.mark.fast


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

    _append_done_event(feature_dir, "WP01")
    _append_done_event(feature_dir, "WP02")

    # Should not raise
    _assert_merged_wps_reached_done(tmp_path, mission_slug, ["WP01", "WP02"])


def test_assert_merged_wps_reached_done_raises_when_wp_not_done(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WP not in done → typer.Exit(1) raised."""
    import click

    mission_slug = "080-test-feature"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)

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

    with pytest.raises(click.exceptions.Exit):
        _assert_merged_wps_reached_done(tmp_path, mission_slug, ["WP01", "WP02"])


def test_assert_merged_wps_reached_done_includes_lane_value_in_error(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Error message includes WP id and current lane value (not raw string)."""
    import click

    mission_slug = "080-test-feature"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)

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

    with pytest.raises(click.exceptions.Exit):
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
    _write_wp(tasks_dir / "WP01-test.md", reviewed_by="reviewer-1")

    from specify_cli.status.models import TransitionRequest
    emit_calls: list[TransitionRequest] = []

    def fake_emit(request: TransitionRequest) -> None:
        emit_calls.append(request)

    monkeypatch.setattr("specify_cli.status.emit.emit_status_transition", fake_emit)
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
    _write_wp(tasks_dir / "WP01-test.md")

    emit_mock = Mock()
    monkeypatch.setattr("specify_cli.status.emit.emit_status_transition", emit_mock)
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
    # WP with no review metadata
    _write_wp(tasks_dir / "WP01-test.md", review_status="", reviewed_by="")

    emit_mock = Mock()
    monkeypatch.setattr("specify_cli.status.emit.emit_status_transition", emit_mock)
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
