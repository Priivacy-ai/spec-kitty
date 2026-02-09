"""Tests for the migration module (status.migrate).

Validates full history reconstruction from frontmatter, alias resolution,
3-layer idempotency (marker, live-events, migration-only replace),
backup creation, materialization, and the CLI ``migrate`` command.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.status.migrate import (
    FeatureMigrationResult,
    MigrationResult,
    WPMigrationDetail,
    migrate_feature,
)
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import EVENTS_FILENAME, read_events


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _write_wp(
    tasks_dir: Path,
    wp_id: str,
    lane: str,
    *,
    history: list[dict[str, str]] | None = None,
    review_status: str | None = None,
    reviewed_by: str | None = None,
) -> Path:
    """Create a minimal WP markdown file with the given lane.

    Args:
        tasks_dir: Directory to write the WP file into.
        wp_id: Work package ID (e.g. "WP01").
        lane: Current lane value for frontmatter.
        history: Optional multi-step history array. Each dict should have
            keys: timestamp, lane, agent.
        review_status: Optional review_status field.
        reviewed_by: Optional reviewed_by field.
    """
    lines = [
        "---",
        f'work_package_id: "{wp_id}"',
        f'title: "Test {wp_id}"',
        f'lane: "{lane}"',
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
    lines.append(f"# {wp_id}")

    content = "\n".join(lines) + "\n"
    wp_file = tasks_dir / f"{wp_id}-test.md"
    wp_file.write_text(content, encoding="utf-8")
    return wp_file


@pytest.fixture
def feature_with_wps(tmp_path: Path) -> Path:
    """Feature with 4 WPs at planned, doing, for_review, done.

    Each non-planned WP has a history array to support full reconstruction.
    """
    feature_dir = tmp_path / "kitty-specs" / "099-test-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # WP01: planned (no history needed, no events expected)
    _write_wp(tasks_dir, "WP01", "planned")

    # WP02: doing (alias) with history: planned -> doing
    _write_wp(tasks_dir, "WP02", "doing", history=[
        {"timestamp": "2026-02-08T09:00:00Z", "lane": "planned", "agent": "system"},
        {"timestamp": "2026-02-08T10:00:00Z", "lane": "doing", "agent": "agent-a"},
    ])

    # WP03: for_review with history: planned -> in_progress -> for_review
    _write_wp(tasks_dir, "WP03", "for_review", history=[
        {"timestamp": "2026-02-08T09:00:00Z", "lane": "planned", "agent": "system"},
        {"timestamp": "2026-02-08T10:00:00Z", "lane": "in_progress", "agent": "agent-b"},
        {"timestamp": "2026-02-08T11:00:00Z", "lane": "for_review", "agent": "agent-b"},
    ])

    # WP04: done with history: planned -> in_progress -> for_review -> done
    _write_wp(
        tasks_dir, "WP04", "done",
        history=[
            {"timestamp": "2026-02-08T09:00:00Z", "lane": "planned", "agent": "system"},
            {"timestamp": "2026-02-08T10:00:00Z", "lane": "in_progress", "agent": "agent-c"},
            {"timestamp": "2026-02-08T11:00:00Z", "lane": "for_review", "agent": "agent-c"},
            {"timestamp": "2026-02-08T12:00:00Z", "lane": "done", "agent": "reviewer"},
        ],
        review_status="approved",
        reviewed_by="reviewer",
    )

    return feature_dir


@pytest.fixture
def feature_already_migrated(tmp_path: Path) -> Path:
    """Feature with events containing a non-migration actor (live events)."""
    feature_dir = tmp_path / "kitty-specs" / "098-already-done"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    _write_wp(tasks_dir, "WP01", "done")

    # Create events file with a live (non-migration) actor
    events_file = feature_dir / EVENTS_FILENAME
    live_event = StatusEvent(
        event_id="01LIVE000000000000000000000",
        feature_slug="098-already-done",
        wp_id="WP01",
        from_lane=Lane.PLANNED,
        to_lane=Lane.DONE,
        at="2026-01-01T00:00:00Z",
        actor="claude-agent",
        force=True,
        execution_mode="worktree",
        reason="manual transition",
    )
    events_file.write_text(
        json.dumps(live_event.to_dict(), sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return feature_dir


# ---------------------------------------------------------------------------
# T070 -- migrate_feature core tests
# ---------------------------------------------------------------------------

class TestMigrateFeature:

    def test_four_wps_various_lanes(self, feature_with_wps: Path) -> None:
        """4 WPs at planned/doing/for_review/done -> multi-event history reconstruction."""
        result = migrate_feature(feature_with_wps)

        assert result.status == "migrated"
        assert result.feature_slug == "099-test-feature"
        assert len(result.wp_details) == 4

        # Verify events written
        events = read_events(feature_with_wps)

        # WP01 (planned): 0 events
        # WP02 (doing, 2 history entries): 1 transition (planned -> in_progress)
        # WP03 (for_review, 3 history entries): 2 transitions
        # WP04 (done, 4 history entries): 3 transitions
        assert len(events) == 6

        # Check that all events have correct fields
        for event in events:
            assert event.actor != ""
            assert event.execution_mode == "direct_repo"
            assert event.force is True
            assert event.reason is not None

        # Check specific WP events
        wp02_events = [e for e in events if e.wp_id == "WP02"]
        assert len(wp02_events) == 1
        assert wp02_events[0].from_lane == Lane.PLANNED
        assert wp02_events[0].to_lane == Lane.IN_PROGRESS  # doing -> in_progress alias

        wp03_events = [e for e in events if e.wp_id == "WP03"]
        assert len(wp03_events) == 2
        assert wp03_events[0].from_lane == Lane.PLANNED
        assert wp03_events[0].to_lane == Lane.IN_PROGRESS
        assert wp03_events[1].from_lane == Lane.IN_PROGRESS
        assert wp03_events[1].to_lane == Lane.FOR_REVIEW

        wp04_events = [e for e in events if e.wp_id == "WP04"]
        assert len(wp04_events) == 3
        assert wp04_events[-1].to_lane == Lane.DONE

    def test_planned_wp_no_event(self, feature_with_wps: Path) -> None:
        """WP at planned produces no events."""
        result = migrate_feature(feature_with_wps)

        wp01_detail = next(d for d in result.wp_details if d.wp_id == "WP01")
        assert wp01_detail.canonical_lane == "planned"
        assert wp01_detail.events_created == 0
        assert wp01_detail.event_ids == []

        events = read_events(feature_with_wps)
        wp_ids_with_events = {e.wp_id for e in events}
        assert "WP01" not in wp_ids_with_events

    def test_custom_actor(self, tmp_path: Path) -> None:
        """Custom actor is used as fallback when history actor is 'migration'."""
        feature_dir = tmp_path / "kitty-specs" / "105-actor"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # No history -> gap_fill creates transition with actor="migration"
        # which gets resolved to the custom actor param
        _write_wp(tasks_dir, "WP01", "in_progress")

        result = migrate_feature(feature_dir, actor="custom-agent")

        events = read_events(feature_dir)
        assert len(events) == 1
        assert events[0].actor == "custom-agent"

    def test_history_actor_preserved(self, tmp_path: Path) -> None:
        """Actor from history entries is preserved (not replaced by fallback)."""
        feature_dir = tmp_path / "kitty-specs" / "106-hist-actor"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_wp(tasks_dir, "WP01", "in_progress", history=[
            {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
            {"timestamp": "2026-01-01T11:00:00Z", "lane": "in_progress", "agent": "claude-dev"},
        ])

        result = migrate_feature(feature_dir, actor="fallback-actor")

        events = read_events(feature_dir)
        assert len(events) == 1
        # Actor from history should be used, not the fallback
        assert events[0].actor == "claude-dev"

    def test_history_timestamp_used(self, tmp_path: Path) -> None:
        """Events use the timestamp from frontmatter history."""
        feature_dir = tmp_path / "kitty-specs" / "100-ts-test"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_wp(tasks_dir, "WP01", "done", history=[
            {"timestamp": "2026-01-15T09:00:00Z", "lane": "planned", "agent": "system"},
            {"timestamp": "2026-01-15T09:30:00Z", "lane": "done", "agent": "reviewer"},
        ])

        migrate_feature(feature_dir)
        events = read_events(feature_dir)
        assert len(events) == 1
        assert events[0].at == "2026-01-15T09:30:00Z"

    def test_no_tasks_dir(self, tmp_path: Path) -> None:
        """Feature without tasks/ directory returns failed result."""
        feature_dir = tmp_path / "kitty-specs" / "101-no-tasks"
        feature_dir.mkdir(parents=True)

        result = migrate_feature(feature_dir)
        assert result.status == "failed"
        assert "No tasks/ directory" in result.error

    def test_empty_tasks_dir(self, tmp_path: Path) -> None:
        """Feature with empty tasks/ directory returns failed result."""
        feature_dir = tmp_path / "kitty-specs" / "102-empty-tasks"
        (feature_dir / "tasks").mkdir(parents=True)

        result = migrate_feature(feature_dir)
        assert result.status == "failed"
        assert "No WP*.md files" in result.error

    def test_wp_with_no_lane_field(self, tmp_path: Path) -> None:
        """WP with missing lane field treated as planned (no event)."""
        feature_dir = tmp_path / "kitty-specs" / "103-no-lane"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Write WP without lane field
        wp_file = tasks_dir / "WP01-test.md"
        wp_file.write_text(
            '---\nwork_package_id: "WP01"\ntitle: "No Lane"\n---\n# WP01\n',
            encoding="utf-8",
        )

        result = migrate_feature(feature_dir)
        assert result.status == "migrated"
        assert len(result.wp_details) == 1
        assert result.wp_details[0].canonical_lane == "planned"
        assert result.wp_details[0].events_created == 0

        events = read_events(feature_dir)
        assert len(events) == 0

    def test_wp_with_invalid_lane(self, tmp_path: Path) -> None:
        """WP with unrecognized lane is reported as error, others continue."""
        feature_dir = tmp_path / "kitty-specs" / "104-bad-lane"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_wp(tasks_dir, "WP01", "nonexistent")
        _write_wp(tasks_dir, "WP02", "done", history=[
            {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
            {"timestamp": "2026-01-01T11:00:00Z", "lane": "done", "agent": "reviewer"},
        ])

        result = migrate_feature(feature_dir)
        assert result.status == "migrated"

        wp01 = next(d for d in result.wp_details if d.wp_id == "WP01")
        assert wp01.events_created == 0

        wp02 = next(d for d in result.wp_details if d.wp_id == "WP02")
        assert wp02.events_created > 0

        events = read_events(feature_dir)
        assert len(events) == 1
        assert events[0].wp_id == "WP02"

    def test_event_ids_are_unique(self, feature_with_wps: Path) -> None:
        """All generated event IDs are unique ULIDs."""
        migrate_feature(feature_with_wps)
        events = read_events(feature_with_wps)
        event_ids = [e.event_id for e in events]
        assert len(event_ids) == len(set(event_ids))
        # Verify ULID format (26 uppercase base32 characters)
        import re
        ulid_pattern = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
        for eid in event_ids:
            assert ulid_pattern.match(eid), f"Invalid ULID: {eid}"

    def test_first_event_per_wp_has_marker_reason(self, feature_with_wps: Path) -> None:
        """First event per WP has the v1 marker reason."""
        migrate_feature(feature_with_wps)
        events = read_events(feature_with_wps)

        # Group events by WP
        wp_events: dict[str, list[StatusEvent]] = {}
        for e in events:
            wp_events.setdefault(e.wp_id, []).append(e)

        for wp_id, wp_evts in wp_events.items():
            assert "historical_frontmatter_to_jsonl:v1" in (wp_evts[0].reason or ""), (
                f"First event for {wp_id} missing marker reason"
            )
            for subsequent in wp_evts[1:]:
                assert subsequent.reason == "historical migration"

    def test_wp_details_fields(self, feature_with_wps: Path) -> None:
        """WPMigrationDetail contains correct events_created, event_ids, history_entries."""
        result = migrate_feature(feature_with_wps)

        wp04 = next(d for d in result.wp_details if d.wp_id == "WP04")
        assert wp04.events_created == 3
        assert len(wp04.event_ids) == 3
        assert wp04.history_entries == 4
        assert wp04.has_evidence is True

        wp01 = next(d for d in result.wp_details if d.wp_id == "WP01")
        assert wp01.events_created == 0
        assert wp01.event_ids == []

    def test_multi_event_transitions_ordered(self, tmp_path: Path) -> None:
        """Multi-step history produces events in correct chronological order."""
        feature_dir = tmp_path / "kitty-specs" / "107-ordered"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_wp(tasks_dir, "WP01", "for_review", history=[
            {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
            {"timestamp": "2026-01-01T11:00:00Z", "lane": "claimed", "agent": "agent-x"},
            {"timestamp": "2026-01-01T12:00:00Z", "lane": "in_progress", "agent": "agent-x"},
            {"timestamp": "2026-01-01T13:00:00Z", "lane": "for_review", "agent": "agent-x"},
        ])

        migrate_feature(feature_dir)
        events = read_events(feature_dir)

        assert len(events) == 3
        assert events[0].from_lane == Lane.PLANNED
        assert events[0].to_lane == Lane.CLAIMED
        assert events[1].from_lane == Lane.CLAIMED
        assert events[1].to_lane == Lane.IN_PROGRESS
        assert events[2].from_lane == Lane.IN_PROGRESS
        assert events[2].to_lane == Lane.FOR_REVIEW


# ---------------------------------------------------------------------------
# T071 -- Alias resolution
# ---------------------------------------------------------------------------

class TestAliasResolution:

    def test_doing_resolved_to_in_progress(self, tmp_path: Path) -> None:
        """``doing`` alias is resolved to ``in_progress``."""
        feature_dir = tmp_path / "kitty-specs" / "110-alias"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_wp(tasks_dir, "WP01", "doing")

        result = migrate_feature(feature_dir)
        detail = result.wp_details[0]
        assert detail.original_lane == "doing"
        assert detail.canonical_lane == "in_progress"
        assert detail.alias_resolved is True

        events = read_events(feature_dir)
        assert events[0].to_lane == Lane.IN_PROGRESS

    def test_canonical_lane_not_flagged_as_alias(self, tmp_path: Path) -> None:
        """``in_progress`` is not flagged as alias-resolved."""
        feature_dir = tmp_path / "kitty-specs" / "111-no-alias"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_wp(tasks_dir, "WP01", "in_progress")

        result = migrate_feature(feature_dir)
        detail = result.wp_details[0]
        assert detail.alias_resolved is False

    def test_alias_resolution_count(self, tmp_path: Path) -> None:
        """MigrationResult correctly counts total aliases resolved."""
        feature_dir = tmp_path / "kitty-specs" / "112-count"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_wp(tasks_dir, "WP01", "doing")
        _write_wp(tasks_dir, "WP02", "doing")
        _write_wp(tasks_dir, "WP03", "for_review")

        fr = migrate_feature(feature_dir)

        agg = MigrationResult()
        agg.features.append(fr)
        agg.aliases_resolved = sum(
            1 for f in agg.features for wp in f.wp_details if wp.alias_resolved
        )
        assert agg.aliases_resolved == 2

    @pytest.mark.parametrize("raw_lane", ["Doing", "DOING", " doing ", " Doing "])
    def test_case_and_whitespace_variants(self, tmp_path: Path, raw_lane: str) -> None:
        """Various casing/whitespace variants of ``doing`` all resolve."""
        feature_dir = tmp_path / "kitty-specs" / "113-case"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Write manually to control exact content
        wp_file = tasks_dir / "WP01-test.md"
        wp_file.write_text(
            f'---\nwork_package_id: "WP01"\ntitle: "Test"\nlane: "{raw_lane}"\n---\n# WP01\n',
            encoding="utf-8",
        )

        result = migrate_feature(feature_dir)
        detail = result.wp_details[0]
        assert detail.canonical_lane == "in_progress"
        assert detail.alias_resolved is True


# ---------------------------------------------------------------------------
# T072 -- Idempotency (3-layer)
# ---------------------------------------------------------------------------

class TestIdempotency:

    def test_second_run_is_skipped_via_marker(self, feature_with_wps: Path) -> None:
        """Running migrate twice: second call detects marker and skips (layer 1)."""
        result1 = migrate_feature(feature_with_wps)
        assert result1.status == "migrated"

        result2 = migrate_feature(feature_with_wps)
        assert result2.status == "skipped"

        # Verify no duplicate events
        events = read_events(feature_with_wps)
        assert len(events) == 6  # Same count as first run

    def test_marker_prevents_remigration(self, feature_with_wps: Path) -> None:
        """Features with full-history marker in events are skipped (layer 1)."""
        result1 = migrate_feature(feature_with_wps)
        assert result1.status == "migrated"

        # Verify marker exists in at least one event
        events = read_events(feature_with_wps)
        marker_events = [
            e for e in events
            if e.reason and "historical_frontmatter_to_jsonl:v1" in e.reason
        ]
        assert len(marker_events) > 0

        # Run again → skipped
        result2 = migrate_feature(feature_with_wps)
        assert result2.status == "skipped"

        # Event count unchanged
        events2 = read_events(feature_with_wps)
        assert len(events2) == len(events)

    def test_live_events_not_touched(self, feature_already_migrated: Path) -> None:
        """Features with live (non-migration) actors are skipped (layer 2)."""
        result = migrate_feature(feature_already_migrated)
        assert result.status == "skipped"

        # Original event unchanged
        events = read_events(feature_already_migrated)
        assert len(events) == 1
        assert events[0].actor == "claude-agent"

    def test_live_events_skip_with_explicit_actor(self, tmp_path: Path) -> None:
        """Layer 2: non-migration actor detected regardless of migration request."""
        feature_dir = tmp_path / "kitty-specs" / "800-live"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "done")

        # Write an event with a non-migration actor
        events_file = feature_dir / EVENTS_FILENAME
        live_event = StatusEvent(
            event_id="01LIVE000000000000000000000",
            feature_slug="800-live",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.DONE,
            at="2026-01-01T00:00:00Z",
            actor="claude-agent",
            force=True,
            execution_mode="worktree",
            reason="manual transition",
        )
        events_file.write_text(
            json.dumps(live_event.to_dict(), sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = migrate_feature(feature_dir)
        assert result.status == "skipped"

        events = read_events(feature_dir)
        assert len(events) == 1
        assert events[0].actor == "claude-agent"

    def test_migration_only_replaced_with_backup(self, tmp_path: Path) -> None:
        """Legacy bootstrap events (migration-only) are backed up and replaced (layer 3)."""
        feature_dir = tmp_path / "kitty-specs" / "810-legacy"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create WP with multi-step history
        _write_wp(tasks_dir, "WP01", "done", history=[
            {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
            {"timestamp": "2026-01-01T11:00:00Z", "lane": "doing", "agent": "claude"},
            {"timestamp": "2026-01-01T12:00:00Z", "lane": "done", "agent": "reviewer"},
        ])

        # Write legacy bootstrap event (migration-only actor)
        events_file = feature_dir / EVENTS_FILENAME
        legacy_event = StatusEvent(
            event_id="01LEGACY0000000000000000000",
            feature_slug="810-legacy",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.DONE,
            at="2026-01-01T10:00:00Z",
            actor="migration",
            force=False,
            execution_mode="direct_repo",
        )
        events_file.write_text(
            json.dumps(legacy_event.to_dict(), sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = migrate_feature(feature_dir)
        assert result.status == "migrated"
        assert result.was_replace is True
        assert result.backup_path is not None

        # Verify backup exists
        assert Path(result.backup_path).exists()

        # Verify new events have full history (more than 1 event)
        events = read_events(feature_dir)
        assert len(events) > 1  # Full reconstruction, not just bootstrap
        assert all(e.force is True for e in events)
        assert all(e.reason is not None for e in events)

    def test_whitespace_only_events_file_treated_as_empty(self, tmp_path: Path) -> None:
        """Events file with only whitespace is treated as empty (migrates)."""
        feature_dir = tmp_path / "kitty-specs" / "120-whitespace"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "done", history=[
            {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
            {"timestamp": "2026-01-01T11:00:00Z", "lane": "done", "agent": "reviewer"},
        ])

        events_file = feature_dir / EVENTS_FILENAME
        events_file.write_text("   \n\n  \n", encoding="utf-8")

        result = migrate_feature(feature_dir)
        # After strip, empty -> not skipped -> migrates
        assert result.status == "migrated"


# ---------------------------------------------------------------------------
# T073 -- Dry-run
# ---------------------------------------------------------------------------

class TestDryRun:

    def test_dry_run_no_files_created(self, feature_with_wps: Path) -> None:
        """dry_run=True computes result but writes nothing."""
        result = migrate_feature(feature_with_wps, dry_run=True)

        assert result.status == "migrated"
        assert len(result.wp_details) == 4

        events_file = feature_with_wps / EVENTS_FILENAME
        assert not events_file.exists()

    def test_dry_run_details_correct(self, feature_with_wps: Path) -> None:
        """Dry-run result contains correct WP details."""
        result = migrate_feature(feature_with_wps, dry_run=True)

        wp02 = next(d for d in result.wp_details if d.wp_id == "WP02")
        assert wp02.canonical_lane == "in_progress"
        assert wp02.alias_resolved is True
        assert wp02.events_created > 0
        assert len(wp02.event_ids) > 0

    def test_dry_run_no_snapshot(self, feature_with_wps: Path) -> None:
        """Dry-run does not produce a status.json snapshot."""
        migrate_feature(feature_with_wps, dry_run=True)
        assert not (feature_with_wps / "status.json").exists()

    def test_dry_run_no_backup(self, tmp_path: Path) -> None:
        """Dry-run does not create backup even for migration-only events."""
        feature_dir = tmp_path / "kitty-specs" / "820-dry-backup"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "done", history=[
            {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
            {"timestamp": "2026-01-01T11:00:00Z", "lane": "done", "agent": "reviewer"},
        ])

        # Write legacy migration event
        events_file = feature_dir / EVENTS_FILENAME
        legacy = StatusEvent(
            event_id="01LEGACY0000000000000000000",
            feature_slug="820-dry-backup",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.DONE,
            at="2026-01-01T10:00:00Z",
            actor="migration",
            force=False,
            execution_mode="direct_repo",
        )
        events_file.write_text(
            json.dumps(legacy.to_dict(), sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = migrate_feature(feature_dir, dry_run=True)
        assert result.status == "migrated"
        # No backup created during dry-run
        import glob
        backups = glob.glob(str(feature_dir / f"{EVENTS_FILENAME}.bak.*"))
        assert len(backups) == 0


# ---------------------------------------------------------------------------
# T073 -- Materialization
# ---------------------------------------------------------------------------

class TestMaterialization:

    def test_materialization_produces_valid_snapshot(self, feature_with_wps: Path) -> None:
        """status.json is materialized after migration."""
        migrate_feature(feature_with_wps)

        snapshot_file = feature_with_wps / "status.json"
        assert snapshot_file.exists()

        snapshot = json.loads(snapshot_file.read_text(encoding="utf-8"))
        assert snapshot["feature_slug"] == "099-test-feature"
        assert snapshot["event_count"] > 0
        assert "work_packages" in snapshot

    def test_snapshot_reflects_final_lanes(self, feature_with_wps: Path) -> None:
        """Materialized snapshot has correct final lanes for each WP."""
        migrate_feature(feature_with_wps)

        snapshot_file = feature_with_wps / "status.json"
        snapshot = json.loads(snapshot_file.read_text(encoding="utf-8"))

        wps = snapshot["work_packages"]
        assert wps["WP02"]["lane"] == "in_progress"  # doing alias resolved
        assert wps["WP03"]["lane"] == "for_review"
        assert wps["WP04"]["lane"] == "done"
        # WP01 is planned with no events, so not in snapshot
        assert "WP01" not in wps

    def test_no_materialization_when_no_events(self, tmp_path: Path) -> None:
        """When all WPs are planned (no events), no snapshot is created."""
        feature_dir = tmp_path / "kitty-specs" / "130-all-planned"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "planned")
        _write_wp(tasks_dir, "WP02", "planned")

        migrate_feature(feature_dir)

        # No events means no snapshot
        assert not (feature_dir / "status.json").exists()


# ---------------------------------------------------------------------------
# T073 -- CLI command tests
# ---------------------------------------------------------------------------

class TestMigrateCLI:
    """CLI tests invoke the ``migrate`` command via CliRunner."""

    def test_cli_single_feature_dry_run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CLI: --feature with --dry-run previews without writing."""
        feature_dir = tmp_path / "kitty-specs" / "200-cli-test"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "doing")
        _write_wp(tasks_dir, "WP02", "done", history=[
            {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
            {"timestamp": "2026-01-01T11:00:00Z", "lane": "done", "agent": "reviewer"},
        ])

        (tmp_path / ".kittify").mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        from specify_cli.cli.commands.agent.status import app as status_app

        runner = CliRunner()
        result = runner.invoke(status_app, ["migrate", "--feature", "200-cli-test", "--dry-run"])

        assert result.exit_code == 0
        assert not (feature_dir / EVENTS_FILENAME).exists()

    def test_cli_single_feature_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CLI: --json produces valid JSON output."""
        feature_dir = tmp_path / "kitty-specs" / "201-json-test"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "for_review", history=[
            {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
            {"timestamp": "2026-01-01T11:00:00Z", "lane": "for_review", "agent": "agent-a"},
        ])

        (tmp_path / ".kittify").mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        from specify_cli.cli.commands.agent.status import app as status_app

        runner = CliRunner()
        result = runner.invoke(status_app, ["migrate", "--feature", "201-json-test", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "features" in data
        assert "summary" in data
        assert data["summary"]["total_migrated"] == 1

    def test_cli_requires_feature_or_all(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CLI: neither --feature nor --all produces error."""
        (tmp_path / ".kittify").mkdir(parents=True)
        (tmp_path / "kitty-specs").mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        from specify_cli.cli.commands.agent.status import app as status_app

        runner = CliRunner()
        result = runner.invoke(status_app, ["migrate"])

        assert result.exit_code == 1

    def test_cli_both_feature_and_all_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CLI: --feature and --all together produces error."""
        (tmp_path / ".kittify").mkdir(parents=True)
        (tmp_path / "kitty-specs").mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        from specify_cli.cli.commands.agent.status import app as status_app

        runner = CliRunner()
        result = runner.invoke(status_app, ["migrate", "--feature", "foo", "--all"])

        assert result.exit_code == 1

    def test_cli_all_features(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CLI: --all migrates multiple features."""
        (tmp_path / ".kittify").mkdir(parents=True)

        for slug in ["300-feat-a", "301-feat-b"]:
            tasks_dir = tmp_path / "kitty-specs" / slug / "tasks"
            tasks_dir.mkdir(parents=True)
            _write_wp(tasks_dir, "WP01", "done", history=[
                {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
                {"timestamp": "2026-01-01T11:00:00Z", "lane": "done", "agent": "reviewer"},
            ])

        monkeypatch.chdir(tmp_path)

        from specify_cli.cli.commands.agent.status import app as status_app

        runner = CliRunner()
        result = runner.invoke(status_app, ["migrate", "--all", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["summary"]["total_migrated"] == 2

    def test_cli_exit_1_on_failure(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CLI: exit code 1 when a feature fails."""
        (tmp_path / ".kittify").mkdir(parents=True)

        feature_dir = tmp_path / "kitty-specs" / "400-no-tasks"
        feature_dir.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)

        from specify_cli.cli.commands.agent.status import app as status_app

        runner = CliRunner()
        result = runner.invoke(status_app, ["migrate", "--feature", "400-no-tasks"])

        assert result.exit_code == 1

    def test_cli_custom_actor(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CLI: --actor is passed through to events."""
        feature_dir = tmp_path / "kitty-specs" / "500-actor"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "done", history=[
            {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
            {"timestamp": "2026-01-01T11:00:00Z", "lane": "done", "agent": "migration"},
        ])

        (tmp_path / ".kittify").mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        from specify_cli.cli.commands.agent.status import app as status_app

        runner = CliRunner()
        result = runner.invoke(
            status_app,
            ["migrate", "--feature", "500-actor", "--actor", "my-bot"],
        )

        assert result.exit_code == 0
        events = read_events(feature_dir)
        assert len(events) == 1
        # Actor "migration" in history gets replaced by the custom actor "my-bot"
        assert events[0].actor == "my-bot"


# ---------------------------------------------------------------------------
# T074 -- Integration / JSON output shape
# ---------------------------------------------------------------------------

class TestMigrationResultJSON:

    def test_json_output_schema(self, feature_with_wps: Path) -> None:
        """Verify the JSON output structure matches expected schema."""
        from specify_cli.cli.commands.agent.status import _migration_result_to_dict

        fr = migrate_feature(feature_with_wps)
        agg = MigrationResult(
            features=[fr],
            total_migrated=1,
            total_skipped=0,
            total_failed=0,
            aliases_resolved=1,
        )

        data = _migration_result_to_dict(agg)

        # Top-level keys
        assert set(data.keys()) == {"features", "summary"}

        # Feature entry
        feat = data["features"][0]
        assert set(feat.keys()) == {"feature_slug", "status", "wp_count", "wp_details", "error"}

        # WP detail entry (the CLI function only extracts these 4 fields)
        wp = feat["wp_details"][0]
        assert set(wp.keys()) == {"wp_id", "original_lane", "canonical_lane", "alias_resolved"}

        # Summary
        assert set(data["summary"].keys()) == {
            "total_migrated",
            "total_skipped",
            "total_failed",
            "aliases_resolved",
        }


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_malformed_frontmatter_continues(self, tmp_path: Path) -> None:
        """WP with malformed frontmatter is reported but doesn't fail feature."""
        feature_dir = tmp_path / "kitty-specs" / "600-malformed"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Write malformed WP
        bad_file = tasks_dir / "WP01-bad.md"
        bad_file.write_text("not valid frontmatter at all", encoding="utf-8")

        # Write good WP
        _write_wp(tasks_dir, "WP02", "done", history=[
            {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
            {"timestamp": "2026-01-01T11:00:00Z", "lane": "done", "agent": "reviewer"},
        ])

        result = migrate_feature(feature_dir)
        assert result.status == "migrated"

        events = read_events(feature_dir)
        assert len(events) == 1
        assert events[0].wp_id == "WP02"

    def test_empty_lane_field_treated_as_planned(self, tmp_path: Path) -> None:
        """WP with empty lane field treated as planned."""
        feature_dir = tmp_path / "kitty-specs" / "601-empty-lane"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        wp_file = tasks_dir / "WP01-test.md"
        wp_file.write_text(
            '---\nwork_package_id: "WP01"\ntitle: "Empty Lane"\nlane: ""\n---\n# WP01\n',
            encoding="utf-8",
        )

        result = migrate_feature(feature_dir)
        assert result.status == "migrated"
        assert result.wp_details[0].canonical_lane == "planned"

        events = read_events(feature_dir)
        assert len(events) == 0

    def test_multiple_features_mixed_results(self, tmp_path: Path) -> None:
        """MigrationResult aggregates mixed migrated/skipped/failed."""
        kitty_specs = tmp_path / "kitty-specs"

        # Feature A: will migrate
        a_dir = kitty_specs / "700-a"
        a_tasks = a_dir / "tasks"
        a_tasks.mkdir(parents=True)
        _write_wp(a_tasks, "WP01", "done", history=[
            {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
            {"timestamp": "2026-01-01T11:00:00Z", "lane": "done", "agent": "reviewer"},
        ])

        # Feature B: will skip (has live events)
        b_dir = kitty_specs / "701-b"
        b_tasks = b_dir / "tasks"
        b_tasks.mkdir(parents=True)
        _write_wp(b_tasks, "WP01", "done")
        live_event = StatusEvent(
            event_id="01LIVE000000000000000000000",
            feature_slug="701-b",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.DONE,
            at="2026-01-01T00:00:00Z",
            actor="live-agent",
            force=True,
            execution_mode="worktree",
        )
        (b_dir / EVENTS_FILENAME).write_text(
            json.dumps(live_event.to_dict(), sort_keys=True) + "\n",
            encoding="utf-8",
        )

        # Feature C: will fail (no tasks dir)
        c_dir = kitty_specs / "702-c"
        c_dir.mkdir(parents=True)

        agg = MigrationResult()
        for fdir in [a_dir, b_dir, c_dir]:
            fr = migrate_feature(fdir)
            agg.features.append(fr)
            if fr.status == "migrated":
                agg.total_migrated += 1
            elif fr.status == "skipped":
                agg.total_skipped += 1
            elif fr.status == "failed":
                agg.total_failed += 1

        assert agg.total_migrated == 1
        assert agg.total_skipped == 1
        assert agg.total_failed == 1

    def test_done_evidence_attached_to_events(self, tmp_path: Path) -> None:
        """DoneEvidence is attached to events targeting 'done' lane."""
        feature_dir = tmp_path / "kitty-specs" / "610-evidence"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        _write_wp(
            tasks_dir, "WP01", "done",
            history=[
                {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
                {"timestamp": "2026-01-01T11:00:00Z", "lane": "done", "agent": "reviewer"},
            ],
            review_status="approved",
            reviewed_by="reviewer-x",
        )

        result = migrate_feature(feature_dir)
        assert result.status == "migrated"

        wp01 = next(d for d in result.wp_details if d.wp_id == "WP01")
        assert wp01.has_evidence is True

        events = read_events(feature_dir)
        done_events = [e for e in events if e.to_lane == Lane.DONE]
        assert len(done_events) == 1
        assert done_events[0].evidence is not None
        assert done_events[0].evidence.review.reviewer == "reviewer-x"
        assert done_events[0].evidence.review.verdict == "approved"

    def test_gap_fill_when_history_missing(self, tmp_path: Path) -> None:
        """WP with no history but non-planned lane gets a bootstrap transition."""
        feature_dir = tmp_path / "kitty-specs" / "620-gap"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # No history array, lane is in_progress
        _write_wp(tasks_dir, "WP01", "in_progress")

        migrate_feature(feature_dir)
        events = read_events(feature_dir)
        assert len(events) == 1
        assert events[0].from_lane == Lane.PLANNED
        assert events[0].to_lane == Lane.IN_PROGRESS

    def test_gap_fill_when_history_behind(self, tmp_path: Path) -> None:
        """When last history lane differs from current lane, gap-fill adds transition."""
        feature_dir = tmp_path / "kitty-specs" / "621-gap-behind"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # History ends at in_progress, but current lane is for_review
        _write_wp(tasks_dir, "WP01", "for_review", history=[
            {"timestamp": "2026-01-01T10:00:00Z", "lane": "planned", "agent": "system"},
            {"timestamp": "2026-01-01T11:00:00Z", "lane": "in_progress", "agent": "agent-a"},
        ])

        migrate_feature(feature_dir)
        events = read_events(feature_dir)

        # Should have: planned->in_progress + in_progress->for_review (gap fill)
        assert len(events) == 2
        assert events[0].from_lane == Lane.PLANNED
        assert events[0].to_lane == Lane.IN_PROGRESS
        assert events[1].from_lane == Lane.IN_PROGRESS
        assert events[1].to_lane == Lane.FOR_REVIEW
