"""Tests for the status validation engine.

Covers: validate_event_schema, validate_transition_legality,
validate_done_evidence, validate_materialization_drift,
validate_derived_views, and ValidationResult.
"""

from __future__ import annotations

import json
from pathlib import Path


from specify_cli.status.validate import (
    ValidationResult,
    validate_derived_views,
    validate_done_evidence,
    validate_event_schema,
    validate_materialization_drift,
    validate_transition_legality,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    *,
    event_id: str = "01HXYZ0123456789ABCDEFGHJK",
    feature_slug: str = "034-test-feature",
    wp_id: str = "WP01",
    from_lane: str = "planned",
    to_lane: str = "claimed",
    at: str = "2026-02-08T12:00:00Z",
    actor: str = "claude-opus",
    force: bool = False,
    execution_mode: str = "worktree",
    reason: str | None = None,
    review_ref: str | None = None,
    evidence: dict | None = None,
    **extra,
) -> dict:
    """Build a valid event dict with optional overrides."""
    event: dict = {
        "event_id": event_id,
        "feature_slug": feature_slug,
        "wp_id": wp_id,
        "from_lane": from_lane,
        "to_lane": to_lane,
        "at": at,
        "actor": actor,
        "force": force,
        "execution_mode": execution_mode,
    }
    if reason is not None:
        event["reason"] = reason
    if review_ref is not None:
        event["review_ref"] = review_ref
    if evidence is not None:
        event["evidence"] = evidence
    event.update(extra)
    return event


def _make_done_evidence(
    reviewer: str = "reviewer-1",
    verdict: str = "approved",
    reference: str = "ref-001",
) -> dict:
    return {
        "review": {
            "reviewer": reviewer,
            "verdict": verdict,
            "reference": reference,
        }
    }


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------


class TestValidationResult:
    def test_empty_result_passes(self):
        r = ValidationResult()
        assert r.passed is True
        assert r.errors == []
        assert r.warnings == []

    def test_with_errors_fails(self):
        r = ValidationResult(errors=["something bad"])
        assert r.passed is False

    def test_with_only_warnings_passes(self):
        r = ValidationResult(warnings=["minor issue"])
        assert r.passed is True

    def test_phase_source_default(self):
        r = ValidationResult()
        assert r.phase_source == ""


# ---------------------------------------------------------------------------
# validate_event_schema
# ---------------------------------------------------------------------------


