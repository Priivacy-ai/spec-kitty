"""WP06 (#3407): CLI guard family — resolve the actual mission family.

``_check_cli_guards`` (``runtime_bridge.py``) used to hardcode
``mission_family="software-dev"`` into ``gather_artifact_presence``, routing
every mission type's CLI-guard evaluation *around* the per-type
``_GUARD_TABLES`` dispatch -- including the already-existing ``"plan"`` table
(``_evaluate_plan_guards``). The fix resolves the mission's actual family via
``get_mission_type(feature_dir)`` and threads it through, so
``evaluate_guards_strict``'s ``_GUARD_TABLES.get(family)`` dispatch reaches
the correct table.

This file pins three things (plan.md §6, spec.md AC-13/AC-14):

- AC-13 (latent-defect pin): a ``plan``-type mission's ``review`` step must
  route to ``_GUARD_TABLES["plan"]`` (``_evaluate_plan_guards`` -> ``[]``)
  instead of aliasing into ``_evaluate_wp_iteration_guard`` (the WP-block
  string), which is what happened while the family was hardcoded to
  ``"software-dev"``.
- AC-14 / NFR-003: a ``software-dev`` mission's CLI-guard evaluation is
  byte-identical to ``main`` -- the fix must not perturb the one family that
  was always being routed correctly by the hardcoded default.
- Family-key identity: ``get_mission_type`` must return exactly the
  ``_GUARD_TABLES`` family key for every built-in mission type. If a
  built-in's ``meta.json`` string ever diverged from its guard-table key, a
  legitimate mission would wrongly fail-closed via
  ``UnregisteredMissionFamilyError`` after this routing fix lands.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.next.runtime_bridge import _check_cli_guards
from runtime.next.runtime_bridge_cores import (
    _GUARD_TABLES,
    _evaluate_plan_guards,
    UnregisteredMissionFamilyError,
    evaluate_guards_strict,
)
from runtime.next.runtime_bridge_io import gather_artifact_presence
from specify_cli.mission import get_mission_type
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_meta(feature_dir: Path, mission_type: str) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_type": mission_type}), encoding="utf-8"
    )


def _seed_wp(feature_dir: Path, wp_id: str, lane: str) -> None:
    """Seed one WP file plus a canonical status event placing it in *lane*."""
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    (tasks_dir / f"{wp_id}.md").write_text(
        f"---\nwork_package_id: {wp_id}\nlane: {lane}\ntitle: {wp_id} task\n---\n"
        f"# {wp_id}\nDo something.\n",
        encoding="utf-8",
    )
    event = StatusEvent(
        event_id=f"test-{wp_id}-{lane}",
        mission_slug=feature_dir.name,
        wp_id=wp_id,
        from_lane=Lane.PLANNED,
        to_lane=Lane(lane),
        at="2026-01-01T00:00:00+00:00",
        actor="test",
        force=True,
        execution_mode="worktree",
    )
    append_event(feature_dir, event)


WP_BLOCK_REVIEW_MESSAGE = "Not all work packages are approved or done"


# ---------------------------------------------------------------------------
# AC-13 — latent-defect pin: plan-family review routes to the plan table
# ---------------------------------------------------------------------------


class TestAC13PlanReviewRoutesToPlanTable:
    def test_check_cli_guards_routes_plan_review_to_plan_table(self, tmp_path: Path) -> None:
        feature_dir = tmp_path / "kitty-specs" / "042-plan-feature"
        _write_meta(feature_dir, "plan")
        # An unapproved lane -- under the (pre-fix) hardcoded software-dev
        # routing this alone was enough to make "review" fail via
        # `_evaluate_wp_iteration_guard`.
        _seed_wp(feature_dir, "WP01", "planned")

        failures = _check_cli_guards("review", feature_dir)

        assert failures == []
        assert WP_BLOCK_REVIEW_MESSAGE not in failures

    def test_routing_reaches_the_real_plan_guard_table_entry(self, tmp_path: Path) -> None:
        """Directly proves the dispatch, not just the resulting empty list."""
        feature_dir = tmp_path / "kitty-specs" / "042-plan-feature"
        _write_meta(feature_dir, "plan")
        _seed_wp(feature_dir, "WP01", "planned")

        family = get_mission_type(feature_dir)
        assert family == "plan"

        snapshot = gather_artifact_presence(feature_dir, mission_family=family, step_id="review")

        assert evaluate_guards_strict(snapshot) == _evaluate_plan_guards(snapshot) == []


# ---------------------------------------------------------------------------
# AC-14 / NFR-003 — software-dev evaluation is unchanged
# ---------------------------------------------------------------------------


class TestAC14SoftwareDevUnchanged:
    def test_review_still_blocks_on_unapproved_wps(self, tmp_path: Path) -> None:
        feature_dir = tmp_path / "kitty-specs" / "042-sd-feature"
        _write_meta(feature_dir, "software-dev")
        _seed_wp(feature_dir, "WP01", "planned")

        failures = _check_cli_guards("review", feature_dir)

        assert failures == [WP_BLOCK_REVIEW_MESSAGE]

    def test_review_passes_once_all_wps_are_approved_or_done(self, tmp_path: Path) -> None:
        feature_dir = tmp_path / "kitty-specs" / "042-sd-feature"
        _write_meta(feature_dir, "software-dev")
        _seed_wp(feature_dir, "WP01", "approved")
        _seed_wp(feature_dir, "WP02", "done")

        failures = _check_cli_guards("review", feature_dir)

        assert failures == []

    def test_specify_guard_still_requires_spec_md(self, tmp_path: Path) -> None:
        feature_dir = tmp_path / "kitty-specs" / "042-sd-feature"
        _write_meta(feature_dir, "software-dev")

        failures = _check_cli_guards("specify", feature_dir)

        assert len(failures) == 1
        assert "spec.md" in failures[0]


# ---------------------------------------------------------------------------
# Family-key identity guard
# ---------------------------------------------------------------------------


BUILT_IN_MISSION_TYPES = ("research", "documentation", "software-dev", "plan")


class TestFamilyKeyIdentity:
    def test_guard_table_covers_exactly_the_four_built_ins(self) -> None:
        assert set(_GUARD_TABLES) == set(BUILT_IN_MISSION_TYPES)

    @pytest.mark.parametrize("mission_type", BUILT_IN_MISSION_TYPES)
    def test_get_mission_type_round_trips_to_the_guard_table_key(
        self, tmp_path: Path, mission_type: str
    ) -> None:
        feature_dir = tmp_path / "kitty-specs" / "042-identity-feature"
        _write_meta(feature_dir, mission_type)

        resolved = get_mission_type(feature_dir)

        # If a built-in's meta.json string ever diverged from its
        # `_GUARD_TABLES` key, a valid mission of that type would wrongly
        # fail-close post-fix -- stop and report rather than silently
        # mapping around the mismatch.
        assert resolved == mission_type
        assert resolved in _GUARD_TABLES


# ---------------------------------------------------------------------------
# None / typeless family handling
# ---------------------------------------------------------------------------


class TestTypelessMissionFamily:
    def test_typeless_mission_fails_closed_not_crash(self, tmp_path: Path) -> None:
        """No meta.json at all -> ``get_mission_type`` degrades to ``""``
        (the neutral/typeless result, never ``None`` and never a silent
        ``software-dev`` default). ``""`` has no ``_GUARD_TABLES`` entry, so
        ``_check_cli_guards`` must fail closed via
        ``UnregisteredMissionFamilyError`` -- a clean, typed exception, not
        an ``AttributeError``/``TypeError`` crash from an unhandled ``None``.
        """
        feature_dir = tmp_path / "kitty-specs" / "042-typeless-feature"
        feature_dir.mkdir(parents=True)

        assert get_mission_type(feature_dir) == ""

        with pytest.raises(UnregisteredMissionFamilyError):
            _check_cli_guards("review", feature_dir)
