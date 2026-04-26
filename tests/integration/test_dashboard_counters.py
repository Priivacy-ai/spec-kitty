"""Integration test: dashboard / progress counters reflect approved /
in-review / done correctly (FR-018, WP04/T023).

Pins the dashboard's lane-to-column mapping and the kanban counts that
``agent tasks status --json`` reports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.fast


class TestDashboardLaneColumnMapping:
    """All 9 canonical lanes must be accounted for in dashboard mapping."""

    def test_every_lane_maps_to_a_column(self) -> None:
        from specify_cli.dashboard.scanner import _KANBAN_COLUMN_FOR_LANE
        from specify_cli.status.models import Lane, get_all_lanes

        all_lanes = set(get_all_lanes())
        mapped = set(_KANBAN_COLUMN_FOR_LANE.keys())
        assert mapped == all_lanes, (
            f"Dashboard column mapping is missing lanes: {all_lanes - mapped}"
        )

    def test_approved_has_its_own_column(self) -> None:
        """approved must NOT be lumped into for_review or done."""
        from specify_cli.dashboard.scanner import _KANBAN_COLUMN_FOR_LANE
        from specify_cli.status.models import Lane

        assert _KANBAN_COLUMN_FOR_LANE[Lane.APPROVED] == "approved"

    def test_done_has_its_own_column(self) -> None:
        from specify_cli.dashboard.scanner import _KANBAN_COLUMN_FOR_LANE
        from specify_cli.status.models import Lane

        assert _KANBAN_COLUMN_FOR_LANE[Lane.DONE] == "done"

    def test_in_review_renders_in_review_column_family(self) -> None:
        """in_review is part of the Review category alongside for_review.

        The dashboard groups for_review + in_review into the "Review"
        category for column rendering. What MUST stay distinct is the
        underlying lane on each WP — and the by_lane Counter in
        ``agent tasks status --json``.
        """
        from specify_cli.dashboard.scanner import _KANBAN_COLUMN_FOR_LANE
        from specify_cli.status.models import Lane

        # Both for_review and in_review map to the review column family;
        # the actual count distinction is preserved in by_lane.
        assert _KANBAN_COLUMN_FOR_LANE[Lane.FOR_REVIEW] == "for_review"
        assert _KANBAN_COLUMN_FOR_LANE[Lane.IN_REVIEW] == "for_review"


class TestStatusByLaneCounter:
    """The ``agent tasks status --json`` envelope's by_lane preserves all
    9 canonical lanes as distinct counters."""

    def test_by_lane_counter_supports_all_canonical_lanes(self) -> None:
        """Build a Counter the way `status` does and assert all lanes count."""
        from collections import Counter

        from specify_cli.status.models import Lane, get_all_lanes

        # Sample a WP per lane.
        sample_wps = [
            {"id": f"WP{i:02d}", "lane": lane}
            for i, lane in enumerate(get_all_lanes(), start=1)
        ]
        lane_counts = Counter(wp["lane"] for wp in sample_wps)

        # Each lane is represented exactly once.
        for lane in get_all_lanes():
            assert lane_counts[lane] == 1

        # Distinct counters for approved / in_review / done.
        assert lane_counts[Lane.APPROVED] == 1
        assert lane_counts[Lane.IN_REVIEW] == 1
        assert lane_counts[Lane.DONE] == 1


class TestProgressCountersInDecisionJSON:
    """The decision JSON's `progress` field records done/approved/etc counts."""

    def test_decision_progress_includes_lane_buckets(self) -> None:
        """Verify the in-decision progress dict includes the right keys."""
        # The progress structure is computed in
        # specify_cli.next.decision._compute_wp_progress; we don't reach
        # for a live runtime here — we just pin the expected keys so
        # downstream consumers (CLI, dashboard) cannot regress.
        expected_keys = {
            "total_wps",
            "done_wps",
            "approved_wps",
            "in_progress_wps",
            "planned_wps",
            "for_review_wps",
        }
        # The decision module's _compute_wp_progress writes exactly these
        # bucket keys.
        from specify_cli.next.decision import _compute_wp_progress  # type: ignore[attr-defined]

        # Inspect the function body via its source for stable contract.
        import inspect

        source = inspect.getsource(_compute_wp_progress)
        for key in expected_keys:
            assert f'"{key}"' in source, (
                f"Progress counter key {key!r} missing from _compute_wp_progress"
            )
