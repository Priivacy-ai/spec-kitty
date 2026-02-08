"""Tests for rollback-aware conflict resolution in the deterministic reducer.

These tests verify that the reducer correctly handles concurrent events
from parallel worktrees, ensuring that reviewer rollbacks take precedence
over concurrent forward transitions.
"""

from __future__ import annotations

from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.reducer import reduce


def _make_event(
    *,
    event_id: str = "01HXYZ0000000000000000000A",
    feature_slug: str = "034-feature-name",
    wp_id: str = "WP01",
    from_lane: Lane = Lane.PLANNED,
    to_lane: Lane = Lane.CLAIMED,
    at: str = "2026-02-08T12:00:00Z",
    actor: str = "claude-opus",
    force: bool = False,
    execution_mode: str = "worktree",
    reason: str | None = None,
    review_ref: str | None = None,
) -> StatusEvent:
    """Helper to build StatusEvent with sensible defaults."""
    return StatusEvent(
        event_id=event_id,
        feature_slug=feature_slug,
        wp_id=wp_id,
        from_lane=from_lane,
        to_lane=to_lane,
        at=at,
        actor=actor,
        force=force,
        execution_mode=execution_mode,
        reason=reason,
        review_ref=review_ref,
    )


class TestRollbackBeatsForward:
    """Rollback (for_review -> in_progress with review_ref) beats
    concurrent forward (for_review -> done)."""

    def test_rollback_beats_forward(self) -> None:
        """Branch A moves WP01 for_review -> done. Branch B rolls it
        back for_review -> in_progress with a review_ref. Both have
        the same timestamp. Rollback wins."""
        # First, get WP01 to for_review
        setup_events = [
            _make_event(
                event_id="01HXYZ0000000000000000000A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.CLAIMED,
                at="2026-02-08T10:00:00Z",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000B",
                wp_id="WP01",
                from_lane=Lane.CLAIMED,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T11:00:00Z",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000C",
                wp_id="WP01",
                from_lane=Lane.IN_PROGRESS,
                to_lane=Lane.FOR_REVIEW,
                at="2026-02-08T12:00:00Z",
            ),
        ]

        # Concurrent events at same timestamp
        forward_event = _make_event(
            event_id="01HXYZ0000000000000000000D",
            wp_id="WP01",
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.DONE,
            at="2026-02-08T13:00:00Z",
            actor="auto-merger",
        )
        rollback_event = _make_event(
            event_id="01HXYZ0000000000000000000E",
            wp_id="WP01",
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.IN_PROGRESS,
            at="2026-02-08T13:00:00Z",
            actor="reviewer",
            review_ref="PR#42-comment-7",
        )

        # Forward event sorts before rollback (D < E)
        events = setup_events + [forward_event, rollback_event]
        snapshot = reduce(events)

        # Rollback should win
        assert snapshot.work_packages["WP01"]["lane"] == "in_progress"
        assert snapshot.work_packages["WP01"]["actor"] == "reviewer"

    def test_rollback_beats_forward_earlier_timestamp(self) -> None:
        """Even when the rollback event has an earlier event_id (sorts
        first), it still wins over a concurrent forward event."""
        setup_events = [
            _make_event(
                event_id="01HXYZ0000000000000000000A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.FOR_REVIEW,
                at="2026-02-08T12:00:00Z",
            ),
        ]

        # Rollback has earlier event_id but same timestamp
        rollback_event = _make_event(
            event_id="01HXYZ0000000000000000000B",
            wp_id="WP01",
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.IN_PROGRESS,
            at="2026-02-08T13:00:00Z",
            actor="reviewer",
            review_ref="PR#42-review",
        )
        forward_event = _make_event(
            event_id="01HXYZ0000000000000000000C",
            wp_id="WP01",
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.DONE,
            at="2026-02-08T13:00:00Z",
            actor="auto-merger",
        )

        # Even though rollback sorts first, it should still be the
        # final state since forward should not override it
        events = setup_events + [rollback_event, forward_event]
        snapshot = reduce(events)

        assert snapshot.work_packages["WP01"]["lane"] == "in_progress"
        assert snapshot.work_packages["WP01"]["actor"] == "reviewer"


class TestNonConflictingDifferentWPs:
    """Events on different WPs never conflict."""

    def test_non_conflicting_different_wps(self) -> None:
        """Concurrent events on different WPs are both applied."""
        events = [
            _make_event(
                event_id="01HXYZ0000000000000000000A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.FOR_REVIEW,
                at="2026-02-08T12:00:00Z",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000B",
                wp_id="WP02",
                from_lane=Lane.PLANNED,
                to_lane=Lane.FOR_REVIEW,
                at="2026-02-08T12:00:00Z",
            ),
            # Concurrent events at same timestamp on different WPs
            _make_event(
                event_id="01HXYZ0000000000000000000C",
                wp_id="WP01",
                from_lane=Lane.FOR_REVIEW,
                to_lane=Lane.DONE,
                at="2026-02-08T13:00:00Z",
                actor="reviewer-a",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000D",
                wp_id="WP02",
                from_lane=Lane.FOR_REVIEW,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T13:00:00Z",
                actor="reviewer-b",
                review_ref="PR#99-comment",
            ),
        ]
        snapshot = reduce(events)

        # Each WP has its own transition applied independently
        assert snapshot.work_packages["WP01"]["lane"] == "done"
        assert snapshot.work_packages["WP02"]["lane"] == "in_progress"


