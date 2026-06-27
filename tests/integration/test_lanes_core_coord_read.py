"""RED-first lanes/core/status routing tests on the divergent coord fixture.

Mission ``coord-read-residuals-merge-lanes-and-identity-routing-01KW2M8V`` —
Lane A (#2185 / #2187 / #2186), WP03. Proves the lanes/core/status-display
PRIMARY reads resolve their domain value off the PRIMARY checkout, NOT the
STATUS-only ``-coord`` husk.

Each assertion targets a RETURNED DOMAIN VALUE — the resolved lane→WP set, the
recovery states, the reconstructed workspace context, the materialized worktree
topology, the discovered coordination branch, or the kanban board / resolved
identity — NOT a resolved-path equality and NOT the fixture's
``assert_reads_primary`` / ``assert_both_legs`` path-equality helpers (T022).
Reverting any routed read to a coord-aware resolver surfaces the empty/sentinel
husk → the test goes RED.

**NFR-004 (no primary-dir stub):** every test drives the REAL production
function against a REAL ``git worktree`` coord fixture. No test hands a primary
dir directly to the function under test — the PRIMARY-vs-coord routing decision
is exercised inside production code; monkeypatches only CAPTURE returned values.

================================================================================
WP03 ROUTE / KEEP map (re-resolved on the lane-c tree, verified)
================================================================================

| Site                                                       | Verdict | Kind             |
|------------------------------------------------------------|---------|------------------|
| lanes/merge.py `_resolve_lane_manifest` (:68)              | ROUTE   | LANE_STATE       |
| lanes/merge.py `merge_mission_to_target` (:198)            | ROUTE   | LANE_STATE       |
| lanes/recovery.py `scan_recovery_state` lanes/tasks (:356) | ROUTE   | LANE_STATE/WP_TASK |
| lanes/recovery.py `scan_recovery_state` events leg         | KEEP    | coord-aware (C-001) |
| lanes/recovery.py `recover_context` (:611)                 | ROUTE   | LANE_STATE       |
| lanes/recovery.py `reconcile_status` (:664)                | KEEP    | coord-aware (STATUS-write, C-001/#2155) |
| lanes/worktree_allocator.py `_read_coordination_branch` (:360) | ROUTE | PRIMARY_METADATA |
| core/worktree_topology.py `materialize_worktree_topology` (:138) | ROUTE | LANE_STATE (co-resolves META+WP_TASK) |
| agent_utils/status.py `show_kanban_status` tasks (:126, #2187) | ROUTE | WORK_PACKAGE_TASK |
| agent_utils/status.py `show_kanban_status` identity (:132, #2186) | ROUTE | PRIMARY_METADATA |
| agent_utils/status.py `show_kanban_status` events (:151)   | KEEP    | coord-aware (C-001) |
"""

from __future__ import annotations

import subprocess
from typing import Any, NoReturn

import pytest

