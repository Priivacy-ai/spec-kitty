"""Lane workspace context integrity tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import write_lanes_json
from specify_cli.workspace_context import (
    WorkspaceContext,
    build_feature_context_index,
    find_orphaned_contexts,
    list_contexts,
    load_context,
    resolve_feature_worktree,
    resolve_workspace_for_wp,
    save_context,
)


@pytest.fixture
def kittify_project(tmp_path: Path) -> Path:
    (tmp_path / ".kittify" / "workspaces").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _lane_manifest(feature_slug: str = "001-feature") -> LanesManifest:
    return LanesManifest(
        version=1,
        feature_slug=feature_slug,
        mission_id=f"mission-{feature_slug}",
        mission_branch=f"kitty/mission-{feature_slug}",
        target_branch="main",
        lanes=[
            ExecutionLane(
                lane_id="lane-a",
                wp_ids=("WP01", "WP02"),
                write_scope=("src/**",),
                predicted_surfaces=("core",),
                depends_on_lanes=(),
                parallel_group=0,
            )
        ],
        computed_at="2026-04-04T10:00:00Z",
        computed_from="test",
    )


def _context(*, current_wp: str = "WP02") -> WorkspaceContext:
    return WorkspaceContext(
        wp_id=current_wp,
        feature_slug="001-feature",
        worktree_path=".worktrees/001-feature-lane-a",
        branch_name="kitty/mission-001-feature-lane-a",
        base_branch="kitty/mission-001-feature",
        base_commit="abc123",
        dependencies=["WP01"],
        created_at="2026-01-25T12:00:00Z",
        created_by="implement-command-lane",
        vcs_backend="git",
        lane_id="lane-a",
        lane_wp_ids=["WP01", "WP02"],
        current_wp=current_wp,
    )


class TestOrphanedContext:
    def test_orphaned_context_detected(self, kittify_project: Path) -> None:
        save_context(kittify_project, _context())

        orphaned = find_orphaned_contexts(kittify_project)

        assert len(orphaned) == 1
        assert orphaned[0][0] == "001-feature-lane-a"


class TestCorruptedContext:
    def test_invalid_json_handled(self, kittify_project: Path) -> None:
        context_file = kittify_project / ".kittify" / "workspaces" / "001-feature-lane-a.json"
        context_file.write_text("{invalid json", encoding="utf-8")

        loaded = load_context(kittify_project, "001-feature-lane-a")
        assert loaded is None
        assert list_contexts(kittify_project) == []


class TestContextIndexAndResolution:
    def test_build_feature_context_index_expands_lane_membership(self, kittify_project: Path) -> None:
        save_context(kittify_project, _context())

        index = build_feature_context_index(kittify_project, "001-feature")

        assert set(index) == {"WP01", "WP02"}
        assert index["WP01"].lane_id == "lane-a"
        assert index["WP02"].lane_wp_ids == ["WP01", "WP02"]

    def test_build_feature_context_index_cache_invalidated_on_save(self, kittify_project: Path) -> None:
        save_context(kittify_project, _context(current_wp="WP01"))
        initial = build_feature_context_index(kittify_project, "001-feature")
        assert set(initial) == {"WP01", "WP02"}

        second = WorkspaceContext(
            wp_id="WP03",
            feature_slug="001-feature",
            worktree_path=".worktrees/001-feature-lane-b",
            branch_name="kitty/mission-001-feature-lane-b",
            base_branch="kitty/mission-001-feature",
            base_commit="def456",
            dependencies=[],
            created_at="2026-01-25T12:02:00Z",
            created_by="implement-command-lane",
            vcs_backend="git",
            lane_id="lane-b",
            lane_wp_ids=["WP03"],
            current_wp="WP03",
        )
        save_context(kittify_project, second)

        refreshed = build_feature_context_index(kittify_project, "001-feature")
        assert set(refreshed) == {"WP01", "WP02", "WP03"}

    def test_resolve_feature_worktree_prefers_context_backed_workspace(self, kittify_project: Path) -> None:
        worktree = kittify_project / ".worktrees" / "001-feature-lane-a"
        worktree.mkdir(parents=True, exist_ok=True)
        save_context(kittify_project, _context())

        resolved = resolve_feature_worktree(kittify_project, "001-feature")

        assert resolved == worktree

    def test_resolve_feature_worktree_falls_back_to_lane_manifest(self, kittify_project: Path) -> None:
        feature_dir = kittify_project / "kitty-specs" / "001-feature"
        feature_dir.mkdir(parents=True, exist_ok=True)
        write_lanes_json(feature_dir, _lane_manifest())

        lane_worktree = kittify_project / ".worktrees" / "001-feature-lane-a"
        lane_worktree.mkdir(parents=True, exist_ok=True)

        resolved = resolve_feature_worktree(kittify_project, "001-feature")

        assert resolved == lane_worktree

    def test_resolve_feature_worktree_returns_none_without_lane_manifest(self, kittify_project: Path) -> None:
        assert resolve_feature_worktree(kittify_project, "001-feature") is None

    def test_resolve_workspace_for_wp_uses_lane_manifest(self, kittify_project: Path) -> None:
        feature_dir = kittify_project / "kitty-specs" / "001-feature"
        feature_dir.mkdir(parents=True, exist_ok=True)
        write_lanes_json(feature_dir, _lane_manifest())

        resolved = resolve_workspace_for_wp(kittify_project, "001-feature", "WP02")

        assert resolved.workspace_name == "001-feature-lane-a"
        assert resolved.branch_name == "kitty/mission-001-feature-lane-a"
        assert resolved.lane_id == "lane-a"
        assert resolved.lane_wp_ids == ["WP01", "WP02"]

    def test_resolve_workspace_for_wp_errors_when_wp_not_in_manifest(self, kittify_project: Path) -> None:
        feature_dir = kittify_project / "kitty-specs" / "001-feature"
        feature_dir.mkdir(parents=True, exist_ok=True)
        write_lanes_json(feature_dir, _lane_manifest())

        with pytest.raises(ValueError, match="not assigned to any lane"):
            resolve_workspace_for_wp(kittify_project, "001-feature", "WP99")
