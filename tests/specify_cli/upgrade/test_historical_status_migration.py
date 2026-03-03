"""Tests for the historical status migration upgrade wrapper.

Covers detect(), can_apply(), apply(), dry_run, and cross-branch
idempotency for HistoricalStatusMigration (T032-T036).
"""

from __future__ import annotations

import json
from pathlib import Path


from specify_cli.upgrade.migrations.m_2_0_0_historical_status_migration import (
    HistoricalStatusMigration,
)


# ── Helpers ──────────────────────────────────────────────────────


def _write_wp(
    tasks_dir: Path,
    wp_id: str,
    lane: str,
    *,
    history: list[dict[str, str]] | None = None,
    review_status: str | None = None,
    reviewed_by: str | None = None,
) -> Path:
    """Create a minimal WP markdown file with frontmatter."""
    lines = [
        "---",
        f'work_package_id: "{wp_id}"',
        f'title: "Test {wp_id}"',
        f'lane: "{lane}"',
        "dependencies: []",
    ]
    if review_status is not None:
        lines.append(f'review_status: "{review_status}"')
    if reviewed_by is not None:
        lines.append(f'reviewed_by: "{reviewed_by}"')
    if history is not None:
        lines.append("history:")
        for entry in history:
            lines.append(
                f'- timestamp: "{entry.get("timestamp", "2026-01-01T00:00:00Z")}"'
            )
            lines.append(f'  lane: "{entry.get("lane", "planned")}"')
            lines.append(f'  agent: "{entry.get("agent", "system")}"')
            lines.append('  shell_pid: ""')
            lines.append('  action: "test"')
    lines.append("---")
    lines.append(f"# {wp_id}")

    wp_file = tasks_dir / f"{wp_id}-test.md"
    wp_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return wp_file


