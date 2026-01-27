"""
Comprehensive unit tests for centralized feature detection.

Tests cover all detection scenarios:
1. Explicit parameter (highest priority)
2. Environment variable
3. Git branch name (with/without WP suffix)
4. Current directory path
5. Single feature auto-detect
6. Multiple features (strict/lenient modes)
7. No features found
8. Invalid slug format
9. FeatureContext dataclass fields
10. Error messages and guidance
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from specify_cli.core.feature_detection import (
    FeatureContext,
    FeatureDetectionError,
    MultipleFeaturesError,
    NoFeatureFoundError,
    detect_feature,
    detect_feature_slug,
    detect_feature_directory,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def repo_with_features(tmp_path: Path) -> Path:
    """Create a temporary repository with multiple features."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create kitty-specs directory
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir()

    # Create multiple feature directories
    (kitty_specs / "020-feature-a").mkdir()
    (kitty_specs / "021-feature-b").mkdir()
    (kitty_specs / "022-feature-c").mkdir()

    return repo_root


@pytest.fixture
def repo_with_single_feature(tmp_path: Path) -> Path:
    """Create a temporary repository with a single feature."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create kitty-specs directory
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir()

    # Create single feature directory
    (kitty_specs / "020-my-feature").mkdir()

    return repo_root


@pytest.fixture
def repo_empty(tmp_path: Path) -> Path:
    """Create a temporary repository with no features."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create empty kitty-specs directory
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir()

    return repo_root


# ============================================================================
# Core Detection Tests
# ============================================================================


def test_detect_explicit_feature(repo_with_features: Path):
    """Test explicit parameter wins (highest priority)."""
    ctx = detect_feature(repo_with_features, explicit_feature="020-feature-a")

    assert ctx is not None
    assert ctx.slug == "020-feature-a"
    assert ctx.number == "020"
    assert ctx.name == "feature-a"
    assert ctx.directory == repo_with_features / "kitty-specs" / "020-feature-a"
    assert ctx.detection_method == "explicit"


def test_detect_env_var(repo_with_features: Path):
    """Test SPECIFY_FEATURE env var."""
    env = {"SPECIFY_FEATURE": "021-feature-b"}
    ctx = detect_feature(repo_with_features, env=env)

    assert ctx is not None
    assert ctx.slug == "021-feature-b"
    assert ctx.detection_method == "env_var"


def test_detect_env_var_with_whitespace(repo_with_features: Path):
    """Test SPECIFY_FEATURE env var strips whitespace."""
    env = {"SPECIFY_FEATURE": "  021-feature-b  "}
    ctx = detect_feature(repo_with_features, env=env)

    assert ctx is not None
    assert ctx.slug == "021-feature-b"


def test_detect_git_branch(repo_with_features: Path):
    """Test git branch name detection."""
    # Mock git command to return branch name
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="020-feature-a\n",
        )

        ctx = detect_feature(repo_with_features)

        assert ctx is not None
        assert ctx.slug == "020-feature-a"
        assert ctx.detection_method == "git_branch"


def test_detect_git_branch_wp_suffix(repo_with_features: Path):
    """Test git branch name detection strips -WP## suffix."""
    # Mock git command to return worktree branch name
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="020-feature-a-WP01\n",
        )

        ctx = detect_feature(repo_with_features)

        assert ctx is not None
        assert ctx.slug == "020-feature-a"
        assert ctx.detection_method == "git_branch"


def test_detect_git_branch_wp_suffix_multiple_digits(repo_with_features: Path):
    """Test git branch name detection strips -WP## suffix (various formats)."""
    # Mock git command to return worktree branch name
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="020-feature-a-WP99\n",
        )

        ctx = detect_feature(repo_with_features)

        assert ctx is not None
        assert ctx.slug == "020-feature-a"


def test_detect_cwd_path_inside_feature(repo_with_features: Path):
    """Test detection from current directory (inside feature directory)."""
    feature_dir = repo_with_features / "kitty-specs" / "021-feature-b"
    cwd = feature_dir / "some" / "nested" / "dir"
    cwd.mkdir(parents=True)

    # Mock git to fail (force cwd detection)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        ctx = detect_feature(repo_with_features, cwd=cwd)

        assert ctx is not None
        assert ctx.slug == "021-feature-b"
        assert ctx.detection_method == "cwd_path"


def test_detect_cwd_path_inside_worktree(repo_with_features: Path):
    """Test detection from current directory (inside worktree)."""
    worktree_dir = repo_with_features / ".worktrees" / "020-feature-a-WP01"
    worktree_dir.mkdir(parents=True)
    cwd = worktree_dir / "some" / "nested" / "dir"
    cwd.mkdir(parents=True)

    # Mock git to fail (force cwd detection)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        ctx = detect_feature(repo_with_features, cwd=cwd)

        assert ctx is not None
        assert ctx.slug == "020-feature-a"
        assert ctx.detection_method == "cwd_path"


