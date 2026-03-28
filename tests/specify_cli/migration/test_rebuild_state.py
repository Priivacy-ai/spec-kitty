"""Tests for migration/rebuild_state.py — Subtask T069 (state rebuild part).

Covers:
- T069-1: Existing event log preserved as-is when consistent
- T069-2: status.json state correctly converted to events when no event log
- T069-3: Frontmatter lane correctly converted to events when no event log/status.json
- T069-4: Precedence: event_log > status_json > frontmatter for conflicts
- T069-5: Conflicting sources: warning logged, highest-precedence wins
- T069-6: Mid-flight features: event chain is realistic (multi-step)
- T069-7: Deduplication of identical event_ids
- T069-8: Identity enrichment backfills work_package_id on events
- T069-9: RebuildResult counters are correct
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from specify_cli.migration.rebuild_state import (
    rebuild_event_log,
    _build_chain,
    _dedup_events,
    _enrich_event_identity,
    _resolve_alias,
)


# ---------------------------------------------------------------------------
# Test helpers / fixtures
# ---------------------------------------------------------------------------


def _write_metadata(tmp_path: Path) -> None:
    """Create a minimal .kittify/metadata.yaml."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    data = {
        "spec_kitty": {
            "version": "2.1.0",
            "initialized_at": "2026-01-01T00:00:00",
        }
    }
    (kittify / "metadata.yaml").write_text(yaml.dump(data), encoding="utf-8")


