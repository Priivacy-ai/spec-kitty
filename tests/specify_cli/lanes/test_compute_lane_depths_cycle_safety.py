"""Lock the fix from commit 72ff0d723: _compute_lane_depths handles cycles.

A self-loop or arbitrary cycle in the lane dependency graph must NOT
trigger ``RecursionError: maximum recursion depth exceeded``. Cycle
detection is best-effort (the depth value for cycle members may not
reflect graph reality), but the function MUST return a valid dict
without blowing the stack.

Regression test for FR-015 of mission test-stabilization-and-debt-pass-01KSF9HJ.
"""
from __future__ import annotations

from specify_cli.lanes.compute import _compute_lane_depths
from specify_cli.lanes.models import ExecutionLane


def _make_lane(lane_id: str) -> ExecutionLane:
    """Minimal ExecutionLane factory for tests.

    ExecutionLane is a frozen dataclass with tuple-typed sequence fields;
    pass empty tuples for the unused fields.
    """
    return ExecutionLane(
        lane_id=lane_id,
        wp_ids=(),
        write_scope=(),
        predicted_surfaces=(),
        depends_on_lanes=(),
        parallel_group=0,
    )


def test_self_loop_does_not_recurse():
    """Lane that depends on itself returns depth 0 without RecursionError."""
    lanes = [_make_lane("lane-a")]
    lane_deps = {"lane-a": {"lane-a"}}
    depths = _compute_lane_depths(lanes, lane_deps)
    assert depths == {"lane-a": 0}


def test_two_lane_cycle_does_not_recurse():
    """A -> B -> A cycle returns a dict without RecursionError."""
    lanes = [_make_lane("lane-a"), _make_lane("lane-b")]
    lane_deps = {"lane-a": {"lane-b"}, "lane-b": {"lane-a"}}
    depths = _compute_lane_depths(lanes, lane_deps)
    assert set(depths.keys()) == {"lane-a", "lane-b"}
    # Each lane's depth is a finite int. Exact value is best-effort.
    for d in depths.values():
        assert isinstance(d, int)
        assert d >= 0


def test_three_lane_cycle_does_not_recurse():
    """A -> B -> C -> A returns a dict without RecursionError."""
    lanes = [_make_lane(x) for x in ("lane-a", "lane-b", "lane-c")]
    lane_deps = {"lane-a": {"lane-b"}, "lane-b": {"lane-c"}, "lane-c": {"lane-a"}}
    depths = _compute_lane_depths(lanes, lane_deps)
    assert set(depths.keys()) == {"lane-a", "lane-b", "lane-c"}


def test_clean_dag_still_computes_correct_depths():
    """The cycle-detection guard MUST NOT regress clean-DAG output."""
    lanes = [_make_lane(x) for x in ("lane-a", "lane-b", "lane-c")]
    lane_deps: dict[str, set[str]] = {
        "lane-a": set(),
        "lane-b": {"lane-a"},
        "lane-c": {"lane-a", "lane-b"},
    }
    depths = _compute_lane_depths(lanes, lane_deps)
    assert depths == {"lane-a": 0, "lane-b": 1, "lane-c": 2}


def test_independent_lanes_get_depth_zero():
    """Lanes with no deps all get depth 0."""
    lanes = [_make_lane(x) for x in ("lane-a", "lane-b", "lane-c")]
    lane_deps: dict[str, set[str]] = {
        "lane-a": set(),
        "lane-b": set(),
        "lane-c": set(),
    }
    depths = _compute_lane_depths(lanes, lane_deps)
    assert depths == {"lane-a": 0, "lane-b": 0, "lane-c": 0}
