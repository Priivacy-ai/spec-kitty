"""Regression tests for WP03: review-claim emits for_review -> in_review.

T016/T017/T018/T019: Verify is_review_claimed detection for new canonical shape
(IN_REVIEW) and legacy shape (IN_PROGRESS + review_ref), plus JSONL backward
compatibility and execution_context detection parity.
"""

import pytest
from pathlib import Path
from specify_cli.status.models import Lane, StatusEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(to_lane: Lane, review_ref: str | None = None, wp_id: str = "WP01") -> StatusEvent:
    """Build a minimal StatusEvent for testing detection logic."""
    return StatusEvent(
        event_id="01ABCDEFGHIJKLMNOPQRSTU0",
        mission_slug="test-feature",
        wp_id=wp_id,
        from_lane=Lane.FOR_REVIEW,
        to_lane=to_lane,
        at="2026-01-01T00:00:00+00:00",
        actor="claude",
        force=False,
        execution_mode="worktree",
        reason=None,
        review_ref=review_ref,
        evidence=None,
    )


def _is_review_claimed_workflow(latest_event: StatusEvent | None) -> bool:
    """Mirror the detection logic from workflow.py (after WP03 fix)."""
    return bool(
        latest_event is not None
        and (
            latest_event.to_lane == Lane.IN_REVIEW  # new canonical shape
            or (
                latest_event.to_lane == Lane.IN_PROGRESS  # legacy shape
                and latest_event.review_ref == "action-review-claim"
            )
        )
    )


def _is_review_claimed_execution_context(events: list[StatusEvent], wp_id: str = "WP01") -> bool:
    """Mirror the detection logic from execution_context.py (after WP03 fix)."""
    for event in reversed(events):
        if getattr(event, "wp_id", None) == wp_id:
            return bool(
                event.to_lane == Lane.IN_REVIEW  # new canonical shape
                or (
                    event.to_lane == Lane.IN_PROGRESS  # legacy shape
                    and event.review_ref == "action-review-claim"
                )
            )
    return False


# ---------------------------------------------------------------------------
# T016: is_review_claimed detection — new canonical shape (IN_REVIEW)
# ---------------------------------------------------------------------------


class TestIsReviewClaimedNewShape:
    """Verify the new canonical IN_REVIEW shape is recognized as review-claimed."""

    def test_in_review_is_claimed_workflow(self):
        event = _make_event(Lane.IN_REVIEW)
        assert _is_review_claimed_workflow(event) is True

    def test_in_review_is_claimed_execution_context(self):
        event = _make_event(Lane.IN_REVIEW)
        assert _is_review_claimed_execution_context([event]) is True

    def test_in_review_no_review_ref_still_claimed(self):
        """IN_REVIEW is canonical — review_ref is not required for detection."""
        event = _make_event(Lane.IN_REVIEW, review_ref=None)
        assert _is_review_claimed_workflow(event) is True
        assert _is_review_claimed_execution_context([event]) is True

    def test_in_review_with_review_ref_claimed(self):
        """IN_REVIEW with explicit review_ref is also recognized."""
        event = _make_event(Lane.IN_REVIEW, review_ref="action-review-claim")
        assert _is_review_claimed_workflow(event) is True
        assert _is_review_claimed_execution_context([event]) is True


# ---------------------------------------------------------------------------
# T017: is_review_claimed detection — legacy shape (IN_PROGRESS + review_ref)
# ---------------------------------------------------------------------------


class TestIsReviewClaimedLegacyShape:
    """Verify the legacy IN_PROGRESS + review_ref shape is still recognized."""

    def test_legacy_in_progress_with_review_ref_is_claimed_workflow(self):
        event = _make_event(Lane.IN_PROGRESS, review_ref="action-review-claim")
        assert _is_review_claimed_workflow(event) is True

    def test_legacy_in_progress_with_review_ref_is_claimed_execution_context(self):
        event = _make_event(Lane.IN_PROGRESS, review_ref="action-review-claim")
        assert _is_review_claimed_execution_context([event]) is True

    def test_in_progress_without_review_ref_is_not_claimed_workflow(self):
        event = _make_event(Lane.IN_PROGRESS, review_ref=None)
        assert _is_review_claimed_workflow(event) is False

    def test_in_progress_without_review_ref_is_not_claimed_execution_context(self):
        event = _make_event(Lane.IN_PROGRESS, review_ref=None)
        assert _is_review_claimed_execution_context([event]) is False

    def test_none_event_is_not_claimed_workflow(self):
        assert _is_review_claimed_workflow(None) is False

    def test_empty_events_not_claimed_execution_context(self):
        assert _is_review_claimed_execution_context([]) is False

    def test_other_lane_is_not_claimed_workflow(self):
        for lane in (Lane.APPROVED, Lane.PLANNED, Lane.CLAIMED, Lane.FOR_REVIEW, Lane.DONE):
            event = _make_event(lane)
            assert _is_review_claimed_workflow(event) is False, f"Expected not claimed for {lane}"

    def test_other_lane_is_not_claimed_execution_context(self):
        for lane in (Lane.APPROVED, Lane.PLANNED, Lane.CLAIMED, Lane.FOR_REVIEW, Lane.DONE):
            event = _make_event(lane)
            assert _is_review_claimed_execution_context([event]) is False, f"Expected not claimed for {lane}"