def test_detect_single_feature_auto(repo_with_single_feature: Path):
    """Test single feature auto-detect (only one feature exists)."""
    # Mock git to fail (force auto-detect)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        ctx = detect_feature(repo_with_single_feature, cwd=repo_with_single_feature)

        assert ctx is not None
        assert ctx.slug == "020-my-feature"
        assert ctx.detection_method == "single_auto"


def test_detect_multiple_features_error_strict(repo_with_features: Path):
    """Test error when multiple features exist (strict mode)."""
    # Mock git to fail (force auto-detect)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(MultipleFeaturesError) as exc_info:
            detect_feature(repo_with_features, cwd=repo_with_features, mode="strict")

        error = exc_info.value
        assert len(error.features) == 3
        assert "020-feature-a" in error.features
        assert "021-feature-b" in error.features
        assert "022-feature-c" in error.features
        assert "--feature" in str(error)


def test_detect_multiple_features_none_lenient(repo_with_features: Path):
    """Test returns None when multiple features exist (lenient mode)."""
    # Mock git to fail (force auto-detect)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        ctx = detect_feature(repo_with_features, cwd=repo_with_features, mode="lenient")

        assert ctx is None


def test_detect_no_features_error(repo_empty: Path):
    """Test error when no features found."""
    # Mock git to fail
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(NoFeatureFoundError) as exc_info:
            detect_feature(repo_empty, cwd=repo_empty, mode="strict")

        error = str(exc_info.value)
        assert "No features found" in error
        assert "spec-kitty specify" in error


def test_detect_no_features_none_lenient(repo_empty: Path):
    """Test returns None when no features found (lenient mode)."""
    # Mock git to fail
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        ctx = detect_feature(repo_empty, cwd=repo_empty, mode="lenient")

        assert ctx is None


def test_invalid_slug_format_explicit(repo_with_features: Path):
    """Test error for invalid slug format (explicit parameter)."""
    with pytest.raises(FeatureDetectionError) as exc_info:
        detect_feature(repo_with_features, explicit_feature="invalid-slug")

    error = str(exc_info.value)
    assert "Invalid feature slug format" in error
    assert "###-feature-name" in error


def test_feature_not_found_explicit(repo_with_features: Path):
    """Test error when explicitly specified feature doesn't exist."""
    with pytest.raises(NoFeatureFoundError) as exc_info:
        detect_feature(repo_with_features, explicit_feature="999-nonexistent")

    error = str(exc_info.value)
    assert "Feature directory not found" in error
    assert "999-nonexistent" in error


def test_feature_context_dataclass_fields(repo_with_features: Path):
    """Test FeatureContext dataclass has all expected fields."""
    ctx = detect_feature(repo_with_features, explicit_feature="020-feature-a")

    # Check all fields are populated
    assert isinstance(ctx.slug, str)
    assert isinstance(ctx.number, str)
    assert isinstance(ctx.name, str)
    assert isinstance(ctx.directory, Path)
    assert isinstance(ctx.detection_method, str)

    # Check field values
    assert ctx.slug == "020-feature-a"
    assert ctx.number == "020"
    assert ctx.name == "feature-a"
    assert ctx.directory.name == "020-feature-a"
    assert ctx.detection_method == "explicit"


# ============================================================================
# Priority Order Tests
# ============================================================================


def test_priority_explicit_over_env(repo_with_features: Path):
    """Test explicit parameter takes priority over env var."""
    env = {"SPECIFY_FEATURE": "021-feature-b"}
    ctx = detect_feature(repo_with_features, explicit_feature="020-feature-a", env=env)

    assert ctx.slug == "020-feature-a"
    assert ctx.detection_method == "explicit"


def test_priority_env_over_git(repo_with_features: Path):
    """Test env var takes priority over git branch."""
    env = {"SPECIFY_FEATURE": "021-feature-b"}

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="020-feature-a\n",
        )

        ctx = detect_feature(repo_with_features, env=env)

        assert ctx.slug == "021-feature-b"
        assert ctx.detection_method == "env_var"


def test_priority_git_over_cwd(repo_with_features: Path):
    """Test git branch takes priority over cwd."""
    feature_dir = repo_with_features / "kitty-specs" / "021-feature-b"
    cwd = feature_dir

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="020-feature-a\n",
        )

        ctx = detect_feature(repo_with_features, cwd=cwd)

        assert ctx.slug == "020-feature-a"
        assert ctx.detection_method == "git_branch"


def test_priority_cwd_over_single_auto(repo_with_single_feature: Path):
    """Test cwd takes priority over single auto-detect."""
    feature_dir = repo_with_single_feature / "kitty-specs" / "020-my-feature"

    # Create a second feature to make cwd detection meaningful
    (repo_with_single_feature / "kitty-specs" / "021-other").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        ctx = detect_feature(repo_with_single_feature, cwd=feature_dir)

        assert ctx.slug == "020-my-feature"
        assert ctx.detection_method == "cwd_path"


