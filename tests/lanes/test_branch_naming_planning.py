"""Regression tests for lane_branch_name() lane-planning behaviour (T011, FR-103).

Verifies that:
- lane_branch_name with lane-planning returns the planning branch, not a kitty/ branch.
- Existing behaviour for normal lane IDs is unchanged.
"""

from __future__ import annotations

import pytest

from specify_cli.lanes.branch_naming import lane_branch_name
from specify_cli.lanes.compute import PLANNING_LANE_ID

pytestmark = pytest.mark.fast


class TestLaneBranchNamePlanningLane:
    """T2.3 — lane_branch_name for lane-planning returns the planning branch."""

    def test_lane_branch_name_planning_returns_main_by_default(self):
        """When no planning_base_branch is given, lane-planning → 'main'."""
        result = lane_branch_name("079-test", "lane-planning")
        assert result == "main"
        assert result != "kitty/mission-079-test-lane-planning"

    def test_lane_branch_name_planning_with_explicit_main(self):
        """Explicit planning_base_branch='main' → 'main'."""
        result = lane_branch_name("079-test", "lane-planning", planning_base_branch="main")
        assert result == "main"

    def test_lane_branch_name_planning_with_custom_branch(self):
        """Explicit planning_base_branch is returned verbatim."""
        result = lane_branch_name("079-test", "lane-planning", planning_base_branch="release/3.x")
        assert result == "release/3.x"

    def test_lane_branch_name_planning_constant(self):
        """PLANNING_LANE_ID resolves to 'main' without a planning_base_branch."""
        result = lane_branch_name("079-test", PLANNING_LANE_ID)
        assert result == "main"

    def test_lane_branch_name_planning_does_not_use_kitty_prefix(self):
        """lane-planning must never produce a kitty/mission-… style name."""
        result = lane_branch_name("079-test", "lane-planning")
        assert not result.startswith("kitty/")


class TestLaneBranchNameNormalLanesUnchanged:
    """Existing behaviour for non-planning lanes must be preserved."""

    def test_lane_branch_name_for_normal_lane_unchanged(self):
        """lane-a style IDs still produce kitty/mission-… names."""
        assert lane_branch_name("079-test", "lane-a") == "kitty/mission-079-test-lane-a"

    def test_lane_branch_name_for_lane_b_unchanged(self):
        assert lane_branch_name("079-test", "lane-b") == "kitty/mission-079-test-lane-b"

    def test_lane_branch_name_normal_lane_ignores_planning_base_branch(self):
        """planning_base_branch is ignored for non-planning lane IDs."""
        result = lane_branch_name("079-test", "lane-a", planning_base_branch="main")
        assert result == "kitty/mission-079-test-lane-a"

    def test_lane_branch_name_slug_with_hyphens(self):
        """Mission slugs with hyphens are preserved verbatim."""
        result = lane_branch_name("079-post-555-release-hardening", "lane-a")
        assert result == "kitty/mission-079-post-555-release-hardening-lane-a"
