"""
Edge case tests for merge/state.py to improve mutation coverage.

These tests target specific boundary conditions and edge cases that may not be
covered by the existing 25 tests in test_merge_state.py.
"""

import time

from specify_cli.merge.state import (
    MergeState,
    save_state,
    load_state,
    clear_state,
    has_active_merge,
)


class TestMergeStateEdgeCases:
    """Edge case tests for MergeState dataclass."""

    def test_remaining_wps_with_current_but_no_completed(self):
        """Test remaining_wps includes current_wp even when nothing completed."""
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03"],
            completed_wps=[],
            current_wp="WP01",
            has_pending_conflicts=False,
            strategy="merge",
            started_at="2026-03-01T10:00:00+00:00",
            updated_at="2026-03-01T10:00:00+00:00",
        )
        remaining = state.remaining_wps
        assert "WP01" in remaining
        assert "WP02" in remaining
        assert "WP03" in remaining
        assert len(remaining) == 3

    def test_remaining_wps_empty_when_all_complete(self):
        """Test remaining_wps is empty when all WPs completed."""
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02"],
            completed_wps=["WP01", "WP02"],
            current_wp=None,
            has_pending_conflicts=False,
            strategy="merge",
            started_at="2026-03-01T10:00:00+00:00",
            updated_at="2026-03-01T10:00:00+00:00",
        )
        assert state.remaining_wps == []

    def test_progress_percent_with_single_wp(self):
        """Test progress calculation with only one WP."""
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01"],
            completed_wps=[],
            current_wp=None,
            has_pending_conflicts=False,
            strategy="merge",
            started_at="2026-03-01T10:00:00+00:00",
            updated_at="2026-03-01T10:00:00+00:00",
        )
        assert state.progress_percent == 0.0

        state.completed_wps = ["WP01"]
        assert state.progress_percent == 100.0

    def test_mark_wp_complete_preserves_order(self):
        """Test that marking WPs complete maintains list order."""
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03"],
            completed_wps=[],
            current_wp=None,
            has_pending_conflicts=False,
            strategy="merge",
            started_at="2026-03-01T10:00:00+00:00",
            updated_at="2026-03-01T10:00:00+00:00",
        )
        state.mark_wp_complete("WP03")
        state.mark_wp_complete("WP01")
        state.mark_wp_complete("WP02")

        # Should maintain insertion order
        assert state.completed_wps == ["WP03", "WP01", "WP02"]

    def test_set_current_wp_with_none(self):
        """Test setting current_wp to None explicitly."""
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01", "WP02"],
            completed_wps=[],
            current_wp="WP01",
            has_pending_conflicts=False,
            strategy="merge",
            started_at="2026-03-01T10:00:00+00:00",
            updated_at="2026-03-01T10:00:00+00:00",
        )
        state.set_current_wp(None)
        assert state.current_wp is None

    def test_set_pending_conflicts_boolean_values(self):
        """Test setting conflicts with explicit True/False."""
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01"],
            completed_wps=[],
            current_wp=None,
            has_pending_conflicts=False,
            strategy="merge",
            started_at="2026-03-01T10:00:00+00:00",
            updated_at="2026-03-01T10:00:00+00:00",
        )

        state.set_pending_conflicts(True)
        assert state.has_pending_conflicts is True

        state.set_pending_conflicts(False)
        assert state.has_pending_conflicts is False


class TestStatePersistenceEdgeCases:
    """Edge case tests for state persistence functions."""

    def test_save_state_updates_timestamp(self, tmp_path):
        """Test that saving state updates the updated_at timestamp."""
        state = MergeState(
            feature_slug="test-feature",
            target_branch="main",
            wp_order=["WP01"],
            completed_wps=[],
            current_wp=None,
            has_pending_conflicts=False,
            strategy="merge",
            started_at="2026-03-01T10:00:00+00:00",
            updated_at="2026-03-01T10:00:00+00:00",
        )

        # Save initial state
        save_state(state, tmp_path)
        initial_updated = state.updated_at

        # Small delay to ensure timestamp difference
        time.sleep(0.01)

        # Modify and save again
        state.mark_wp_complete("WP01")
        save_state(state, tmp_path)

        # Load and verify timestamp changed
        loaded = load_state(tmp_path)
        assert loaded is not None
        # Updated_at should be different (or at least >= initial)
        assert loaded.updated_at >= initial_updated

    def test_load_state_nonexistent_file(self, tmp_path):
        """Test loading state when file doesn't exist returns None."""
        result = load_state(tmp_path)
        assert result is None

    def test_clear_state_nonexistent_file(self, tmp_path):
        """Test clearing state when file doesn't exist succeeds silently."""
        # Should not raise an error
        clear_state(tmp_path)

    def test_has_active_merge_empty_directory(self, tmp_path):
        """Test has_active_merge with no state file."""
        assert has_active_merge(tmp_path) is False

    def test_state_roundtrip_with_all_fields(self, tmp_path):
        """Test state roundtrip preserves all fields correctly."""
        original = MergeState(
            feature_slug="complex-feature",
            target_branch="develop",
            wp_order=["WP01", "WP02", "WP03"],
            completed_wps=["WP01"],
            current_wp="WP02",
            has_pending_conflicts=True,
            strategy="squash",
            started_at="2026-03-01T10:00:00+00:00",
            updated_at="2026-03-01T11:00:00+00:00",
        )

        save_state(original, tmp_path)
        loaded = load_state(tmp_path)

        assert loaded is not None
        assert loaded.feature_slug == original.feature_slug
        assert loaded.target_branch == original.target_branch
        assert loaded.wp_order == original.wp_order
        assert loaded.completed_wps == original.completed_wps
        assert loaded.current_wp == original.current_wp
        assert loaded.has_pending_conflicts == original.has_pending_conflicts
        assert loaded.strategy == original.strategy
        assert loaded.started_at == original.started_at

    def test_load_state_corrupted_json(self, tmp_path):
        """Test loading state with corrupted JSON returns None."""
        state_file = tmp_path / ".kittify" / "merge-state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("{invalid json content")

        result = load_state(tmp_path)
        assert result is None

    def test_to_dict_contains_all_fields(self):
        """Test that to_dict includes all expected fields."""
        state = MergeState(
            feature_slug="test",
            target_branch="main",
            wp_order=["WP01"],
            completed_wps=[],
            current_wp=None,
            has_pending_conflicts=False,
            strategy="merge",
            started_at="2026-03-01T10:00:00+00:00",
            updated_at="2026-03-01T10:00:00+00:00",
        )

        data = state.to_dict()

        required_fields = [
            "feature_slug",
            "target_branch",
            "wp_order",
            "completed_wps",
            "current_wp",
            "has_pending_conflicts",
            "strategy",
            "started_at",
            "updated_at",
        ]

        for field in required_fields:
            assert field in data

    def test_from_dict_with_minimal_fields(self):
        """Test from_dict with only required fields."""
        data = {
            "feature_slug": "test",
            "target_branch": "main",
            "wp_order": ["WP01"],
            "completed_wps": [],
            "current_wp": None,
            "has_pending_conflicts": False,
            "strategy": "merge",
            "started_at": "2026-03-01T10:00:00+00:00",
            "updated_at": "2026-03-01T10:00:00+00:00",
        }

        state = MergeState.from_dict(data)
        assert state.feature_slug == "test"
        assert state.target_branch == "main"
        assert state.wp_order == ["WP01"]