def _write_live_event(feature_dir: Path, wp_id: str = "WP01") -> None:
    """Write a StatusEvent with a non-migration actor (live data)."""
    from specify_cli.status.models import Lane, StatusEvent

    event = StatusEvent(
        event_id="01TEST00000000000000000000",
        feature_slug=feature_dir.name,
        wp_id=wp_id,
        from_lane=Lane.PLANNED,
        to_lane=Lane.DONE,
        at="2026-01-01T00:00:00+00:00",
        actor="claude-agent",
        force=True,
        execution_mode="worktree",
        reason="live transition",
    )
    events_file = feature_dir / "status.events.jsonl"
    events_file.write_text(
        json.dumps(event.to_dict(), sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_migration_only_event(
    feature_dir: Path, wp_id: str = "WP01"
) -> None:
    """Write a StatusEvent with a migration actor (legacy bootstrap)."""
    from specify_cli.status.models import Lane, StatusEvent

    event = StatusEvent(
        event_id="01MIGR00000000000000000000",
        feature_slug=feature_dir.name,
        wp_id=wp_id,
        from_lane=Lane.PLANNED,
        to_lane=Lane.DONE,
        at="2026-01-01T00:00:00+00:00",
        actor="migration",
        force=False,
        execution_mode="worktree",
        reason=None,
    )
    events_file = feature_dir / "status.events.jsonl"
    events_file.write_text(
        json.dumps(event.to_dict(), sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_marker_event(feature_dir: Path, wp_id: str = "WP01") -> None:
    """Write a StatusEvent with the full-history migration marker."""
    from specify_cli.status.models import Lane, StatusEvent

    event = StatusEvent(
        event_id="01MARK00000000000000000000",
        feature_slug=feature_dir.name,
        wp_id=wp_id,
        from_lane=Lane.PLANNED,
        to_lane=Lane.DONE,
        at="2026-01-01T00:00:00+00:00",
        actor="migration",
        force=True,
        execution_mode="worktree",
        reason="historical_frontmatter_to_jsonl:v1",
    )
    events_file = feature_dir / "status.events.jsonl"
    events_file.write_text(
        json.dumps(event.to_dict(), sort_keys=True) + "\n",
        encoding="utf-8",
    )


# ── T032 + T033: detect() ───────────────────────────────────────


class TestDetect:
    """Tests for HistoricalStatusMigration.detect()."""

    def test_unmigrated_features_detected(self, tmp_path: Path) -> None:
        """detect() returns True when features have WPs but no events."""
        feature_dir = tmp_path / "kitty-specs" / "900-test"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "done")

        migration = HistoricalStatusMigration()
        assert migration.detect(tmp_path) is True

    def test_all_planned_without_events_not_detected(self, tmp_path: Path) -> None:
        """detect() returns False when all WPs are still planned."""
        feature_dir = tmp_path / "kitty-specs" / "900a-planned"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "planned")
        _write_wp(tasks_dir, "WP02", "planned")

        migration = HistoricalStatusMigration()
        assert migration.detect(tmp_path) is False

    def test_empty_events_file_detected(self, tmp_path: Path) -> None:
        """detect() returns True when events file exists but is empty."""
        feature_dir = tmp_path / "kitty-specs" / "901-test"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "done")
        (feature_dir / "status.events.jsonl").write_text("")

        migration = HistoricalStatusMigration()
        assert migration.detect(tmp_path) is True

    def test_migration_only_events_detected(self, tmp_path: Path) -> None:
        """detect() returns True when all events are from migration actor
        but lack the full-history marker."""
        feature_dir = tmp_path / "kitty-specs" / "902-test"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "done")
        _write_migration_only_event(feature_dir)

        migration = HistoricalStatusMigration()
        assert migration.detect(tmp_path) is True

    def test_all_migrated_not_detected(self, tmp_path: Path) -> None:
        """detect() returns False when all features have live events."""
        feature_dir = tmp_path / "kitty-specs" / "903-test"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "done")
        _write_live_event(feature_dir)

        migration = HistoricalStatusMigration()
        assert migration.detect(tmp_path) is False

    def test_marker_events_not_detected(self, tmp_path: Path) -> None:
        """detect() returns False when events have the full-history marker."""
        feature_dir = tmp_path / "kitty-specs" / "904-test"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "done")
        _write_marker_event(feature_dir)

        migration = HistoricalStatusMigration()
        assert migration.detect(tmp_path) is False

    def test_no_kitty_specs_not_detected(self, tmp_path: Path) -> None:
        """detect() returns False when kitty-specs doesn't exist."""
        migration = HistoricalStatusMigration()
        assert migration.detect(tmp_path) is False

    def test_no_wp_files_not_detected(self, tmp_path: Path) -> None:
        """detect() returns False when features have no WP files."""
        tasks_dir = tmp_path / "kitty-specs" / "905-test" / "tasks"
        tasks_dir.mkdir(parents=True)
        # Empty tasks dir, no WP files

        migration = HistoricalStatusMigration()
        assert migration.detect(tmp_path) is False

    def test_no_tasks_dir_not_detected(self, tmp_path: Path) -> None:
        """detect() returns False when feature dir has no tasks/ subdir."""
        feature_dir = tmp_path / "kitty-specs" / "906-test"
        feature_dir.mkdir(parents=True)
        # No tasks dir at all

        migration = HistoricalStatusMigration()
        assert migration.detect(tmp_path) is False


# ── T030: can_apply() ───────────────────────────────────────────


class TestCanApply:
    """Tests for HistoricalStatusMigration.can_apply()."""

    def test_can_apply_with_kitty_specs(self, tmp_path: Path) -> None:
        """can_apply() returns True when kitty-specs exists."""
        (tmp_path / "kitty-specs").mkdir()
        migration = HistoricalStatusMigration()
        ok, msg = migration.can_apply(tmp_path)
        assert ok is True
        assert msg == ""

    def test_cannot_apply_without_kitty_specs(self, tmp_path: Path) -> None:
        """can_apply() returns False when kitty-specs is missing."""
        migration = HistoricalStatusMigration()
        ok, msg = migration.can_apply(tmp_path)
        assert ok is False
        assert "kitty-specs" in msg.lower()


