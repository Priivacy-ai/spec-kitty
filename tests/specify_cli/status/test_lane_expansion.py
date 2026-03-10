import pytest
from specify_cli.tasks_support import LANES, LANE_ALIASES, ensure_lane, TaskCliError


class TestLaneExpansion:
    def test_lanes_tuple_has_seven_values(self):
        assert len(LANES) == 7

    def test_lanes_tuple_values(self):
        assert LANES == ("planned", "claimed", "in_progress", "for_review", "done", "blocked", "canceled")

    def test_doing_not_in_lanes(self):
        assert "doing" not in LANES

    def test_doing_in_aliases(self):
        assert "doing" in LANE_ALIASES
        assert LANE_ALIASES["doing"] == "in_progress"

    def test_ensure_lane_doing_resolves(self):
        assert ensure_lane("doing") == "in_progress"

    def test_ensure_lane_claimed_valid(self):
        assert ensure_lane("claimed") == "claimed"

    def test_ensure_lane_blocked_valid(self):
        assert ensure_lane("blocked") == "blocked"

    def test_ensure_lane_canceled_valid(self):
        assert ensure_lane("canceled") == "canceled"

    def test_ensure_lane_in_progress_valid(self):
        assert ensure_lane("in_progress") == "in_progress"

    def test_ensure_lane_planned_valid(self):
        assert ensure_lane("planned") == "planned"

    def test_ensure_lane_for_review_valid(self):
        assert ensure_lane("for_review") == "for_review"

    def test_ensure_lane_done_valid(self):
        assert ensure_lane("done") == "done"

    def test_ensure_lane_case_insensitive(self):
        assert ensure_lane("DOING") == "in_progress"
        assert ensure_lane("Planned") == "planned"
        assert ensure_lane("BLOCKED") == "blocked"

    def test_ensure_lane_strips_whitespace(self):
        assert ensure_lane("  doing  ") == "in_progress"
        assert ensure_lane(" planned ") == "planned"

    def test_ensure_lane_invalid_raises(self):
        with pytest.raises(TaskCliError, match="Invalid lane"):
            ensure_lane("invalid_lane")

    def test_ensure_lane_empty_raises(self):
        with pytest.raises(TaskCliError, match="Invalid lane"):
            ensure_lane("")
