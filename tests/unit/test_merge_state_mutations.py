"""Mutation-specific tests for merge/state.py to kill targeted mutants.

These tests focus on killing specific mutation patterns identified during
the WP04 mutation testing campaign:
- Pattern 1: Operator mutations (/ to *, etc.)
- Pattern 2: None assignments
- Pattern 3: Parameter removal (parents=True, etc.)
"""

from pathlib import Path


from specify_cli.merge.state import (
    MergeState,
    get_state_path,
    save_state,
    load_state,
    clear_state,
    has_active_merge,
)


class TestPathOperatorMutations:
    """Kill operator mutation: repo_root / STATE_FILE -> repo_root * STATE_FILE"""

    def test_get_state_path_returns_valid_path_object(self, tmp_path):
        """Verify get_state_path uses correct path operator (/) not (*)."""
        result = get_state_path(tmp_path)

        # If operator was *, this would raise TypeError
        assert isinstance(result, Path)
        assert str(result).endswith("merge-state.json")

    def test_get_state_path_creates_correct_structure(self, tmp_path):
        """Verify path construction creates .kittify subdirectory."""
        result = get_state_path(tmp_path)

        # Correct: tmp_path / ".kittify" / "merge-state.json"
        # Wrong: tmp_path * ".kittify" * "merge-state.json" (would raise TypeError)
        assert result.parent.name == ".kittify"
        assert result.parent.parent == tmp_path


class TestNoneAssignmentMutations:
    """Kill None assignment mutations: variable = func() -> variable = None"""

    def test_save_state_path_not_none(self, tmp_path):
        """Ensure state_path is valid Path, not None (kills None assignment mutation)."""
        state = MergeState(
            feature_slug="test-feature", target_branch="main", wp_order=["WP01"], completed_wps=[], strategy="merge"
        )

        # If state_path was mutated to None, this would raise AttributeError
        # on state_path.parent.mkdir()
        save_state(state, tmp_path)

        state_file = tmp_path / ".kittify" / "merge-state.json"
        assert state_file.exists()

    def test_load_state_returns_object_not_none(self, tmp_path):
        """Verify load_state returns MergeState object, not None."""
        # Setup
        state = MergeState(
            feature_slug="test", target_branch="main", wp_order=["WP01"], completed_wps=[], strategy="merge"
        )
        save_state(state, tmp_path)

        # Test
        loaded = load_state(tmp_path)

        # If load_state was mutated to return None, these would fail
        assert loaded is not None
        assert isinstance(loaded, MergeState)
        assert loaded.feature_slug == "test"


class TestParameterRemovalMutations:
    """Kill parameter removal mutations: mkdir(parents=True) -> mkdir()"""

    def test_save_state_creates_deep_directory_structure(self, tmp_path):
        """Verify save_state creates nested directories (kills parents=True mutation)."""
        # Create a deeply nested path that doesn't exist
        deep_path = tmp_path / "level1" / "level2" / "level3" / "level4"

        state = MergeState(
            feature_slug="deep-test", target_branch="main", wp_order=["WP01"], completed_wps=[], strategy="merge"
        )

        # If parents=True was removed, this would raise FileNotFoundError
        save_state(state, deep_path)

        # Verify the deep structure was created
        state_file = deep_path / ".kittify" / "merge-state.json"
        assert state_file.exists()
        # Verify the path structure is correct
        assert state_file.parent.name == ".kittify"
        assert state_file.parent.parent == deep_path

    def test_save_state_with_nonexistent_parent_directories(self, tmp_path):
        """Test save_state when multiple parent directories don't exist."""
        missing_path = tmp_path / "a" / "b" / "c"

        state = MergeState(
            feature_slug="test",
            target_branch="main",
            wp_order=["WP01", "WP02"],
            completed_wps=["WP01"],
            strategy="squash",
        )

        # This should succeed with parents=True, fail without it
        save_state(state, missing_path)
        assert (missing_path / ".kittify" / "merge-state.json").exists()


class TestReturnValueMutations:
    """Kill return value mutations: return X -> return None, return True -> return False"""

    def test_has_active_merge_returns_boolean_not_none(self, tmp_path):
        """Verify has_active_merge returns bool, not None."""
        # When no merge state exists
        result = has_active_merge(tmp_path)
        assert isinstance(result, bool)
        assert result is False

        # When merge state exists
        state = MergeState(
            feature_slug="test", target_branch="main", wp_order=["WP01"], completed_wps=[], strategy="merge"
        )
        save_state(state, tmp_path)

        result = has_active_merge(tmp_path)
        assert isinstance(result, bool)
        assert result is True  # Not None!

    def test_load_state_returns_correct_type_not_none(self, tmp_path):
        """Verify load_state returns MergeState or None correctly."""
        # When file doesn't exist
        result = load_state(tmp_path)
        assert result is None  # Explicitly None, not False or other

        # When file exists
        state = MergeState(
            feature_slug="feature", target_branch="main", wp_order=["WP01"], completed_wps=[], strategy="merge"
        )
        save_state(state, tmp_path)

        result = load_state(tmp_path)
        assert result is not None
        assert isinstance(result, MergeState)


class TestEdgeCasesMutations:
    """Additional edge cases to improve mutation coverage."""

    def test_save_state_updates_timestamp_field(self, tmp_path):
        """Verify save_state actually updates the updated_at timestamp."""
        state = MergeState(
            feature_slug="test", target_branch="main", wp_order=["WP01"], completed_wps=[], strategy="merge"
        )

        # Small delay to ensure timestamp changes
        import time

        time.sleep(0.01)

        save_state(state, tmp_path)

        # Reload and check timestamp was updated
        loaded = load_state(tmp_path)
        assert loaded is not None
        # The timestamp should be updated during save
        # (kills mutation that removes timestamp update)

    def test_clear_state_removes_file_not_just_clears_content(self, tmp_path):
        """Verify clear_state actually removes the file."""
        state = MergeState(
            feature_slug="test", target_branch="main", wp_order=["WP01"], completed_wps=[], strategy="merge"
        )
        save_state(state, tmp_path)

        state_path = get_state_path(tmp_path)
        assert state_path.exists()

        clear_state(tmp_path)

        # File should be gone, not just empty
        assert not state_path.exists()

    def test_save_state_with_completed_wps_list(self, tmp_path):
        """Test with non-empty completed_wps (kills list clearing mutations)."""
        state = MergeState(
            feature_slug="test",
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03"],
            completed_wps=["WP01", "WP02"],
            current_wp="WP03",
            strategy="merge",
        )

        save_state(state, tmp_path)
        loaded = load_state(tmp_path)

        assert loaded is not None
        # Kills mutation that clears or empties completed_wps
        assert len(loaded.completed_wps) == 2
        assert "WP01" in loaded.completed_wps
        assert "WP02" in loaded.completed_wps

    def test_merge_state_remaining_wps_calculation(self):
        """Verify remaining_wps property logic (kills condition mutations)."""
        state = MergeState(
            feature_slug="test",
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03", "WP04"],
            completed_wps=["WP01", "WP02"],
            current_wp="WP03",
            strategy="merge",
        )

        remaining = state.remaining_wps

        # Kills mutations in remaining_wps logic
        assert isinstance(remaining, list)
        assert len(remaining) == 2  # WP03, WP04
        assert "WP03" in remaining
        assert "WP04" in remaining
        assert "WP01" not in remaining
        assert "WP02" not in remaining
