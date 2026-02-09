"""Tests for the status emit orchestration pipeline.

Covers the full emit_status_transition pipeline, _saas_fan_out,
TransitionError, force transitions, done-evidence contracts,
alias resolution, and pipeline ordering guarantees.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.status.emit import (
    TransitionError,
    _build_done_evidence,
    _derive_from_lane,
    _saas_fan_out,
    emit_status_transition,
)
from specify_cli.status.models import (
    DoneEvidence,
    Lane,
    ReviewApproval,
    StatusEvent,
    StatusSnapshot,
)
from specify_cli.status.store import EVENTS_FILENAME, read_events


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def feature_dir(tmp_path: Path) -> Path:
    """Create a minimal feature directory for tests."""
    fd = tmp_path / "kitty-specs" / "034-test-feature"
    fd.mkdir(parents=True)
    return fd


@pytest.fixture
def valid_evidence_dict() -> dict:
    """A valid evidence dict for done transitions."""
    return {
        "review": {
            "reviewer": "reviewer-1",
            "verdict": "approved",
            "reference": "PR#42",
        },
        "repos": [
            {
                "repo": "org/repo",
                "branch": "feature-branch",
                "commit": "abc1234",
            }
        ],
        "verification": [
            {
                "command": "pytest tests/ -x",
                "result": "pass",
                "summary": "10 tests passed",
            }
        ],
    }


# ── _derive_from_lane ────────────────────────────────────────


class TestDeriveFromLane:
    """Tests for _derive_from_lane helper."""

    def test_no_events_returns_planned(self, feature_dir: Path):
        """First WP with no events defaults to 'planned'."""
        result = _derive_from_lane(feature_dir, "WP01")
        assert result == "planned"

    def test_returns_last_to_lane_for_wp(self, feature_dir: Path):
        """Derives from_lane from the last event's to_lane for the WP."""
        event = StatusEvent(
            event_id="01HXYZ0000000000000000TEST",
            feature_slug="034-test-feature",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-02-08T12:00:00Z",
            actor="test-actor",
            force=False,
            execution_mode="worktree",
        )
        from specify_cli.status.store import append_event

        append_event(feature_dir, event)

        result = _derive_from_lane(feature_dir, "WP01")
        assert result == "claimed"

    def test_filters_by_wp_id(self, feature_dir: Path):
        """Only considers events for the specified WP."""
        from specify_cli.status.store import append_event

        event_wp01 = StatusEvent(
            event_id="01HXYZ0000000000000000TST1",
            feature_slug="034-test-feature",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-02-08T12:00:00Z",
            actor="test-actor",
            force=False,
            execution_mode="worktree",
        )
        event_wp02 = StatusEvent(
            event_id="01HXYZ0000000000000000TST2",
            feature_slug="034-test-feature",
            wp_id="WP02",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-02-08T12:01:00Z",
            actor="test-actor",
            force=False,
            execution_mode="worktree",
        )
        append_event(feature_dir, event_wp01)
        append_event(feature_dir, event_wp02)

        result = _derive_from_lane(feature_dir, "WP01")
        assert result == "claimed"

    def test_unknown_wp_returns_planned(self, feature_dir: Path):
        """WP with no events in existing log returns 'planned'."""
        from specify_cli.status.store import append_event

        event = StatusEvent(
            event_id="01HXYZ0000000000000000TST3",
            feature_slug="034-test-feature",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-02-08T12:00:00Z",
            actor="test-actor",
            force=False,
            execution_mode="worktree",
        )
        append_event(feature_dir, event)

        result = _derive_from_lane(feature_dir, "WP99")
        assert result == "planned"

    def test_uses_reduced_state_not_append_order(self, feature_dir: Path):
        """Derivation uses canonical reducer order when log lines are out of order."""
        from specify_cli.status.store import append_event

        # Write a later transition first, then an earlier one.
        append_event(
            feature_dir,
            StatusEvent(
                event_id="01HXYZ0000000000000000OO02",
                feature_slug="034-test-feature",
                wp_id="WP01",
                from_lane=Lane.CLAIMED,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T13:00:00Z",
                actor="test-actor",
                force=False,
                execution_mode="worktree",
            ),
        )
        append_event(
            feature_dir,
            StatusEvent(
                event_id="01HXYZ0000000000000000OO01",
                feature_slug="034-test-feature",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.CLAIMED,
                at="2026-02-08T12:00:00Z",
                actor="test-actor",
                force=False,
                execution_mode="worktree",
            ),
        )

        result = _derive_from_lane(feature_dir, "WP01")
        assert result == "in_progress"


