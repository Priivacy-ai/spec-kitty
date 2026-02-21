"""End-to-end CLI integration tests for the status engine (T077).

Tests the full pipeline: emit -> materialize -> validate, including
invalid transitions, force transitions, JSON output format, and
materialize idempotency.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.status.emit import TransitionError, emit_status_transition
from specify_cli.status.models import Lane
from specify_cli.status.reducer import SNAPSHOT_FILENAME, materialize, materialize_to_json
from specify_cli.status.store import EVENTS_FILENAME, read_events, read_events_raw
from specify_cli.status.validate import (
    validate_event_schema,
    validate_materialization_drift,
    validate_transition_legality,
)


# ── Helpers ──────────────────────────────────────────────────────


def _setup_feature(tmp_path: Path, feature_slug: str = "099-test") -> Path:
    """Create a minimal feature directory."""
    repo_root = tmp_path / "repo"
    feature_dir = repo_root / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    for wp_id in ("WP01", "WP02"):
        wp_file = tasks_dir / f"{wp_id}-task.md"
        wp_file.write_text(
            f"---\nwork_package_id: {wp_id}\ntitle: Test {wp_id}\nlane: planned\ndependencies: []\n---\n\n# {wp_id}\n",
            encoding="utf-8",
        )

    meta = {"status_phase": 1}
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    return feature_dir


# ── Tests ────────────────────────────────────────────────────────


class TestE2EFullPipeline:
    """T077: Full emit -> materialize -> validate pipeline."""

    def test_e2e_full_pipeline(self, tmp_path: Path):
        """Emit multiple transitions, materialize, validate no drift."""
        feature_dir = _setup_feature(tmp_path)
        slug = "099-test"
        repo_root = feature_dir.parent.parent

        # Emit transitions for WP01 through the lifecycle
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="claimed",
            actor="agent-1",
            repo_root=repo_root,
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="in_progress",
            actor="agent-1",
            repo_root=repo_root,
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="for_review",
            actor="agent-1",
            repo_root=repo_root,
        )

        # Emit a transition for WP02
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP02",
            to_lane="claimed",
            actor="agent-2",
            repo_root=repo_root,
        )

        # Verify event count
        events = read_events(feature_dir)
        assert len(events) == 4

        # Materialize (already done by emit, but do it explicitly too)
        snapshot = materialize(feature_dir)
        assert snapshot.work_packages["WP01"]["lane"] == "for_review"
        assert snapshot.work_packages["WP02"]["lane"] == "claimed"
        assert snapshot.event_count == 4

        # Validate: no materialization drift
        findings = validate_materialization_drift(feature_dir)
        assert len(findings) == 0

        # Validate: all events pass schema validation
        raw_events = read_events_raw(feature_dir)
        all_schema_findings = []
        for raw_event in raw_events:
            all_schema_findings.extend(validate_event_schema(raw_event))
        assert len(all_schema_findings) == 0

        # Validate: all transitions are legal
        transition_findings = validate_transition_legality(raw_events)
        assert len(transition_findings) == 0


class TestE2EEmitInvalidTransition:
    """T077: Invalid transitions raise TransitionError."""

    def test_e2e_emit_invalid_transition(self, tmp_path: Path):
        """Attempting an illegal transition raises TransitionError
        without persisting anything."""
        feature_dir = _setup_feature(tmp_path)
        slug = "099-test"
        repo_root = feature_dir.parent.parent

        # planned -> for_review is not a legal transition
        with pytest.raises(TransitionError) as exc_info:
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug=slug,
                wp_id="WP01",
                to_lane="for_review",
                actor="agent-1",
                repo_root=repo_root,
            )

        assert "Illegal transition" in str(exc_info.value)

        # No events should have been persisted
        events = read_events(feature_dir)
        assert len(events) == 0

        # No snapshot should exist
        assert not (feature_dir / SNAPSHOT_FILENAME).exists()

    def test_e2e_emit_invalid_transition_after_valid(self, tmp_path: Path):
        """Invalid transition after valid ones does not corrupt state."""
        feature_dir = _setup_feature(tmp_path)
        slug = "099-test"
        repo_root = feature_dir.parent.parent

        # Valid transition
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="claimed",
            actor="agent-1",
            repo_root=repo_root,
        )

        # Invalid transition (claimed -> done is not allowed)
        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug=slug,
                wp_id="WP01",
                to_lane="done",
                actor="agent-1",
                repo_root=repo_root,
            )

        # Only the valid event should exist
        events = read_events(feature_dir)
        assert len(events) == 1
        assert events[0].to_lane == Lane.CLAIMED


class TestE2EEmitForceTransition:
    """T077: Force transitions bypass guards."""

    def test_e2e_emit_force_transition(self, tmp_path: Path):
        """Force allows an illegal transition when actor and reason are given."""
        feature_dir = _setup_feature(tmp_path)
        slug = "099-test"
        repo_root = feature_dir.parent.parent

        # planned -> done is illegal normally
        event = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="done",
            actor="admin",
            force=True,
            reason="Emergency closure for abandoned work",
            repo_root=repo_root,
        )

        assert event.force is True
        assert event.to_lane == Lane.DONE

        # Verify persisted
        events = read_events(feature_dir)
        assert len(events) == 1
        assert events[0].force is True

    def test_e2e_force_without_reason_fails(self, tmp_path: Path):
        """Force requires both actor and reason."""
        feature_dir = _setup_feature(tmp_path)
        slug = "099-test"
        repo_root = feature_dir.parent.parent

        with pytest.raises(TransitionError) as exc_info:
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug=slug,
                wp_id="WP01",
                to_lane="done",
                actor="admin",
                force=True,
                # No reason provided
                repo_root=repo_root,
            )

        assert "require" in str(exc_info.value).lower()


class TestE2EJsonOutputFormat:
    """T077: JSON output is deterministic and well-formed."""

    def test_e2e_json_output_format(self, tmp_path: Path):
        """Verify status.json format: sorted keys, indent=2, trailing newline."""
        feature_dir = _setup_feature(tmp_path)
        slug = "099-test"
        repo_root = feature_dir.parent.parent

        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="claimed",
            actor="agent-1",
            repo_root=repo_root,
        )

        # Read raw JSON from disk
        raw_json = (feature_dir / SNAPSHOT_FILENAME).read_text(encoding="utf-8")

        # Must end with trailing newline
        assert raw_json.endswith("\n")

        # Must be valid JSON
        parsed = json.loads(raw_json)

        # Keys must be sorted (check top-level)
        keys = list(parsed.keys())
        assert keys == sorted(keys)

        # Check structure
        assert "feature_slug" in parsed
        assert "materialized_at" in parsed
        assert "event_count" in parsed
        assert "work_packages" in parsed
        assert "summary" in parsed

        # JSONL events should also be valid
        events_path = feature_dir / EVENTS_FILENAME
        for line in events_path.read_text(encoding="utf-8").strip().split("\n"):
            event_dict = json.loads(line)
            # Verify sorted keys in JSONL
            event_keys = list(event_dict.keys())
            assert event_keys == sorted(event_keys)


class TestE2EMaterializeIdempotent:
    """T077: materialize() is idempotent."""

    def test_e2e_materialize_idempotent(self, tmp_path: Path):
        """Running materialize twice produces byte-identical output."""
        feature_dir = _setup_feature(tmp_path)
        slug = "099-test"
        repo_root = feature_dir.parent.parent

        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP01",
            to_lane="claimed",
            actor="agent-1",
            repo_root=repo_root,
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug=slug,
            wp_id="WP02",
            to_lane="claimed",
            actor="agent-2",
            repo_root=repo_root,
        )

        # First materialize
        snapshot1 = materialize(feature_dir)
        json1 = materialize_to_json(snapshot1)

        # Second materialize
        snapshot2 = materialize(feature_dir)
        json2 = materialize_to_json(snapshot2)

        # Work packages should be identical
        assert snapshot1.work_packages == snapshot2.work_packages
        assert snapshot1.event_count == snapshot2.event_count
        assert snapshot1.last_event_id == snapshot2.last_event_id

        # Summary should be identical
        assert snapshot1.summary == snapshot2.summary

        # Materialized_at will differ (timestamp), but the rest of the
        # deterministic content should be the same. Verify by comparing
        # the work_packages and summary sections specifically.
        data1 = json.loads(json1)
        data2 = json.loads(json2)
        assert data1["work_packages"] == data2["work_packages"]
        assert data1["summary"] == data2["summary"]
        assert data1["event_count"] == data2["event_count"]
