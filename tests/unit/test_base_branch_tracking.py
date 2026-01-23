"""Tests for base branch tracking in frontmatter and workspace context.

Verifies Phase 1 implementation:
- base_branch and base_commit written to WP frontmatter
- created_at timestamp added
- Workspace context file created in .kittify/workspaces/
- Context file readable from worktrees
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from specify_cli.frontmatter import read_frontmatter
from specify_cli.workspace_context import (
    WorkspaceContext,
    cleanup_orphaned_contexts,
    delete_context,
    find_orphaned_contexts,
    get_context_path,
    list_contexts,
    load_context,
    save_context,
)


class TestWorkspaceContext:
    """Tests for WorkspaceContext dataclass and persistence."""

    def test_context_to_dict(self):
        """Test context serialization to dict."""
        context = WorkspaceContext(
            wp_id="WP02",
            feature_slug="010-feature",
            worktree_path=".worktrees/010-feature-WP02",
            branch_name="010-feature-WP02",
            base_branch="010-feature-WP01",
            base_commit="abc123def456",
            dependencies=["WP01"],
            created_at="2026-01-23T10:00:00Z",
            created_by="implement-command",
            vcs_backend="git",
        )

        data = context.to_dict()

        assert data["wp_id"] == "WP02"
        assert data["base_branch"] == "010-feature-WP01"
        assert data["base_commit"] == "abc123def456"
        assert data["dependencies"] == ["WP01"]

    def test_context_from_dict(self):
        """Test context deserialization from dict."""
        data = {
            "wp_id": "WP02",
            "feature_slug": "010-feature",
            "worktree_path": ".worktrees/010-feature-WP02",
            "branch_name": "010-feature-WP02",
            "base_branch": "010-feature-WP01",
            "base_commit": "abc123def456",
            "dependencies": ["WP01"],
            "created_at": "2026-01-23T10:00:00Z",
            "created_by": "implement-command",
            "vcs_backend": "git",
        }

        context = WorkspaceContext.from_dict(data)

        assert context.wp_id == "WP02"
        assert context.base_branch == "010-feature-WP01"
        assert context.dependencies == ["WP01"]

    def test_context_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        original = WorkspaceContext(
            wp_id="WP03",
            feature_slug="010-feature",
            worktree_path=".worktrees/010-feature-WP03",
            branch_name="010-feature-WP03",
            base_branch="main",
            base_commit="fedcba987654",
            dependencies=[],
            created_at="2026-01-23T11:00:00Z",
            created_by="implement-command",
            vcs_backend="git",
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = WorkspaceContext.from_dict(data)

        assert restored == original


class TestWorkspaceContextPersistence:
    """Tests for saving/loading workspace context files."""

    def test_save_and_load_context(self, tmp_path: Path):
        """Test saving and loading context file."""
        # Create context
        context = WorkspaceContext(
            wp_id="WP01",
            feature_slug="015-jj-integration",
            worktree_path=".worktrees/015-jj-integration-WP01",
            branch_name="015-jj-integration-WP01",
            base_branch="main",
            base_commit="abc123",
            dependencies=[],
            created_at="2026-01-23T10:00:00Z",
            created_by="implement-command",
            vcs_backend="git",
        )

        # Save context
        context_path = save_context(tmp_path, context)

        # Verify file created
        assert context_path.exists()
        assert context_path.name == "015-jj-integration-WP01.json"

        # Load context
        loaded = load_context(tmp_path, "015-jj-integration-WP01")

        assert loaded is not None
        assert loaded.wp_id == "WP01"
        assert loaded.base_branch == "main"
        assert loaded.base_commit == "abc123"

    def test_load_nonexistent_context(self, tmp_path: Path):
        """Test loading context that doesn't exist."""
        loaded = load_context(tmp_path, "nonexistent-WP99")
        assert loaded is None

    def test_load_malformed_context(self, tmp_path: Path):
        """Test loading malformed JSON."""
        # Create .kittify/workspaces/ directory
        workspaces_dir = tmp_path / ".kittify" / "workspaces"
        workspaces_dir.mkdir(parents=True, exist_ok=True)

        # Write invalid JSON
        context_file = workspaces_dir / "malformed-WP01.json"
        context_file.write_text("{invalid json}", encoding="utf-8")

        # Should return None for malformed file
        loaded = load_context(tmp_path, "malformed-WP01")
        assert loaded is None

    def test_delete_context(self, tmp_path: Path):
        """Test deleting context file."""
        # Create context
        context = WorkspaceContext(
            wp_id="WP01",
            feature_slug="010-feature",
            worktree_path=".worktrees/010-feature-WP01",
            branch_name="010-feature-WP01",
            base_branch="main",
            base_commit="abc123",
            dependencies=[],
            created_at="2026-01-23T10:00:00Z",
            created_by="implement-command",
            vcs_backend="git",
        )

        save_context(tmp_path, context)

        # Delete context
        deleted = delete_context(tmp_path, "010-feature-WP01")
        assert deleted is True

        # Verify deleted
        loaded = load_context(tmp_path, "010-feature-WP01")
        assert loaded is None

        # Delete again (should return False)
        deleted_again = delete_context(tmp_path, "010-feature-WP01")
        assert deleted_again is False

    def test_list_contexts(self, tmp_path: Path):
        """Test listing all workspace contexts."""
        # Create multiple contexts
        contexts = [
            WorkspaceContext(
                wp_id=f"WP0{i}",
                feature_slug="010-feature",
                worktree_path=f".worktrees/010-feature-WP0{i}",
                branch_name=f"010-feature-WP0{i}",
                base_branch="main" if i == 1 else f"010-feature-WP0{i-1}",
                base_commit=f"commit{i}",
                dependencies=[] if i == 1 else [f"WP0{i-1}"],
                created_at="2026-01-23T10:00:00Z",
                created_by="implement-command",
                vcs_backend="git",
            )
            for i in range(1, 4)
        ]

        for ctx in contexts:
            save_context(tmp_path, ctx)

        # List contexts
        loaded_contexts = list_contexts(tmp_path)

        assert len(loaded_contexts) == 3
        assert all(ctx.feature_slug == "010-feature" for ctx in loaded_contexts)

    def test_list_contexts_empty(self, tmp_path: Path):
        """Test listing contexts when none exist."""
        loaded = list_contexts(tmp_path)
        assert loaded == []


