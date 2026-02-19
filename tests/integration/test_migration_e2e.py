"""Migration integration tests (T080).

Tests the full legacy migration pipeline: reading frontmatter lanes,
generating full history reconstruction events, alias resolution, dry-run mode,
and post-migration transitions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.branch_contract import IS_2X_BRANCH, LEGACY_0X_ONLY_REASON

from specify_cli.status.migrate import (
    migrate_feature,
)
from specify_cli.status.models import Lane
from specify_cli.status.store import EVENTS_FILENAME, read_events, read_events_raw
from specify_cli.status.reducer import materialize, SNAPSHOT_FILENAME
from specify_cli.status.emit import emit_status_transition


# ── Helpers ──────────────────────────────────────────────────────


def _create_wp_file(
    tasks_dir: Path,
    wp_id: str,
    lane: str,
    title: str = "Test WP",
    *,
    history: list[dict[str, str]] | None = None,
    review_status: str | None = None,
    reviewed_by: str | None = None,
) -> Path:
    """Create a WP markdown file with frontmatter."""
    lines = [
        "---",
        f"work_package_id: {wp_id}",
        f"title: {title}",
        f"lane: {lane}",
        "dependencies: []",
    ]

    if review_status is not None:
        lines.append(f'review_status: "{review_status}"')
    if reviewed_by is not None:
        lines.append(f'reviewed_by: "{reviewed_by}"')

    if history is not None:
        lines.append("history:")
        for entry in history:
            lines.append(f'- timestamp: "{entry.get("timestamp", "")}"')
            lines.append(f'  lane: "{entry.get("lane", "")}"')
            if "agent" in entry:
                lines.append(f'  agent: "{entry["agent"]}"')

    lines.append("---")
    lines.append(f"\n# {wp_id}: {title}")

    wp_file = tasks_dir / f"{wp_id}-{title.lower().replace(' ', '-')}.md"
    wp_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return wp_file


def _setup_legacy_feature(
    tmp_path: Path,
    feature_slug: str = "099-legacy-test",
    wp_lanes: dict[str, str] | None = None,
) -> Path:
    """Create a legacy feature directory with WP files but no event log."""
    if wp_lanes is None:
        wp_lanes = {
            "WP01": "in_progress",
            "WP02": "for_review",
            "WP03": "planned",
            "WP04": "doing",  # alias for in_progress
        }

    feature_dir = tmp_path / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    for wp_id, lane in wp_lanes.items():
        _create_wp_file(tasks_dir, wp_id, lane)

    return feature_dir


# ── Tests ────────────────────────────────────────────────────────


class TestLegacyFeatureFullMigrationPipeline:
    """T080: Full migration pipeline from frontmatter to event log."""

    def test_legacy_feature_full_migration_pipeline(self, tmp_path: Path):
        """Migrate a feature with 4 WPs at various lanes. Verify events,
        snapshot, and consistency."""
        feature_dir = _setup_legacy_feature(tmp_path)

        result = migrate_feature(feature_dir)

        # Migration succeeded
        assert result.status == "migrated"

        # WP03 is at "planned" so no event for it (no transition from planned)
        # WP01 (in_progress), WP02 (for_review), WP04 (doing->in_progress)
        # Each generates exactly one bootstrap event (from planned -> current)
        # because no history arrays are provided
        events = read_events(feature_dir)
        assert len(events) == 3

        # Verify each event
        event_wps = {e.wp_id: e for e in events}
        assert event_wps["WP01"].from_lane == Lane.PLANNED
        assert event_wps["WP01"].to_lane == Lane.IN_PROGRESS
        assert event_wps["WP02"].from_lane == Lane.PLANNED
        assert event_wps["WP02"].to_lane == Lane.FOR_REVIEW
        assert event_wps["WP04"].from_lane == Lane.PLANNED
        assert event_wps["WP04"].to_lane == Lane.IN_PROGRESS  # alias resolved

        # All events use force=True
        for e in events:
            assert e.force is True
            assert e.reason is not None

        # Materialize and verify snapshot
        snapshot = materialize(feature_dir)
        assert snapshot.work_packages["WP01"]["lane"] == "in_progress"
        assert snapshot.work_packages["WP02"]["lane"] == "for_review"
        assert snapshot.work_packages["WP04"]["lane"] == "in_progress"

        # WP03 has no events so it won't be in the snapshot's work_packages
        assert "WP03" not in snapshot.work_packages

    def test_migration_idempotent(self, tmp_path: Path):
        """Running migration twice skips on the second run."""
        feature_dir = _setup_legacy_feature(tmp_path)

        result1 = migrate_feature(feature_dir)
        assert result1.status == "migrated"

        result2 = migrate_feature(feature_dir)
        assert result2.status == "skipped"

        # Event count unchanged
        events = read_events(feature_dir)
        assert len(events) == 3

    def test_multi_step_history_reconstruction(self, tmp_path: Path):
        """Full history reconstruction from multi-step history arrays."""
        feature_dir = tmp_path / "kitty-specs" / "099-multi-history"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _create_wp_file(
            tasks_dir, "WP01", "done", history=[
                {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
                {"timestamp": "2026-01-01T11:00:00Z", "lane": "in_progress", "agent": "agent-a"},
                {"timestamp": "2026-01-01T12:00:00Z", "lane": "for_review", "agent": "agent-a"},
                {"timestamp": "2026-01-01T13:00:00Z", "lane": "done", "agent": "reviewer"},
            ],
            review_status="approved",
            reviewed_by="reviewer",
        )

        result = migrate_feature(feature_dir)
        assert result.status == "migrated"

        events = read_events(feature_dir)
        assert len(events) == 3  # 3 transitions from 4 history entries

        assert events[0].from_lane == Lane.PLANNED
        assert events[0].to_lane == Lane.IN_PROGRESS
        assert events[1].from_lane == Lane.IN_PROGRESS
        assert events[1].to_lane == Lane.FOR_REVIEW
        assert events[2].from_lane == Lane.FOR_REVIEW
        assert events[2].to_lane == Lane.DONE

        # DoneEvidence attached to last event
        assert events[2].evidence is not None
        assert events[2].evidence.review.reviewer == "reviewer"


class TestMigrationThenTransition:
    """T080: After migration, normal transitions work."""

    def test_migration_then_transition(self, tmp_path: Path):
        """Migrate, then emit a transition on top of the bootstrapped state."""
        feature_dir = _setup_legacy_feature(
            tmp_path,
            wp_lanes={"WP01": "claimed", "WP02": "planned"},
        )
        feature_slug = "099-legacy-test"
        repo_root = tmp_path

        # Set up phase 1
        (feature_dir / "meta.json").write_text(
            json.dumps({"status_phase": 1}), encoding="utf-8"
        )

        # Migrate
        result = migrate_feature(feature_dir)
        assert result.status == "migrated"

        # WP01 should be at "claimed" via bootstrap event
        events_before = read_events(feature_dir)
        assert len(events_before) == 1
        assert events_before[0].wp_id == "WP01"
        assert events_before[0].to_lane == Lane.CLAIMED

        # Now emit a normal transition: claimed -> in_progress
        event = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=feature_slug,
            wp_id="WP01",
            to_lane="in_progress",
            actor="agent-1",
            repo_root=repo_root,
        )

        assert event.from_lane == Lane.CLAIMED
        assert event.to_lane == Lane.IN_PROGRESS

        # Total events should be bootstrap + new
        events_after = read_events(feature_dir)
        assert len(events_after) == 2


class TestMigrationAliasEndToEnd:
    """T080: Alias resolution works end-to-end in migration."""

    def test_migration_alias_end_to_end(self, tmp_path: Path):
        """'doing' alias in frontmatter is resolved to 'in_progress' in events."""
        feature_dir = _setup_legacy_feature(
            tmp_path,
            wp_lanes={"WP01": "doing"},
        )

        result = migrate_feature(feature_dir)
        assert result.status == "migrated"

        # Check wp_details for alias resolution
        wp01_detail = next(
            (d for d in result.wp_details if d.wp_id == "WP01"), None
        )
        assert wp01_detail is not None
        assert wp01_detail.original_lane == "doing"
        assert wp01_detail.canonical_lane == "in_progress"
        assert wp01_detail.alias_resolved is True

        # Verify in the event log
        events = read_events(feature_dir)
        assert len(events) == 1
        assert events[0].to_lane == Lane.IN_PROGRESS

        # Verify in raw JSONL
        raw_events = read_events_raw(feature_dir)
        assert raw_events[0]["to_lane"] == "in_progress"


class TestMigrationDryRunThenReal:
    """T080: dry_run=True computes results without writing."""

    def test_migration_dry_run_then_real(self, tmp_path: Path):
        """Dry run reports what would happen, then real run persists."""
        feature_dir = _setup_legacy_feature(
            tmp_path,
            wp_lanes={"WP01": "in_progress", "WP02": "for_review"},
        )

        # Dry run
        dry_result = migrate_feature(feature_dir, dry_run=True)
        assert dry_result.status == "migrated"  # Reports as migrated
        assert len(dry_result.wp_details) > 0

        # But no events should be written
        events_path = feature_dir / EVENTS_FILENAME
        assert not events_path.exists()

        # Now do the real run
        real_result = migrate_feature(feature_dir, dry_run=False)
        assert real_result.status == "migrated"

        # Events should now be written
        events = read_events(feature_dir)
        assert len(events) == 2

        # WP details should match between dry and real
        dry_wps = {d.wp_id: d for d in dry_result.wp_details}
        real_wps = {d.wp_id: d for d in real_result.wp_details}

        for wp_id in dry_wps:
            if wp_id in real_wps:
                assert dry_wps[wp_id].canonical_lane == real_wps[wp_id].canonical_lane
                assert dry_wps[wp_id].alias_resolved == real_wps[wp_id].alias_resolved

    def test_dry_run_no_side_effects(self, tmp_path: Path):
        """Dry run leaves no files on disk."""
        feature_dir = _setup_legacy_feature(
            tmp_path,
            wp_lanes={"WP01": "claimed"},
        )

        migrate_feature(feature_dir, dry_run=True)

        # No JSONL file
        assert not (feature_dir / EVENTS_FILENAME).exists()

        # No snapshot file
        assert not (feature_dir / SNAPSHOT_FILENAME).exists()


class TestMigrationEdgeCases:
    """Additional migration edge cases."""

    def test_migration_no_tasks_dir(self, tmp_path: Path):
        """Migration fails gracefully when tasks/ directory is missing."""
        feature_dir = tmp_path / "kitty-specs" / "099-no-tasks"
        feature_dir.mkdir(parents=True)

        result = migrate_feature(feature_dir)
        assert result.status == "failed"
        assert "tasks/" in (result.error or "")

    def test_migration_empty_tasks_dir(self, tmp_path: Path):
        """Migration fails when tasks/ has no WP files."""
        feature_dir = tmp_path / "kitty-specs" / "099-empty-tasks"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        result = migrate_feature(feature_dir)
        assert result.status == "failed"
        assert "WP" in (result.error or "")

    @pytest.mark.skipif(IS_2X_BRANCH, reason=LEGACY_0X_ONLY_REASON)
    def test_migration_all_planned_wps(self, tmp_path: Path):
        """Migration of all-planned WPs produces no events."""
        feature_dir = _setup_legacy_feature(
            tmp_path,
            wp_lanes={"WP01": "planned", "WP02": "planned"},
        )

        result = migrate_feature(feature_dir)
        assert result.status == "skipped"

        # No events because no transitions occurred (all at planned)
        events_path = feature_dir / EVENTS_FILENAME
        if events_path.exists():
            events = read_events(feature_dir)
            assert len(events) == 0

    def test_migration_custom_actor(self, tmp_path: Path):
        """Migration with custom actor name."""
        feature_dir = _setup_legacy_feature(
            tmp_path,
            wp_lanes={"WP01": "in_progress"},
        )

        result = migrate_feature(feature_dir, actor="custom-migration-bot")
        assert result.status == "migrated"

        events = read_events(feature_dir)
        assert len(events) == 1
        assert events[0].actor == "custom-migration-bot"