# ── _build_done_evidence ─────────────────────────────────────


class TestBuildDoneEvidence:
    """Tests for _build_done_evidence helper."""

    def test_valid_evidence(self, valid_evidence_dict: dict):
        """Builds DoneEvidence from a valid dict."""
        result = _build_done_evidence(valid_evidence_dict)
        assert isinstance(result, DoneEvidence)
        assert result.review.reviewer == "reviewer-1"
        assert result.review.verdict == "approved"
        assert result.review.reference == "PR#42"
        assert len(result.repos) == 1
        assert len(result.verification) == 1

    def test_missing_review_raises(self):
        """Missing 'review' key raises TransitionError."""
        with pytest.raises(TransitionError, match="review.reviewer"):
            _build_done_evidence({"repos": []})

    def test_review_not_dict_raises(self):
        """Non-dict 'review' value raises TransitionError."""
        with pytest.raises(TransitionError, match="review.reviewer"):
            _build_done_evidence({"review": "just a string"})

    def test_missing_reviewer_raises(self):
        """Missing reviewer in review raises TransitionError."""
        with pytest.raises(TransitionError, match="review.reviewer"):
            _build_done_evidence({"review": {"verdict": "approved"}})

    def test_missing_verdict_raises(self):
        """Missing verdict in review raises TransitionError."""
        with pytest.raises(TransitionError, match="review.reviewer"):
            _build_done_evidence({"review": {"reviewer": "rev"}})

    def test_missing_reference_raises(self):
        """Missing approval reference in review raises TransitionError."""
        with pytest.raises(TransitionError, match="review.reference"):
            _build_done_evidence(
                {"review": {"reviewer": "rev", "verdict": "approved"}}
            )

    def test_empty_reviewer_raises(self):
        """Empty reviewer string raises TransitionError."""
        with pytest.raises(TransitionError, match="review.reviewer"):
            _build_done_evidence(
                {"review": {"reviewer": "", "verdict": "approved"}}
            )

    def test_minimal_evidence_works(self):
        """Minimal evidence with required review fields succeeds."""
        result = _build_done_evidence(
            {
                "review": {
                    "reviewer": "rev",
                    "verdict": "approved",
                    "reference": "PR#1",
                }
            }
        )
        assert result.review.reviewer == "rev"
        assert result.review.reference == "PR#1"
        assert result.repos == []
        assert result.verification == []

    def test_extra_fields_accepted(self):
        """Extra fields in evidence dict are silently ignored."""
        result = _build_done_evidence(
            {
                "review": {
                    "reviewer": "rev",
                    "verdict": "approved",
                    "reference": "PR#2",
                },
                "extra_field": "should_be_ignored",
            }
        )
        assert result.review.reviewer == "rev"


# ── emit_status_transition ───────────────────────────────────


