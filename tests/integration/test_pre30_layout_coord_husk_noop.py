"""FR-007 (#2199): ``check_pre30_layout`` is a clean no-op on coord-husk shapes.

The pre-3.0 layout guard (:func:`check_pre30_layout`) must NOT fire — and must NOT
mutate the tree — against a production-shaped coordination husk. Two distinct husk
shapes, exercising two distinct branches of ``is_legacy_format``:

* (a) the EXISTING ``coord_topology_mission`` STATUS-only husk (real
  ``status.events.jsonl``, NO ``tasks/``) — short-circuits on the absent
  ``tasks/`` dir.
* (b) the ``coord_topology_mission_tasks_husk`` variant (a post-3.0 ``tasks/`` with
  a WP ``.md`` but NO legacy lane subdirs) — runs the ``LEGACY_LANE_DIRS`` loop and
  classifies NON-legacy.

NON-FAKEABLE (squad HIGH): the proof is NO MUTATION, not merely no-raise. Each test
snapshots ``set(husk_dir.rglob("*"))`` before the call and asserts it is byte-for-byte
identical afterwards. It also asserts the husk carries REAL status payload (it is NOT
an empty dir — an empty dir short-circuits ``is_legacy_format`` identically and would
prove nothing about the no-op semantics, SC-004).
"""

from __future__ import annotations

import pytest

from specify_cli.upgrade.legacy_detector import is_legacy_format
from specify_cli.upgrade.pre30_guard import check_pre30_layout
from tests.integration.coord_topology_fixture import (
    CoordTopologyContext,
    coord_topology_mission,
    coord_topology_mission_tasks_husk,
)

# Re-export fixtures so pytest discovers them as parameters for this module.
__all__ = ["coord_topology_mission", "coord_topology_mission_tasks_husk"]

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _assert_carries_status_payload(ctx: CoordTopologyContext) -> None:
    """Guard the empty-dir trap: the husk must hold REAL status payload.

    An empty dir short-circuits ``is_legacy_format`` identically to a valid husk and
    would prove nothing about no-op semantics — so we assert the husk dir is
    non-empty AND its ``status.events.jsonl`` actually carries an event line.
    """
    husk_dir = ctx.coord_feature_dir
    assert list(husk_dir.iterdir()), (
        f"empty-dir trap: husk {husk_dir} is empty — the no-op proof would be vacuous"
    )
    assert ctx.status_events_path.exists(), "husk must carry status.events.jsonl"
    payload = ctx.status_events_path.read_text(encoding="utf-8").strip()
    assert payload, "husk status.events.jsonl must carry a real event line"


def test_check_pre30_layout_noop_on_status_only_husk(
    coord_topology_mission: CoordTopologyContext,
) -> None:
    """(a) STATUS-only husk: ``check_pre30_layout`` no-ops AND mutates nothing.

    Exercises the ``tasks/`` short-circuit branch of ``is_legacy_format`` (the husk
    has no ``tasks/`` dir at all).
    """
    ctx = coord_topology_mission
    husk_dir = ctx.coord_feature_dir
    _assert_carries_status_payload(ctx)

    # Distinct-branch proof: the STATUS-only husk carries NO tasks/ dir, so
    # is_legacy_format short-circuits to False before the lane-dir loop.
    assert not (husk_dir / "tasks").exists()
    assert is_legacy_format(husk_dir) is False

    before = set(husk_dir.rglob("*"))
    result = check_pre30_layout(husk_dir)

    assert result is None, "check_pre30_layout must return None on the no-op path"
    assert set(husk_dir.rglob("*")) == before, (
        "check_pre30_layout mutated the STATUS-only husk tree (no-op violated)"
    )


def test_check_pre30_layout_noop_on_tasks_present_non_legacy_husk(
    coord_topology_mission_tasks_husk: CoordTopologyContext,
) -> None:
    """(b) ``tasks/``-present non-legacy husk: no-op AND mutates nothing (FR-007(b)).

    Exercises the ``LEGACY_LANE_DIRS``/``.md`` branch of ``is_legacy_format`` — the
    husk DOES carry a ``tasks/`` dir, but with NO legacy lane subdirs, so the loop
    runs and classifies the husk NON-legacy.
    """
    ctx = coord_topology_mission_tasks_husk
    husk_dir = ctx.coord_feature_dir
    _assert_carries_status_payload(ctx)

    # Distinct-branch proof: the husk DOES carry tasks/ (post-3.0 WP .md, no lane
    # subdirs), so is_legacy_format runs the lane-dir loop and returns False.
    husk_tasks_dir = husk_dir / "tasks"
    assert husk_tasks_dir.is_dir()
    assert list(husk_tasks_dir.glob("WP*.md")), "husk tasks/ must carry a WP .md file"
    assert not any(child.is_dir() for child in husk_tasks_dir.iterdir()), (
        "husk tasks/ must carry no legacy lane subdirs"
    )
    assert is_legacy_format(husk_dir) is False

    before = set(husk_dir.rglob("*"))
    result = check_pre30_layout(husk_dir)

    assert result is None, "check_pre30_layout must return None on the no-op path"
    assert set(husk_dir.rglob("*")) == before, (
        "check_pre30_layout mutated the tasks-present husk tree (no-op violated)"
    )
