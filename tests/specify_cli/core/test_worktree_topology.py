"""Mixed-mission topology tests for repository-root planning work."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.core.worktree_topology import materialize_worktree_topology, render_topology_json
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import write_lanes_json
from specify_cli.workspace.context import clear_workspace_resolution_caches

pytestmark = pytest.mark.fast


def _write_wp(path: Path, wp_id: str, *, execution_mode: str | None = None) -> None:
    lines = ["---", f"work_package_id: {wp_id}", "dependencies: []"]
    if execution_mode is not None:
        lines.extend(
            [
                f"execution_mode: {execution_mode}",
                "owned_files:",
                "  - kitty-specs/077-feature/**",
                "authoritative_surface: kitty-specs/077-feature/",
            ]
        )
    lines.extend(["---", f"# {wp_id}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _manifest(mission_slug: str) -> LanesManifest:
    return LanesManifest(
        version=1,
        mission_slug=mission_slug,
        mission_id=f"mission-{mission_slug}",
        mission_branch=f"kitty/mission-{mission_slug}",
        target_branch="main",
        lanes=[
            ExecutionLane(
                lane_id="lane-a",
                wp_ids=("WP01",),
                write_scope=("src/**",),
                predicted_surfaces=("core",),
                depends_on_lanes=(),
                parallel_group=0,
            )
        ],
        computed_at="2026-04-08T00:00:00Z",
        computed_from="test",
    )


@pytest.fixture(autouse=True)
def _clear_workspace_cache() -> None:
    clear_workspace_resolution_caches()


def test_mixed_mission_topology_includes_repo_root_planning_entry(tmp_path: Path) -> None:
    repo_root = tmp_path
    mission_slug = "077-feature"
    feature_dir = repo_root / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (repo_root / ".git").mkdir()
    (feature_dir / "meta.json").write_text(
        json.dumps({"feature_number": "077", "mission_slug": mission_slug, "target_branch": "main"}),
        encoding="utf-8",
    )
    _write_wp(tasks_dir / "WP01-code.md", "WP01", execution_mode="code_change")
    _write_wp(tasks_dir / "WP02-planning.md", "WP02", execution_mode="planning_artifact")
    write_lanes_json(feature_dir, _manifest(mission_slug))

    topology = materialize_worktree_topology(repo_root, mission_slug)

    assert [entry.wp_id for entry in topology.entries] == ["WP01", "WP02"]
    assert topology.has_stacking is True

    planning_entry = topology.get_entry("WP02")
    assert planning_entry is not None
    assert planning_entry.execution_mode == "planning_artifact"
    assert planning_entry.resolution_kind == "repo_root"
    assert planning_entry.lane_id == "lane-planning"
    assert planning_entry.branch_name is None
    assert planning_entry.base_branch is None


def test_render_topology_json_marks_repo_root_planning_workspace(tmp_path: Path) -> None:
    repo_root = tmp_path
    mission_slug = "077-feature"
    feature_dir = repo_root / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (repo_root / ".git").mkdir()
    (feature_dir / "meta.json").write_text(
        json.dumps({"feature_number": "077", "mission_slug": mission_slug, "target_branch": "main"}),
        encoding="utf-8",
    )
    _write_wp(tasks_dir / "WP01-code.md", "WP01", execution_mode="code_change")
    _write_wp(tasks_dir / "WP02-planning.md", "WP02", execution_mode="planning_artifact")
    write_lanes_json(feature_dir, _manifest(mission_slug))

    topology = materialize_worktree_topology(repo_root, mission_slug)
    payload = json.loads("\n".join(render_topology_json(topology, "WP02")[1:-1]))

    assert payload["diff_command"] == "unavailable: no deterministic implementation claim commit found"
    assert payload["note"] == "WP02 runs in the repository root planning workspace."
    planning_entry = next(entry for entry in payload["entries"] if entry["wp"] == "WP02")
    assert planning_entry["workspace_kind"] == "repo_root"
    assert planning_entry["execution_mode"] == "planning_artifact"
    assert planning_entry["lane_id"] == "lane-planning"
    assert planning_entry["branch"] is None


def test_planning_only_mission_without_lanes_json_still_materializes_topology(tmp_path: Path) -> None:
    repo_root = tmp_path
    mission_slug = "077-feature"
    feature_dir = repo_root / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (repo_root / ".git").mkdir()
    (feature_dir / "meta.json").write_text(
        json.dumps({"feature_number": "077", "mission_slug": mission_slug, "target_branch": "main"}),
        encoding="utf-8",
    )
    _write_wp(tasks_dir / "WP02-planning.md", "WP02", execution_mode="planning_artifact")

    topology = materialize_worktree_topology(repo_root, mission_slug)

    assert [entry.wp_id for entry in topology.entries] == ["WP02"]
    entry = topology.get_entry("WP02")
    assert entry is not None
    assert entry.resolution_kind == "repo_root"
    assert entry.lane_id == "lane-planning"