# ============================================================================
# Simplified Wrapper Tests
# ============================================================================


def test_detect_feature_slug_wrapper(repo_with_features: Path):
    """Test detect_feature_slug() wrapper returns just the slug."""
    slug = detect_feature_slug(repo_with_features, explicit_feature="020-feature-a")

    assert isinstance(slug, str)
    assert slug == "020-feature-a"


def test_detect_feature_slug_wrapper_raises_on_error(repo_empty: Path):
    """Test detect_feature_slug() wrapper raises on error (strict mode)."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(NoFeatureFoundError):
            detect_feature_slug(repo_empty, cwd=repo_empty)


def test_detect_feature_directory_wrapper(repo_with_features: Path):
    """Test detect_feature_directory() wrapper returns just the Path."""
    directory = detect_feature_directory(repo_with_features, explicit_feature="020-feature-a")

    assert isinstance(directory, Path)
    assert directory.name == "020-feature-a"
    assert directory.parent.name == "kitty-specs"


def test_detect_feature_directory_wrapper_raises_on_error(repo_empty: Path):
    """Test detect_feature_directory() wrapper raises on error (strict mode)."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(NoFeatureFoundError):
            detect_feature_directory(repo_empty, cwd=repo_empty)


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_allow_single_auto_disabled(repo_with_single_feature: Path):
    """Test single auto-detect can be disabled."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(NoFeatureFoundError):
            detect_feature(
                repo_with_single_feature,
                cwd=repo_with_single_feature,
                allow_single_auto=False
            )


def test_empty_env_var_ignored(repo_with_features: Path):
    """Test empty SPECIFY_FEATURE env var is ignored."""
    env = {"SPECIFY_FEATURE": "   "}  # Only whitespace

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="020-feature-a\n",
        )

        ctx = detect_feature(repo_with_features, env=env)

        # Should fall through to git branch detection
        assert ctx.detection_method == "git_branch"


def test_git_command_not_found(repo_with_single_feature: Path):
    """Test graceful handling when git command not found."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError()

        # Should fall through to single auto-detect
        ctx = detect_feature(repo_with_single_feature, cwd=repo_with_single_feature)

        assert ctx.slug == "020-my-feature"
        assert ctx.detection_method == "single_auto"


def test_feature_slug_with_hyphens(tmp_path: Path):
    """Test feature slug with multiple hyphens in name."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir()
    (kitty_specs / "020-my-complex-feature-name").mkdir()

    ctx = detect_feature(repo_root, explicit_feature="020-my-complex-feature-name")

    assert ctx.slug == "020-my-complex-feature-name"
    assert ctx.number == "020"
    assert ctx.name == "my-complex-feature-name"


def test_worktree_context_with_main_repo_root(tmp_path: Path):
    """Test detection works in worktree context (simulated)."""
    # Create main repo
    main_repo = tmp_path / "main"
    main_repo.mkdir()
    kitty_specs = main_repo / "kitty-specs"
    kitty_specs.mkdir()
    (kitty_specs / "020-feature-a").mkdir()

    # Create worktree-like structure
    worktree = tmp_path / "worktrees" / "020-feature-a-WP01"
    worktree.mkdir(parents=True)

    # Create .git file pointing to main repo (simulates worktree)
    git_file = worktree / ".git"
    git_file.write_text(f"gitdir: {main_repo / '.git' / 'worktrees' / '020-feature-a-WP01'}")

    # Mock git command
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="020-feature-a-WP01\n",
        )

        ctx = detect_feature(worktree, cwd=worktree)

        # Should detect from git branch and strip WP suffix
        assert ctx.slug == "020-feature-a"


# ============================================================================
# Error Message Quality Tests
# ============================================================================


def test_error_message_multiple_features_includes_guidance(repo_with_features: Path):
    """Test error message for multiple features includes helpful guidance."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(MultipleFeaturesError) as exc_info:
            detect_feature(repo_with_features, cwd=repo_with_features)

        error_msg = str(exc_info.value)
        assert "--feature" in error_msg
        assert "SPECIFY_FEATURE" in error_msg
        assert "020-feature-a" in error_msg
        assert "021-feature-b" in error_msg
        assert "022-feature-c" in error_msg


def test_error_message_no_features_includes_creation_command(repo_empty: Path):
    """Test error message for no features includes creation command."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(NoFeatureFoundError) as exc_info:
            detect_feature(repo_empty, cwd=repo_empty)

        error_msg = str(exc_info.value)
        assert "spec-kitty specify" in error_msg
        assert "/spec-kitty.specify" in error_msg


def test_error_message_feature_not_found_lists_available(repo_with_features: Path):
    """Test error message for nonexistent feature lists available features."""
    with pytest.raises(NoFeatureFoundError) as exc_info:
        detect_feature(repo_with_features, explicit_feature="999-nonexistent")

    error_msg = str(exc_info.value)
    assert "Available features:" in error_msg
    assert "020-feature-a" in error_msg
    assert "021-feature-b" in error_msg
