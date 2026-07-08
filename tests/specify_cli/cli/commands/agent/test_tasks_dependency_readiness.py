"""Readiness-gating coverage for the ``tasks_dependency_graph`` seam (WP05, #2058).

Fills the research-flagged readiness coverage gap (FR-003, FR-004):

- A WP whose dependent is still ``in_progress`` is surfaced as incomplete, so a
  for_review transition cannot silently proceed without the dependency alert.
- ``get_dependents`` surfaces direct dependents correctly through the seam.
- The planning-artifact-only behind-commit path returns True when upstream
  commits only touch planning/status files (so lane transitions are not blocked
  by metadata churn), and False when any source file changed.

These exercise the moved helpers directly, without driving the full
``move_task`` command flow.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.cli.commands.agent.tasks_dependency_graph import (
    _behind_commits_touch_only_planning_artifacts,
    _check_dependent_warnings,
    compute_incomplete_dependents,
)
from specify_cli.core.dependency_graph import get_dependents
from specify_cli.status import Lane, StatusEvent
from specify_cli.status.store import append_event

pytestmark = [pytest.mark.unit, pytest.mark.fast]

MISSION_SLUG = "010-readiness-mission"


def _event(wp_id: str, from_lane: str, to_lane: str, event_id: str) -> StatusEvent:
    return StatusEvent(
        event_id=event_id,
        mission_slug=MISSION_SLUG,
        wp_id=wp_id,
        from_lane=Lane(from_lane),
        to_lane=Lane(to_lane),
        at="2026-01-01T12:00:00+00:00",
        actor="test-agent",
        force=False,
        execution_mode="worktree",
    )


def _seed(feature_dir: Path, *events: StatusEvent) -> None:
    for ev in events:
        append_event(feature_dir, ev)


# ---------------------------------------------------------------------------
# compute_incomplete_dependents — readiness gating (FR-003 / FR-004)
# ---------------------------------------------------------------------------


def test_dependent_in_progress_is_incomplete(tmp_path: Path) -> None:
    """WP02 depends on WP01; WP02 is in_progress → surfaced as incomplete.

    This is the readiness gate: moving WP01 to for_review must report that a
    dependent is still mid-flight rather than treat it as complete.
    """
    graph = {"WP01": [], "WP02": ["WP01"]}
    _seed(
        tmp_path,
        _event("WP02", "planned", "claimed", "01HZCLAIM00000000000000001"),
        _event("WP02", "claimed", "in_progress", "01HZPROG000000000000000001"),
    )

    incomplete = compute_incomplete_dependents("WP01", tmp_path, graph)

    assert incomplete == ["WP02"]


def test_dependent_done_is_not_incomplete(tmp_path: Path) -> None:
    """A dependent that reached an advanced lane is not flagged as incomplete."""
    graph = {"WP01": [], "WP02": ["WP01"]}
    _seed(
        tmp_path,
        _event("WP02", "planned", "claimed", "01HZCLAIM00000000000000002"),
        _event("WP02", "claimed", "in_progress", "01HZPROG000000000000000002"),
        _event("WP02", "in_progress", "for_review", "01HZREVIEW0000000000000002"),
        _event("WP02", "for_review", "approved", "01HZAPPRV00000000000000002"),
    )

    incomplete = compute_incomplete_dependents("WP01", tmp_path, graph)

    assert incomplete == []


def test_no_dependents_returns_empty(tmp_path: Path) -> None:
    """A WP nobody depends on yields no incomplete dependents (and no event read)."""
    graph = {"WP01": [], "WP02": ["WP01"]}

    assert compute_incomplete_dependents("WP02", tmp_path, graph) == []


def test_missing_event_log_treats_dependents_as_planned(tmp_path: Path) -> None:
    """With no event log, dependents default to PLANNED → incomplete.

    Exercises the graceful-fallback branch where ``read_events`` finds nothing,
    so the lane map is empty and every dependent is treated as not-yet-done.
    """
    graph = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP01"]}

    incomplete = compute_incomplete_dependents("WP01", tmp_path, graph)

    assert sorted(incomplete) == ["WP02", "WP03"]


def test_get_dependents_surfaces_direct_dependents() -> None:
    """``get_dependents`` (re-imported by the seam) returns direct dependents."""
    graph = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP01"], "WP04": ["WP02"]}

    assert sorted(get_dependents("WP01", graph)) == ["WP02", "WP03"]
    assert get_dependents("WP02", graph) == ["WP04"]
    assert get_dependents("WP04", graph) == []


# ---------------------------------------------------------------------------
# _check_dependent_warnings — composition over the pure core
# ---------------------------------------------------------------------------


def test_check_dependent_warnings_skips_non_for_review() -> None:
    """No graph build, no resolution when the target lane is not for_review."""
    with patch(
        "specify_cli.cli.commands.agent.tasks_dependency_graph.build_dependency_graph"
    ) as build_mock:
        _check_dependent_warnings(Path("/repo"), MISSION_SLUG, "WP01", Lane.IN_PROGRESS, json_mode=False)
    build_mock.assert_not_called()


def test_check_dependent_warnings_skips_json_mode() -> None:
    """JSON mode suppresses the warning path entirely."""
    with patch(
        "specify_cli.cli.commands.agent.tasks_dependency_graph.build_dependency_graph"
    ) as build_mock:
        _check_dependent_warnings(Path("/repo"), MISSION_SLUG, "WP01", Lane.FOR_REVIEW, json_mode=True)
    build_mock.assert_not_called()


def test_check_dependent_warnings_emits_alert_for_incomplete_dependent(tmp_path: Path) -> None:
    """for_review with an in_progress dependent prints the dependency alert."""
    feature_dir = tmp_path / "kitty-specs" / MISSION_SLUG
    feature_dir.mkdir(parents=True)
    _seed(
        feature_dir,
        _event("WP02", "planned", "claimed", "01HZCLAIM00000000000000003"),
        _event("WP02", "claimed", "in_progress", "01HZPROG000000000000000003"),
    )

    dep_ws = MagicMock()
    dep_ws.branch_name = None  # planning-lane workspace branch
    seam = "specify_cli.cli.commands.agent.tasks_dependency_graph"
    # read-surface-ssot-closeout WP08 / FR-001: the STATUS leg now routes
    # through the late-imported ``mission_runtime.placement_seam(...)
    # .read_dir(STATUS_STATE)`` seam — stub the seam, not the retired
    # ``resolve_feature_dir_for_mission`` name.
    mock_seam = MagicMock()
    mock_seam.read_dir.return_value = feature_dir
    with (
        patch(f"{seam}.get_main_repo_root", return_value=tmp_path),
        patch("mission_runtime.placement_seam", return_value=mock_seam),
        patch(f"{seam}.build_dependency_graph", return_value={"WP01": [], "WP02": ["WP01"]}),
        patch(f"{seam}.resolve_workspace_for_wp", return_value=dep_ws),
        patch(f"{seam}.console") as console_mock,
    ):
        _check_dependent_warnings(tmp_path, MISSION_SLUG, "WP01", Lane.FOR_REVIEW, json_mode=False)

    printed = " ".join(str(call.args[0]) for call in console_mock.print.call_args_list if call.args)
    assert "Dependency Alert" in printed
    assert "WP02" in printed


def test_check_dependent_warnings_emits_rebase_commands_per_lane(tmp_path: Path) -> None:
    """Same-lane dependents get a 'shares branch' note; others get a rebase cmd."""
    feature_dir = tmp_path / "kitty-specs" / MISSION_SLUG
    feature_dir.mkdir(parents=True)
    _seed(
        feature_dir,
        _event("WP02", "planned", "in_progress", "01HZPROG000000000000000004"),
        _event("WP03", "planned", "in_progress", "01HZPROG000000000000000005"),
    )

    current_ws = MagicMock()
    current_ws.branch_name = "lane-current"
    same_lane_ws = MagicMock()
    same_lane_ws.branch_name = "lane-current"  # shares the WP01 branch
    other_lane_ws = MagicMock()
    other_lane_ws.branch_name = "lane-other"
    other_lane_ws.worktree_path = "/wt/other"

    def _resolve(_root: Path, _slug: str, wp: str) -> MagicMock:
        return {"WP01": current_ws, "WP02": same_lane_ws, "WP03": other_lane_ws}[wp]

    seam = "specify_cli.cli.commands.agent.tasks_dependency_graph"
    mock_seam = MagicMock()
    mock_seam.read_dir.return_value = feature_dir
    with (
        patch(f"{seam}.get_main_repo_root", return_value=tmp_path),
        patch("mission_runtime.placement_seam", return_value=mock_seam),
        patch(f"{seam}.build_dependency_graph", return_value={"WP01": [], "WP02": ["WP01"], "WP03": ["WP01"]}),
        patch(f"{seam}.resolve_workspace_for_wp", side_effect=_resolve),
        patch(f"{seam}.console") as console_mock,
    ):
        _check_dependent_warnings(tmp_path, MISSION_SLUG, "WP01", Lane.FOR_REVIEW, json_mode=False)

    printed = " ".join(str(call.args[0]) for call in console_mock.print.call_args_list if call.args)
    assert "WP02: shares lane-current" in printed
    assert "cd /wt/other && git rebase lane-current" in printed


def test_check_dependent_warnings_silent_on_graph_build_failure(tmp_path: Path) -> None:
    """A graph-build failure is swallowed and produces no alert (graceful)."""
    seam = "specify_cli.cli.commands.agent.tasks_dependency_graph"
    mock_seam = MagicMock()
    mock_seam.read_dir.return_value = tmp_path
    with (
        patch(f"{seam}.get_main_repo_root", return_value=tmp_path),
        patch("mission_runtime.placement_seam", return_value=mock_seam),
        patch(f"{seam}.build_dependency_graph", side_effect=RuntimeError("boom")),
        patch(f"{seam}.console") as console_mock,
    ):
        _check_dependent_warnings(tmp_path, MISSION_SLUG, "WP01", Lane.FOR_REVIEW, json_mode=False)

    console_mock.print.assert_not_called()


# ---------------------------------------------------------------------------
# _behind_commits_touch_only_planning_artifacts — planning-only fast path
# ---------------------------------------------------------------------------


def _subproc(returncode: int = 0, stdout: str = "") -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    return m


def test_behind_commits_planning_only_returns_true(tmp_path: Path) -> None:
    """Upstream commits touching only kitty-specs/<mission>/ are non-blocking."""
    responses = [
        _subproc(returncode=0, stdout="abc123\n"),  # merge-base
        _subproc(
            returncode=0,
            stdout=f"kitty-specs/{MISSION_SLUG}/tasks.md\nkitty-specs/{MISSION_SLUG}/status.events.jsonl\n",
        ),
    ]
    with patch("subprocess.run", side_effect=responses):
        result = _behind_commits_touch_only_planning_artifacts(tmp_path, "main", MISSION_SLUG)
    assert result is True


def test_behind_commits_source_change_returns_false(tmp_path: Path) -> None:
    """Any non-planning file in the behind set blocks the transition."""
    responses = [
        _subproc(returncode=0, stdout="abc123\n"),
        _subproc(returncode=0, stdout=f"kitty-specs/{MISSION_SLUG}/tasks.md\nsrc/specify_cli/foo.py\n"),
    ]
    with patch("subprocess.run", side_effect=responses):
        result = _behind_commits_touch_only_planning_artifacts(tmp_path, "main", MISSION_SLUG)
    assert result is False


def test_behind_commits_detached_head_merge_base_failure(tmp_path: Path) -> None:
    """Detached HEAD / missing ref → merge-base fails → graceful False."""
    with patch("subprocess.run", return_value=_subproc(returncode=128, stdout="")):
        result = _behind_commits_touch_only_planning_artifacts(tmp_path, "missing-ref", MISSION_SLUG)
    assert result is False


def test_behind_commits_empty_merge_base_returns_false(tmp_path: Path) -> None:
    """Empty merge-base output (no common ancestor) → graceful False."""
    with patch("subprocess.run", return_value=_subproc(returncode=0, stdout="\n")):
        result = _behind_commits_touch_only_planning_artifacts(tmp_path, "main", MISSION_SLUG)
    assert result is False


def test_behind_commits_diff_subprocess_failure_returns_false(tmp_path: Path) -> None:
    """A failing diff subprocess → graceful False."""
    responses = [
        _subproc(returncode=0, stdout="abc123\n"),  # merge-base ok
        _subproc(returncode=129, stdout=""),  # diff fails
    ]
    with patch("subprocess.run", side_effect=responses):
        result = _behind_commits_touch_only_planning_artifacts(tmp_path, "main", MISSION_SLUG)
    assert result is False


def test_behind_commits_no_changed_files_returns_true(tmp_path: Path) -> None:
    """Empty diff (already up to date) → True (non-blocking)."""
    responses = [
        _subproc(returncode=0, stdout="abc123\n"),
        _subproc(returncode=0, stdout="\n"),
    ]
    with patch("subprocess.run", side_effect=responses):
        result = _behind_commits_touch_only_planning_artifacts(tmp_path, "main", MISSION_SLUG)
    assert result is True
