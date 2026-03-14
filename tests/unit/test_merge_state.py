"""Unit tests for merge state persistence module.

Tests the MergeState dataclass and state persistence functions for
resumable merge operations.
"""

from __future__ import annotations


import pytest

from specify_cli.merge.state import (
    MergeState,
    clear_state,
    get_state_path,
    has_active_merge,
    load_state,
    save_state,
)


class TestMergeStateDataclass:
    """Tests for MergeState dataclass."""

    def test_create_minimal(self):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03"],
        )
        assert state.feature_slug == "test-feature"
        assert state.target_branch == "main"
        assert state.wp_order == ["WP01", "WP02", "WP03"]
        assert state.completed_wps == []
        assert state.current_wp is None
        assert state.has_pending_conflicts is False
        assert state.strategy == "merge"

    def test_remaining_wps(self):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03"],
            completed_wps=["WP01"],
        )
        assert state.remaining_wps == ["WP02", "WP03"]

    def test_remaining_wps_all_complete(self):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02"],
            completed_wps=["WP01", "WP02"],
        )
        assert state.remaining_wps == []

    def test_progress_percent_zero(self):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03"],
        )
        assert state.progress_percent == 0.0

    def test_progress_percent_partial(self):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03", "WP04"],
            completed_wps=["WP01", "WP02"],
        )
        assert state.progress_percent == 50.0

    def test_progress_percent_complete(self):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02"],
            completed_wps=["WP01", "WP02"],
        )
        assert state.progress_percent == 100.0

    def test_progress_percent_empty_wp_order(self):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=[],
        )
        assert state.progress_percent == 0.0

    def test_mark_wp_complete(self):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02"],
            current_wp="WP01",
            has_pending_conflicts=True,
        )
        state.mark_wp_complete("WP01")
        assert "WP01" in state.completed_wps
        assert state.current_wp is None
        assert state.has_pending_conflicts is False

    def test_mark_wp_complete_no_duplicate(self):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02"],
            completed_wps=["WP01"],
        )
        state.mark_wp_complete("WP01")
        assert state.completed_wps == ["WP01"]  # Still only one entry

    def test_set_current_wp(self):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02"],
        )
        state.set_current_wp("WP02")
        assert state.current_wp == "WP02"

    def test_set_pending_conflicts(self):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01"],
        )
        state.set_pending_conflicts(True)
        assert state.has_pending_conflicts is True
        state.set_pending_conflicts(False)
        assert state.has_pending_conflicts is False

    def test_to_dict(self):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02"],
            completed_wps=["WP01"],
            current_wp="WP02",
            strategy="squash",
        )
        d = state.to_dict()
        assert d["feature_slug"] == "test-feature"
        assert d["target_branch"] == "main"
        assert d["wp_order"] == ["WP01", "WP02"]
        assert d["completed_wps"] == ["WP01"]
        assert d["current_wp"] == "WP02"
        assert d["strategy"] == "squash"

    def test_from_dict(self):
        data = {
            "feature_slug": "test-feature",
            "target_branch": "main",
            "wp_order": ["WP01", "WP02"],
            "completed_wps": ["WP01"],
            "current_wp": "WP02",
            "has_pending_conflicts": True,
            "strategy": "squash",
            "started_at": "2026-01-18T10:00:00",
            "updated_at": "2026-01-18T10:30:00",
        }
        state = MergeState.from_dict(data)
        assert state.feature_slug == "test-feature"
        assert state.completed_wps == ["WP01"]
        assert state.current_wp == "WP02"
        assert state.has_pending_conflicts is True


class TestStatePersistence:
    """Tests for save_state, load_state, and clear_state functions."""

    def test_save_and_load_state(self, tmp_path):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03"],
            completed_wps=["WP01"],
            current_wp="WP02",
        )
        save_state(state, tmp_path)

        loaded = load_state(tmp_path)
        assert loaded is not None
        assert loaded.feature_slug == "test-feature"
        assert loaded.wp_order == ["WP01", "WP02", "WP03"]
        assert loaded.completed_wps == ["WP01"]
        assert loaded.current_wp == "WP02"

    def test_get_state_path(self, tmp_path):
        path = get_state_path(tmp_path)
        assert path == tmp_path / ".kittify" / "merge-state.json"

    def test_load_state_missing_file(self, tmp_path):
        result = load_state(tmp_path)
        assert result is None

    def test_load_state_invalid_json(self, tmp_path):
        state_file = tmp_path / ".kittify" / "merge-state.json"
        state_file.parent.mkdir(parents=True)
        state_file.write_text("not valid json{", encoding="utf-8")

        result = load_state(tmp_path)
        assert result is None

    def test_load_state_missing_fields(self, tmp_path):
        state_file = tmp_path / ".kittify" / "merge-state.json"
        state_file.parent.mkdir(parents=True)
        state_file.write_text('{"feature_slug": "test"}', encoding="utf-8")

        result = load_state(tmp_path)
        assert result is None  # Missing required fields

    def test_clear_state(self, tmp_path):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01"],
        )
        save_state(state, tmp_path)

        # Verify file exists
        state_path = get_state_path(tmp_path)
        assert state_path.exists()

        # Clear and verify
        result = clear_state(tmp_path)
        assert result is True
        assert not state_path.exists()

    def test_clear_state_no_file(self, tmp_path):
        result = clear_state(tmp_path)
        assert result is False

    def test_save_creates_directory(self, tmp_path):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01"],
        )
        # .kittify directory shouldn't exist yet
        kittify_dir = tmp_path / ".kittify"
        assert not kittify_dir.exists()

        save_state(state, tmp_path)

        assert kittify_dir.exists()
        assert (kittify_dir / "merge-state.json").exists()


class TestHasActiveMerge:
    """Tests for has_active_merge function."""

    def test_no_state_file(self, tmp_path):
        assert has_active_merge(tmp_path) is False

    def test_active_merge_with_remaining_wps(self, tmp_path):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02"],
            completed_wps=["WP01"],
        )
        save_state(state, tmp_path)
        assert has_active_merge(tmp_path) is True

    def test_no_active_merge_all_complete(self, tmp_path):
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02"],
            completed_wps=["WP01", "WP02"],
        )
        save_state(state, tmp_path)
        assert has_active_merge(tmp_path) is False


class TestStateRoundTrip:
    """Integration tests for complete state round-trip."""

    def test_complete_workflow(self, tmp_path):
        # Start merge
        state = MergeState(
            feature_slug="017-feature",
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03"],
            strategy="squash",
        )
        save_state(state, tmp_path)

        # Merge WP01
        state.set_current_wp("WP01")
        save_state(state, tmp_path)

        state.mark_wp_complete("WP01")
        save_state(state, tmp_path)

        # Simulate interruption - load from file
        loaded = load_state(tmp_path)
        assert loaded is not None
        assert loaded.completed_wps == ["WP01"]
        assert loaded.remaining_wps == ["WP02", "WP03"]
        assert loaded.progress_percent == pytest.approx(33.33, rel=0.01)

        # Continue with WP02
        loaded.set_current_wp("WP02")
        save_state(loaded, tmp_path)

        loaded.mark_wp_complete("WP02")
        save_state(loaded, tmp_path)

        # Verify final state
        final = load_state(tmp_path)
        assert final is not None
        assert final.completed_wps == ["WP01", "WP02"]
        assert final.remaining_wps == ["WP03"]
        assert final.progress_percent == pytest.approx(66.67, rel=0.01)