class TestEmitStatusTransition:
    """Tests for the main emit orchestration function."""

    def test_happy_path_planned_to_claimed(self, feature_dir: Path):
        """Basic transition from planned to claimed persists and returns event."""
        event = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test-feature",
            wp_id="WP01",
            to_lane="claimed",
            actor="claude-opus",
        )

        assert isinstance(event, StatusEvent)
        assert event.from_lane == Lane.PLANNED
        assert event.to_lane == Lane.CLAIMED
        assert event.wp_id == "WP01"
        assert event.feature_slug == "034-test-feature"
        assert event.actor == "claude-opus"
        assert event.force is False
        assert event.execution_mode == "worktree"
        assert len(event.event_id) == 26  # ULID length

        # Verify event is persisted
        events = read_events(feature_dir)
        assert len(events) == 1
        assert events[0].event_id == event.event_id

    def test_snapshot_materialized(self, feature_dir: Path):
        """Snapshot file is written after successful emit."""
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test-feature",
            wp_id="WP01",
            to_lane="claimed",
            actor="claude-opus",
        )

        snapshot_path = feature_dir / "status.json"
        assert snapshot_path.exists()
        data = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert data["work_packages"]["WP01"]["lane"] == "claimed"

    def test_chained_transitions(self, feature_dir: Path):
        """Multiple transitions chain correctly, deriving from_lane."""
        e1 = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test-feature",
            wp_id="WP01",
            to_lane="claimed",
            actor="agent-1",
        )
        assert e1.from_lane == Lane.PLANNED
        assert e1.to_lane == Lane.CLAIMED

        e2 = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test-feature",
            wp_id="WP01",
            to_lane="in_progress",
            actor="agent-1",
        )
        assert e2.from_lane == Lane.CLAIMED
        assert e2.to_lane == Lane.IN_PROGRESS

        e3 = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test-feature",
            wp_id="WP01",
            to_lane="for_review",
            actor="agent-1",
        )
        assert e3.from_lane == Lane.IN_PROGRESS
        assert e3.to_lane == Lane.FOR_REVIEW

        # Verify 3 events in JSONL
        events = read_events(feature_dir)
        assert len(events) == 3

    def test_alias_resolution_doing(self, feature_dir: Path):
        """'doing' alias resolves to 'in_progress'."""
        # First move to claimed
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test-feature",
            wp_id="WP01",
            to_lane="claimed",
            actor="agent-1",
        )
        # Now use 'doing' alias
        event = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test-feature",
            wp_id="WP01",
            to_lane="doing",
            actor="agent-1",
        )
        assert event.to_lane == Lane.IN_PROGRESS

    def test_invalid_transition_rejected_no_persistence(
        self, feature_dir: Path
    ):
        """Invalid transition raises TransitionError and persists nothing."""
        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="034-test-feature",
                wp_id="WP01",
                to_lane="done",
                actor="agent-1",
            )

        # Verify nothing was persisted
        events_path = feature_dir / EVENTS_FILENAME
        assert not events_path.exists()

    def test_invalid_lane_rejected(self, feature_dir: Path):
        """Unknown lane value raises TransitionError."""
        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="034-test-feature",
                wp_id="WP01",
                to_lane="invalid_lane",
                actor="agent-1",
            )

    def test_execution_mode_direct_repo(self, feature_dir: Path):
        """Non-default execution_mode is recorded in event."""
        event = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test-feature",
            wp_id="WP01",
            to_lane="claimed",
            actor="agent-1",
            execution_mode="direct_repo",
        )
        assert event.execution_mode == "direct_repo"

    def test_multiple_wps_independent(self, feature_dir: Path):
        """Events for different WPs are independent."""
        e1 = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test-feature",
            wp_id="WP01",
            to_lane="claimed",
            actor="agent-1",
        )
        e2 = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test-feature",
            wp_id="WP02",
            to_lane="claimed",
            actor="agent-2",
        )

        assert e1.wp_id == "WP01"
        assert e2.wp_id == "WP02"
        assert e1.from_lane == Lane.PLANNED
        assert e2.from_lane == Lane.PLANNED

        # Both should show in snapshot
        snapshot_path = feature_dir / "status.json"
        data = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert "WP01" in data["work_packages"]
        assert "WP02" in data["work_packages"]


# ── Force Transition Tests ───────────────────────────────────