class TestValidateEventSchema:
    def test_valid_event_no_findings(self):
        event = _make_event()
        findings = validate_event_schema(event)
        assert findings == []

    def test_missing_required_field(self):
        event = _make_event()
        del event["actor"]
        findings = validate_event_schema(event)
        assert any("Missing required field: actor" in f for f in findings)

    def test_missing_multiple_required_fields(self):
        event = _make_event()
        del event["event_id"]
        del event["wp_id"]
        findings = validate_event_schema(event)
        assert any("Missing required field: event_id" in f for f in findings)
        assert any("Missing required field: wp_id" in f for f in findings)

    def test_invalid_event_id_format(self):
        event = _make_event(event_id="not-a-ulid")
        findings = validate_event_schema(event)
        assert any("Invalid event ID format" in f for f in findings)

    def test_valid_ulid_passes(self):
        event = _make_event(event_id="01HXYZ0123456789ABCDEFGHJK")
        findings = validate_event_schema(event)
        assert not any("Invalid event ID" in f for f in findings)

    def test_valid_uuid_hyphenated_passes(self):
        event = _make_event(event_id="550e8400-e29b-41d4-a716-446655440000")
        findings = validate_event_schema(event)
        assert not any("Invalid event ID" in f for f in findings)

    def test_valid_uuid_bare_passes(self):
        event = _make_event(event_id="550e8400e29b41d4a716446655440000")
        findings = validate_event_schema(event)
        assert not any("Invalid event ID" in f for f in findings)

    def test_non_canonical_from_lane(self):
        """Alias 'doing' is NOT canonical and should be flagged."""
        event = _make_event(from_lane="doing")
        findings = validate_event_schema(event)
        assert any("from_lane is not canonical: doing" in f for f in findings)

    def test_non_canonical_to_lane(self):
        event = _make_event(to_lane="reviewing")
        findings = validate_event_schema(event)
        assert any("to_lane is not canonical: reviewing" in f for f in findings)

    def test_canonical_lanes_pass(self):
        for lane in [
            "planned",
            "claimed",
            "in_progress",
            "for_review",
            "done",
            "blocked",
            "canceled",
        ]:
            event = _make_event(from_lane=lane, to_lane=lane)
            findings = validate_event_schema(event)
            assert not any("is not canonical" in f for f in findings)

    def test_force_without_reason(self):
        event = _make_event(force=True)
        findings = validate_event_schema(event)
        assert any("force=true without reason" in f for f in findings)

    def test_force_with_reason(self):
        event = _make_event(force=True, reason="emergency fix")
        findings = validate_event_schema(event)
        assert not any("force=true without reason" in f for f in findings)

    def test_review_ref_required_for_for_review_to_in_progress(self):
        event = _make_event(
            from_lane="for_review", to_lane="in_progress"
        )
        findings = validate_event_schema(event)
        assert any("for_review->in_progress without review_ref" in f for f in findings)

    def test_review_ref_present(self):
        event = _make_event(
            from_lane="for_review",
            to_lane="in_progress",
            review_ref="PR#42-comment-3",
        )
        findings = validate_event_schema(event)
        assert not any("review_ref" in f for f in findings)

    def test_extra_fields_not_flagged(self):
        """Forward compatibility: extra fields should NOT produce findings."""
        event = _make_event(custom_field="extra-data", future_version=2)
        findings = validate_event_schema(event)
        assert findings == []

    def test_invalid_iso8601_timestamp(self):
        event = _make_event(at="not-a-date")
        findings = validate_event_schema(event)
        assert any("invalid ISO 8601 timestamp" in f for f in findings)

    def test_valid_iso8601_z_suffix(self):
        event = _make_event(at="2026-02-08T12:00:00Z")
        findings = validate_event_schema(event)
        assert not any("timestamp" in f for f in findings)

    def test_valid_iso8601_offset(self):
        event = _make_event(at="2026-02-08T12:00:00+00:00")
        findings = validate_event_schema(event)
        assert not any("timestamp" in f for f in findings)

    def test_force_not_boolean(self):
        event = _make_event()
        event["force"] = "yes"
        findings = validate_event_schema(event)
        assert any("force must be boolean" in f for f in findings)

    def test_invalid_execution_mode(self):
        event = _make_event(execution_mode="hybrid")
        findings = validate_event_schema(event)
        assert any("execution_mode must be" in f for f in findings)

    def test_valid_execution_modes(self):
        for mode in ("worktree", "direct_repo"):
            event = _make_event(execution_mode=mode)
            findings = validate_event_schema(event)
            assert not any("execution_mode" in f for f in findings)


# ---------------------------------------------------------------------------
# validate_transition_legality
# ---------------------------------------------------------------------------


class TestValidateTransitionLegality:
    def test_all_legal_transitions(self):
        """Legal transitions should produce zero findings."""
        legal_pairs = [
            ("planned", "claimed"),
            ("claimed", "in_progress"),
            ("in_progress", "for_review"),
            ("for_review", "done"),
            ("for_review", "in_progress"),
            ("in_progress", "planned"),
            ("planned", "blocked"),
            ("claimed", "blocked"),
            ("in_progress", "blocked"),
            ("for_review", "blocked"),
            ("blocked", "in_progress"),
            ("planned", "canceled"),
            ("claimed", "canceled"),
            ("in_progress", "canceled"),
            ("for_review", "canceled"),
            ("blocked", "canceled"),
        ]
        events = [
            _make_event(
                event_id=f"01HXYZ012345678{i:09d}ABCDE",
                from_lane=f,
                to_lane=t,
                at=f"2026-02-08T{12+i:02d}:00:00Z",
            )
            for i, (f, t) in enumerate(legal_pairs)
        ]
        findings = validate_transition_legality(events)
        assert findings == []

    def test_illegal_transition(self):
        """planned -> done is not a legal transition."""
        events = [
            _make_event(from_lane="planned", to_lane="done"),
        ]
        findings = validate_transition_legality(events)
        assert len(findings) == 1
        assert "illegal transition planned -> done" in findings[0]

    def test_forced_illegal_transition_not_flagged(self):
        """Force bypasses transition legality check."""
        events = [
            _make_event(
                from_lane="planned",
                to_lane="done",
                force=True,
                reason="emergency",
            ),
        ]
        findings = validate_transition_legality(events)
        assert findings == []

    def test_events_sorted_before_check(self):
        """Out-of-order events should be sorted by (at, event_id)."""
        events = [
            _make_event(
                event_id="01HXYZ0123456789ABCDEFGHJM",
                from_lane="in_progress",
                to_lane="for_review",
                at="2026-02-08T14:00:00Z",
            ),
            _make_event(
                event_id="01HXYZ0123456789ABCDEFGHJK",
                from_lane="planned",
                to_lane="claimed",
                at="2026-02-08T12:00:00Z",
            ),
        ]
        findings = validate_transition_legality(events)
        assert findings == []

    def test_missing_lanes_skipped(self):
        """Events with missing lane fields are skipped (schema catches them)."""
        events = [{"event_id": "01HXYZ0123456789ABCDEFGHJK"}]
        findings = validate_transition_legality(events)
        assert findings == []


