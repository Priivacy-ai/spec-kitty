"""WP04 / FR-006 (#2698): review-handoff per-WP lane reads the coord STATUS surface.

The generated review handoff embeds a per-WP lane (a STATUS_STATE / COORD-partition
kind). Before this fix ``materialize_worktree_topology`` read that lane from the
PRIMARY ``LANE_STATE`` dir, so on a multi-WP coord-topology mission every WP rendered
back as stale ``planned`` — the real (coord) lanes were never consulted.

This is a live, un-stubbed multi-WP coord-topology proof (NFR-001):

* A REAL ``git worktree`` coord husk carries the authoritative
  ``status.events.jsonl`` with WPs in MIXED lanes (WP01 ``in_progress``, WP02
  ``claimed``); the PRIMARY dir carries a stale/empty status log.
* :func:`materialize_worktree_topology` (the production function the handoff
  renderer consumes) must resolve the TRUE per-WP lanes off the coord husk while
  identity / lanes.json / tasks continue to resolve from PRIMARY (C-002).
* The routing is proven LOAD-BEARING by an *executed* revert (monkeypatching the
  seam's ``read_dir(STATUS_STATE)`` projection back to PRIMARY) that flips every
  lane back to stale ``planned`` — the exact pre-fix symptom.

Plus a non-coord control (``flat_topology_mission``): on a flat mission the
STATUS surface IS the primary surface, so the lane read is unchanged.

No resolver is patched to build the fixture — topology routing uses real git +
filesystem state (the shared ``coord_topology_fixture`` helpers).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.core.worktree_topology import materialize_worktree_topology
from tests.integration.coord_topology_fixture import (
    FlatTopologyContext,
    _git,
    _make_git_repo,
    _write_meta,
    _write_wp_task,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Multi-WP coord-topology builder (mixed lanes) — the shared fixtures are
# single-WP, so WP04 materialises its own multi-WP mission here.
# ---------------------------------------------------------------------------

_MISSION_ID = "01KW2E7CFC0000000000000001"
_MID8 = "01KW2E7C"


def _status_event(
    slug: str, wp_id: str, event_id: str, from_lane: str, to_lane: str
) -> str:
    """Return one reducible JSONL status-event line (no wrong-leg probe marker)."""
    return json.dumps(
        {
            "actor": "claude",
            "at": "2026-06-26T00:00:00+00:00",
            "event_id": event_id,
            "evidence": None,
            "execution_mode": "code_change",
            "feature_slug": slug,
            "force": False,
            "from_lane": from_lane,
            "reason": None,
            "review_ref": None,
            "to_lane": to_lane,
            "wp_id": wp_id,
        }
    )


def _write_two_lane_manifest(feature_dir: Path, *, slug: str, mission_id: str) -> None:
    """Write a 2-lane ``lanes.json`` (lane-a→WP01, lane-b→WP02) to *feature_dir*."""
    payload = {
        "version": 1,
        "mission_slug": slug,
        "mission_id": mission_id,
        "mission_branch": f"kitty/mission-{slug}",
        "target_branch": "main",
        "lanes": [
            {
                "lane_id": "lane-a",
                "wp_ids": ["WP01"],
                "write_scope": [],
                "predicted_surfaces": [],
                "depends_on_lanes": [],
                "parallel_group": 0,
            },
            {
                "lane_id": "lane-b",
                "wp_ids": ["WP02"],
                "write_scope": [],
                "predicted_surfaces": [],
                "depends_on_lanes": [],
                "parallel_group": 0,
            },
        ],
        "computed_at": "2026-06-26T00:00:00+00:00",
        "computed_from": "wp04-handoff-lane-read-fixture",
        "planning_artifact_wps": [],
    }
    (feature_dir / "lanes.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


@pytest.fixture()
def multi_wp_coord_mission(tmp_path: Path) -> tuple[Path, str, Path, Path]:
    """A REAL multi-WP coord-topology mission with WPs in MIXED lanes.

    Shape on disk (no resolver patched):

    * ``<repo>/kitty-specs/<slug>/`` (PRIMARY):
      - ``meta.json`` (``topology=coord``, ``coordination_branch`` set)
      - ``tasks/WP01.md`` + ``tasks/WP02.md``
      - ``lanes.json`` (lane-a→WP01, lane-b→WP02)
      - ``status.events.jsonl`` — EMPTY (stale: PRIMARY never advanced)
    * ``<repo>/.worktrees/<slug>-coord/kitty-specs/<slug>/`` (coord husk):
      - ``status.events.jsonl`` — AUTHORITATIVE: WP01 → ``in_progress``,
        WP02 → ``claimed`` (mixed lanes)

    Returns ``(repo, slug, primary_feature_dir, coord_feature_dir)``.
    """
    slug = f"multi-wp-coord-{_MID8}"
    coord_branch = f"kitty/mission-{slug}"

    repo = _make_git_repo(tmp_path / "multi-wp-coord")
    _git(repo, "branch", coord_branch)

    primary_feature_dir = repo / "kitty-specs" / slug
    primary_feature_dir.mkdir(parents=True)
    _write_meta(
        primary_feature_dir,
        slug=slug,
        mission_id=_MISSION_ID,
        topology="coord",
        coordination_branch=coord_branch,
    )
    tasks_dir = primary_feature_dir / "tasks"
    tasks_dir.mkdir()
    _write_wp_task(tasks_dir, "WP01")
    _write_wp_task(tasks_dir, "WP02")
    _write_two_lane_manifest(primary_feature_dir, slug=slug, mission_id=_MISSION_ID)
    # PRIMARY status log is present but EMPTY — the stale surface a coord mission
    # leaves behind (all status transitions land on the coord husk).
    (primary_feature_dir / "status.events.jsonl").write_text("", encoding="utf-8")

    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "feat: multi-wp coord-topology primary planning artifacts")

    # Coord husk via the REAL CoordinationWorkspace helper (no stub).
    coord_root = CoordinationWorkspace.resolve(repo, slug, _MID8)
    coord_feature_dir = coord_root / "kitty-specs" / slug
    coord_feature_dir.mkdir(parents=True)
    coord_lines = [
        _status_event(slug, "WP01", "01KW2E7C0000000000000000A1", "planned", "claimed"),
        _status_event(slug, "WP01", "01KW2E7C0000000000000000A2", "claimed", "in_progress"),
        _status_event(slug, "WP02", "01KW2E7C0000000000000000B1", "planned", "claimed"),
    ]
    (coord_feature_dir / "status.events.jsonl").write_text(
        "\n".join(coord_lines) + "\n", encoding="utf-8"
    )

    # Divergence precondition: the coord husk carries NO tasks/ or lanes.json —
    # those stay PRIMARY-only, so a PRIMARY-vs-coord routing bug is falsifiable.
    assert not (coord_feature_dir / "tasks").exists()
    assert not (coord_feature_dir / "lanes.json").exists()

    return repo, slug, primary_feature_dir, coord_feature_dir


def _reroute_status_leg_to_primary(
    monkeypatch: pytest.MonkeyPatch, primary_feature_dir: Path
) -> None:
    """Re-route ONLY the ``STATUS_STATE`` seam read back to PRIMARY (pre-fix behavior).

    Simulates the pre-#2698 code, which resolved the per-WP lane off the PRIMARY
    dir. Every other kind delegates to the real seam so the resulting lane flip is
    attributable to the STATUS leg alone.
    """
    from mission_runtime import MissionArtifactKind, PlacementSeam

    real_read_dir = PlacementSeam.read_dir

    def _rerouted(self: PlacementSeam, kind: MissionArtifactKind) -> Path:
        if kind is MissionArtifactKind.STATUS_STATE:
            return primary_feature_dir
        resolved: Path = real_read_dir(self, kind)
        return resolved

    monkeypatch.setattr(PlacementSeam, "read_dir", _rerouted)


def test_handoff_renders_true_per_wp_lane_from_coord_husk(
    multi_wp_coord_mission: tuple[Path, str, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-006: per-WP lanes resolve off the coord STATUS surface, not stale PRIMARY.

    Domain value: the per-WP ``entry.lane`` set. The coord husk has WP01 in
    ``in_progress`` and WP02 in ``claimed``; the PRIMARY status log is empty.

    * BEFORE the fix (executed revert below): the STATUS read lands on PRIMARY
      (empty) → every WP renders stale ``planned``.
    * AFTER the fix: the STATUS read resolves the coord husk → the TRUE mixed
      lanes. Identity / lanes.json / tasks still resolve from PRIMARY (C-002).
    """
    repo, slug, primary_feature_dir, _coord_feature_dir = multi_wp_coord_mission

    topo = materialize_worktree_topology(repo, slug)
    lanes = {entry.wp_id: entry.lane for entry in topo.entries}

    # PRIMARY-partition legs unaffected: both WPs materialize from PRIMARY tasks/lanes.
    assert set(lanes) == {"WP01", "WP02"}, (
        "the multi-WP topology must materialize both WPs from the PRIMARY tasks/lanes"
    )
    # AFTER-fix truth: the per-WP lane comes from the coord husk STATUS surface.
    assert lanes["WP01"] == "in_progress", (
        f"WP01 lane must resolve the coord husk STATUS ('in_progress'); got {lanes['WP01']!r} "
        "(stale 'planned' ⇒ the lane read hit the PRIMARY status surface, the #2698 bug)"
    )
    assert lanes["WP02"] == "claimed", (
        f"WP02 lane must resolve the coord husk STATUS ('claimed'); got {lanes['WP02']!r}"
    )
    assert lanes["WP01"] != "planned" and lanes["WP02"] != "planned"

    # --- Executed revert→stale: re-route the STATUS leg back to PRIMARY. ---
    # This reproduces the pre-#2698 code path and proves the coord-aware STATUS
    # routing is LOAD-BEARING: the empty PRIMARY log collapses every lane to the
    # stale 'planned' default.
    _reroute_status_leg_to_primary(monkeypatch, primary_feature_dir)
    reverted = materialize_worktree_topology(repo, slug)
    reverted_lanes = {entry.wp_id: entry.lane for entry in reverted.entries}
    assert reverted_lanes == {"WP01": "planned", "WP02": "planned"}, (
        "REVERT GUARD FAILED: with the STATUS read routed to the (empty) PRIMARY "
        "surface every WP must collapse to stale 'planned' — the #2698 symptom; "
        f"got {reverted_lanes!r}"
    )


def test_flat_topology_lane_read_is_unchanged(
    flat_topology_mission: FlatTopologyContext,
) -> None:
    """Non-coord control: on a flat mission the STATUS surface IS the primary surface.

    The flat fixture seeds a single ``planned`` → ``claimed`` event on the only
    surface. The per-WP lane must resolve ``claimed`` — identical before and after
    the fix, because STATUS_STATE and LANE_STATE resolve the same dir (C-002: only
    coord-partition reads move; flat topology is a structural no-op).
    """
    ctx = flat_topology_mission

    topo = materialize_worktree_topology(ctx.repo, ctx.slug)
    lanes = {entry.wp_id: entry.lane for entry in topo.entries}

    assert lanes == {"WP01": "claimed"}, (
        f"flat-topology lane read must resolve the single-surface STATUS ('claimed'); "
        f"got {lanes!r}"
    )