class TestOrphanedContexts:
    """Tests for finding and cleaning up orphaned contexts."""

    def test_find_orphaned_contexts(self, tmp_path: Path):
        """Test finding contexts for deleted workspaces."""
        # Create context for non-existent workspace
        context = WorkspaceContext(
            wp_id="WP01",
            feature_slug="010-feature",
            worktree_path=".worktrees/010-feature-WP01",
            branch_name="010-feature-WP01",
            base_branch="main",
            base_commit="abc123",
            dependencies=[],
            created_at="2026-01-23T10:00:00Z",
            created_by="implement-command",
            vcs_backend="git",
        )

        save_context(tmp_path, context)

        # Find orphaned (worktree doesn't exist)
        orphaned = find_orphaned_contexts(tmp_path)

        assert len(orphaned) == 1
        assert orphaned[0][0] == "010-feature-WP01"
        assert orphaned[0][1].wp_id == "WP01"

    def test_find_orphaned_with_existing_workspace(self, tmp_path: Path):
        """Test that existing workspaces are not considered orphaned."""
        # Create worktree directory
        worktree_path = tmp_path / ".worktrees" / "010-feature-WP01"
        worktree_path.mkdir(parents=True, exist_ok=True)

        # Create context
        context = WorkspaceContext(
            wp_id="WP01",
            feature_slug="010-feature",
            worktree_path=".worktrees/010-feature-WP01",
            branch_name="010-feature-WP01",
            base_branch="main",
            base_commit="abc123",
            dependencies=[],
            created_at="2026-01-23T10:00:00Z",
            created_by="implement-command",
            vcs_backend="git",
        )

        save_context(tmp_path, context)

        # Find orphaned (should be empty - workspace exists)
        orphaned = find_orphaned_contexts(tmp_path)

        assert len(orphaned) == 0

    def test_cleanup_orphaned_contexts(self, tmp_path: Path):
        """Test cleaning up orphaned context files."""
        # Create multiple orphaned contexts
        for i in range(1, 4):
            context = WorkspaceContext(
                wp_id=f"WP0{i}",
                feature_slug="010-feature",
                worktree_path=f".worktrees/010-feature-WP0{i}",
                branch_name=f"010-feature-WP0{i}",
                base_branch="main",
                base_commit=f"commit{i}",
                dependencies=[],
                created_at="2026-01-23T10:00:00Z",
                created_by="implement-command",
                vcs_backend="git",
            )
            save_context(tmp_path, context)

        # Cleanup orphaned
        cleaned = cleanup_orphaned_contexts(tmp_path)

        assert cleaned == 3
        assert len(list_contexts(tmp_path)) == 0