class TestForceTransitions:
    """Tests for force transition handling."""

    def test_force_illegal_transition_succeeds(self, feature_dir: Path):
        """Force allows normally-illegal transitions (e.g. planned -> done)."""
        event = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test-feature",
            wp_id="WP01",
            to_lane="done",
            actor="admin",
            force=True,
            reason="Emergency fix deployed directly",
        )
        assert event.to_lane == Lane.DONE
        assert event.force is True
        assert event.reason == "Emergency fix deployed directly"

    def test_force_without_actor_rejected(self, feature_dir: Path):
        """Force transition without actor raises TransitionError."""
        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="034-test-feature",
                wp_id="WP01",
                to_lane="done",
                actor="",
                force=True,
                reason="Some reason",
            )

    def test_force_without_reason_rejected(self, feature_dir: Path):
        """Force transition without reason raises TransitionError."""
        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="034-test-feature",
                wp_id="WP01",
                to_lane="done",
                actor="admin",
                force=True,
                reason=None,
            )

    def test_force_with_invalid_lane_rejected(self, feature_dir: Path):
        """Force does not bypass invalid lane names."""
        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="034-test-feature",
                wp_id="WP01",
                to_lane="imaginary",
                actor="admin",
                force=True,
                reason="testing",
            )

    def test_force_no_persistence_on_failure(self, feature_dir: Path):
        """Force transition that fails validation persists nothing."""
        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="034-test-feature",
                wp_id="WP01",
                to_lane="done",
                actor="",
                force=True,
                reason="some reason",
            )
        events_path = feature_dir / EVENTS_FILENAME
        assert not events_path.exists()

    def test_force_from_done_state(self, feature_dir: Path):
        """Force can exit the terminal done state."""
        # First force to done
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test-feature",
            wp_id="WP01",
            to_lane="done",
            actor="admin",
            force=True,
            reason="Initial done",
        )
        # Force back to in_progress
        event = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test-feature",
            wp_id="WP01",
            to_lane="in_progress",
            actor="admin",
            force=True,
            reason="Reopening for fixes",
        )
        assert event.from_lane == Lane.DONE
        assert event.to_lane == Lane.IN_PROGRESS

    def test_force_to_done_without_evidence(self, feature_dir: Path):
        """Force to done bypasses evidence requirement."""
        event = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test-feature",
            wp_id="WP01",
            to_lane="done",
            actor="admin",
            force=True,
            reason="Emergency override, no evidence needed",
        )
        assert event.to_lane == Lane.DONE
        assert event.evidence is None


# ── Done-Evidence Contract ───────────────────────────────────


class TestDoneEvidence:
    """Tests for the done-evidence contract in emit."""

    def test_done_without_evidence_rejected(self, feature_dir: Path):
        """Transition to done without evidence is rejected."""
        # Move through the pipeline to get to for_review
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="claimed",
            actor="a",
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="in_progress",
            actor="a",
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="for_review",
            actor="a",
        )

        with pytest.raises(TransitionError, match="evidence"):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="034-test",
                wp_id="WP01",
                to_lane="done",
                actor="reviewer",
            )

    def test_done_with_valid_evidence(
        self, feature_dir: Path, valid_evidence_dict: dict
    ):
        """Transition to done with valid evidence succeeds."""
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="claimed",
            actor="a",
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="in_progress",
            actor="a",
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="for_review",
            actor="a",
        )

        event = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="done",
            actor="reviewer",
            evidence=valid_evidence_dict,
        )
        assert event.to_lane == Lane.DONE
        assert event.evidence is not None
        assert event.evidence.review.reviewer == "reviewer-1"
        assert event.evidence.review.verdict == "approved"

    def test_done_with_bad_evidence_rejected(self, feature_dir: Path):
        """Transition to done with malformed evidence is rejected."""
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="claimed",
            actor="a",
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="in_progress",
            actor="a",
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="for_review",
            actor="a",
        )

        with pytest.raises(TransitionError, match="review.reviewer"):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="034-test",
                wp_id="WP01",
                to_lane="done",
                actor="reviewer",
                evidence={"not_review": "data"},
            )

        # Verify no done event was persisted (only 3 prior events)
        events = read_events(feature_dir)
        assert len(events) == 3


