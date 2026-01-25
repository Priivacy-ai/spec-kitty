"""Workspace context integrity tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.workspace_context import (
    WorkspaceContext,
    find_orphaned_contexts,
    list_contexts,
    load_context,
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
