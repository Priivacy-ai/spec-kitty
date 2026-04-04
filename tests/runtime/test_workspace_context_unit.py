"""Workspace context integrity tests."""

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
    """Create minimal project structure with .kittify directory."""
    (tmp_path / ".kittify" / "workspaces").mkdir(parents=True, exist_ok=True)
    return tmp_path


class TestOrphanedContext:
    def test_orphaned_context_detected(self, kittify_project: Path) -> None:
        """Context without worktree should be detected."""
        context = WorkspaceContext(
            wp_id="WP01",
            feature_slug="001-feature",
            worktree_path=".worktrees/001-feature-WP01",
            branch_name="001-feature-WP01",
            base_branch="main",
            base_commit="abc123",
            dependencies=[],
            created_at="2026-01-25T12:00:00Z",
            created_by="implement-command",
            vcs_backend="git",
        )

        save_context(kittify_project, context)

        orphaned = find_orphaned_contexts(kittify_project)

        assert len(orphaned) == 1
        assert orphaned[0][0] == "001-feature-WP01"


class TestCorruptedContext:
    def test_invalid_json_handled(self, kittify_project: Path) -> None:
        """Invalid JSON in context should be handled gracefully."""
        context_file = kittify_project / ".kittify" / "workspaces" / "001-feature-WP01.json"
        context_file.write_text("{invalid json", encoding="utf-8")

        loaded = load_context(kittify_project, "001-feature-WP01")
        assert loaded is None

        contexts = list_contexts(kittify_project)
        assert contexts == []


