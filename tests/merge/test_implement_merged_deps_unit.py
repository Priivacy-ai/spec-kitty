"""Tests for implementing work packages with merged dependencies (ADR-18).

Verifies:
- Single-parent dependency that is merged (done lane) → branch from target
- Single-parent dependency that is in-progress → branch from workspace
- Multi-parent dependencies all merged (done lane) → branch from target (optimization)
- Multi-parent dependencies mixed status → create merge base
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.core.dependency_resolver import check_dependency_status
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event

pytestmark = pytest.mark.fast


def _write_wp_event(feature_dir: Path, feature_slug: str, wp_id: str, to_lane: str) -> None:
    """Write a single forced event to the event log to set a WP's lane.

    Uses force=True with from_lane="planned" so the reducer materialises
    the WP at the requested lane without requiring the full transition chain.
    """
    event = StatusEvent(
        event_id=f"01TEST{wp_id.replace('WP', '').zfill(20)}",
        feature_slug=feature_slug,
        wp_id=wp_id,
        from_lane=Lane.PLANNED,
        to_lane=Lane(to_lane),
        at="2026-01-01T00:00:00+00:00",
        actor="test-fixture",
        force=True,
        execution_mode="direct_repo",
        reason="test fixture bootstrap",
    )
    append_event(feature_dir, event)


class TestSingleParentMergedDependency:
    """Tests for single-parent dependency status detection."""

    def test_dependency_merged_uses_target_branch(self, tmp_path: Path):
        """When base WP is in 'done' lane, should branch from target branch."""
        # Setup: Create feature directory with WP01 in 'done' lane
        feature_dir = tmp_path / "kitty-specs" / "025-cli-event-log-integration"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create WP01 file (no lane in frontmatter — event log is sole authority)
        wp01_file = tasks_dir / "WP01-event-infrastructure.md"
        wp01_file.write_text(
            "---\n"
            "work_package_id: WP01\n"
            "title: Event Infrastructure\n"
            "dependencies: []\n"
            "---\n"
            "# Content\n"
        )

        # Emit event to put WP01 in 'done' lane
        _write_wp_event(feature_dir, "025-cli-event-log-integration", "WP01", "done")

        # Create WP02 depending on WP01
        wp02_file = tasks_dir / "WP02-event-logger.md"
        wp02_file.write_text(
            "---\n"
            "work_package_id: WP02\n"
            "title: Event Logger\n"
            "dependencies: [WP01]\n"
            "---\n"
            "# Content\n"
        )

        # Check dependency status
        status = check_dependency_status(feature_dir, "WP02", ["WP01"])

        # Assertions
        assert status.wp_id == "WP02"
        assert status.dependencies == ["WP01"]
        assert status.all_done is True
        assert status.lanes == {"WP01": "done"}
        assert status.is_multi_parent is False

        # Recommendation should use --base flag (but implement will detect 'done' and use target)
        recommendation = status.get_recommendation()
        assert "WP01" in recommendation
        assert "--base" in recommendation

    def test_dependency_in_progress_uses_workspace(self, tmp_path: Path):
        """When base WP is in 'in_progress' lane, should branch from workspace branch."""
        # Setup: Create feature directory with WP01 in 'in_progress' lane
        feature_dir = tmp_path / "kitty-specs" / "025-cli-event-log-integration"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create WP01 file (no lane in frontmatter — event log is sole authority)
        wp01_file = tasks_dir / "WP01-event-infrastructure.md"
        wp01_file.write_text(
            "---\n"
            "work_package_id: WP01\n"
            "title: Event Infrastructure\n"
            "dependencies: []\n"
            "---\n"
            "# Content\n"
        )

        # Emit event to put WP01 in 'in_progress' lane
        _write_wp_event(feature_dir, "025-cli-event-log-integration", "WP01", "in_progress")

        # Create WP02 depending on WP01
        wp02_file = tasks_dir / "WP02-event-logger.md"
        wp02_file.write_text(
            "---\n"
            "work_package_id: WP02\n"
            "title: Event Logger\n"
            "dependencies: [WP01]\n"
            "---\n"
            "# Content\n"
        )

        # Check dependency status
        status = check_dependency_status(feature_dir, "WP02", ["WP01"])

        # Assertions
        assert status.wp_id == "WP02"
        assert status.all_done is False
        assert status.lanes == {"WP01": "in_progress"}
        assert status.is_multi_parent is False

        # Recommendation should indicate cannot implement (but this is for testing logic)
        recommendation = status.get_recommendation()
        assert "WP01" in recommendation


class TestMultiParentAllDoneDependencies:
    """Tests for multi-parent dependencies when all are merged."""

    def test_all_dependencies_done_branches_from_target(self, tmp_path: Path):
        """When all multi-parent dependencies are 'done', should branch from target (optimization)."""
        # Setup: Create feature directory with all dependencies in 'done' lane
        feature_dir = tmp_path / "kitty-specs" / "010-workspace-per-wp"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create WP01, WP02, WP03 all in 'done' lane via event log
        for i in range(1, 4):
            wp_file = tasks_dir / f"WP0{i}-component-{i}.md"
            wp_file.write_text(
                f"---\n"
                f"work_package_id: WP0{i}\n"
                f"title: Component {i}\n"
                f"dependencies: []\n"
                f"---\n"
                f"# Content\n"
            )
            _write_wp_event(feature_dir, "010-workspace-per-wp", f"WP0{i}", "done")

        # Create WP04 depending on all three
        wp04_file = tasks_dir / "WP04-integration.md"
        wp04_file.write_text(
            "---\n"
            "work_package_id: WP04\n"
            "title: Integration\n"
            "dependencies: [WP01, WP02, WP03]\n"
            "---\n"
            "# Content\n"
        )

        # Check dependency status
        status = check_dependency_status(feature_dir, "WP04", ["WP01", "WP02", "WP03"])

        # Assertions
        assert status.wp_id == "WP04"
        assert status.dependencies == ["WP01", "WP02", "WP03"]
        assert status.all_done is True
        assert status.lanes == {"WP01": "done", "WP02": "done", "WP03": "done"}
        assert status.is_multi_parent is True

        # Should suggest merging first (but implement will detect all_done and use target)
        assert status.should_suggest_merge_first is True
        recommendation = status.get_recommendation()
        assert "merge" in recommendation.lower()

    def test_mixed_status_requires_merge_base(self, tmp_path: Path):
        """When multi-parent dependencies are mixed status, should create merge base."""
        # Setup: Create feature directory with mixed status dependencies
        feature_dir = tmp_path / "kitty-specs" / "010-workspace-per-wp"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create WP01 in 'done', WP02 in 'in_progress', WP03 in 'done' via event log
        statuses = [("WP01", "done"), ("WP02", "in_progress"), ("WP03", "done")]
        for wp_id, lane in statuses:
            wp_file = tasks_dir / f"{wp_id}-component.md"
            wp_file.write_text(
                f"---\n"
                f"work_package_id: {wp_id}\n"
                f"title: Component {wp_id}\n"
                f"dependencies: []\n"
                f"---\n"
                f"# Content\n"
            )
            _write_wp_event(feature_dir, "010-workspace-per-wp", wp_id, lane)

        # Create WP04 depending on all three
        wp04_file = tasks_dir / "WP04-integration.md"
        wp04_file.write_text(
            "---\n"
            "work_package_id: WP04\n"
            "title: Integration\n"
            "dependencies: [WP01, WP02, WP03]\n"
            "---\n"
            "# Content\n"
        )

        # Check dependency status
        status = check_dependency_status(feature_dir, "WP04", ["WP01", "WP02", "WP03"])

        # Assertions
        assert status.wp_id == "WP04"
        assert status.all_done is False
        assert status.lanes == {"WP01": "done", "WP02": "in_progress", "WP03": "done"}
        assert status.is_multi_parent is True

        # Should NOT suggest merge-first (WP02 not done)
        assert status.should_suggest_merge_first is False
        recommendation = status.get_recommendation()
        assert "WP02" in recommendation  # Should mention incomplete dependency


class TestDependencyStatusEdgeCases:
    """Tests for edge cases in dependency status detection."""

    def test_dependency_file_not_found(self, tmp_path: Path):
        """When dependency WP file doesn't exist, status should be 'unknown'."""
        # Setup: Feature directory without WP01 file
        feature_dir = tmp_path / "kitty-specs" / "025-cli-event-log-integration"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Only create WP02 (no WP01)
        wp02_file = tasks_dir / "WP02-event-logger.md"
        wp02_file.write_text(
            "---\n"
            "work_package_id: WP02\n"
            "title: Event Logger\n"
            "lane: planned\n"
            "dependencies: [WP01]\n"
            "---\n"
            "# Content\n"
        )

        # Check dependency status
        status = check_dependency_status(feature_dir, "WP02", ["WP01"])

        # Assertions
        assert status.lanes == {"WP01": "unknown"}
        assert status.all_done is False

    def test_dependency_no_lane_in_frontmatter(self, tmp_path: Path):
        """When dependency WP has no 'lane' field, status should be 'unknown'."""
        # Setup: Feature directory with WP01 missing lane field
        feature_dir = tmp_path / "kitty-specs" / "025-cli-event-log-integration"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create WP01 without lane field
        wp01_file = tasks_dir / "WP01-event-infrastructure.md"
        wp01_file.write_text(
            "---\n"
            "work_package_id: WP01\n"
            "title: Event Infrastructure\n"
            "dependencies: []\n"
            "---\n"
            "# Content\n"
        )

        # Create WP02 depending on WP01
        wp02_file = tasks_dir / "WP02-event-logger.md"
        wp02_file.write_text(
            "---\n"
            "work_package_id: WP02\n"
            "title: Event Logger\n"
            "lane: planned\n"
            "dependencies: [WP01]\n"
            "---\n"
            "# Content\n"
        )

        # Check dependency status
        status = check_dependency_status(feature_dir, "WP02", ["WP01"])

        # Assertions
        assert status.lanes == {"WP01": "unknown"}
        assert status.all_done is False

    def test_no_dependencies_returns_empty_status(self, tmp_path: Path):
        """When WP has no dependencies, status should reflect that."""
        # Setup: Feature directory with independent WP
        feature_dir = tmp_path / "kitty-specs" / "025-cli-event-log-integration"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create WP01 with no dependencies
        wp01_file = tasks_dir / "WP01-event-infrastructure.md"
        wp01_file.write_text(
            "---\n"
            "work_package_id: WP01\n"
            "title: Event Infrastructure\n"
            "lane: planned\n"
            "dependencies: []\n"
            "---\n"
            "# Content\n"
        )

        # Check dependency status
        status = check_dependency_status(feature_dir, "WP01", [])

        # Assertions
        assert status.dependencies == []
        assert status.all_done is True  # Vacuously true
        assert status.lanes == {}
        assert status.is_multi_parent is False
        assert status.should_suggest_merge_first is False

        recommendation = status.get_recommendation()
        assert "No dependencies" in recommendation