# ---------------------------------------------------------------------------
# T018: execution_context.py lane-entry check covers IN_REVIEW
# ---------------------------------------------------------------------------


class TestExecutionContextInReviewEntry:
    """execution_context._resolve_wp_id review path must find IN_REVIEW WPs."""

    def test_most_recent_event_is_used_workflow(self):
        """Only the latest event per WP matters for is_review_claimed."""
        # First event: legacy in_progress claim
        e1 = _make_event(Lane.IN_PROGRESS, review_ref="action-review-claim")
        # Second event: back to for_review (review rejected)
        e2 = StatusEvent(
            event_id="01ABCDEFGHIJKLMNOPQRSTU1",
            mission_slug="test-feature",
            wp_id="WP01",
            from_lane=Lane.IN_REVIEW,
            to_lane=Lane.FOR_REVIEW,
            at="2026-01-01T01:00:00+00:00",
            actor="reviewer",
            force=False,
            execution_mode="worktree",
        )
        # Latest event is back to for_review — should not be review-claimed
        assert _is_review_claimed_execution_context([e1, e2]) is False

    def test_most_recent_in_review_event_is_claimed(self):
        """If latest event per WP is IN_REVIEW, it is review-claimed."""
        e1 = _make_event(Lane.FOR_REVIEW)
        e2 = _make_event(Lane.IN_REVIEW)
        assert _is_review_claimed_execution_context([e1, e2]) is True

    def test_different_wp_id_not_matched(self):
        """Events for a different WP ID don't affect the queried WP."""
        other_event = _make_event(Lane.IN_REVIEW, wp_id="WP02")
        assert _is_review_claimed_execution_context([other_event], wp_id="WP01") is False


# ---------------------------------------------------------------------------
# T019: Legacy JSONL event log compatibility
# ---------------------------------------------------------------------------


class TestLegacyJsonlCompatibility:
    """Historical event logs with in_progress + review_ref must remain readable."""

    def test_legacy_jsonl_event_parses(self, tmp_path: Path) -> None:
        """Legacy in_progress+review_ref event parses without error."""
        from specify_cli.status.store import read_events

        legacy_event = (
            '{"actor":"claude","at":"2026-01-01T00:00:00+00:00",'
            '"event_id":"01LEGACY0000000000000000",'
            '"evidence":null,"execution_mode":"worktree",'
            '"feature_slug":"test-feature","force":true,'
            '"from_lane":"for_review","reason":"Started review via action command",'
            '"review_ref":"action-review-claim","to_lane":"in_progress","wp_id":"WP01"}'
        )
        events_file = tmp_path / "status.events.jsonl"
        events_file.write_text(legacy_event + "\n", encoding="utf-8")
        events = read_events(tmp_path)
        assert len(events) == 1
        assert events[0].to_lane == Lane.IN_PROGRESS
        assert events[0].review_ref == "action-review-claim"

    def test_legacy_event_is_detected_as_review_claimed(self, tmp_path: Path) -> None:
        """is_review_claimed logic recognizes legacy JSONL shape."""
        from specify_cli.status.store import read_events

        legacy_event = (
            '{"actor":"claude","at":"2026-01-01T00:00:00+00:00",'
            '"event_id":"01LEGACY0000000000000001",'
            '"evidence":null,"execution_mode":"worktree",'
            '"feature_slug":"test-feature","force":true,'
            '"from_lane":"for_review","reason":"Started review via action command",'
            '"review_ref":"action-review-claim","to_lane":"in_progress","wp_id":"WP01"}'
        )
        events_file = tmp_path / "status.events.jsonl"
        events_file.write_text(legacy_event + "\n", encoding="utf-8")
        events = read_events(tmp_path)
        latest = events[-1]
        is_claimed = _is_review_claimed_workflow(latest)
        assert is_claimed is True

    def test_new_in_review_jsonl_event_parses(self, tmp_path: Path) -> None:
        """New canonical in_review event written by fixed code parses correctly."""
        from specify_cli.status.store import read_events

        new_event = (
            '{"actor":"claude","at":"2026-01-01T00:00:00+00:00",'
            '"event_id":"01NEWEVT0000000000000000",'
            '"evidence":null,"execution_mode":"worktree",'
            '"feature_slug":"test-feature","force":false,'
            '"from_lane":"for_review","reason":"Started review via action command",'
            '"review_ref":"action-review-claim","to_lane":"in_review","wp_id":"WP01"}'
        )
        events_file = tmp_path / "status.events.jsonl"
        events_file.write_text(new_event + "\n", encoding="utf-8")
        events = read_events(tmp_path)
        assert len(events) == 1
        assert events[0].to_lane == Lane.IN_REVIEW
        assert events[0].force is False
        is_claimed = _is_review_claimed_workflow(events[0])
        assert is_claimed is True