# ---------------------------------------------------------------------------
# validate_done_evidence
# ---------------------------------------------------------------------------


class TestValidateDoneEvidence:
    def test_done_with_full_evidence(self):
        evidence = _make_done_evidence()
        events = [
            _make_event(
                from_lane="for_review",
                to_lane="done",
                evidence=evidence,
            ),
        ]
        findings = validate_done_evidence(events)
        assert findings == []

    def test_done_without_evidence_not_forced(self):
        events = [
            _make_event(from_lane="for_review", to_lane="done"),
        ]
        findings = validate_done_evidence(events)
        assert len(findings) == 1
        assert "done without evidence (not forced)" in findings[0]

    def test_done_with_force_no_evidence(self):
        events = [
            _make_event(
                from_lane="for_review",
                to_lane="done",
                force=True,
                reason="emergency close",
            ),
        ]
        findings = validate_done_evidence(events)
        assert findings == []

    def test_done_evidence_missing_reviewer(self):
        evidence = {
            "review": {
                "verdict": "approved",
                "reference": "ref-001",
            }
        }
        events = [
            _make_event(
                from_lane="for_review",
                to_lane="done",
                evidence=evidence,
            ),
        ]
        findings = validate_done_evidence(events)
        assert any("missing reviewer identity" in f for f in findings)

    def test_done_evidence_missing_verdict(self):
        evidence = {
            "review": {
                "reviewer": "reviewer-1",
                "reference": "ref-001",
            }
        }
        events = [
            _make_event(
                from_lane="for_review",
                to_lane="done",
                evidence=evidence,
            ),
        ]
        findings = validate_done_evidence(events)
        assert any("missing verdict" in f for f in findings)

    def test_done_evidence_missing_reference(self):
        evidence = {
            "review": {
                "reviewer": "reviewer-1",
                "verdict": "approved",
            }
        }
        events = [
            _make_event(
                from_lane="for_review",
                to_lane="done",
                evidence=evidence,
            ),
        ]
        findings = validate_done_evidence(events)
        assert any("missing approval reference" in f for f in findings)

    def test_done_evidence_missing_review_section(self):
        evidence = {"repos": []}
        events = [
            _make_event(
                from_lane="for_review",
                to_lane="done",
                evidence=evidence,
            ),
        ]
        findings = validate_done_evidence(events)
        assert any("missing review section" in f for f in findings)

    def test_done_evidence_not_a_dict(self):
        events = [
            _make_event(
                from_lane="for_review",
                to_lane="done",
                evidence="just-a-string",
            ),
        ]
        findings = validate_done_evidence(events)
        assert any("not a dict" in f for f in findings)

    def test_non_done_events_skipped(self):
        """Events not transitioning to done are ignored."""
        events = [
            _make_event(from_lane="planned", to_lane="claimed"),
            _make_event(from_lane="claimed", to_lane="in_progress"),
        ]
        findings = validate_done_evidence(events)
        assert findings == []

    def test_done_evidence_with_extra_fields(self):
        """Extra fields in evidence should not cause findings."""
        evidence = _make_done_evidence()
        evidence["custom_field"] = "extra"
        events = [
            _make_event(
                from_lane="for_review",
                to_lane="done",
                evidence=evidence,
            ),
        ]
        findings = validate_done_evidence(events)
        assert findings == []


# ---------------------------------------------------------------------------
# validate_materialization_drift
# ---------------------------------------------------------------------------


