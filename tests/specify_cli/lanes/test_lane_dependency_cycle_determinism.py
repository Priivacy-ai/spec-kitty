"""Pure-domain determinism matrix for execution-lane cycle diagnostics."""

from __future__ import annotations

import json
from collections.abc import Iterable

import pytest

from specify_cli.lanes.compute import LaneDependencyCycleError, compute_lanes
from specify_cli.ownership.models import OwnershipManifest, WorkProductKind

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _manifest(path: str) -> OwnershipManifest:
    return OwnershipManifest(
        execution_mode=WorkProductKind.CODE_CHANGE,
        owned_files=(path,),
        authoritative_surface=path.removesuffix("**"),
    )


def _materialize(values: Iterable[str], *, reverse: bool) -> list[str]:
    """Exercise set insertion order before returning an intentionally ordered list."""
    ordered = sorted(values, reverse=reverse)
    materialized: set[str] = set()
    for value in ordered:
        materialized.add(value)
    return sorted(materialized, reverse=reverse)


def _inputs(*, reverse: bool) -> tuple[dict[str, list[str]], dict[str, OwnershipManifest]]:
    dependency_items = [
        ("WP01", _materialize(("WP02", "WP06"), reverse=reverse)),
        ("WP02", []),
        ("WP03", ["WP04"]),
        ("WP04", []),
        ("WP05", ["WP06"]),
        ("WP06", []),
        ("WP07", ["WP08"]),
        ("WP08", []),
    ]
    ownership_items = [
        ("WP01", _manifest("src/a/**")),
        ("WP02", _manifest("src/b/**")),
        ("WP03", _manifest("src/b/**")),
        ("WP04", _manifest("src/a/**")),
        ("WP05", _manifest("src/c/**")),
        ("WP06", _manifest("src/d/**")),
        ("WP07", _manifest("src/d/**")),
        ("WP08", _manifest("src/c/**")),
    ]
    if reverse:
        dependency_items.reverse()
        ownership_items.reverse()
    return dict(dependency_items), dict(ownership_items)


def _stable_cycle_facts(*, reverse: bool) -> tuple[bytes, LaneDependencyCycleError]:
    graph, manifests = _inputs(reverse=reverse)
    with pytest.raises(LaneDependencyCycleError) as exc_info:
        compute_lanes(graph, manifests, "multi-cycle")
    error = exc_info.value
    facts = {
        "error_code": error.error_code,
        "cycle_path": error.cycle_path,
        "cycle_lanes": [{"lane_id": lane.lane_id, "wp_ids": lane.wp_ids} for lane in error.cycle_lanes],
    }
    return (
        json.dumps(facts, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        error,
    )


def test_equivalent_multi_cycle_inputs_have_byte_identical_diagnostics() -> None:
    """Mapping, dependency, set, and ownership order cannot change the winner."""
    captures = [_stable_cycle_facts(reverse=reverse) for reverse in (False, True)]
    captures.extend(_stable_cycle_facts(reverse=False) for _ in range(5))

    serialized = [capture[0] for capture in captures]
    assert len(set(serialized)) == 1

    error = captures[0][1]
    assert error.error_code == "LANE_DEPENDENCY_CYCLE"
    assert error.cycle_path == ("lane-a", "lane-b", "lane-a")
    assert error.cycle_path[0] == error.cycle_path[-1]
    assert error.cycle_path[0] == min(error.cycle_path[:-1])

    expected_edges = {"lane-a": {"lane-b"}, "lane-b": {"lane-a"}}
    assert all(downstream in expected_edges[upstream] for upstream, downstream in zip(error.cycle_path, error.cycle_path[1:], strict=False))
    assert tuple(lane.lane_id for lane in error.cycle_lanes) == error.cycle_path[:-1]
    assert len(error.cycle_lanes) == len(set(error.cycle_path[:-1]))
    assert all(lane.wp_ids == tuple(sorted(lane.wp_ids)) for lane in error.cycle_lanes)
