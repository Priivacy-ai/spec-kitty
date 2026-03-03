"""Tests for the legacy bridge compatibility views.

Tests view generation from StatusSnapshot, phase-aware behavior,
round-trip consistency, and error handling.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.frontmatter import FrontmatterManager, FrontmatterError
from specify_cli.status.legacy_bridge import (
    update_all_views,
    update_frontmatter_views,
    update_tasks_md_views,
)
from specify_cli.status.models import StatusSnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_wp_file(tasks_dir: Path, wp_id: str, title: str, lane: str, *, extra_fields: dict | None = None) -> Path:
    """Create a minimal WP markdown file with frontmatter."""
    fm = FrontmatterManager()
    slug = title.lower().replace(" ", "-")
    filename = f"{wp_id}-{slug}.md"
    wp_file = tasks_dir / filename

    frontmatter: dict = {
        "work_package_id": wp_id,
        "title": title,
        "lane": lane,
        "dependencies": [],
    }
    if extra_fields:
        frontmatter.update(extra_fields)

    body = f"\n# {title}\n\nDescription for {wp_id}.\n"
    fm.write(wp_file, frontmatter, body)
    return wp_file


def create_snapshot(
    feature_slug: str,
    wps: dict[str, str],
    *,
    materialized_at: str = "2026-02-08T12:00:00+00:00",
) -> StatusSnapshot:
    """Build a StatusSnapshot from a WP ID -> lane mapping.

    Uses fixed timestamps and event IDs for deterministic testing.
    """
    work_packages: dict = {}
    summary: dict[str, int] = {}

    for wp_id, lane in wps.items():
        work_packages[wp_id] = {
            "lane": lane,
            "actor": "test-agent",
            "last_transition_at": materialized_at,
            "last_event_id": f"ULID_{wp_id}",
            "force_count": 0,
        }
        summary[lane] = summary.get(lane, 0) + 1

    return StatusSnapshot(
        feature_slug=feature_slug,
        materialized_at=materialized_at,
        event_count=len(wps),
        last_event_id="ULID_LAST" if wps else None,
        work_packages=work_packages,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Frontmatter view tests
# ---------------------------------------------------------------------------

class TestUpdateFrontmatterViews:
    """Tests for update_frontmatter_views()."""

    def test_update_frontmatter_changes_lane(self, tmp_path: Path) -> None:
        """WP01.md has lane: planned, snapshot says for_review, after update
        frontmatter reads for_review."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        create_wp_file(tasks_dir, "WP01", "Test Task", "planned")

        snapshot = create_snapshot("034-test-feature", {"WP01": "for_review"})
        update_frontmatter_views(feature_dir, snapshot)

        fm = FrontmatterManager()
        frontmatter, _ = fm.read(tasks_dir / "WP01-test-task.md")
        assert frontmatter["lane"] == "for_review"

    def test_update_frontmatter_no_change_when_matching(self, tmp_path: Path) -> None:
        """WP01.md already has correct lane, no file write occurs."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        wp_file = create_wp_file(tasks_dir, "WP01", "Test Task", "for_review")
        original_mtime = wp_file.stat().st_mtime_ns

        snapshot = create_snapshot("034-test-feature", {"WP01": "for_review"})

        # Small delay to ensure mtime would differ if file were written
        import time
        time.sleep(0.01)

        update_frontmatter_views(feature_dir, snapshot)

        # File should not have been rewritten
        assert wp_file.stat().st_mtime_ns == original_mtime

    def test_update_frontmatter_multiple_wps(self, tmp_path: Path) -> None:
        """Snapshot has WP01, WP02, WP03 at different lanes, all updated."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        create_wp_file(tasks_dir, "WP01", "First Task", "planned")
        create_wp_file(tasks_dir, "WP02", "Second Task", "planned")
        create_wp_file(tasks_dir, "WP03", "Third Task", "in_progress")

        snapshot = create_snapshot("034-test-feature", {
            "WP01": "for_review",
            "WP02": "done",
            "WP03": "blocked",
        })

        update_frontmatter_views(feature_dir, snapshot)

        fm = FrontmatterManager()
        fm1, _ = fm.read(tasks_dir / "WP01-first-task.md")
        fm2, _ = fm.read(tasks_dir / "WP02-second-task.md")
        fm3, _ = fm.read(tasks_dir / "WP03-third-task.md")

        assert fm1["lane"] == "for_review"
        assert fm2["lane"] == "done"
        assert fm3["lane"] == "blocked"

    def test_update_frontmatter_missing_wp_file(self, tmp_path: Path, caplog) -> None:
        """Snapshot has WP04 but no WP04-*.md file exists, warning logged,
        other WPs still updated."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        create_wp_file(tasks_dir, "WP01", "Test Task", "planned")

        snapshot = create_snapshot("034-test-feature", {
            "WP01": "for_review",
            "WP04": "done",
        })

        with caplog.at_level("WARNING"):
            update_frontmatter_views(feature_dir, snapshot)

        # WP01 should still be updated
        fm = FrontmatterManager()
        fm1, _ = fm.read(tasks_dir / "WP01-test-task.md")
        assert fm1["lane"] == "for_review"

        # Warning should be logged for WP04
        assert any("WP04" in record.message for record in caplog.records)

    def test_update_frontmatter_preserves_other_fields(self, tmp_path: Path) -> None:
        """Frontmatter has title, assignee, etc.; only lane is updated."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        create_wp_file(
            tasks_dir, "WP01", "Test Task", "planned",
            extra_fields={
                "assignee": "alice",
                "agent": "claude",
                "review_status": "",
                "subtasks": ["T001", "T002"],
            },
        )

        snapshot = create_snapshot("034-test-feature", {"WP01": "for_review"})
        update_frontmatter_views(feature_dir, snapshot)

        fm = FrontmatterManager()
        frontmatter, _ = fm.read(tasks_dir / "WP01-test-task.md")

        assert frontmatter["lane"] == "for_review"
        assert frontmatter["title"] == "Test Task"
        assert frontmatter["assignee"] == "alice"
        assert frontmatter["agent"] == "claude"
        assert frontmatter["subtasks"] == ["T001", "T002"]

    def test_update_frontmatter_tasks_dir_missing(self, tmp_path: Path, caplog) -> None:
        """Feature dir has no tasks/ subdirectory, warning logged."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        feature_dir.mkdir(parents=True)
        # No tasks/ dir

        snapshot = create_snapshot("034-test-feature", {"WP01": "for_review"})

        with caplog.at_level("WARNING"):
            update_frontmatter_views(feature_dir, snapshot)

        assert any("Tasks directory not found" in record.message for record in caplog.records)

    def test_update_frontmatter_empty_snapshot(self, tmp_path: Path) -> None:
        """Snapshot with empty work_packages dict, no WPs to update."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        create_wp_file(tasks_dir, "WP01", "Test Task", "planned")

        snapshot = create_snapshot("034-test-feature", {})
        update_frontmatter_views(feature_dir, snapshot)

        # WP01 should be unchanged
        fm = FrontmatterManager()
        fm1, _ = fm.read(tasks_dir / "WP01-test-task.md")
        assert fm1["lane"] == "planned"

    def test_update_frontmatter_wp_with_no_lane_in_snapshot(self, tmp_path: Path) -> None:
        """WP state in snapshot has no 'lane' key, skip it."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        create_wp_file(tasks_dir, "WP01", "Test Task", "planned")

        # Create a snapshot with a WP state that has no lane key
        snapshot = StatusSnapshot(
            feature_slug="034-test-feature",
            materialized_at="2026-02-08T12:00:00+00:00",
            event_count=1,
            last_event_id="ULID_01",
            work_packages={"WP01": {"actor": "test", "force_count": 0}},
            summary={},
        )

        update_frontmatter_views(feature_dir, snapshot)

        fm = FrontmatterManager()
        fm1, _ = fm.read(tasks_dir / "WP01-test-task.md")
        assert fm1["lane"] == "planned"  # Unchanged

    def test_update_frontmatter_wp_file_only_frontmatter(self, tmp_path: Path) -> None:
        """WP file has no body (only frontmatter)."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        fm = FrontmatterManager()
        wp_file = tasks_dir / "WP01-test.md"
        frontmatter = {
            "work_package_id": "WP01",
            "title": "Test",
            "lane": "planned",
            "dependencies": [],
        }
        fm.write(wp_file, frontmatter, "")

        snapshot = create_snapshot("034-test-feature", {"WP01": "done"})
        update_frontmatter_views(feature_dir, snapshot)

        fm_result, body = fm.read(wp_file)
        assert fm_result["lane"] == "done"

    def test_update_frontmatter_alias_replaced_by_canonical(self, tmp_path: Path) -> None:
        """WP file has lane: doing (old alias), update to canonical value from snapshot."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        create_wp_file(tasks_dir, "WP01", "Test Task", "doing")

        snapshot = create_snapshot("034-test-feature", {"WP01": "in_progress"})
        update_frontmatter_views(feature_dir, snapshot)

        fm = FrontmatterManager()
        fm1, _ = fm.read(tasks_dir / "WP01-test-task.md")
        assert fm1["lane"] == "in_progress"


# ---------------------------------------------------------------------------
# Tasks.md view tests
# ---------------------------------------------------------------------------

class TestUpdateTasksMdViews:
    """Tests for update_tasks_md_views()."""

    def test_update_tasks_md_no_file(self, tmp_path: Path) -> None:
        """tasks.md does not exist, no error."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        feature_dir.mkdir(parents=True)

        snapshot = create_snapshot("034-test-feature", {"WP01": "done"})
        # Should not raise
        update_tasks_md_views(feature_dir, snapshot)

    def test_update_tasks_md_appends_generated_block(self, tmp_path: Path) -> None:
        """tasks.md gets a generated canonical status block."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        feature_dir.mkdir(parents=True)

        tasks_md = feature_dir / "tasks.md"
        original_content = "# Tasks\n\n## WP01: Do Stuff\n\n- [ ] Subtask 1\n- [x] Subtask 2\n"
        tasks_md.write_text(original_content, encoding="utf-8")

        snapshot = create_snapshot("034-test-feature", {"WP01": "done"})
        update_tasks_md_views(feature_dir, snapshot)

        updated = tasks_md.read_text(encoding="utf-8")
        assert "<!-- status-model:start -->" in updated
        assert "- WP01: done" in updated
        assert "<!-- status-model:end -->" in updated

    def test_update_tasks_md_replaces_existing_generated_block(self, tmp_path: Path) -> None:
        """Existing generated block is replaced, not duplicated."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        feature_dir.mkdir(parents=True)
        tasks_md = feature_dir / "tasks.md"
        tasks_md.write_text(
            "\n".join(
                [
                    "# Tasks",
                    "",
                    "<!-- status-model:start -->",
                    "## Canonical Status (Generated)",
                    "- WP01: planned",
                    "<!-- status-model:end -->",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        snapshot = create_snapshot("034-test-feature", {"WP01": "in_progress"})
        update_tasks_md_views(feature_dir, snapshot)
        updated = tasks_md.read_text(encoding="utf-8")
        assert updated.count("<!-- status-model:start -->") == 1
        assert "- WP01: in_progress" in updated
        assert "- WP01: planned" not in updated

    def test_update_tasks_md_empty_file(self, tmp_path: Path) -> None:
        """tasks.md is empty, generated block is written."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        feature_dir.mkdir(parents=True)

        tasks_md = feature_dir / "tasks.md"
        tasks_md.write_text("", encoding="utf-8")

        snapshot = create_snapshot("034-test-feature", {"WP01": "done"})
        update_tasks_md_views(feature_dir, snapshot)

        updated = tasks_md.read_text(encoding="utf-8")
        assert "<!-- status-model:start -->" in updated
        assert "- WP01: done" in updated


# ---------------------------------------------------------------------------
# Phase-aware behavior tests
# ---------------------------------------------------------------------------

class TestPhaseAwareBehavior:
    """Tests for update_all_views() phase-aware routing."""

    @patch("specify_cli.status.legacy_bridge.resolve_phase")
    def test_phase_0_noop(self, mock_resolve_phase, tmp_path: Path) -> None:
        """Phase 0: no file modifications."""
        mock_resolve_phase.return_value = (0, "test override")

        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        wp_file = create_wp_file(tasks_dir, "WP01", "Test Task", "planned")
        original_mtime = wp_file.stat().st_mtime_ns

        snapshot = create_snapshot("034-test-feature", {"WP01": "for_review"})

        import time
        time.sleep(0.01)

        update_all_views(feature_dir, snapshot, repo_root=tmp_path)

        # File should NOT have been modified
        assert wp_file.stat().st_mtime_ns == original_mtime

        # Verify frontmatter still says planned
        fm = FrontmatterManager()
        fm1, _ = fm.read(wp_file)
        assert fm1["lane"] == "planned"

    @patch("specify_cli.status.legacy_bridge.resolve_phase")
    def test_phase_1_updates_views(self, mock_resolve_phase, tmp_path: Path) -> None:
        """Phase 1: frontmatter updated."""
        mock_resolve_phase.return_value = (1, "dual-write")

        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        create_wp_file(tasks_dir, "WP01", "Test Task", "planned")

        snapshot = create_snapshot("034-test-feature", {"WP01": "for_review"})
        update_all_views(feature_dir, snapshot, repo_root=tmp_path)

        fm = FrontmatterManager()
        fm1, _ = fm.read(tasks_dir / "WP01-test-task.md")
        assert fm1["lane"] == "for_review"

    @patch("specify_cli.status.legacy_bridge.resolve_phase")
    def test_phase_2_updates_views(self, mock_resolve_phase, tmp_path: Path) -> None:
        """Phase 2: frontmatter updated (views are regenerated, not read as authority)."""
        mock_resolve_phase.return_value = (2, "read cutover")

        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        create_wp_file(tasks_dir, "WP01", "Test Task", "planned")

        snapshot = create_snapshot("034-test-feature", {"WP01": "done"})
        update_all_views(feature_dir, snapshot, repo_root=tmp_path)

        fm = FrontmatterManager()
        fm1, _ = fm.read(tasks_dir / "WP01-test-task.md")
        assert fm1["lane"] == "done"

    @patch("specify_cli.status.legacy_bridge.resolve_phase")
    def test_repo_root_derived_from_feature_dir(self, mock_resolve_phase, tmp_path: Path) -> None:
        """When repo_root is None, it is derived from feature_dir."""
        mock_resolve_phase.return_value = (1, "dual-write")

        repo_root = tmp_path
        feature_dir = repo_root / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        create_wp_file(tasks_dir, "WP01", "Test Task", "planned")

        snapshot = create_snapshot("034-test-feature", {"WP01": "for_review"})

        # Pass repo_root=None explicitly so it derives from feature_dir
        update_all_views(feature_dir, snapshot, repo_root=None)

        # Verify resolve_phase was called with derived repo_root
        mock_resolve_phase.assert_called_once_with(repo_root, "034-test-feature")

    @patch("specify_cli.status.legacy_bridge.resolve_phase")
    def test_resolve_phase_error_propagates(self, mock_resolve_phase, tmp_path: Path) -> None:
        """If resolve_phase() fails, error propagates without catching."""
        mock_resolve_phase.side_effect = RuntimeError("config corrupted")

        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        create_wp_file(tasks_dir, "WP01", "Test Task", "planned")

        snapshot = create_snapshot("034-test-feature", {"WP01": "for_review"})

        with pytest.raises(RuntimeError, match="config corrupted"):
            update_all_views(feature_dir, snapshot, repo_root=tmp_path)


# ---------------------------------------------------------------------------
# Round-trip consistency tests
# ---------------------------------------------------------------------------

class TestRoundTripConsistency:
    """Tests for round-trip read/write consistency."""

    def test_round_trip_consistency(self, tmp_path: Path) -> None:
        """Create snapshot, update views, read frontmatter back, verify lane
        values match snapshot."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        create_wp_file(tasks_dir, "WP01", "First Task", "planned")
        create_wp_file(tasks_dir, "WP02", "Second Task", "planned")
        create_wp_file(tasks_dir, "WP03", "Third Task", "planned")

        expected = {
            "WP01": "for_review",
            "WP02": "done",
            "WP03": "in_progress",
        }
        snapshot = create_snapshot("034-test-feature", expected)
        update_frontmatter_views(feature_dir, snapshot)

        fm = FrontmatterManager()
        for wp_id, expected_lane in expected.items():
            slug = {
                "WP01": "first-task",
                "WP02": "second-task",
                "WP03": "third-task",
            }[wp_id]
            frontmatter, _ = fm.read(tasks_dir / f"{wp_id}-{slug}.md")
            assert frontmatter["lane"] == expected_lane, (
                f"Round-trip mismatch for {wp_id}: "
                f"expected {expected_lane}, got {frontmatter['lane']}"
            )

    def test_idempotent_update(self, tmp_path: Path) -> None:
        """Call update_all_views twice with same snapshot, verify no changes
        on second call."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        wp_file = create_wp_file(tasks_dir, "WP01", "Test Task", "planned")

        snapshot = create_snapshot("034-test-feature", {"WP01": "for_review"})

        # First update
        update_frontmatter_views(feature_dir, snapshot)

        fm = FrontmatterManager()
        fm1, _ = fm.read(wp_file)
        assert fm1["lane"] == "for_review"

        # Record mtime after first update
        import time
        time.sleep(0.01)
        mtime_after_first = wp_file.stat().st_mtime_ns

        # Second update with same snapshot
        time.sleep(0.01)
        update_frontmatter_views(feature_dir, snapshot)

        # File should NOT have been rewritten
        assert wp_file.stat().st_mtime_ns == mtime_after_first


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Tests for error propagation and edge cases."""

    def test_frontmatter_write_error_propagates(self, tmp_path: Path) -> None:
        """Simulate write failure, verify error is raised (not silently swallowed)."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        create_wp_file(tasks_dir, "WP01", "Test Task", "planned")

        snapshot = create_snapshot("034-test-feature", {"WP01": "for_review"})

        # Make the file read-only to cause a write error
        wp_file = tasks_dir / "WP01-test-task.md"
        wp_file.chmod(0o444)

        try:
            with pytest.raises(PermissionError):
                update_frontmatter_views(feature_dir, snapshot)
        finally:
            # Restore permissions for cleanup
            wp_file.chmod(0o644)

    def test_frontmatter_read_error_propagates(self, tmp_path: Path) -> None:
        """WP file with malformed frontmatter raises FrontmatterError."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Write a malformed WP file (no closing ---)
        wp_file = tasks_dir / "WP01-bad-frontmatter.md"
        wp_file.write_text("---\nlane: planned\n# No closing delimiter\n", encoding="utf-8")

        snapshot = create_snapshot("034-test-feature", {"WP01": "done"})

        with pytest.raises(FrontmatterError):
            update_frontmatter_views(feature_dir, snapshot)

    def test_feature_dir_does_not_exist(self, tmp_path: Path) -> None:
        """Feature directory does not exist, tasks dir will not exist, warning logged."""
        feature_dir = tmp_path / "kitty-specs" / "nonexistent-feature"
        snapshot = create_snapshot("nonexistent-feature", {"WP01": "done"})

        # Should not raise, just log a warning
        update_frontmatter_views(feature_dir, snapshot)

    def test_multiple_wp_files_uses_first_with_warning(self, tmp_path: Path, caplog) -> None:
        """Multiple task files match WP01 glob, uses first, warns about ambiguity."""
        feature_dir = tmp_path / "kitty-specs" / "034-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create two files for WP01
        create_wp_file(tasks_dir, "WP01", "first-match", "planned")
        create_wp_file(tasks_dir, "WP01", "second-match", "planned")

        snapshot = create_snapshot("034-test-feature", {"WP01": "done"})

        with caplog.at_level("WARNING"):
            update_frontmatter_views(feature_dir, snapshot)

        # Warning about multiple files
        assert any("Multiple task files" in record.message for record in caplog.records)

        # At least one file should have been updated
        fm = FrontmatterManager()
        wp_files = list(tasks_dir.glob("WP01-*.md"))
        updated_count = 0
        for f in wp_files:
            fm_data, _ = fm.read(f)
            if fm_data["lane"] == "done":
                updated_count += 1
        assert updated_count >= 1