from specify_cli.lanes.branch_naming import lane_branch_name
from tests.integration.coord_topology_fixture import (
    SENTINEL_HUSK_MISSION_ID,
    SENTINEL_HUSK_MISSION_TYPE,
    CoordTopologyContext,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# The PRIMARY values the fixture resolves (distinct from the husk sentinel).
_PRIMARY_MISSION_ID = "01KW2E7AFC0000000000000001"
_PRIMARY_MISSION_TYPE = "software-dev"
_PRIMARY_MISSION_BRANCH = "kitty/mission-coord-topo-fixture-01KW2E7A"


class _StopProbe(BaseException):
    """Short-circuit a deep flow once the domain value is captured.

    Subclasses ``BaseException`` (not ``Exception``) so it propagates THROUGH any
    defensive ``except Exception`` in production code — the capture has already
    happened; we only want to stop before the real (heavy) work.
    """


def _git(repo: Any, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(repo), check=True, capture_output=True, text=True)


def _seed_reducible_husk_event(ctx: CoordTopologyContext) -> None:
    """Overwrite the husk event log with a production-shaped (reducible) event.

    The shared fixture stuffs a plain-string marker into ``evidence`` (a wrong-leg
    probe), which the real status reducer rejects. ``show_kanban_status`` reads the
    STATUS event log off the coord husk (the C-001 KEEP leg), so it needs a
    reducible log to render a board. We seed a realistic ``claimed`` event for WP01
    on the husk — this exercises the STATUS leg legitimately while leaving the
    PRIMARY tasks/identity routing under test untouched.
    """
    import json as _json

    event = {
        "actor": "claude",
        "at": "2026-06-26T00:00:00+00:00",
        "event_id": "01KW2E7AFC00000000000CLAIM",
        "evidence": None,
        "execution_mode": "code_change",
        "feature_slug": ctx.slug,
        "force": False,
        "from_lane": "planned",
        "reason": None,
        "review_ref": None,
        "to_lane": "claimed",
        "wp_id": "WP01",
    }
    (ctx.coord_feature_dir / "status.events.jsonl").write_text(
        _json.dumps(event) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Pre-condition sanity (re-states the falsifiability premise)
# ---------------------------------------------------------------------------


def test_sentinel_husk_diverges_from_primary(
    coord_topology_mission_sentinel_meta: CoordTopologyContext,
) -> None:
    """Husk lacks lanes.json + tasks/ and carries a sentinel identity ≠ PRIMARY."""
    ctx = coord_topology_mission_sentinel_meta
    assert not (ctx.coord_feature_dir / "lanes.json").exists()
    assert not (ctx.coord_feature_dir / "tasks").exists()
    assert ctx.coord_husk_meta_path is not None and ctx.coord_husk_meta_path.exists()
    assert ctx.mission_id == _PRIMARY_MISSION_ID
    assert SENTINEL_HUSK_MISSION_ID != _PRIMARY_MISSION_ID
    assert SENTINEL_HUSK_MISSION_TYPE != _PRIMARY_MISSION_TYPE


# ---------------------------------------------------------------------------
# lanes/merge.py — LANE_STATE
# ---------------------------------------------------------------------------


def test_resolve_lane_manifest_reads_primary_lane_set(
    coord_topology_mission_sentinel_meta: CoordTopologyContext,
) -> None:
    """``_resolve_lane_manifest`` loads the PRIMARY ``lanes.json`` (lane-a → WP01).

    Domain value: the manifest's lane→WP membership.
    RED-first: reverting the LANE_STATE read to a coord-aware resolver lands on the
    husk (no ``lanes.json``) → ``read_lanes_json`` returns ``None`` → ``manifest``
    is ``None`` and the ``.lanes`` deref AttributeErrors / the assertion fails.
    """
    from specify_cli.lanes.merge import _resolve_lane_manifest

    ctx = coord_topology_mission_sentinel_meta
    manifest = _resolve_lane_manifest(ctx.repo, ctx.slug, None)

    assert manifest is not None, "routed LANE_STATE read must find PRIMARY lanes.json"
    assert [lane.lane_id for lane in manifest.lanes] == ["lane-a"]
    assert list(manifest.lanes[0].wp_ids) == ["WP01"]


def test_merge_mission_to_target_reads_primary_lanes(
    coord_topology_mission_sentinel_meta: CoordTopologyContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``merge_mission_to_target`` resolves the PRIMARY mission_branch from lanes.json.

    Domain value: the ``mission_branch`` the function derives from the loaded
    manifest and hands to the branch-existence check. We CAPTURE it and stop.
    RED-first: reverting the LANE_STATE read lands on the husk → ``read_lanes_json``
    returns ``None`` → the function returns early with the "No lanes.json found"
    error BEFORE ``_branch_exists`` is ever called → ``_StopProbe`` never raised.
    """
    from specify_cli.lanes import merge as merge_mod

    ctx = coord_topology_mission_sentinel_meta
    captured: dict[str, Any] = {}

    def _fake_branch_exists(repo_root: Any, branch: str) -> NoReturn:
        captured["mission_branch"] = branch
        raise _StopProbe

    monkeypatch.setattr(merge_mod, "_branch_exists", _fake_branch_exists)

    with pytest.raises(_StopProbe):
        merge_mod.merge_mission_to_target(ctx.repo, ctx.slug, lanes_manifest=None)

    assert captured["mission_branch"] == _PRIMARY_MISSION_BRANCH


# ---------------------------------------------------------------------------
# lanes/recovery.py — scan_recovery_state (LANE_STATE/WP_TASK PRIMARY; events KEEP)
# ---------------------------------------------------------------------------


def test_scan_recovery_state_reads_primary_lane_membership(
    coord_topology_mission_sentinel_meta: CoordTopologyContext,
) -> None:
    """``scan_recovery_state`` reads lane→WP membership off the PRIMARY lanes.json.

    A live ``lane-a`` branch is created so the live-branch scan runs. Domain value:
    the recovery states carry ``wp_id='WP01'`` (read from PRIMARY lanes.json).
    RED-first: reverting the LANE_STATE read lands on the husk (no lanes.json) →
    ``_find_wp_ids_for_lane`` returns ``[]`` → the WP id falls back to ``'unknown'``.
    """
    from specify_cli.lanes.recovery import scan_recovery_state

    ctx = coord_topology_mission_sentinel_meta
    lane_branch = lane_branch_name(ctx.slug, "lane-a", mission_id=ctx.mission_id)
    _git(ctx.repo, "branch", lane_branch, "main")

    states = scan_recovery_state(ctx.repo, ctx.slug)
    wp_ids = {rs.wp_id for rs in states}

    assert "WP01" in wp_ids, (
        "routed LANE_STATE read must resolve lane-a → WP01 off PRIMARY lanes.json"
    )
    assert "unknown" not in wp_ids, (
        "the husk fallback ('unknown') means the read regressed to coord-aware"
    )


def test_recover_context_reads_primary_lane_wps(
    coord_topology_mission_sentinel_meta: CoordTopologyContext,
) -> None:
    """``recover_context`` reconstructs ``lane_wp_ids`` from the PRIMARY lanes.json.

    Domain value: the reconstructed ``WorkspaceContext.lane_wp_ids``. The seed
    state's own ``wp_id`` is deliberately ``WPXX`` (≠ the PRIMARY membership) so the
    fallback is distinguishable.
    RED-first: reverting the LANE_STATE read lands on the husk → no lanes.json →
    ``_find_wp_ids_for_lane`` returns ``[]`` → ``lane_wp_ids`` falls back to the
    seed ``['WPXX']`` instead of the PRIMARY ``['WP01']``.
    """
    from specify_cli.lanes.recovery import RecoveryState, recover_context

    ctx = coord_topology_mission_sentinel_meta
    state = RecoveryState(
        wp_id="WPXX",
        lane_id="lane-a",
        branch_name=lane_branch_name(ctx.slug, "lane-a", mission_id=ctx.mission_id),
        branch_exists=True,
        worktree_exists=False,
        context_exists=False,
        status_lane="claimed",
        has_commits=False,
        recovery_action="recreate_context",
    )

    context = recover_context(ctx.repo, ctx.slug, state)

    assert context.lane_wp_ids == ["WP01"], (
        "routed LANE_STATE read must reconstruct lane_wp_ids from PRIMARY lanes.json"
    )


# ---------------------------------------------------------------------------
# lanes/worktree_allocator.py — PRIMARY_METADATA (chicken-and-egg coord discovery)
# ---------------------------------------------------------------------------


def test_read_coordination_branch_reads_primary_meta(
    coord_topology_mission: CoordTopologyContext,
) -> None:
    """``_read_coordination_branch`` reads ``coordination_branch`` off PRIMARY meta.

    Uses the BASE (STATUS-only) fixture: the husk carries NO ``meta.json`` at all,
    so the revert is cleanly falsifiable.
    Domain value: the returned coordination-branch string.
    RED-first: reverting the PRIMARY_METADATA read lands on the husk (no meta.json)
    → ``_read_coordination_branch`` returns ``None``.
    """
    from specify_cli.lanes.worktree_allocator import _read_coordination_branch

    ctx = coord_topology_mission
    branch = _read_coordination_branch(ctx.repo, ctx.slug)

    assert branch == ctx.coord_branch, (
        "routed PRIMARY_METADATA read must discover coordination_branch off PRIMARY "
        f"meta.json; got {branch!r} (None means the read regressed to the husk)"
    )


# ---------------------------------------------------------------------------
# core/worktree_topology.py — single PRIMARY swap (META + LANE_STATE + WP_TASK)
# ---------------------------------------------------------------------------


def test_materialize_worktree_topology_reads_primary(
    coord_topology_mission_sentinel_meta: CoordTopologyContext,
) -> None:
    """``materialize_worktree_topology`` builds entries from PRIMARY lanes/tasks.

    Domain value: the set of WP IDs in the materialized topology entries (derived
    from the PRIMARY ``tasks/`` dependency graph + ``lanes.json``).
    RED-first: reverting the single PRIMARY read lands on the husk → no tasks/ →
    the dependency graph is empty → ``entries`` is empty (and the resolved identity
    would be the sentinel).
    """
    from specify_cli.core.worktree_topology import materialize_worktree_topology

    ctx = coord_topology_mission_sentinel_meta
    topo = materialize_worktree_topology(ctx.repo, ctx.slug)

    assert {entry.wp_id for entry in topo.entries} == {"WP01"}, (
        "routed PRIMARY read must materialize WP01 from PRIMARY tasks/lanes; an "
        "empty topology means the read regressed to the STATUS-only husk"
    )
    assert topo.mission_type == _PRIMARY_MISSION_TYPE


# ---------------------------------------------------------------------------
# agent_utils/status.py — show_kanban_status BOTH legs (#2187 tasks + #2186 identity)
# ---------------------------------------------------------------------------


def test_show_kanban_status_tasks_leg_reads_primary(
    coord_topology_mission_sentinel_meta: CoordTopologyContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The #2187 ``tasks/`` glob reads PRIMARY → the board lists WP01 (non-empty).

    Domain value: the rendered board's ``work_packages`` list.
    RED-first: reverting the WORK_PACKAGE_TASK read lands on the husk (no tasks/) →
    the function returns ``{"error": "Tasks directory not found: ..."}`` and the
    board is empty.
    """
    from specify_cli.agent_utils.status import show_kanban_status

    ctx = coord_topology_mission_sentinel_meta
    _seed_reducible_husk_event(ctx)
    monkeypatch.chdir(ctx.repo)

    result = show_kanban_status(ctx.slug)

    assert "error" not in result, f"board should render, got error: {result.get('error')}"
    assert [wp["id"] for wp in result["work_packages"]] == ["WP01"], (
        "routed #2187 tasks read must glob PRIMARY tasks/ (WP01); an empty/errored "
        "board means the tasks read regressed to the STATUS-only husk"
    )


def test_show_kanban_status_identity_leg_reads_primary(
    coord_topology_mission_sentinel_meta: CoordTopologyContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The #2186 identity leg reads PRIMARY → mission_type is the PRIMARY type.

    Domain value: the board's resolved ``mission_type``.
    RED-first: reverting the PRIMARY_METADATA read lands on the husk → the sentinel
    meta resolves ``mission_type='research'`` (≠ the PRIMARY ``software-dev``).
    """
    from specify_cli.agent_utils.status import show_kanban_status

    ctx = coord_topology_mission_sentinel_meta
    _seed_reducible_husk_event(ctx)
    monkeypatch.chdir(ctx.repo)

    result = show_kanban_status(ctx.slug)

    assert "error" not in result, f"board should render, got error: {result.get('error')}"
    assert result["mission_type"] == _PRIMARY_MISSION_TYPE, (
        "routed #2186 identity read must resolve mission_type off PRIMARY meta.json; "
        f"got {result['mission_type']!r} (the sentinel means the read regressed)"
    )
    assert result["mission_type"] != SENTINEL_HUSK_MISSION_TYPE