class TestContextIndexAndResolution:
    def test_build_feature_context_index_expands_lane_membership(self, kittify_project: Path) -> None:
        """Lane contexts should be indexed under every WP they own."""
        context = WorkspaceContext(
            wp_id="WP02",
            feature_slug="001-feature",
            worktree_path=".worktrees/001-feature-lane-a",
            branch_name="kitty/mission-001-feature-lane-a",
            base_branch="kitty/mission-001-feature",
            base_commit="abc123",
            dependencies=["WP01"],
            created_at="2026-01-25T12:00:00Z",
            created_by="implement-command",
            vcs_backend="git",
            lane_id="lane-a",
            lane_wp_ids=["WP01", "WP02"],
            current_wp="WP02",
        )
        save_context(kittify_project, context)

        unrelated = WorkspaceContext(
            wp_id="WP01",
            feature_slug="999-other",
            worktree_path=".worktrees/999-other-WP01",
            branch_name="999-other-WP01",
            base_branch="main",
            base_commit="def456",
            dependencies=[],
            created_at="2026-01-25T12:01:00Z",
            created_by="implement-command",
            vcs_backend="git",
        )
        save_context(kittify_project, unrelated)

        index = build_feature_context_index(kittify_project, "001-feature")

        assert set(index) == {"WP01", "WP02"}
        assert index["WP01"].lane_id == "lane-a"
        assert index["WP02"].lane_wp_ids == ["WP01", "WP02"]

    def test_build_feature_context_index_cache_invalidated_on_save(self, kittify_project: Path) -> None:
        """Saving a new context should invalidate the process-local index cache."""
        first = WorkspaceContext(
            wp_id="WP01",
            feature_slug="001-feature",
            worktree_path=".worktrees/001-feature-lane-a",
            branch_name="kitty/mission-001-feature-lane-a",
            base_branch="kitty/mission-001-feature",
            base_commit="abc123",
            dependencies=[],
            created_at="2026-01-25T12:00:00Z",
            created_by="implement-command",
            vcs_backend="git",
            lane_id="lane-a",
            lane_wp_ids=["WP01"],
            current_wp="WP01",
        )
        save_context(kittify_project, first)

        initial = build_feature_context_index(kittify_project, "001-feature")
        assert set(initial) == {"WP01"}

        second = WorkspaceContext(
            wp_id="WP02",
            feature_slug="001-feature",
            worktree_path=".worktrees/001-feature-lane-b",
            branch_name="kitty/mission-001-feature-lane-b",
            base_branch="kitty/mission-001-feature",
            base_commit="def456",
            dependencies=[],
            created_at="2026-01-25T12:02:00Z",
            created_by="implement-command",
            vcs_backend="git",
            lane_id="lane-b",
            lane_wp_ids=["WP02"],
            current_wp="WP02",
        )
        save_context(kittify_project, second)

        refreshed = build_feature_context_index(kittify_project, "001-feature")
        assert set(refreshed) == {"WP01", "WP02"}

    def test_resolve_feature_worktree_prefers_context_backed_workspace(self, kittify_project: Path) -> None:
        """Existing context-backed worktrees should win over inferred paths."""
        worktree = kittify_project / ".worktrees" / "001-feature-lane-b"
        worktree.mkdir(parents=True, exist_ok=True)
        save_context(
            kittify_project,
            WorkspaceContext(
                wp_id="WP02",
                feature_slug="001-feature",
                worktree_path=".worktrees/001-feature-lane-b",
                branch_name="kitty/mission-001-feature-lane-b",
                base_branch="kitty/mission-001-feature",
                base_commit="abc123",
                dependencies=["WP01"],
                created_at="2026-01-25T12:00:00Z",
                created_by="implement-command",
                vcs_backend="git",
                lane_id="lane-b",
                lane_wp_ids=["WP02"],
                current_wp="WP02",
            ),
        )

        resolved = resolve_feature_worktree(kittify_project, "001-feature")

        assert resolved == worktree

    def test_resolve_feature_worktree_falls_back_to_lane_manifest(self, kittify_project: Path) -> None:
        """If no context exists, lane manifests should still identify the right workspace."""
        feature_dir = kittify_project / "kitty-specs" / "001-feature"
        feature_dir.mkdir(parents=True, exist_ok=True)
        write_lanes_json(
            feature_dir,
            LanesManifest(
                version=1,
                feature_slug="001-feature",
                mission_id="mission-001-feature",
                mission_branch="kitty/mission-001-feature",
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
            ),
        )
        lane_worktree = kittify_project / ".worktrees" / "001-feature-lane-a"
        lane_worktree.mkdir(parents=True, exist_ok=True)

        resolved = resolve_feature_worktree(kittify_project, "001-feature")

        assert resolved == lane_worktree

    def test_resolve_feature_worktree_falls_back_to_legacy_wp_paths(self, kittify_project: Path) -> None:
        """Legacy per-WP worktrees should still be discovered deterministically."""
        wp02 = kittify_project / ".worktrees" / "001-feature-WP02"
        wp01 = kittify_project / ".worktrees" / "001-feature-WP01"
        wp02.mkdir(parents=True, exist_ok=True)
        wp01.mkdir(parents=True, exist_ok=True)

        resolved = resolve_feature_worktree(kittify_project, "001-feature")

        assert resolved == wp01

    def test_resolve_workspace_for_wp_falls_back_when_lane_for_wp_returns_none(self, kittify_project: Path) -> None:
        """A WP missing from lanes.json should fall back to the legacy naming contract."""
        feature_dir = kittify_project / "kitty-specs" / "001-feature"
        feature_dir.mkdir(parents=True, exist_ok=True)
        write_lanes_json(
            feature_dir,
            LanesManifest(
                version=1,
                feature_slug="001-feature",
                mission_id="mission-001-feature",
                mission_branch="kitty/mission-001-feature",
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
                computed_at="2026-04-04T10:00:00Z",
                computed_from="test",
            ),
        )

        resolved = resolve_workspace_for_wp(kittify_project, "001-feature", "WP99")

        assert resolved.workspace_name == "001-feature-WP99"
        assert resolved.branch_name == "001-feature-WP99"
        assert resolved.lane_id is None
