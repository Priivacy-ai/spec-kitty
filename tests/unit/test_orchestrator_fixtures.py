"""Tests for orchestrator checkpoint fixtures.

Tests for WP05 implementation:
- T021: Base feature structure
- T022: checkpoint_wp_created fixture
- T023: checkpoint_wp_implemented fixture
- T024: checkpoint_review_pending fixture
- T025: Fixture manifest

Tests for WP11 implementation:
- T052: checkpoint_review_rejected fixture
- T053: checkpoint_review_approved fixture
- T054: checkpoint_wp_merged fixture
- T055: Stale checkpoint detection
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.fixtures.orchestrator import (
    CHECKPOINTS,
    FIXTURES_DIR,
    FIXTURES_VERSION,
    check_fixture_staleness,
    get_checkpoint_description,
    get_checkpoint_path,
    get_checkpoint_with_validation,
    list_checkpoints,
    validate_all_checkpoints,
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


# =============================================================================
# WP11: New Checkpoint Tests (T052-T054)
# =============================================================================


class TestCheckpointReviewRejected:
    """Tests specific to checkpoint_review_rejected (T052)."""

    def test_wp01_review_rejected(self) -> None:
        """WP01 should have review_rejected status."""
        path = get_checkpoint_path("review_rejected")
        state_file = path / "state.json"

        with open(state_file) as f:
            state = json.load(f)

        wp01 = state["work_packages"]["WP01"]
        assert wp01["status"] == "review_rejected"
        assert wp01["review_completed"] is not None
        assert wp01["review_exit_code"] == 1

    def test_has_rejection_reason(self) -> None:
        """WP01 should have rejection_reason."""
        path = get_checkpoint_path("review_rejected")
        state_file = path / "state.json"

        with open(state_file) as f:
            state = json.load(f)

        wp01 = state["work_packages"]["WP01"]
        assert "rejection_reason" in wp01
        assert wp01["rejection_reason"] is not None
        assert len(wp01["rejection_reason"]) > 0

    def test_has_review_count(self) -> None:
        """WP01 should have review_count."""
        path = get_checkpoint_path("review_rejected")
        state_file = path / "state.json"

        with open(state_file) as f:
            state = json.load(f)

        wp01 = state["work_packages"]["WP01"]
        assert "review_count" in wp01
        assert wp01["review_count"] == 1

    def test_wp01_lane_is_doing(self) -> None:
        """WP01.md should have lane: doing (back to re-implementation)."""
        path = get_checkpoint_path("review_rejected")
        wp01_file = path / "feature" / "tasks" / "WP01.md"

        content = wp01_file.read_text()
        assert 'lane: "doing"' in content or "lane: doing" in content

    def test_wp01_review_status_rejected(self) -> None:
        """WP01.md should have review_status: rejected."""
        path = get_checkpoint_path("review_rejected")
        wp01_file = path / "feature" / "tasks" / "WP01.md"

        content = wp01_file.read_text()
        assert 'review_status: "rejected"' in content or "review_status: rejected" in content


class TestCheckpointReviewApproved:
    """Tests specific to checkpoint_review_approved (T053)."""

    def test_wp01_review_approved(self) -> None:
        """WP01 should have review_approved status."""
        path = get_checkpoint_path("review_approved")
        state_file = path / "state.json"

        with open(state_file) as f:
            state = json.load(f)

        wp01 = state["work_packages"]["WP01"]
        assert wp01["status"] == "review_approved"
        assert wp01["review_completed"] is not None
        assert wp01["review_exit_code"] == 0

    def test_has_review_count(self) -> None:
        """WP01 should have review_count."""
        path = get_checkpoint_path("review_approved")
        state_file = path / "state.json"

        with open(state_file) as f:
            state = json.load(f)

        wp01 = state["work_packages"]["WP01"]
        assert "review_count" in wp01
        assert wp01["review_count"] == 1

    def test_wps_completed_is_one(self) -> None:
        """wps_completed should be 1."""
        path = get_checkpoint_path("review_approved")
        state_file = path / "state.json"

        with open(state_file) as f:
            state = json.load(f)

        assert state["wps_completed"] == 1

    def test_wp01_lane_is_for_review(self) -> None:
        """WP01.md should have lane: for_review (awaiting merge)."""
        path = get_checkpoint_path("review_approved")
        wp01_file = path / "feature" / "tasks" / "WP01.md"

        content = wp01_file.read_text()
        assert 'lane: "for_review"' in content or "lane: for_review" in content

    def test_wp01_review_status_approved(self) -> None:
        """WP01.md should have review_status: approved."""
        path = get_checkpoint_path("review_approved")
        wp01_file = path / "feature" / "tasks" / "WP01.md"

        content = wp01_file.read_text()
        assert 'review_status: "approved"' in content or "review_status: approved" in content


class TestCheckpointWpMerged:
    """Tests specific to checkpoint_wp_merged (T054)."""

    def test_wp01_done(self) -> None:
        """WP01 should have done status."""
        path = get_checkpoint_path("wp_merged")
        state_file = path / "state.json"

        with open(state_file) as f:
            state = json.load(f)

        wp01 = state["work_packages"]["WP01"]
        assert wp01["status"] == "done"

    def test_has_merge_commit(self) -> None:
        """WP01 should have merge_commit."""
        path = get_checkpoint_path("wp_merged")
        state_file = path / "state.json"

        with open(state_file) as f:
            state = json.load(f)

        wp01 = state["work_packages"]["WP01"]
        assert "merge_commit" in wp01
        assert wp01["merge_commit"] is not None
        assert len(wp01["merge_commit"]) > 0

    def test_has_merged_at(self) -> None:
        """WP01 should have merged_at timestamp."""
        path = get_checkpoint_path("wp_merged")
        state_file = path / "state.json"

        with open(state_file) as f:
            state = json.load(f)

        wp01 = state["work_packages"]["WP01"]
        assert "merged_at" in wp01
        assert wp01["merged_at"] is not None

    def test_wp01_worktree_removed(self) -> None:
        """WP01 should have no worktree (removed after merge)."""
        path = get_checkpoint_path("wp_merged")
        state_file = path / "state.json"

        with open(state_file) as f:
            state = json.load(f)

        wp01 = state["work_packages"]["WP01"]
        assert wp01["worktree_path"] is None

    def test_wp02_in_progress(self) -> None:
        """WP02 should be in_progress (dependency satisfied)."""
        path = get_checkpoint_path("wp_merged")
        state_file = path / "state.json"

        with open(state_file) as f:
            state = json.load(f)

        wp02 = state["work_packages"]["WP02"]
        assert wp02["status"] == "in_progress"
        assert wp02["implementation_started"] is not None

    def test_wp02_worktree_active(self) -> None:
        """WP02 worktree should be active."""
        path = get_checkpoint_path("wp_merged")
        worktrees_file = path / "worktrees.json"

        with open(worktrees_file) as f:
            data = json.load(f)

        assert len(data["worktrees"]) == 1
        assert data["worktrees"][0]["wp_id"] == "WP02"

    def test_wp01_lane_is_done(self) -> None:
        """WP01.md should have lane: done."""
        path = get_checkpoint_path("wp_merged")
        wp01_file = path / "feature" / "tasks" / "WP01.md"

        content = wp01_file.read_text()
        assert 'lane: "done"' in content or "lane: done" in content


# =============================================================================
# WP11: Stale Checkpoint Detection Tests (T055)
# =============================================================================


class TestStalenessDetection:
    """Tests for fixture staleness detection (T055)."""

    def test_all_checkpoints_have_version(self) -> None:
        """All checkpoints should have fixture_version field."""
        for name in list_checkpoints():
            path = get_checkpoint_path(name)
            state_file = path / "state.json"

            with open(state_file) as f:
                state = json.load(f)

            assert "fixture_version" in state, f"{name} missing fixture_version"

    def test_all_checkpoints_version_matches(self) -> None:
        """All checkpoints should have matching fixture_version."""
        for name in list_checkpoints():
            path = get_checkpoint_path(name)
            state_file = path / "state.json"

            with open(state_file) as f:
                state = json.load(f)

            assert state["fixture_version"] == FIXTURES_VERSION, (
                f"{name} version mismatch: {state['fixture_version']} != {FIXTURES_VERSION}"
            )

    def test_check_fixture_staleness_valid(self) -> None:
        """check_fixture_staleness should return False for valid fixture."""
        path = get_checkpoint_path("wp_created")
        is_stale, warning = check_fixture_staleness(path)

        assert is_stale is False
        assert warning is None

    def test_check_fixture_staleness_missing_version(self, tmp_path: Path) -> None:
        """check_fixture_staleness should detect missing version."""
        # Create fixture without version
        state_file = tmp_path / "state.json"
        state_file.write_text('{"run_id": "test"}')

        is_stale, warning = check_fixture_staleness(tmp_path)

        assert is_stale is True
        assert warning is not None
        assert "no version field" in warning

    def test_check_fixture_staleness_wrong_version(self, tmp_path: Path) -> None:
        """check_fixture_staleness should detect version mismatch."""
        # Create fixture with wrong version
        state_file = tmp_path / "state.json"
        state_file.write_text('{"fixture_version": "0.0.0", "run_id": "test"}')

        is_stale, warning = check_fixture_staleness(tmp_path)

        assert is_stale is True
        assert warning is not None
        assert "version mismatch" in warning

    def test_check_fixture_staleness_missing_state(self, tmp_path: Path) -> None:
        """check_fixture_staleness should detect missing state.json."""
        is_stale, warning = check_fixture_staleness(tmp_path)

        assert is_stale is True
        assert warning is not None
        assert "Missing state.json" in warning

    def test_check_fixture_staleness_invalid_json(self, tmp_path: Path) -> None:
        """check_fixture_staleness should detect invalid JSON."""
        state_file = tmp_path / "state.json"
        state_file.write_text("not valid json")

        is_stale, warning = check_fixture_staleness(tmp_path)

        assert is_stale is True
        assert warning is not None
        assert "Invalid JSON" in warning

    def test_validate_all_checkpoints_success(self) -> None:
        """validate_all_checkpoints should return empty list for valid fixtures."""
        warnings = validate_all_checkpoints()

        assert warnings == [], f"Unexpected warnings: {warnings}"

    def test_get_checkpoint_with_validation_valid(self) -> None:
        """get_checkpoint_with_validation should not warn for valid fixture."""
        import warnings as w

        with w.catch_warnings(record=True) as caught:
            w.simplefilter("always")
            path = get_checkpoint_with_validation("wp_created")

        assert path.exists()
        # No warnings should be raised for valid fixture
        stale_warnings = [x for x in caught if "version" in str(x.message)]
        assert len(stale_warnings) == 0
