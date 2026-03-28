"""Scope: lane expansion unit tests — no real git or subprocesses."""

import pytest
from specify_cli.tasks_support import LANES, LANE_ALIASES, ensure_lane, TaskCliError

pytestmark = pytest.mark.fast


class TestLaneExpansion:
    def test_lanes_tuple_has_nine_values(self):
        """LANES tuple contains exactly nine canonical lane values."""
        # Arrange / Act — LANES is a module constant
        # Assumption check
        assert isinstance(LANES, tuple)
        # Assert
        assert len(LANES) == 9

    def test_lanes_tuple_values(self):
        """LANES matches the expected ordered set of canonical lane names."""
        # Arrange / Assumption check — constant from import
        # Act / Assert
        assert LANES == ("planned", "claimed", "in_progress", "for_review", "in_review", "approved", "done", "blocked", "canceled")

    def test_doing_not_in_lanes(self):
        """'doing' is an alias, not a canonical lane value."""
        # Arrange / Act — module-level constant
        # Assert
        assert "doing" not in LANES

    def test_doing_in_aliases(self):
        """'doing' alias maps to 'in_progress' in LANE_ALIASES."""
        # Arrange / Act — module-level constant
        # Assert
        assert "doing" in LANE_ALIASES
        assert LANE_ALIASES["doing"] == "in_progress"

    def test_ensure_lane_doing_resolves(self):
        """ensure_lane('doing') expands to 'in_progress'."""
        # Arrange
        alias = "doing"
        # Assumption check
        assert alias in LANE_ALIASES
        # Act / Assert
        assert ensure_lane(alias) == "in_progress"

    def test_ensure_lane_claimed_valid(self):
        """ensure_lane('claimed') returns 'claimed' unchanged."""
        # Arrange / Assumption check
        assert "claimed" in LANES
        # Act / Assert
        assert ensure_lane("claimed") == "claimed"

    def test_ensure_lane_blocked_valid(self):
        """ensure_lane('blocked') returns 'blocked' unchanged."""
        # Arrange / Assumption check
        assert "blocked" in LANES
        # Act / Assert
        assert ensure_lane("blocked") == "blocked"

    def test_ensure_lane_canceled_valid(self):
        """ensure_lane('canceled') returns 'canceled' unchanged."""
        # Arrange / Assumption check
        assert "canceled" in LANES
        # Act / Assert
        assert ensure_lane("canceled") == "canceled"

    def test_ensure_lane_in_progress_valid(self):
        """ensure_lane('in_progress') returns 'in_progress' unchanged."""
        # Arrange / Assumption check
        assert "in_progress" in LANES
        # Act / Assert
        assert ensure_lane("in_progress") == "in_progress"

    def test_ensure_lane_planned_valid(self):
        """ensure_lane('planned') returns 'planned' unchanged."""
        # Arrange / Assumption check
        assert "planned" in LANES
        # Act / Assert
        assert ensure_lane("planned") == "planned"

    def test_ensure_lane_for_review_valid(self):
        """ensure_lane('for_review') returns 'for_review' unchanged."""
        # Arrange / Assumption check
        assert "for_review" in LANES
        # Act / Assert
        assert ensure_lane("for_review") == "for_review"

    def test_ensure_lane_approved_valid(self):
        """ensure_lane('approved') returns 'approved' unchanged."""
        # Arrange / Assumption check
        assert "approved" in LANES
        # Act / Assert
        assert ensure_lane("approved") == "approved"

    def test_ensure_lane_done_valid(self):
        """ensure_lane('done') returns 'done' unchanged."""
        # Arrange / Assumption check
        assert "done" in LANES
        # Act / Assert
        assert ensure_lane("done") == "done"

    def test_ensure_lane_case_insensitive(self):
        """ensure_lane normalises input to lowercase before resolving."""
        # Arrange
        inputs = [("DOING", "in_progress"), ("Planned", "planned"), ("BLOCKED", "blocked")]
        # Assumption check
        assert len(inputs) == 3
        # Act / Assert
        for raw, expected in inputs:
            assert ensure_lane(raw) == expected

    def test_ensure_lane_strips_whitespace(self):
        """ensure_lane strips surrounding whitespace before resolving."""
        # Arrange
        inputs = [("  doing  ", "in_progress"), (" planned ", "planned")]
        # Assumption check
        assert len(inputs) == 2
        # Act / Assert
        for raw, expected in inputs:
            assert ensure_lane(raw) == expected

    def test_ensure_lane_invalid_raises(self):
        """Unknown lane name raises TaskCliError with 'Invalid lane' message."""
        # Arrange
        bad = "invalid_lane"
        # Assumption check
        assert bad not in LANES and bad not in LANE_ALIASES
        # Act / Assert
        with pytest.raises(TaskCliError, match="Invalid lane"):
            ensure_lane(bad)

    def test_ensure_lane_empty_raises(self):
        """Empty string raises TaskCliError with 'Invalid lane' message."""
        # Arrange
        bad = ""
        # Assumption check
        assert bad not in LANES
        # Act / Assert
        with pytest.raises(TaskCliError, match="Invalid lane"):
            ensure_lane(bad)
