"""ATDD: uninitialized canonical-status error must name a dependency cycle.

Regression test for upstream #1589 (facet 1): when ``finalize-tasks`` aborts on a
circular WP dependency, canonical status is never bootstrapped, so downstream
``move-task``/``next`` raise "no canonical status, run finalize-tasks". That hint
loops forever because finalize keeps aborting on the same cycle. The error must
instead surface the dependency cycle as the actionable root cause.

These tests are RED before the fix (the helper does not exist) and GREEN after.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.status.uninitialized_hint import (
    find_wp_dependency_cycles,
    uninitialized_status_error,
)

pytestmark = [pytest.mark.unit]


def _write_wp(tasks_dir: Path, wp_id: str, deps: list[str]) -> None:
    dep_block = "dependencies: []" if not deps else "dependencies:\n" + "".join(
        f"- {d}\n" for d in deps
    )
    tasks_dir.joinpath(f"{wp_id}-x.md").write_text(
        f"---\nwork_package_id: {wp_id}\ntitle: {wp_id}\n{dep_block}\n---\n\n# {wp_id}\n",
        encoding="utf-8",
    )


@pytest.fixture()
def cyclic_feature(tmp_path: Path) -> Path:
    feature_dir = tmp_path / "kitty-specs" / "demo-mission"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    _write_wp(tasks_dir, "WP09", ["WP10"])
    _write_wp(tasks_dir, "WP10", ["WP09"])  # cycle
    _write_wp(tasks_dir, "WP01", [])
    return feature_dir


@pytest.fixture()
def acyclic_feature(tmp_path: Path) -> Path:
    feature_dir = tmp_path / "kitty-specs" / "demo-mission"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    _write_wp(tasks_dir, "WP10", [])
    _write_wp(tasks_dir, "WP09", ["WP10"])
    return feature_dir


def test_find_cycles_detects_frontmatter_cycle(cyclic_feature: Path) -> None:
    cycles = find_wp_dependency_cycles(cyclic_feature)
    assert cycles, "expected a cycle to be detected from WP frontmatter"
    flat = {wp for cycle in cycles for wp in cycle}
    assert {"WP09", "WP10"} <= flat


def test_find_cycles_none_when_acyclic(acyclic_feature: Path) -> None:
    assert find_wp_dependency_cycles(acyclic_feature) is None


def test_error_names_cycle_as_root_cause(cyclic_feature: Path) -> None:
    msg = uninitialized_status_error("demo-mission", "WP10", cyclic_feature)
    lowered = msg.lower()
    # The actionable cause is the cycle, not a bare "run finalize-tasks".
    assert "circular" in lowered or "cycle" in lowered
    assert "WP09" in msg and "WP10" in msg
    # Must explain finalize-tasks cannot initialize until the cycle is resolved,
    # rather than implying re-running it (which loops).
    assert "resolve" in lowered or "break" in lowered or "fix" in lowered


def test_error_is_generic_when_acyclic(acyclic_feature: Path) -> None:
    msg = uninitialized_status_error("demo-mission", "WP09", acyclic_feature)
    assert "finalize-tasks" in msg
    assert "circular" not in msg.lower() and "cycle" not in msg.lower()