def _make_feature(
    tmp_path: Path,
    slug: str,
    wps: list[dict] | None = None,
) -> Path:
    """Create a feature directory under kitty-specs/.

    wps is a list of dicts with keys:
      - name: str  (e.g. "WP01")
      - lane: str  (e.g. "in_progress")
      - work_package_id: str (optional)
    """
    feature_dir = tmp_path / "kitty-specs" / slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    meta = {"feature_slug": slug, "title": f"Feature {slug}"}
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    for wp in (wps or []):
        name = wp["name"]
        lane = wp.get("lane", "planned")
        wp_id = wp.get("work_package_id", "")
        lines = [
            "---",
            f"work_package_id: {wp_id!r}" if wp_id else "# no work_package_id",
            f"wp_code: {name!r}",
            f"title: {name} Title",
            f"lane: {lane!r}",
            "dependencies: []",
            "---",
            "",
            f"# {name} body",
        ]
        (tasks_dir / f"{name}-some-title.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )

    return feature_dir


def _write_events_file(feature_dir: Path, events: list[dict]) -> None:
    """Write a JSONL events file."""
    events_file = feature_dir / "status.events.jsonl"
    with events_file.open("w", encoding="utf-8") as fh:
        for evt in events:
            fh.write(json.dumps(evt, sort_keys=True) + "\n")


def _write_status_json(feature_dir: Path, slug: str, wp_lanes: dict[str, str]) -> None:
    """Write a status.json snapshot."""
    wps = {
        wp_code: {"lane": lane, "actor": "test", "last_transition_at": "2026-01-01T00:00:00+00:00"}
        for wp_code, lane in wp_lanes.items()
    }
    snapshot = {
        "feature_slug": slug,
        "materialized_at": "2026-01-01T12:00:00+00:00",
        "event_count": len(wp_lanes),
        "last_event_id": None,
        "work_packages": wps,
        "summary": {},
    }
    (feature_dir / "status.json").write_text(
        json.dumps(snapshot, indent=2), encoding="utf-8"
    )


def _make_event(
    wp_code: str,
    from_lane: str,
    to_lane: str,
    feature_slug: str = "001-test",
    event_id: str = "",
) -> dict:
    return {
        "event_id": event_id or f"EVT_{wp_code}_{to_lane}",
        "feature_slug": feature_slug,
        "wp_id": wp_code,
        "from_lane": from_lane,
        "to_lane": to_lane,
        "at": "2026-01-01T10:00:00+00:00",
        "actor": "agent",
        "force": False,
        "execution_mode": "worktree",
        "reason": None,
        "review_ref": None,
        "evidence": None,
    }


# ---------------------------------------------------------------------------
# T069-1: Existing event log preserved / identity-enriched
# ---------------------------------------------------------------------------


class TestExistingEventLogPreserved:
    def test_consistent_event_log_preserved(self, tmp_path: Path) -> None:
        """Existing event log consistent with frontmatter is kept unchanged."""
        slug = "001-test"
        feature_dir = _make_feature(
            tmp_path, slug, wps=[{"name": "WP01", "lane": "in_progress"}]
        )
        event = _make_event("WP01", "planned", "in_progress", slug)
        _write_events_file(feature_dir, [event])

        result = rebuild_event_log(feature_dir, slug, {"WP01": "ULID01"})

        assert not result.errors, result.errors
        # Event should be kept (events_kept >= 1)
        assert result.events_kept >= 1

        # Read back and verify event is present
        events_file = feature_dir / "status.events.jsonl"
        assert events_file.exists()
        written_events = json.loads(events_file.read_text().splitlines()[0])
        assert written_events["wp_id"] == "WP01"

    def test_event_log_identity_enriched(self, tmp_path: Path) -> None:
        """Events missing work_package_id get it backfilled."""
        slug = "001-test"
        feature_dir = _make_feature(
            tmp_path, slug, wps=[{"name": "WP01", "lane": "in_progress"}]
        )
        event = _make_event("WP01", "planned", "in_progress", slug)
        # Event has no work_package_id
        assert "work_package_id" not in event
        _write_events_file(feature_dir, [event])

        result = rebuild_event_log(feature_dir, slug, {"WP01": "ULID01ULID01ULID01ULID0001"})

        assert not result.errors, result.errors
        assert result.events_corrected >= 1

        # Verify work_package_id was added
        events_file = feature_dir / "status.events.jsonl"
        lines = [ln for ln in events_file.read_text().splitlines() if ln.strip()]
        for line in lines:
            evt = json.loads(line)
            if evt.get("wp_id") == "WP01":
                assert "work_package_id" in evt
                break
        else:
            pytest.fail("WP01 event not found in output")


# ---------------------------------------------------------------------------
# T069-2: status.json converted to events
# ---------------------------------------------------------------------------


class TestStatusJsonConvertedToEvents:
    def test_status_json_generates_events(self, tmp_path: Path) -> None:
        """status.json state produces synthetic events when no event log exists."""
        slug = "002-test"
        feature_dir = _make_feature(
            tmp_path,
            slug,
            wps=[
                {"name": "WP01", "lane": "done"},
                {"name": "WP02", "lane": "in_progress"},
            ],
        )
        _write_status_json(
            feature_dir, slug, {"WP01": "done", "WP02": "in_progress"}
        )
        # No event log

        result = rebuild_event_log(feature_dir, slug, {"WP01": "ID01", "WP02": "ID02"})

        assert not result.errors, result.errors
        assert result.events_generated > 0

        # Verify events were written
        events_file = feature_dir / "status.events.jsonl"
        assert events_file.exists()
        lines = [ln for ln in events_file.read_text().splitlines() if ln.strip()]
        assert len(lines) > 0

        # Verify WP01 has events leading to 'done'
        wp01_events = [json.loads(ln) for ln in lines if json.loads(ln).get("wp_id") == "WP01"]
        assert len(wp01_events) >= 1
        final_lane = wp01_events[-1]["to_lane"]
        assert final_lane == "done"


# ---------------------------------------------------------------------------
# T069-3: Frontmatter-only path
# ---------------------------------------------------------------------------


class TestFrontmatterLaneConvertedToEvents:
    def test_frontmatter_lane_generates_events(self, tmp_path: Path) -> None:
        """Frontmatter lane produces synthetic events when no event log or status.json."""
        slug = "003-test"
        feature_dir = _make_feature(
            tmp_path,
            slug,
            wps=[{"name": "WP01", "lane": "for_review"}],
        )
        # No event log, no status.json

        result = rebuild_event_log(feature_dir, slug, {"WP01": "ID01"})

        assert not result.errors, result.errors
        events_file = feature_dir / "status.events.jsonl"
        assert events_file.exists()
        lines = [ln for ln in events_file.read_text().splitlines() if ln.strip()]
        assert len(lines) > 0

        final_lanes = {json.loads(ln)["to_lane"] for ln in lines if json.loads(ln).get("wp_id") == "WP01"}
        assert "for_review" in final_lanes

    def test_planned_wp_skips_event_generation(self, tmp_path: Path) -> None:
        """A WP that is still 'planned' does not generate any events."""
        slug = "003b-test"
        feature_dir = _make_feature(
            tmp_path,
            slug,
            wps=[{"name": "WP01", "lane": "planned"}],
        )

        result = rebuild_event_log(feature_dir, slug, {})

        # The result may be skipped (no events to write) or have 0 generated events
        # Either way no errors
        assert not result.errors, result.errors
        assert result.events_generated == 0


# ---------------------------------------------------------------------------
# T069-4: Source precedence
# ---------------------------------------------------------------------------


class TestSourcePrecedence:
    def test_event_log_wins_over_status_json(self, tmp_path: Path) -> None:
        """When event log and status.json agree, no conflict; when they disagree,
        the most-recent-timestamped source wins."""
        slug = "004-test"
        feature_dir = _make_feature(
            tmp_path, slug, wps=[{"name": "WP01", "lane": "for_review"}]
        )
        # Event log says in_progress; status.json says for_review
        event = _make_event("WP01", "planned", "in_progress", slug)
        event["at"] = "2026-01-01T08:00:00+00:00"
        _write_events_file(feature_dir, [event])

        _write_status_json(feature_dir, slug, {"WP01": "for_review"})
        # status.json has materialized_at "2026-01-01T12:00:00+00:00" (more recent)

        result = rebuild_event_log(feature_dir, slug, {"WP01": "ID01"})

        # Conflict should be detected
        assert result.conflicts_found >= 1
        assert any("conflict" in w.lower() for w in result.warnings)

    def test_no_conflict_when_consistent(self, tmp_path: Path) -> None:
        """Consistent sources produce no conflict warnings."""
        slug = "004b-test"
        feature_dir = _make_feature(
            tmp_path, slug, wps=[{"name": "WP01", "lane": "in_progress"}]
        )
        event = _make_event("WP01", "planned", "in_progress", slug)
        _write_events_file(feature_dir, [event])
        _write_status_json(feature_dir, slug, {"WP01": "in_progress"})

        result = rebuild_event_log(feature_dir, slug, {})

        assert result.conflicts_found == 0


# ---------------------------------------------------------------------------
# T069-5: Conflicting sources with warning
# ---------------------------------------------------------------------------


class TestConflictingSourcesWarning:
    def test_conflict_produces_warning(self, tmp_path: Path) -> None:
        """Conflicting sources produce a warning message."""
        slug = "005-test"
        feature_dir = _make_feature(
            tmp_path, slug, wps=[{"name": "WP01", "lane": "done"}]
        )
        # event log says in_progress, frontmatter says done
        event = _make_event("WP01", "planned", "in_progress", slug)
        event["at"] = "2025-12-01T00:00:00+00:00"  # Old timestamp
        _write_events_file(feature_dir, [event])

        result = rebuild_event_log(feature_dir, slug, {})

        assert result.conflicts_found >= 1
        assert result.warnings  # Some warning was emitted


# ---------------------------------------------------------------------------
# T069-6: Mid-flight features have realistic event chains
# ---------------------------------------------------------------------------


class TestMidFlightEventChain:
    def test_in_progress_generates_chain(self, tmp_path: Path) -> None:
        """A mid-flight WP in 'in_progress' generates planned→claimed→in_progress."""
        slug = "006-test"
        feature_dir = _make_feature(
            tmp_path, slug, wps=[{"name": "WP01", "lane": "in_progress"}]
        )

        result = rebuild_event_log(feature_dir, slug, {"WP01": "ID01"})

        assert not result.errors, result.errors
        events_file = feature_dir / "status.events.jsonl"
        lines = [ln for ln in events_file.read_text().splitlines() if ln.strip()]
        wp01_events = [json.loads(ln) for ln in lines if json.loads(ln).get("wp_id") == "WP01"]

        # Should have multiple events (planned→claimed, claimed→in_progress)
        assert len(wp01_events) >= 2, f"Expected chain, got {len(wp01_events)} events"

        # Verify chain structure
        to_lanes = [e["to_lane"] for e in wp01_events]
        assert "in_progress" in to_lanes

    def test_for_review_generates_chain(self, tmp_path: Path) -> None:
        """WP in 'for_review' gets planned→claimed→in_progress→for_review chain."""
        slug = "006b-test"
        feature_dir = _make_feature(
            tmp_path, slug, wps=[{"name": "WP01", "lane": "for_review"}]
        )

        result = rebuild_event_log(feature_dir, slug, {})

        assert not result.errors, result.errors
        events_file = feature_dir / "status.events.jsonl"
        lines = [ln for ln in events_file.read_text().splitlines() if ln.strip()]
        wp01_events = [json.loads(ln) for ln in lines if json.loads(ln).get("wp_id") == "WP01"]
        to_lanes = [e["to_lane"] for e in wp01_events]

        # Last transition should be to for_review
        assert to_lanes[-1] == "for_review"
        # Chain should start from planned (not a single jump)
        assert len(wp01_events) >= 3


# ---------------------------------------------------------------------------
# T069-7: Deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    def test_duplicate_event_ids_dropped(self) -> None:
        """_dedup_events removes events with duplicate event_ids."""
        events = [
            {"event_id": "ID01", "wp_id": "WP01", "to_lane": "in_progress"},
            {"event_id": "ID01", "wp_id": "WP01", "to_lane": "for_review"},  # duplicate
            {"event_id": "ID02", "wp_id": "WP01", "to_lane": "done"},
        ]
        deduped, dropped = _dedup_events(events)
        assert dropped == 1
        assert len(deduped) == 2
        assert deduped[0]["event_id"] == "ID01"
        assert deduped[1]["event_id"] == "ID02"

    def test_no_duplicates_unchanged(self) -> None:
        """_dedup_events leaves a clean list untouched."""
        events = [
            {"event_id": "ID01", "wp_id": "WP01"},
            {"event_id": "ID02", "wp_id": "WP01"},
        ]
        deduped, dropped = _dedup_events(events)
        assert dropped == 0
        assert len(deduped) == 2


# ---------------------------------------------------------------------------
# T069-8: Identity enrichment
# ---------------------------------------------------------------------------


class TestIdentityEnrichment:
    def test_work_package_id_backfilled(self) -> None:
        """_enrich_event_identity adds work_package_id when missing."""
        evt = {"event_id": "ID01", "wp_id": "WP01", "feature_slug": "001-test"}
        wp_id_map = {"WP01": "ULID01ULID01ULID01ULID0001"}
        enriched, changed = _enrich_event_identity(evt, "001-test", wp_id_map)
        assert changed
        assert enriched["work_package_id"] == "ULID01ULID01ULID01ULID0001"

    def test_existing_work_package_id_not_overwritten(self) -> None:
        """_enrich_event_identity does not overwrite existing work_package_id."""
        evt = {
            "event_id": "ID01",
            "wp_id": "WP01",
            "work_package_id": "EXISTING",
            "feature_slug": "001-test",
        }
        enriched, changed = _enrich_event_identity(evt, "001-test", {"WP01": "NEW"})
        # work_package_id already present — no change
        assert enriched["work_package_id"] == "EXISTING"

    def test_feature_slug_backfilled(self) -> None:
        """_enrich_event_identity adds feature_slug when missing."""
        evt = {"event_id": "ID01", "wp_id": "WP01"}
        enriched, changed = _enrich_event_identity(evt, "001-test", {})
        assert changed
        assert enriched["feature_slug"] == "001-test"


# ---------------------------------------------------------------------------
# T069-9: RebuildResult counters
# ---------------------------------------------------------------------------


class TestRebuildResultCounters:
    def test_generated_counter_incremented(self, tmp_path: Path) -> None:
        """events_generated is non-zero when synthetic events are created."""
        slug = "009-test"
        feature_dir = _make_feature(
            tmp_path, slug, wps=[{"name": "WP01", "lane": "in_progress"}]
        )

        result = rebuild_event_log(feature_dir, slug, {})

        assert result.events_generated > 0

    def test_kept_counter_set_for_existing_events(self, tmp_path: Path) -> None:
        """events_kept matches the number of pre-existing events."""
        slug = "009b-test"
        feature_dir = _make_feature(
            tmp_path, slug, wps=[{"name": "WP01", "lane": "in_progress"}]
        )
        event = _make_event("WP01", "planned", "in_progress", slug, event_id="EVT001")
        _write_events_file(feature_dir, [event])

        result = rebuild_event_log(feature_dir, slug, {})

        assert result.events_kept >= 1

    def test_skipped_when_no_wps(self, tmp_path: Path) -> None:
        """Feature with no WPs is skipped gracefully."""
        slug = "009c-test"
        feature_dir = tmp_path / "kitty-specs" / slug
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text("{}", encoding="utf-8")

        result = rebuild_event_log(feature_dir, slug, {})

        assert result.skipped
        assert not result.errors


# ---------------------------------------------------------------------------
# Alias resolution
# ---------------------------------------------------------------------------


class TestAliasResolution:
    @pytest.mark.parametrize(
        "alias, expected",
        [
            ("doing", "in_progress"),
            ("review", "for_review"),
            ("complete", "done"),
            ("cancelled", "canceled"),
            ("planned", "planned"),
            ("in_progress", "in_progress"),
        ],
    )
    def test_resolve_alias(self, alias: str, expected: str) -> None:
        assert _resolve_alias(alias) == expected


# ---------------------------------------------------------------------------
# _build_chain helper
# ---------------------------------------------------------------------------


class TestBuildChain:
    def test_planned_returns_empty(self) -> None:
        """No events generated for WP still in 'planned' state."""
        chain = _build_chain("WP01", "001-test", {}, "planned", "2026-01-01T00:00:00+00:00")
        assert chain == []

    def test_in_progress_has_multiple_steps(self) -> None:
        """in_progress generates at least 2 transition events."""
        chain = _build_chain("WP01", "001-test", {}, "in_progress", "2026-01-01T00:00:00+00:00")
        assert len(chain) >= 2

    def test_done_ends_with_done(self) -> None:
        """Chain for 'done' state ends with to_lane='done'."""
        chain = _build_chain("WP01", "001-test", {}, "done", "2026-01-01T00:00:00+00:00")
        assert chain
        assert chain[-1]["to_lane"] == "done"

    def test_work_package_id_included(self) -> None:
        """work_package_id from wp_id_map is included in events."""
        chain = _build_chain(
            "WP01", "001-test", {"WP01": "WPIDULIDWPIDULIDWPIDULID00"},
            "in_progress", "2026-01-01T00:00:00+00:00"
        )
        for evt in chain:
            assert evt.get("work_package_id") == "WPIDULIDWPIDULIDWPIDULID00"