class TestBaseBranchInFrontmatter:
    """Tests for base_branch and base_commit in WP frontmatter."""

    def test_frontmatter_field_order_includes_base_fields(self):
        """Verify frontmatter schema includes base tracking fields."""
        from specify_cli.frontmatter import FrontmatterManager

        manager = FrontmatterManager()

        # Check that base_branch and base_commit are in field order
        assert "base_branch" in manager.WP_FIELD_ORDER
        assert "base_commit" in manager.WP_FIELD_ORDER
        assert "created_at" in manager.WP_FIELD_ORDER

        # Check order: dependencies should come before base_branch
        deps_idx = manager.WP_FIELD_ORDER.index("dependencies")
        base_branch_idx = manager.WP_FIELD_ORDER.index("base_branch")
        base_commit_idx = manager.WP_FIELD_ORDER.index("base_commit")
        created_at_idx = manager.WP_FIELD_ORDER.index("created_at")

        assert deps_idx < base_branch_idx
        assert base_branch_idx < base_commit_idx
        assert base_commit_idx < created_at_idx

    def test_write_base_tracking_to_frontmatter(self, tmp_path: Path):
        """Test writing base tracking fields to WP frontmatter."""
        from specify_cli.frontmatter import update_fields, write_frontmatter

        # Create WP file
        wp_file = tmp_path / "WP02-build-api.md"
        frontmatter = {
            "work_package_id": "WP02",
            "title": "Build API",
            "lane": "planned",
            "dependencies": ["WP01"],
        }
        body = "\n## Implementation\n\nBuild the REST API.\n"

        write_frontmatter(wp_file, frontmatter, body)

        # Update with base tracking
        update_fields(wp_file, {
            "base_branch": "010-feature-WP01",
            "base_commit": "abc123def456",
            "created_at": "2026-01-23T10:00:00Z",
        })

        # Read and verify
        updated_frontmatter, _ = read_frontmatter(wp_file)

        assert updated_frontmatter["base_branch"] == "010-feature-WP01"
        assert updated_frontmatter["base_commit"] == "abc123def456"
        assert updated_frontmatter["created_at"] == "2026-01-23T10:00:00Z"

    def test_read_base_tracking_from_frontmatter(self, tmp_path: Path):
        """Test reading base tracking fields from WP frontmatter."""
        from specify_cli.frontmatter import get_field, write_frontmatter

        # Create WP file with base tracking
        wp_file = tmp_path / "WP03-write-docs.md"
        frontmatter = {
            "work_package_id": "WP03",
            "title": "Write Documentation",
            "lane": "doing",
            "dependencies": ["WP02"],
            "base_branch": "010-feature-WP02",
            "base_commit": "fedcba987654",
            "created_at": "2026-01-23T11:00:00Z",
        }
        body = "\n## Documentation Tasks\n\nWrite the docs.\n"

        write_frontmatter(wp_file, frontmatter, body)

        # Read individual fields
        base_branch = get_field(wp_file, "base_branch")
        base_commit = get_field(wp_file, "base_commit")
        created_at = get_field(wp_file, "created_at")

        assert base_branch == "010-feature-WP02"
        assert base_commit == "fedcba987654"
        assert created_at == "2026-01-23T11:00:00Z"


class TestIntegrationBaseBranchTracking:
    """Integration tests for complete base branch tracking workflow."""

    def test_context_file_readable_from_worktree(self, tmp_path: Path):
        """Test that context file is readable from worktree via relative path."""
        # Create workspace directory structure
        worktree_path = tmp_path / ".worktrees" / "010-feature-WP02"
        worktree_path.mkdir(parents=True, exist_ok=True)

        # Save context in main repo
        context = WorkspaceContext(
            wp_id="WP02",
            feature_slug="010-feature",
            worktree_path=".worktrees/010-feature-WP02",
            branch_name="010-feature-WP02",
            base_branch="010-feature-WP01",
            base_commit="abc123",
            dependencies=["WP01"],
            created_at="2026-01-23T10:00:00Z",
            created_by="implement-command",
            vcs_backend="git",
        )

        save_context(tmp_path, context)

        # From worktree, access context via ../../.kittify/workspaces/
        context_from_worktree = worktree_path / ".." / ".." / ".kittify" / "workspaces" / "010-feature-WP02.json"
        assert context_from_worktree.exists()

        # Read and verify
        data = json.loads(context_from_worktree.read_text(encoding="utf-8"))
        assert data["wp_id"] == "WP02"
        assert data["base_branch"] == "010-feature-WP01"

    def test_frontmatter_and_context_consistency(self, tmp_path: Path):
        """Test that frontmatter and context have consistent base tracking."""
        from specify_cli.frontmatter import read_frontmatter, write_frontmatter

        # Create WP file with base tracking
        wp_file = tmp_path / "kitty-specs" / "010-feature" / "tasks" / "WP02-api.md"
        wp_file.parent.mkdir(parents=True, exist_ok=True)

        frontmatter = {
            "work_package_id": "WP02",
            "title": "Build API",
            "lane": "doing",
            "dependencies": ["WP01"],
            "base_branch": "010-feature-WP01",
            "base_commit": "abc123def456",
            "created_at": "2026-01-23T10:00:00Z",
        }
        body = "\n## Tasks\n\n- Implement endpoints\n"

        write_frontmatter(wp_file, frontmatter, body)

        # Create matching workspace context
        context = WorkspaceContext(
            wp_id="WP02",
            feature_slug="010-feature",
            worktree_path=".worktrees/010-feature-WP02",
            branch_name="010-feature-WP02",
            base_branch="010-feature-WP01",
            base_commit="abc123def456",
            dependencies=["WP01"],
            created_at="2026-01-23T10:00:00Z",
            created_by="implement-command",
            vcs_backend="git",
        )

        save_context(tmp_path, context)

        # Read and verify consistency
        fm, _ = read_frontmatter(wp_file)
        loaded_ctx = load_context(tmp_path, "010-feature-WP02")

        assert fm["base_branch"] == loaded_ctx.base_branch
        assert fm["base_commit"] == loaded_ctx.base_commit
        assert fm["created_at"] == loaded_ctx.created_at
        assert fm["dependencies"] == loaded_ctx.dependencies