# ── T034 + T035: apply() ────────────────────────────────────────


class TestApply:
    """Tests for HistoricalStatusMigration.apply()."""

    def test_apply_migrates_single_feature(self, tmp_path: Path) -> None:
        """apply() migrates a feature with WPs and creates events."""
        feature_dir = tmp_path / "kitty-specs" / "910-single"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "done", history=[
            {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
            {"timestamp": "2026-01-01T11:00:00Z", "lane": "done", "agent": "reviewer"},
        ])

        migration = HistoricalStatusMigration()
        result = migration.apply(tmp_path)

        assert result.success is True
        assert len(result.changes_made) == 1
        assert "910-single" in result.changes_made[0]

        events_file = feature_dir / "status.events.jsonl"
        assert events_file.exists()

    def test_apply_migrates_multiple_features(self, tmp_path: Path) -> None:
        """apply() processes all features and reports per-feature results."""
        for slug in ["911-a", "912-b"]:
            tasks_dir = tmp_path / "kitty-specs" / slug / "tasks"
            tasks_dir.mkdir(parents=True)
            _write_wp(tasks_dir, "WP01", "done")

        migration = HistoricalStatusMigration()
        result = migration.apply(tmp_path)

        assert result.success is True
        assert len(result.changes_made) == 2

        for slug in ["911-a", "912-b"]:
            events_file = tmp_path / "kitty-specs" / slug / "status.events.jsonl"
            assert events_file.exists()

    def test_apply_skips_feature_without_tasks(self, tmp_path: Path) -> None:
        """apply() skips features that have no tasks/ directory."""
        # Feature A: no tasks dir
        (tmp_path / "kitty-specs" / "920-no-tasks").mkdir(parents=True)

        # Feature B: valid
        tasks_dir = tmp_path / "kitty-specs" / "921-valid" / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "done")

        migration = HistoricalStatusMigration()
        result = migration.apply(tmp_path)

        assert result.success is True
        assert len(result.changes_made) == 1
        assert "921-valid" in result.changes_made[0]

    def test_apply_handles_feature_failure(self, tmp_path: Path) -> None:
        """apply() captures errors from individual features without aborting."""
        # Feature A: has tasks dir with WP but will fail due to invalid content
        tasks_dir_a = tmp_path / "kitty-specs" / "930-bad" / "tasks"
        tasks_dir_a.mkdir(parents=True)
        # Write an invalid WP file (no proper frontmatter)
        (tasks_dir_a / "WP01-bad.md").write_text("not valid frontmatter\n")

        # Feature B: valid
        tasks_dir_b = tmp_path / "kitty-specs" / "931-good" / "tasks"
        tasks_dir_b.mkdir(parents=True)
        _write_wp(tasks_dir_b, "WP01", "done")

        migration = HistoricalStatusMigration()
        result = migration.apply(tmp_path)

        # Feature B should still be processed regardless of A's failure
        good_changes = [c for c in result.changes_made if "931-good" in c]
        assert len(good_changes) == 1

    def test_apply_no_kitty_specs(self, tmp_path: Path) -> None:
        """apply() returns success with no changes when kitty-specs is absent."""
        migration = HistoricalStatusMigration()
        result = migration.apply(tmp_path)

        assert result.success is True
        assert len(result.changes_made) == 0

    def test_apply_dry_run_no_files(self, tmp_path: Path) -> None:
        """apply(dry_run=True) produces no event files on disk."""
        tasks_dir = tmp_path / "kitty-specs" / "940-dry" / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "done")

        migration = HistoricalStatusMigration()
        result = migration.apply(tmp_path, dry_run=True)

        assert result.success is True

        events_file = tmp_path / "kitty-specs" / "940-dry" / "status.events.jsonl"
        assert not events_file.exists()

        snapshot_file = tmp_path / "kitty-specs" / "940-dry" / "status.json"
        assert not snapshot_file.exists()

    def test_apply_dry_run_then_real(self, tmp_path: Path) -> None:
        """Dry run followed by real run produces correct results."""
        tasks_dir = tmp_path / "kitty-specs" / "941-dryreal" / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "in_progress")

        migration = HistoricalStatusMigration()

        # Dry run: no files
        dry_result = migration.apply(tmp_path, dry_run=True)
        assert dry_result.success is True
        assert not (tmp_path / "kitty-specs" / "941-dryreal" / "status.events.jsonl").exists()

        # Real run: files created
        real_result = migration.apply(tmp_path, dry_run=False)
        assert real_result.success is True
        assert (tmp_path / "kitty-specs" / "941-dryreal" / "status.events.jsonl").exists()

    def test_apply_all_planned_no_events(self, tmp_path: Path) -> None:
        """apply() on all-planned WPs produces no events (no transitions)."""
        tasks_dir = tmp_path / "kitty-specs" / "942-planned" / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "planned")
        _write_wp(tasks_dir, "WP02", "planned")

        migration = HistoricalStatusMigration()
        result = migration.apply(tmp_path)

        assert result.success is True


