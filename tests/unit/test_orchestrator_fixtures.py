"""Tests for orchestrator checkpoint fixtures.

Tests for WP05 implementation:
- T021: Base feature structure
- T022: checkpoint_wp_created fixture
- T023: checkpoint_wp_implemented fixture
- T024: checkpoint_review_pending fixture
- T025: Fixture manifest
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.fixtures.orchestrator import (
    CHECKPOINTS,
    FIXTURES_DIR,
    FIXTURES_VERSION,
    get_checkpoint_description,
    get_checkpoint_path,
    list_checkpoints,
)


# =============================================================================
# Fixture Manifest Tests (T025)
# =============================================================================


class TestFixtureManifest:
    """Tests for fixture discovery functions."""

    def test_list_checkpoints_returns_all(self) -> None:
        """list_checkpoints should return all registered checkpoints."""
        checkpoints = list_checkpoints()

        assert "wp_created" in checkpoints
        assert "wp_implemented" in checkpoints
        assert "review_pending" in checkpoints

    def test_list_checkpoints_sorted(self) -> None:
        """list_checkpoints should return sorted list."""
        checkpoints = list_checkpoints()

        assert checkpoints == sorted(checkpoints)

    def test_get_checkpoint_path_valid(self) -> None:
        """get_checkpoint_path should return Path for valid checkpoint."""
        path = get_checkpoint_path("wp_created")

        assert isinstance(path, Path)
        assert path.exists()
        assert path.is_dir()

    def test_get_checkpoint_path_invalid(self) -> None:
        """get_checkpoint_path should raise ValueError for invalid name."""
        with pytest.raises(ValueError, match="Unknown checkpoint"):
            get_checkpoint_path("nonexistent")

    def test_get_checkpoint_description(self) -> None:
        """get_checkpoint_description should return description."""
        desc = get_checkpoint_description("wp_created")

        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_fixtures_version_exists(self) -> None:
        """FIXTURES_VERSION should be defined."""
        assert FIXTURES_VERSION is not None
        assert isinstance(FIXTURES_VERSION, str)


# =============================================================================
# Checkpoint Structure Tests
# =============================================================================


class TestCheckpointStructure:
    """Tests for checkpoint directory structure."""

    @pytest.mark.parametrize("checkpoint_name", list(CHECKPOINTS.keys()))
    def test_checkpoint_has_state_json(self, checkpoint_name: str) -> None:
        """Each checkpoint should have state.json."""
        path = get_checkpoint_path(checkpoint_name)
        state_file = path / "state.json"

        assert state_file.exists(), f"{checkpoint_name} missing state.json"

    @pytest.mark.parametrize("checkpoint_name", list(CHECKPOINTS.keys()))
    def test_checkpoint_has_feature_dir(self, checkpoint_name: str) -> None:
        """Each checkpoint should have feature/ directory."""
        path = get_checkpoint_path(checkpoint_name)
        feature_dir = path / "feature"

        assert feature_dir.exists(), f"{checkpoint_name} missing feature/"
        assert feature_dir.is_dir()

    @pytest.mark.parametrize("checkpoint_name", list(CHECKPOINTS.keys()))
    def test_checkpoint_has_worktrees_json(self, checkpoint_name: str) -> None:
        """Each checkpoint should have worktrees.json."""
        path = get_checkpoint_path(checkpoint_name)
        worktrees_file = path / "worktrees.json"

        assert worktrees_file.exists(), f"{checkpoint_name} missing worktrees.json"

    @pytest.mark.parametrize("checkpoint_name", list(CHECKPOINTS.keys()))
    def test_state_json_is_valid(self, checkpoint_name: str) -> None:
        """state.json should be valid JSON."""
        path = get_checkpoint_path(checkpoint_name)
        state_file = path / "state.json"

        with open(state_file) as f:
            state = json.load(f)

        # Check required fields
        assert "run_id" in state
        assert "feature_slug" in state
        assert "status" in state
        assert "work_packages" in state

    @pytest.mark.parametrize("checkpoint_name", list(CHECKPOINTS.keys()))
    def test_worktrees_json_is_valid(self, checkpoint_name: str) -> None:
        """worktrees.json should be valid JSON with correct structure."""
        path = get_checkpoint_path(checkpoint_name)
        worktrees_file = path / "worktrees.json"

        with open(worktrees_file) as f:
            data = json.load(f)

        assert "worktrees" in data
        assert isinstance(data["worktrees"], list)


# =============================================================================
# Feature Directory Tests
# =============================================================================


class TestFeatureDirectory:
    """Tests for feature/ directory contents."""

    @pytest.mark.parametrize("checkpoint_name", list(CHECKPOINTS.keys()))
    def test_feature_has_spec(self, checkpoint_name: str) -> None:
        """Feature should have spec.md."""
        path = get_checkpoint_path(checkpoint_name)
        spec_file = path / "feature" / "spec.md"

        assert spec_file.exists(), f"{checkpoint_name}/feature missing spec.md"

    @pytest.mark.parametrize("checkpoint_name", list(CHECKPOINTS.keys()))
    def test_feature_has_plan(self, checkpoint_name: str) -> None:
        """Feature should have plan.md."""
        path = get_checkpoint_path(checkpoint_name)
        plan_file = path / "feature" / "plan.md"

        assert plan_file.exists(), f"{checkpoint_name}/feature missing plan.md"

    @pytest.mark.parametrize("checkpoint_name", list(CHECKPOINTS.keys()))
    def test_feature_has_meta(self, checkpoint_name: str) -> None:
        """Feature should have meta.json."""
        path = get_checkpoint_path(checkpoint_name)
        meta_file = path / "feature" / "meta.json"

        assert meta_file.exists(), f"{checkpoint_name}/feature missing meta.json"

    @pytest.mark.parametrize("checkpoint_name", list(CHECKPOINTS.keys()))
    def test_feature_has_tasks(self, checkpoint_name: str) -> None:
        """Feature should have tasks/ directory with WP files."""
        path = get_checkpoint_path(checkpoint_name)
        tasks_dir = path / "feature" / "tasks"

        assert tasks_dir.exists(), f"{checkpoint_name}/feature missing tasks/"
        assert tasks_dir.is_dir()

        # Should have at least WP01.md and WP02.md
        wp_files = list(tasks_dir.glob("WP*.md"))
        assert len(wp_files) >= 2, f"{checkpoint_name} should have at least 2 WP files"


# =============================================================================
# Checkpoint-Specific Tests
# =============================================================================


class TestCheckpointWpCreated:
    """Tests specific to checkpoint_wp_created."""

    def test_all_wps_in_planned_lane(self) -> None:
        """All WPs should be in planned lane."""
        path = get_checkpoint_path("wp_created")
        state_file = path / "state.json"

        with open(state_file) as f:
            state = json.load(f)

        for wp_id, wp in state["work_packages"].items():
            assert wp["status"] == "pending", f"{wp_id} should be pending"

    def test_no_worktrees(self) -> None:
        """Should have no worktrees."""
        path = get_checkpoint_path("wp_created")
        worktrees_file = path / "worktrees.json"

        with open(worktrees_file) as f:
            data = json.load(f)

        assert len(data["worktrees"]) == 0


class TestCheckpointWpImplemented:
    """Tests specific to checkpoint_wp_implemented."""

    def test_wp01_implementation_complete(self) -> None:
        """WP01 should show implementation complete."""
        path = get_checkpoint_path("wp_implemented")
        state_file = path / "state.json"

        with open(state_file) as f:
            state = json.load(f)

        wp01 = state["work_packages"]["WP01"]
        assert wp01["implementation_completed"] is not None
        assert wp01["implementation_agent"] == "claude"

    def test_has_wp01_worktree(self) -> None:
        """Should have WP01 worktree."""
        path = get_checkpoint_path("wp_implemented")
        worktrees_file = path / "worktrees.json"

        with open(worktrees_file) as f:
            data = json.load(f)

        assert len(data["worktrees"]) == 1
        assert data["worktrees"][0]["wp_id"] == "WP01"


class TestCheckpointReviewPending:
    """Tests specific to checkpoint_review_pending."""

    def test_wp01_in_review(self) -> None:
        """WP01 should be in review status."""
        path = get_checkpoint_path("review_pending")
        state_file = path / "state.json"

        with open(state_file) as f:
            state = json.load(f)

        wp01 = state["work_packages"]["WP01"]
        assert wp01["status"] == "review"
        assert wp01["review_agent"] is not None
        assert wp01["review_started"] is not None

    def test_wp01_lane_is_for_review(self) -> None:
        """WP01.md should have lane: for_review."""
        path = get_checkpoint_path("review_pending")
        wp01_file = path / "feature" / "tasks" / "WP01.md"

        content = wp01_file.read_text()
        assert 'lane: "for_review"' in content or "lane: for_review" in content
