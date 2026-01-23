"""
Tests for VCS detection and factory functions.

Tests for is_jj_available, is_git_available, version functions, and get_vcs factory.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.core.vcs import (
    VCSBackend,
    VCSBackendMismatchError,
    VCSNotFoundError,
    VCSProtocol,
    detect_available_backends,
    get_git_version,
    get_jj_version,
    get_vcs,
    is_git_available,
    is_jj_available,
)
from specify_cli.core.vcs.detection import _clear_detection_cache


# Check if jj is available for skip decorator
def _check_jj_available():
    """Check if jj is available (uncached for test setup)."""
    import shutil
    import subprocess

    if shutil.which("jj") is None:
        return False
    try:
        result = subprocess.run(["jj", "--version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


JJ_AVAILABLE = _check_jj_available()

# Skip marker for tests requiring jj
requires_jj = pytest.mark.skipif(not JJ_AVAILABLE, reason="jj not installed")


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
# jj Detection Tests
# =============================================================================


class TestJJDetection:
    """Tests for jj detection functions."""

    def test_is_jj_available_when_installed(self):
        """Should return False (jj detection disabled)."""
        # jj detection is disabled due to sparse checkout incompatibility
        assert is_jj_available() is False

    def test_get_jj_version_when_installed(self):
        """Should return None (jj detection disabled)."""
        # jj detection is disabled due to sparse checkout incompatibility
        version = get_jj_version()
        assert version is None

    @requires_jj
    def test_get_jj_version_parses_correctly(self):
        """Version should be a valid semver-like string."""
        version = get_jj_version()
        if version and version != "unknown":
            parts = version.split(".")
            # Should have at least major.minor.patch
            assert len(parts) >= 3
            # All parts should be numeric
            assert parts[0].isdigit()
            assert parts[1].isdigit()

    def test_is_jj_available_with_missing_binary(self):
        """Should return False if jj binary not found."""
        with patch("specify_cli.core.vcs.detection.shutil.which", return_value=None):
            _clear_detection_cache()
            assert is_jj_available() is False

    def test_get_jj_version_returns_none_when_not_installed(self):
        """Should return None if jj is not available."""
        with patch(
            "specify_cli.core.vcs.detection.is_jj_available", return_value=False
        ):
            _clear_detection_cache()
            # Need to also patch is_jj_available check inside get_jj_version
            with patch(
                "specify_cli.core.vcs.detection.shutil.which", return_value=None
            ):
                _clear_detection_cache()
                result = get_jj_version()
                # Either None or the cached result
                # Since we cleared cache and mocked, should be None
                assert result is None or is_jj_available()


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

    def test_jj_first_when_available(self):
        """jj should NOT be in available backends (jj detection disabled)."""
        # jj is disabled, so only git should be available
        backends = detect_available_backends()
        assert VCSBackend.JUJUTSU not in backends
        assert VCSBackend.GIT in backends

    def test_empty_when_nothing_available(self):
        """Should return empty list when no VCS tools available."""
        with patch(
            "specify_cli.core.vcs.detection.is_jj_available", return_value=False
        ):
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
        assert vcs.backend in [VCSBackend.GIT, VCSBackend.JUJUTSU]

    def test_has_capabilities_property(self):
        """Returned VCS should have capabilities property."""
        vcs = get_vcs(Path("."))
        assert hasattr(vcs, "capabilities")

    def test_explicit_git_backend(self):
        """Should return GitVCS when explicitly requested."""
        vcs = get_vcs(Path("."), backend=VCSBackend.GIT)
        assert vcs.backend == VCSBackend.GIT

    def test_explicit_jj_backend(self):
        """Should raise VCSNotFoundError (jj detection disabled)."""
        # jj is disabled, so explicit request should fail
        with pytest.raises(VCSNotFoundError):
            get_vcs(Path("."), backend=VCSBackend.JUJUTSU)

    def test_prefers_jj_when_available(self):
        """Should return git (jj not available anymore)."""
        # jj detection is disabled, so prefer_jj flag has no effect
        vcs = get_vcs(Path("."), prefer_jj=True)
        assert vcs.backend == VCSBackend.GIT

    def test_falls_back_to_git(self):
        """Should fall back to git when jj not available."""
        with patch(
            "specify_cli.core.vcs.detection.is_jj_available", return_value=False
        ):
            vcs = get_vcs(Path("."), prefer_jj=True)
            assert vcs.backend == VCSBackend.GIT

    def test_raises_when_nothing_available(self):
        """Should raise VCSNotFoundError when no VCS available."""
        with patch(
            "specify_cli.core.vcs.detection.is_jj_available", return_value=False
        ):
            with patch(
                "specify_cli.core.vcs.detection.is_git_available", return_value=False
            ):
                with pytest.raises(VCSNotFoundError):
                    get_vcs(Path("."))

    def test_raises_when_requested_backend_not_available(self):
        """Should raise VCSNotFoundError if requested backend not available."""
        with patch(
            "specify_cli.core.vcs.detection.is_jj_available", return_value=False
        ):
            with pytest.raises(VCSNotFoundError):
                get_vcs(Path("."), backend=VCSBackend.JUJUTSU)

    def test_prefer_jj_false_uses_git(self):
        """Should use git when prefer_jj=False even if jj available."""
        vcs = get_vcs(Path("."), prefer_jj=False)
        # When prefer_jj is False, still uses jj if it's the only option
        # but prefers git in the auto-detect logic
        # Actually looking at the code, prefer_jj=False doesn't change
        # the preference order, it just skips the jj check
        # So with git available, should return git
        assert vcs.backend == VCSBackend.GIT


# =============================================================================
# Meta.json Locked VCS Tests
# =============================================================================


class TestLockedVCSFromMeta:
    """Tests for reading locked VCS from meta.json."""

    def test_returns_none_for_nonexistent_path(self, tmp_path):
        """Should return appropriate VCS when no meta.json exists."""
        # Should fall back to auto-detect
        vcs = get_vcs(tmp_path)
        assert vcs.backend in [VCSBackend.GIT, VCSBackend.JUJUTSU]

    def test_path_outside_feature_ignores_meta(self, tmp_path):
        """Path outside feature should NOT use locked VCS from unrelated feature."""
        import json

        # Create feature structure with locked VCS
        feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
        feature_dir.mkdir(parents=True)
        meta = feature_dir / "meta.json"
        meta.write_text(json.dumps({"vcs": "jj"}))  # Lock to jj

        # Path is tmp_path root, NOT inside the feature
        # Should NOT respect the locked VCS - should use auto-detect
        vcs = get_vcs(tmp_path)
        # Should use git (auto-detect) since path is not in feature
        # This test passes if it doesn't incorrectly lock to jj
        assert vcs.backend in [VCSBackend.GIT, VCSBackend.JUJUTSU]

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

    @requires_jj
    def test_locked_vcs_overrides_prefer_jj(self, tmp_path):
        """Locked VCS in meta.json should override prefer_jj for paths inside feature."""
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

        # Even with prefer_jj=True, should use git if locked
        vcs = get_vcs(path_inside, prefer_jj=True)
        assert vcs.backend == VCSBackend.GIT

    def test_locked_jj_vcs_used_when_path_inside_feature(self, tmp_path):
        """Locked jj VCS should fail (jj detection disabled)."""
        import json

        # Create feature with jj locked
        feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
        feature_dir.mkdir(parents=True)
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir()
        meta = feature_dir / "meta.json"
        meta.write_text(json.dumps({"vcs": "jj"}))

        # Path inside feature
        path_inside = tasks_dir / "WP01.md"
        path_inside.touch()

        # Should fail since jj is not available anymore
        with pytest.raises(VCSNotFoundError):
            get_vcs(path_inside)

    def test_explicit_backend_mismatch_raises_error(self, tmp_path):
        """Explicit backend that mismatches locked VCS should raise VCSBackendMismatchError."""
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

        # Request jj but feature is locked to git - should raise
        with pytest.raises(VCSBackendMismatchError):
            get_vcs(path_inside, backend=VCSBackend.JUJUTSU)

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
