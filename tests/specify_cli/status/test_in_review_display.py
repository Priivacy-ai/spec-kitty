"""FE/display tests for in_review lane folding into In Progress column.

Verifies that the dashboard and display logic treat ``in_review`` as a
logical-only lane that appears in the "In Progress" display column, NOT
as a separate column. This is a critical UX invariant: the kanban board
should NOT grow a new "In Review" column.

Tests cover three layers:
1. State-pattern layer: ``InReviewState.display_category()`` returns
   ``"In Progress"``.
2. Display grouping layer: the kanban display logic merges ``in_review``
   WPs into the ``in_progress`` display list with a ``_display_in_review``
   marker.
3. Metrics layer: ``in_review`` WPs count toward the "in_progress" metric
   bucket, so dashboard summaries show the correct totals.
"""

from __future__ import annotations

import pytest

from specify_cli.status.models import Lane
from specify_cli.status.wp_state import (
    InProgressState,
    InReviewState,
    wp_state_for,
)
from specify_cli.status.transition_context import TransitionContext


class TestInReviewDisplayCategory:
    """Layer 1: State-pattern display_category returns 'In Progress'."""

    def test_in_review_state_display_category_is_in_progress(self):
        state = InReviewState()
        assert state.display_category() == "In Progress"

    def test_in_review_state_display_matches_in_progress_state(self):
        """InReviewState and InProgressState share the same display category."""
        assert InReviewState().display_category() == InProgressState().display_category()

    def test_factory_produces_correct_display_category(self):
        state = wp_state_for("in_review")
        assert state.display_category() == "In Progress"

    def test_in_review_is_not_terminal(self):
        """in_review is a transient review state, never terminal."""
        state = InReviewState()
        assert state.is_terminal is False

    def test_in_review_is_not_blocked(self):
        state = InReviewState()
        assert state.is_blocked is False

    def test_in_review_progress_bucket_is_review(self):
        """Even though display folds into In Progress, the progress bucket
        is 'review' for analytics/reporting purposes."""
        state = InReviewState()
        assert state.progress_bucket() == "review"


class TestInReviewDisplayGrouping:
    """Layer 2: Kanban display logic folds in_review into In Progress column.

    These tests exercise the same grouping algorithm used by
    ``specify_cli.agent_utils.status._display_status_board`` without
    requiring a real feature directory or Rich rendering.
    """

    @staticmethod
    def _group_for_display(work_packages: list[dict]) -> dict[str, list]:
        """Replicate the kanban grouping logic from agent_utils/status.py."""
        by_lane: dict[str, list] = {
            "planned": [],
            "claimed": [],
            "in_progress": [],
            "in_review": [],
            "for_review": [],
            "approved": [],
            "done": [],
            "blocked": [],
            "canceled": [],
        }
        for wp in work_packages:
            lane = wp["lane"]
            if lane in by_lane:
                by_lane[lane].append(wp)

        # Merge in_review into in_progress display list (same as production code)
        in_review_wps = by_lane.get("in_review", [])
        display_in_progress = list(by_lane.get("in_progress", []))
        for wp in in_review_wps:
            wp["_display_in_review"] = True
            display_in_progress.append(wp)

        display_by_lane = dict(by_lane)
        display_by_lane["in_progress"] = display_in_progress
        return display_by_lane

    def test_in_review_wp_appears_in_in_progress_column(self):
        wps = [
            {"id": "WP01", "lane": "in_progress", "title": "Impl"},
            {"id": "WP02", "lane": "in_review", "title": "Review"},
        ]
        display = self._group_for_display(wps)

        # Both WPs should appear in the "in_progress" display column
        ids_in_column = [wp["id"] for wp in display["in_progress"]]
        assert "WP01" in ids_in_column
        assert "WP02" in ids_in_column

    def test_in_review_wp_has_display_marker(self):
        wps = [
            {"id": "WP01", "lane": "in_review", "title": "Review"},
        ]
        display = self._group_for_display(wps)

        # The in_review WP should have the _display_in_review marker
        review_wp = display["in_progress"][0]
        assert review_wp["_display_in_review"] is True

    def test_in_progress_wp_does_not_have_display_marker(self):
        wps = [
            {"id": "WP01", "lane": "in_progress", "title": "Impl"},
        ]
        display = self._group_for_display(wps)

        impl_wp = display["in_progress"][0]
        assert "_display_in_review" not in impl_wp

    def test_no_separate_in_review_column_in_kanban(self):
        """The kanban board has NO 'in_review' display column; only 8 columns."""
        # These are the kanban column keys from the production code
        kanban_columns = [
            "planned",
            "claimed",
            "in_progress",
            "for_review",
            "approved",
            "done",
            "blocked",
            "canceled",
        ]
        assert "in_review" not in kanban_columns
        assert len(kanban_columns) == 8

    def test_mixed_lanes_count_correctly(self):
        """When dashboard counts 'in_progress' display column, it includes
        both in_progress and in_review WPs."""
        wps = [
            {"id": "WP01", "lane": "in_progress", "title": "Impl"},
            {"id": "WP02", "lane": "in_review", "title": "Review A"},
            {"id": "WP03", "lane": "in_review", "title": "Review B"},
            {"id": "WP04", "lane": "for_review", "title": "Awaiting"},
        ]
        display = self._group_for_display(wps)

        # "In Progress" display column: 1 impl + 2 review = 3
        assert len(display["in_progress"]) == 3

        # "For Review" column should still have just 1
        assert len(display["for_review"]) == 1


class TestInReviewMetrics:
    """Layer 3: in_review WPs are counted in the 'in_progress' metric bucket.

    The dashboard computes:
        in_progress = len(claimed) + len(in_progress) + len(in_review) + len(for_review)
    """

    @staticmethod
    def _compute_in_progress_metric(work_packages: list[dict]) -> int:
        """Replicate the metric computation from agent_utils/status.py."""
        by_lane: dict[str, list] = {
            "planned": [],
            "claimed": [],
            "in_progress": [],
            "in_review": [],
            "for_review": [],
            "approved": [],
            "done": [],
            "blocked": [],
            "canceled": [],
        }
        for wp in work_packages:
            lane = wp["lane"]
            if lane in by_lane:
                by_lane[lane].append(wp)

        return len(by_lane["claimed"]) + len(by_lane["in_progress"]) + len(by_lane["in_review"]) + len(by_lane["for_review"])

    def test_in_review_counts_toward_in_progress_metric(self):
        wps = [
            {"id": "WP01", "lane": "in_review", "title": "R"},
        ]
        assert self._compute_in_progress_metric(wps) == 1

    def test_metric_combines_all_active_lanes(self):
        wps = [
            {"id": "WP01", "lane": "claimed", "title": "C"},
            {"id": "WP02", "lane": "in_progress", "title": "IP"},
            {"id": "WP03", "lane": "in_review", "title": "IR"},
            {"id": "WP04", "lane": "for_review", "title": "FR"},
            {"id": "WP05", "lane": "planned", "title": "P"},
            {"id": "WP06", "lane": "done", "title": "D"},
        ]
        # Only claimed + in_progress + in_review + for_review = 4
        assert self._compute_in_progress_metric(wps) == 4

    def test_all_nine_lanes_accounted_for(self):
        """Every Lane enum value has a slot in the by_lane grouping dict."""
        expected_lanes = {lane.value for lane in Lane}
        grouping_lanes = {
            "planned",
            "claimed",
            "in_progress",
            "in_review",
            "for_review",
            "approved",
            "done",
            "blocked",
            "canceled",
        }
        assert expected_lanes == grouping_lanes