# ── SaaS Fan-Out Tests ───────────────────────────────────────


class TestSaasFanOut:
    """Tests for _saas_fan_out."""

    def _make_event(
        self,
        *,
        from_lane: Lane = Lane.PLANNED,
        to_lane: Lane = Lane.CLAIMED,
    ) -> StatusEvent:
        return StatusEvent(
            event_id="01HXYZ0000000000000000SAAS",
            feature_slug="034-test-feature",
            wp_id="WP01",
            from_lane=from_lane,
            to_lane=to_lane,
            at="2026-02-08T12:00:00Z",
            actor="test-actor",
            force=False,
            execution_mode="worktree",
        )

    def test_import_error_silently_skipped(self):
        """ImportError from sync module is silently skipped."""
        event = self._make_event()
        import sys

        # Temporarily remove the sync module to simulate ImportError
        saved = sys.modules.get("specify_cli.sync.events")
        sys.modules["specify_cli.sync.events"] = None  # type: ignore[assignment]
        try:
            # Should not raise
            _saas_fan_out(event, "034-test-feature", None)
        finally:
            if saved is not None:
                sys.modules["specify_cli.sync.events"] = saved
            else:
                sys.modules.pop("specify_cli.sync.events", None)

    def test_saas_called_when_available(self):
        """emit_wp_status_changed is called when sync module is available."""
        event = self._make_event(
            from_lane=Lane.CLAIMED,
            to_lane=Lane.IN_PROGRESS,
        )
        mock_emit = MagicMock()
        with patch(
            "specify_cli.sync.events.emit_wp_status_changed", mock_emit
        ):
            _saas_fan_out(event, "034-test-feature", None)

        mock_emit.assert_called_once_with(
            wp_id="WP01",
            previous_status="planned",
            new_status="doing",
            changed_by="test-actor",
            feature_slug="034-test-feature",
        )

    def test_noop_mapping_transition_skipped(self):
        """No-op SaaS transitions are skipped after lane mapping."""
        event = self._make_event(
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
        )
        mock_emit = MagicMock()
        with patch(
            "specify_cli.sync.events.emit_wp_status_changed", mock_emit
        ):
            _saas_fan_out(event, "034-test-feature", None)
        mock_emit.assert_not_called()

    def test_saas_exception_does_not_propagate(self):
        """Exception from SaaS emit is caught and logged."""
        event = self._make_event(
            from_lane=Lane.CLAIMED,
            to_lane=Lane.IN_PROGRESS,
        )
        with patch(
            "specify_cli.sync.events.emit_wp_status_changed",
            side_effect=RuntimeError("network error"),
        ):
            with patch("specify_cli.status.emit.logger") as mock_logger:
                # Should not raise
                _saas_fan_out(event, "034-test-feature", None)
                mock_logger.warning.assert_called_once()

    def test_saas_failure_does_not_block_emit(self, feature_dir: Path):
        """Full emit succeeds even when SaaS fan-out fails."""
        with patch(
            "specify_cli.sync.events.emit_wp_status_changed",
            side_effect=RuntimeError("network down"),
        ):
            event = emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="034-test-feature",
                wp_id="WP01",
                to_lane="claimed",
                actor="agent-1",
            )
            assert event.to_lane == Lane.CLAIMED
            # Event was still persisted
            events = read_events(feature_dir)
            assert len(events) == 1


# ── Pipeline Order Tests ─────────────────────────────────────


