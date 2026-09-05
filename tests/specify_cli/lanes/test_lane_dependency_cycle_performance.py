"""Governed performance proof for lane-cycle detection."""

from __future__ import annotations

import os
import time

import pytest

from specify_cli.lanes.compute import _find_lane_dependency_cycle

# ``fast`` gives this node a collection home; the explicit skip keeps ordinary
# CI from spending time on the governed performance sample.
pytestmark = [pytest.mark.unit, pytest.mark.fast]

_LANE_COUNT = 100
_EDGE_COUNT = 500
_EXPECTED_CYCLE = (*(f"lane-{index:03d}" for index in range(90, 100)), "lane-090")


def _performance_graph() -> dict[str, set[str]]:
    """Build 499 forward DAG edges plus one late back edge, exactly 500 total."""
    lane_ids = [f"lane-{index:03d}" for index in range(_LANE_COUNT)]
    edges = {(lane_ids[index], lane_ids[index + 1]) for index in range(99)}
    for source_index, source in enumerate(lane_ids):
        for target in lane_ids[source_index + 1 :]:
            edges.add((source, target))
            if len(edges) == _EDGE_COUNT - 1:
                break
        if len(edges) == _EDGE_COUNT - 1:
            break
    edges.add(("lane-099", "lane-090"))
    assert len(edges) == _EDGE_COUNT

    graph = {lane_id: set() for lane_id in lane_ids}
    for source, target in edges:
        graph[source].add(target)
    return graph


@pytest.mark.skipif(
    not os.environ.get("SPEC_KITTY_RUN_PERFORMANCE"),
    reason="set SPEC_KITTY_RUN_PERFORMANCE=1 to run the lane-cycle performance sample",
)
def test_cycle_detection_100_lanes_500_edges_p95_under_100ms() -> None:
    """NFR-003: exact governed fixture completes within the 100 ms p95 budget."""
    graph = _performance_graph()

    for _ in range(5):
        assert _find_lane_dependency_cycle(graph) == _EXPECTED_CYCLE

    durations: list[float] = []
    for _ in range(20):
        started = time.perf_counter()
        result = _find_lane_dependency_cycle(graph)
        durations.append(time.perf_counter() - started)
        assert result == _EXPECTED_CYCLE

    p95 = sorted(durations)[18]
    assert p95 <= 0.100, f"cycle detector p95 {p95:.6f}s exceeded 0.100s"