class TestConcurrentForwardEvents:
    """When two concurrent forward events exist, timestamp+event_id ordering wins."""

    def test_concurrent_forward_events_timestamp_wins(self) -> None:
        """Two forward events at different timestamps; later timestamp wins."""
        events = [
            _make_event(
                event_id="01HXYZ0000000000000000000A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.CLAIMED,
                at="2026-02-08T12:00:00Z",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000B",
                wp_id="WP01",
                from_lane=Lane.CLAIMED,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T13:00:00Z",
            ),
        ]
        snapshot = reduce(events)

        # Later event wins
        assert snapshot.work_packages["WP01"]["lane"] == "in_progress"


class TestConcurrentRollbacks:
    """When two concurrent rollback events exist, sort order applies."""

    def test_concurrent_rollbacks_timestamp_wins(self) -> None:
        """Two rollbacks at the same timestamp; later event_id wins."""
        events = [
            _make_event(
                event_id="01HXYZ0000000000000000000A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.FOR_REVIEW,
                at="2026-02-08T12:00:00Z",
            ),
            # Two concurrent rollbacks
            _make_event(
                event_id="01HXYZ0000000000000000000B",
                wp_id="WP01",
                from_lane=Lane.FOR_REVIEW,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T13:00:00Z",
                actor="reviewer-a",
                review_ref="PR#42-review-a",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000C",
                wp_id="WP01",
                from_lane=Lane.FOR_REVIEW,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T13:00:00Z",
                actor="reviewer-b",
                review_ref="PR#42-review-b",
            ),
        ]
        snapshot = reduce(events)

        # Both are rollbacks, so natural sort order applies.
        # C comes after B in sort order, so C's actor wins.
        assert snapshot.work_packages["WP01"]["lane"] == "in_progress"
        assert snapshot.work_packages["WP01"]["actor"] == "reviewer-b"


class TestSequentialEventsNotConcurrent:
    """Sequential events (different timestamps) are not treated as concurrent."""

    def test_sequential_events_not_concurrent(self) -> None:
        """A forward event followed later by a rollback: rollback wins by
        natural ordering, not by conflict resolution."""
        events = [
            _make_event(
                event_id="01HXYZ0000000000000000000A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.FOR_REVIEW,
                at="2026-02-08T12:00:00Z",
            ),
            # Forward at T+1
            _make_event(
                event_id="01HXYZ0000000000000000000B",
                wp_id="WP01",
                from_lane=Lane.FOR_REVIEW,
                to_lane=Lane.DONE,
                at="2026-02-08T13:00:00Z",
                actor="merger",
            ),
            # Rollback at T+2 (sequential, not concurrent)
            _make_event(
                event_id="01HXYZ0000000000000000000C",
                wp_id="WP01",
                from_lane=Lane.FOR_REVIEW,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T14:00:00Z",
                actor="reviewer",
                review_ref="PR#42-changes",
            ),
        ]
        snapshot = reduce(events)

        # Rollback at later timestamp naturally wins
        assert snapshot.work_packages["WP01"]["lane"] == "in_progress"
        assert snapshot.work_packages["WP01"]["actor"] == "reviewer"


class TestDeduplicationBeforeConflictResolution:
    """Deduplication happens before conflict resolution."""

    def test_deduplication_before_conflict_resolution(self) -> None:
        """Duplicate events are removed before conflict resolution runs,
        so we don't get confused by seeing the same event twice."""
        events = [
            _make_event(
                event_id="01HXYZ0000000000000000000A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.FOR_REVIEW,
                at="2026-02-08T12:00:00Z",
            ),
            # Rollback event
            _make_event(
                event_id="01HXYZ0000000000000000000B",
                wp_id="WP01",
                from_lane=Lane.FOR_REVIEW,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T13:00:00Z",
                actor="reviewer",
                review_ref="PR#42-changes",
            ),
            # Same rollback event again (duplicate from parallel merge)
            _make_event(
                event_id="01HXYZ0000000000000000000B",
                wp_id="WP01",
                from_lane=Lane.FOR_REVIEW,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T13:00:00Z",
                actor="reviewer",
                review_ref="PR#42-changes",
            ),
        ]
        snapshot = reduce(events)

        # Should be 2 events after deduplication, not 3
        assert snapshot.event_count == 2
        assert snapshot.work_packages["WP01"]["lane"] == "in_progress"