class TestValidateMaterializationDrift:
    def test_no_events_no_snapshot_no_drift(self, tmp_path: Path):
        """Neither file exists: nothing to validate."""
        findings = validate_materialization_drift(tmp_path)
        assert findings == []

    def test_snapshot_without_events(self, tmp_path: Path):
        """status.json exists but no events file: drift."""
        (tmp_path / "status.json").write_text("{}", encoding="utf-8")
        findings = validate_materialization_drift(tmp_path)
        assert len(findings) == 1
        assert "status.events.jsonl is missing" in findings[0]

    def test_events_without_snapshot(self, tmp_path: Path):
        """Events exist but no status.json: drift."""
        event = _make_event()
        (tmp_path / "status.events.jsonl").write_text(
            json.dumps(event, sort_keys=True) + "\n", encoding="utf-8"
        )
        findings = validate_materialization_drift(tmp_path)
        assert len(findings) == 1
        assert "status.json is missing" in findings[0]

    def test_matching_snapshot_no_drift(self, tmp_path: Path):
        """status.json matches reducer output: no findings."""
        # Create an event
        event = _make_event()
        (tmp_path / "status.events.jsonl").write_text(
            json.dumps(event, sort_keys=True) + "\n", encoding="utf-8"
        )

        # Materialize correctly
        from specify_cli.status.reducer import materialize

        materialize(tmp_path)

        findings = validate_materialization_drift(tmp_path)
        assert findings == []

    def test_tampered_snapshot_detects_drift(self, tmp_path: Path):
        """Manually editing status.json causes drift detection."""
        # Create an event
        event = _make_event()
        (tmp_path / "status.events.jsonl").write_text(
            json.dumps(event, sort_keys=True) + "\n", encoding="utf-8"
        )

        # Materialize correctly first
        from specify_cli.status.reducer import materialize

        materialize(tmp_path)

        # Tamper with the snapshot
        snapshot_path = tmp_path / "status.json"
        data = json.loads(snapshot_path.read_text())
        data["work_packages"]["WP01"]["lane"] = "done"  # Wrong!
        snapshot_path.write_text(
            json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        )

        findings = validate_materialization_drift(tmp_path)
        assert len(findings) >= 1
        assert any("Materialization drift" in f for f in findings)

    def test_event_count_mismatch(self, tmp_path: Path):
        """Event count mismatch is detected."""
        event = _make_event()
        (tmp_path / "status.events.jsonl").write_text(
            json.dumps(event, sort_keys=True) + "\n", encoding="utf-8"
        )

        from specify_cli.status.reducer import materialize

        materialize(tmp_path)

        # Tamper event count
        snapshot_path = tmp_path / "status.json"
        data = json.loads(snapshot_path.read_text())
        data["event_count"] = 999
        snapshot_path.write_text(
            json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        )

        findings = validate_materialization_drift(tmp_path)
        assert any("event_count" in f for f in findings)


# ---------------------------------------------------------------------------
# validate_derived_views
# ---------------------------------------------------------------------------


