"""
Tests for VCS detection and factory functions.

Tests for is_git_available, version functions, and get_vcs factory.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.core.vcs import (
    VCSBackend,
    VCSNotFoundError,
    VCSProtocol,
    detect_available_backends,
    get_git_version,
    get_vcs,
    is_git_available,
)
from specify_cli.core.vcs.detection import _clear_detection_cache

pytestmark = pytest.mark.fast


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear detection cache before each test."""
    _clear_detection_cache()
    yield
    _clear_detection_cache()


# =============================================================================
# Git Detection Tests
# =============================================================================


class TestGitDetection:
    """Tests for git detection functions."""

    def test_is_git_available(self):
        """Git should be available in any dev environment."""
        # This test assumes git is installed (which it should be for development)
        assert is_git_available() is True

    def test_get_git_version(self):
        """Should return a valid version string for git."""
        version = get_git_version()
        assert version is not None
        # Version should be in format like "2.43.0"
        assert "." in version

    def test_get_git_version_parses_correctly(self):
        """Version should be a valid semver-like string."""
        version = get_git_version()
        if version and version != "unknown":
            parts = version.split(".")
            # Should have at least major.minor.patch
            assert len(parts) >= 3
            # First two parts should be numeric
            assert parts[0].isdigit()
            assert parts[1].isdigit()

    def test_is_git_available_caching(self):
        """Repeated calls should use cache (no new subprocess)."""
        # First call
        result1 = is_git_available()
        # Second call should return same result from cache
        result2 = is_git_available()
        assert result1 == result2

    def test_is_git_available_with_missing_binary(self):
        """Should return False if git binary not found."""
        with patch("specify_cli.core.vcs.detection.shutil.which", return_value=None):
            _clear_detection_cache()
            assert is_git_available() is False


# =============================================================================
# Backend Detection Tests
# =============================================================================


class TestDetectAvailableBackends:
    """Tests for detect_available_backends function."""

    def test_returns_list(self):
        """Should return a list of backends."""
        backends = detect_available_backends()
        assert isinstance(backends, list)

    def test_git_in_backends(self):
        """Git should be in available backends (assuming it's installed)."""
        backends = detect_available_backends()
        assert VCSBackend.GIT in backends

    def test_empty_when_nothing_available(self):
        """Should return empty list when no VCS tools available."""
        with patch(
            "specify_cli.core.vcs.detection.is_git_available", return_value=False
        ):
            backends = detect_available_backends()
            assert backends == []


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestGetVCS:
    """Tests for get_vcs factory function."""

    def test_returns_vcs_protocol(self):
        """Should return an object implementing VCSProtocol."""
        vcs = get_vcs(Path("."))
        assert isinstance(vcs, VCSProtocol)

    def test_has_backend_property(self):
        """Returned VCS should have backend property."""
        vcs = get_vcs(Path("."))
        assert hasattr(vcs, "backend")
        assert vcs.backend == VCSBackend.GIT

    def test_has_capabilities_property(self):
        """Returned VCS should have capabilities property."""
        vcs = get_vcs(Path("."))
        assert hasattr(vcs, "capabilities")

    def test_explicit_git_backend(self):
        """Should return GitVCS when explicitly requested."""
        vcs = get_vcs(Path("."), backend=VCSBackend.GIT)
        assert vcs.backend == VCSBackend.GIT

    def test_raises_when_nothing_available(self):
        """Should raise VCSNotFoundError when no VCS available."""
        with patch(
            "specify_cli.core.vcs.detection.is_git_available", return_value=False
        ), pytest.raises(VCSNotFoundError):
            get_vcs(Path("."))


# =============================================================================
# Meta.json Locked VCS Tests
# =============================================================================


class TestLockedVCSFromMeta:
    """Tests for reading locked VCS from meta.json."""

    def test_returns_none_for_nonexistent_path(self, tmp_path):
        """Should return appropriate VCS when no meta.json exists."""
        # Should fall back to auto-detect
        vcs = get_vcs(tmp_path)
        assert vcs.backend == VCSBackend.GIT

    def test_path_inside_feature_uses_locked_vcs(self, tmp_path):
        """Path inside feature directory should use locked VCS from meta.json."""
        import json

        # Create feature structure with locked VCS
        feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
        feature_dir.mkdir(parents=True)
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()
        meta = feature_dir / "meta.json"
        meta.write_text(json.dumps({"vcs": "git"}))

        # Path is inside the feature directory
        path_inside_feature = tasks_dir / "WP01.md"
        path_inside_feature.touch()

        vcs = get_vcs(path_inside_feature)
        # Should use git (locked VCS) since path is inside feature
        assert vcs.backend == VCSBackend.GIT

    def test_explicit_backend_matching_locked_works(self, tmp_path):
        """Explicit backend that matches locked VCS should work."""
        import json


        # Create feature with git locked
        feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
        feature_dir.mkdir(parents=True)
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()
        meta = feature_dir / "meta.json"
        meta.write_text(json.dumps({"vcs": "git"}))

        # Path inside feature
        path_inside = tasks_dir / "WP01.md"
        path_inside.touch()

        # Request git and feature is locked to git - should work
        vcs = get_vcs(path_inside, backend=VCSBackend.GIT)
        assert vcs.backend == VCSBackend.GIT


# =============================================================================
# Caching Tests
# =============================================================================


class TestCaching:
    """Tests for detection result caching."""

    def test_is_git_available_is_cached(self):
        """is_git_available should cache its result."""
        # Call twice
        result1 = is_git_available()
        result2 = is_git_available()
        assert result1 == result2

    def test_cache_can_be_cleared(self):
        """_clear_detection_cache should clear cached results."""
        # First call
        is_git_available()
        # Clear
        _clear_detection_cache()
        # After clear, calling again should work
        result = is_git_available()
        assert isinstance(result, bool)
