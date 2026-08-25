"""Governed 100-WP performance proof for cancellation-aware finalization."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from specify_cli.cli.commands.agent.mission import finalize_tasks
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _build_100_wp_mission(
    tmp_path: Path,
) -> tuple[Path, dict[str, tuple[str, ...]], frozenset[str]]:
    mission_slug = "3432-canceled-performance"
    mission_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text('{"target_branch": "main"}\n', encoding="utf-8")
    (mission_dir / "spec.md").write_text(
        "# Spec\n## Functional Requirements\n- FR-001: Finalize work packages.\n",
        encoding="utf-8",
    )
    sections: list[str] = []
    dependency_graph: dict[str, tuple[str, ...]] = {}
    canceled_wp_ids = frozenset(f"WP{number:02d}" for number in range(10, 101, 10))
    for number in range(1, 101):
        wp_id = f"WP{number:02d}"
        if number == 1:
            dependencies: tuple[str, ...] = ()
        elif wp_id in canceled_wp_ids:
            # A canceled source still declares a representative direct edge;
            # its outgoing dependency is excluded with the source.
            dependencies = (f"WP{number - 1:02d}",)
        elif f"WP{number - 1:02d}" in canceled_wp_ids:
            # Eligible work never points at a canceled prerequisite.
            dependencies = (f"WP{number - 2:02d}",)
        else:
            dependencies = (f"WP{number - 1:02d}",)
        dependency_graph[wp_id] = dependencies
        dependency_yaml = (
            "[]"
            if not dependencies
            else "[" + ", ".join(dependencies) + "]"
        )
        (tasks_dir / f"{wp_id}-fixture.md").write_text(
            "---\n"
            f"work_package_id: {wp_id}\n"
            f"title: {wp_id}\n"
            f"dependencies: {dependency_yaml}\n"
            "requirement_refs: [FR-001]\n"
            "execution_mode: planning_artifact\n"
            "owned_files: []\n"
            f"authoritative_surface: kitty-specs/{mission_slug}/\n"
            "---\n"
            f"# {wp_id}\n",
            encoding="utf-8",
        )
        sections.append(f"## {wp_id}\n**Requirement Refs**: FR-001\n")
        append_event(
            mission_dir,
            StatusEvent(
                event_id=f"01J3432PERFORMANCE{number:08d}",
                mission_slug=mission_slug,
                wp_id=wp_id,
                from_lane=Lane.PLANNED,
                to_lane=Lane.CANCELED if number % 10 == 0 else Lane.PLANNED,
                at="2026-08-24T00:00:00Z",
                actor="benchmark",
                force=False,
                execution_mode="worktree",
            ),
        )
    (mission_dir / "tasks.md").write_text("\n".join(sections), encoding="utf-8")
    return mission_dir, dependency_graph, canceled_wp_ids


@pytest.mark.performance
@pytest.mark.benchmark(group="cli")
def test_100_wp_cancellation_aware_finalize_p95_under_two_seconds(
    tmp_path: Path,
    benchmark: BenchmarkFixture,
) -> None:
    """NFR-003: governed validate-only finalization stays within two seconds."""
    mission_dir, dependency_graph, canceled_wp_ids = _build_100_wp_mission(tmp_path)

    direct_edges = {
        (wp_id, prerequisite)
        for wp_id, prerequisites in dependency_graph.items()
        for prerequisite in prerequisites
    }
    canceled_source_edges = {
        edge for edge in direct_edges if edge[0] in canceled_wp_ids
    }
    stale_eligible_edges = {
        edge
        for edge in direct_edges
        if edge[0] not in canceled_wp_ids and edge[1] in canceled_wp_ids
    }
    assert len(dependency_graph) == 100
    assert len(canceled_wp_ids) == 10
    assert len(direct_edges) == 99
    assert len(canceled_source_edges) == 10
    assert stale_eligible_edges == set()

    def _finalize() -> None:
        finalize_tasks(
            feature=mission_dir.name,
            json_output=True,
            validate_only=True,
        )

    with (
        patch("specify_cli.cli.commands.agent.mission.locate_project_root", return_value=tmp_path),
        patch("specify_cli.cli.commands.agent.mission._find_feature_directory", return_value=mission_dir),
        patch("specify_cli.cli.commands.agent.mission._show_branch_context", return_value=(tmp_path, "main")),
        patch("specify_cli.cli.commands.agent.mission_finalize._run_saas_boundary_preflight"),
        patch("specify_cli.cli.commands.agent.mission_finalize._emit_json"),
    ):
        benchmark.pedantic(
            _finalize,
            rounds=10,
            iterations=1,
            warmup_rounds=2,
        )

    sorted_data = benchmark.stats.stats.sorted_data
    assert len(sorted_data) == 10
    p95 = sorted_data[9]
    assert p95 <= 2.0, f"100-WP finalize p95 {p95:.6f}s exceeded 2.0s"