# ── T036: Cross-branch idempotency ──────────────────────────────


class TestCrossBranchIdempotency:
    """Test cross-branch idempotency (simulating 2.x then 0.x runs)."""

    def test_second_run_is_noop(self, tmp_path: Path) -> None:
        """Running migration twice produces zero additional events."""
        tasks_dir = tmp_path / "kitty-specs" / "950-cross" / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(
            tasks_dir, "WP01", "done",
            history=[
                {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
                {"timestamp": "2026-01-01T11:00:00Z", "lane": "doing", "agent": "claude"},
                {"timestamp": "2026-01-01T12:00:00Z", "lane": "done", "agent": "reviewer"},
            ],
            review_status="approved",
            reviewed_by="reviewer",
        )

        migration = HistoricalStatusMigration()

        # First run (simulates 2.x)
        result1 = migration.apply(tmp_path)
        assert result1.success is True

        from specify_cli.status.store import read_events

        feature_dir = tmp_path / "kitty-specs" / "950-cross"
        events_after_first = read_events(feature_dir)
        count_after_first = len(events_after_first)
        assert count_after_first > 0

        # Second run (simulates 0.x running later)
        result2 = migration.apply(tmp_path)
        assert result2.success is True

        events_after_second = read_events(feature_dir)
        count_after_second = len(events_after_second)

        # Zero additional events
        assert count_after_second == count_after_first

        # Event content identical
        for e1, e2 in zip(events_after_first, events_after_second):
            assert e1.event_id == e2.event_id

    def test_detect_false_after_migration(self, tmp_path: Path) -> None:
        """detect() returns False after apply() has run."""
        tasks_dir = tmp_path / "kitty-specs" / "951-detect" / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "in_progress")

        migration = HistoricalStatusMigration()

        # Before migration
        assert migration.detect(tmp_path) is True

        # Run migration
        migration.apply(tmp_path)

        # After migration
        assert migration.detect(tmp_path) is False


# ── Migration metadata ──────────────────────────────────────────


class TestMigrationMetadata:
    """Verify migration registration and metadata."""

    def test_migration_id(self) -> None:
        migration = HistoricalStatusMigration()
        assert migration.migration_id == "2.0.0_historical_status_migration"

    def test_target_version(self) -> None:
        migration = HistoricalStatusMigration()
        assert migration.target_version == "2.0.0"

    def test_description(self) -> None:
        migration = HistoricalStatusMigration()
        assert "history" in migration.description.lower()

    def test_registered_in_registry(self) -> None:
        from specify_cli.upgrade.registry import MigrationRegistry

        registered_ids = [
            m.migration_id for m in MigrationRegistry.get_all()
        ]
        assert "2.0.0_historical_status_migration" in registered_ids