class TestValidateDerivedViews:
    def _write_wp_file(self, tasks_dir: Path, wp_id: str, lane: str, title: str = "Test WP"):
        """Helper to create a WP markdown file with frontmatter."""
        content = f"""---
work_package_id: {wp_id}
title: {title}
lane: {lane}
---

# {wp_id}: {title}
"""
        wp_file = tasks_dir / f"{wp_id}-{title.lower().replace(' ', '-')}.md"
        wp_file.write_text(content, encoding="utf-8")

    def test_matching_frontmatter_no_drift(self, tmp_path: Path):
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        self._write_wp_file(tasks_dir, "WP01", "in_progress")

        snapshot_wps = {
            "WP01": {"lane": "in_progress"},
        }
        findings = validate_derived_views(tmp_path, snapshot_wps, phase=2)
        assert findings == []

    def test_frontmatter_drift_phase1_warning(self, tmp_path: Path):
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        self._write_wp_file(tasks_dir, "WP01", "planned")

        snapshot_wps = {
            "WP01": {"lane": "in_progress"},
        }
        findings = validate_derived_views(tmp_path, snapshot_wps, phase=1)
        assert len(findings) == 1
        assert findings[0].startswith("WARNING:")
        assert "WP01" in findings[0]

    def test_frontmatter_drift_phase2_error(self, tmp_path: Path):
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        self._write_wp_file(tasks_dir, "WP01", "planned")

        snapshot_wps = {
            "WP01": {"lane": "in_progress"},
        }
        findings = validate_derived_views(tmp_path, snapshot_wps, phase=2)
        assert len(findings) == 1
        assert findings[0].startswith("ERROR:")

    def test_doing_alias_resolved(self, tmp_path: Path):
        """Frontmatter 'doing' should match canonical 'in_progress'."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        self._write_wp_file(tasks_dir, "WP01", "doing")

        snapshot_wps = {
            "WP01": {"lane": "in_progress"},
        }
        findings = validate_derived_views(tmp_path, snapshot_wps, phase=2)
        assert findings == []

    def test_missing_wp_file(self, tmp_path: Path):
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        # WP01 exists in snapshot but has no file
        snapshot_wps = {
            "WP01": {"lane": "planned"},
        }
        findings = validate_derived_views(tmp_path, snapshot_wps, phase=2)
        assert len(findings) == 1
        assert "no WP file found" in findings[0]

    def test_no_tasks_dir(self, tmp_path: Path):
        """No tasks directory: no findings."""
        snapshot_wps = {
            "WP01": {"lane": "planned"},
        }
        findings = validate_derived_views(tmp_path, snapshot_wps, phase=2)
        assert findings == []

    def test_missing_lane_in_frontmatter(self, tmp_path: Path):
        """WP file without lane field in frontmatter."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        wp_file = tasks_dir / "WP01-test.md"
        wp_file.write_text(
            "---\nwork_package_id: WP01\ntitle: Test\n---\n# WP01\n",
            encoding="utf-8",
        )

        snapshot_wps = {
            "WP01": {"lane": "planned"},
        }
        findings = validate_derived_views(tmp_path, snapshot_wps, phase=2)
        assert len(findings) == 1
        assert "no lane field in frontmatter" in findings[0]

    def test_multiple_wps_some_drifted(self, tmp_path: Path):
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        self._write_wp_file(tasks_dir, "WP01", "done")
        self._write_wp_file(tasks_dir, "WP02", "planned")  # Wrong!

        snapshot_wps = {
            "WP01": {"lane": "done"},
            "WP02": {"lane": "in_progress"},
        }
        findings = validate_derived_views(tmp_path, snapshot_wps, phase=2)
        assert len(findings) == 1
        assert "WP02" in findings[0]

    def test_quoted_lane_value(self, tmp_path: Path):
        """Lane value with quotes in frontmatter should be handled."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        wp_file = tasks_dir / "WP01-test.md"
        wp_file.write_text(
            '---\nwork_package_id: WP01\ntitle: Test\nlane: "in_progress"\n---\n# WP01\n',
            encoding="utf-8",
        )

        snapshot_wps = {"WP01": {"lane": "in_progress"}}
        findings = validate_derived_views(tmp_path, snapshot_wps, phase=2)
        assert findings == []

    def test_tasks_md_missing_status_block(self, tmp_path: Path):
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        self._write_wp_file(tasks_dir, "WP01", "in_progress")
        (tmp_path / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

        snapshot_wps = {"WP01": {"lane": "in_progress"}}
        findings = validate_derived_views(tmp_path, snapshot_wps, phase=2)
        assert any("tasks.md is missing generated canonical status block" in f for f in findings)

    def test_tasks_md_status_block_matches(self, tmp_path: Path):
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        self._write_wp_file(tasks_dir, "WP01", "in_progress")
        (tmp_path / "tasks.md").write_text(
            "\n".join(
                [
                    "# Tasks",
                    "",
                    "<!-- status-model:start -->",
                    "## Canonical Status (Generated)",
                    "- WP01: in_progress",
                    "<!-- status-model:end -->",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        snapshot_wps = {"WP01": {"lane": "in_progress"}}
        findings = validate_derived_views(tmp_path, snapshot_wps, phase=2)
        assert findings == []

    def test_tasks_md_status_block_lane_mismatch(self, tmp_path: Path):
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        self._write_wp_file(tasks_dir, "WP01", "in_progress")
        (tmp_path / "tasks.md").write_text(
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

        snapshot_wps = {"WP01": {"lane": "in_progress"}}
        findings = validate_derived_views(tmp_path, snapshot_wps, phase=2)
        assert any("tasks.md lane=planned" in f for f in findings)