class TestPipelineOrder:
    """Tests verifying the critical pipeline ordering."""

    def test_validation_before_persistence(self, feature_dir: Path):
        """Validation failure means nothing is written to disk."""
        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="034-test-feature",
                wp_id="WP01",
                to_lane="done",  # illegal from planned
                actor="agent-1",
            )

        events_path = feature_dir / EVENTS_FILENAME
        assert not events_path.exists()
        snapshot_path = feature_dir / "status.json"
        assert not snapshot_path.exists()

    def test_event_persisted_even_if_materialize_fails(
        self, feature_dir: Path
    ):
        """If materialize fails, the event is still in the JSONL log."""
        with patch(
            "specify_cli.status.emit._reducer.materialize",
            side_effect=OSError("disk error during materialize"),
        ):
            event = emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="034-test-feature",
                wp_id="WP01",
                to_lane="claimed",
                actor="agent-1",
            )

        # Event was persisted even though materialize failed
        events = read_events(feature_dir)
        assert len(events) == 1
        assert events[0].event_id == event.event_id

    def test_legacy_bridge_import_error_handled(self, feature_dir: Path):
        """ImportError from legacy_bridge does not block emit."""
        event = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test-feature",
            wp_id="WP01",
            to_lane="claimed",
            actor="agent-1",
        )
        # If we got here without error, the ImportError was handled
        assert event.to_lane == Lane.CLAIMED

    def test_legacy_bridge_exception_handled(self, feature_dir: Path):
        """Exception from legacy_bridge does not block emit.

        We simulate this by creating a mock module that raises when
        update_all_views is called, then inject it into sys.modules.
        """
        import sys
        import types

        mock_bridge = types.ModuleType("specify_cli.status.legacy_bridge")
        mock_bridge.update_all_views = MagicMock(  # type: ignore[attr-defined]
            side_effect=RuntimeError("bridge broken"),
        )

        saved = sys.modules.get("specify_cli.status.legacy_bridge")
        sys.modules["specify_cli.status.legacy_bridge"] = mock_bridge
        try:
            event = emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="034-test-feature",
                wp_id="WP01",
                to_lane="claimed",
                actor="agent-1",
            )
            assert event.to_lane == Lane.CLAIMED
        finally:
            if saved is not None:
                sys.modules["specify_cli.status.legacy_bridge"] = saved
            else:
                sys.modules.pop("specify_cli.status.legacy_bridge", None)


# ── Review-Ref Guard Tests ───────────────────────────────────


class TestReviewRefGuard:
    """Tests for review_ref requirement on for_review -> in_progress."""

    def test_for_review_to_in_progress_requires_review_ref(
        self, feature_dir: Path
    ):
        """for_review -> in_progress without review_ref is rejected."""
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="claimed",
            actor="a",
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="in_progress",
            actor="a",
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="for_review",
            actor="a",
        )

        with pytest.raises(TransitionError, match="review_ref"):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="034-test",
                wp_id="WP01",
                to_lane="in_progress",
                actor="reviewer",
            )

    def test_for_review_to_in_progress_with_review_ref(
        self, feature_dir: Path
    ):
        """for_review -> in_progress with review_ref succeeds."""
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="claimed",
            actor="a",
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="in_progress",
            actor="a",
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="for_review",
            actor="a",
        )

        event = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="in_progress",
            actor="reviewer",
            review_ref="PR#42-comment-3",
        )
        assert event.review_ref == "PR#42-comment-3"
        assert event.from_lane == Lane.FOR_REVIEW
        assert event.to_lane == Lane.IN_PROGRESS


# ── Reason Guard Tests ───────────────────────────────────────


class TestReasonGuard:
    """Tests for reason requirement on in_progress -> planned."""

    def test_in_progress_to_planned_requires_reason(
        self, feature_dir: Path
    ):
        """in_progress -> planned without reason is rejected."""
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="claimed",
            actor="a",
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="in_progress",
            actor="a",
        )

        with pytest.raises(TransitionError, match="reason"):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="034-test",
                wp_id="WP01",
                to_lane="planned",
                actor="a",
            )

    def test_in_progress_to_planned_with_reason(self, feature_dir: Path):
        """in_progress -> planned with reason succeeds."""
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="claimed",
            actor="a",
        )
        emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="in_progress",
            actor="a",
        )

        event = emit_status_transition(
            feature_dir=feature_dir,
            feature_slug="034-test",
            wp_id="WP01",
            to_lane="planned",
            actor="a",
            reason="Needs more planning",
        )
        assert event.reason == "Needs more planning"
        assert event.to_lane == Lane.PLANNED
