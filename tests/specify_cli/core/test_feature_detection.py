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
    get_feature_target_branch,
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
    """Test error when multiple features exist and all are complete (strict mode)."""
    # Make all features complete so fallback doesn't activate
    for feature_name in ["020-feature-a", "021-feature-b", "022-feature-c"]:
        tasks_dir = repo_with_features / "kitty-specs" / feature_name / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n"
        )

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
        assert "All features are complete" in str(error)


def test_detect_multiple_features_none_lenient(repo_with_features: Path):
    """Test returns None when multiple features exist and all are complete (lenient mode)."""
    # Make all features complete so fallback doesn't activate
    for feature_name in ["020-feature-a", "021-feature-b", "022-feature-c"]:
        tasks_dir = repo_with_features / "kitty-specs" / feature_name / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n"
        )

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
    """Test error message when all features are complete includes helpful guidance."""
    # Make all features complete so fallback doesn't activate and error is raised
    for feature_name in ["020-feature-a", "021-feature-b", "022-feature-c"]:
        tasks_dir = repo_with_features / "kitty-specs" / feature_name / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n"
        )

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(MultipleFeaturesError) as exc_info:
            detect_feature(repo_with_features, cwd=repo_with_features)

        error_msg = str(exc_info.value)
        assert "--feature" in error_msg
        assert "SPECIFY_FEATURE" in error_msg
        assert "All features are complete" in error_msg


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


# ============================================================================
# Completion Detection Tests (Priority 6 Fallback)
# ============================================================================


def test_is_feature_complete_all_done(tmp_path: Path):
    """Test is_feature_complete when all WPs have lane: 'done'."""
    from specify_cli.core.feature_detection import is_feature_complete

    # Create feature with all WPs done
    feature_dir = tmp_path / "020-my-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create WP files with lane: done
    (tasks_dir / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\nContent"
    )
    (tasks_dir / "WP02.md").write_text(
        "---\nwork_package_id: WP02\ntitle: Test\nlane: done\n---\nContent"
    )

    assert is_feature_complete(feature_dir) is True


def test_is_feature_complete_has_incomplete(tmp_path: Path):
    """Test is_feature_complete when some WPs are not done."""
    from specify_cli.core.feature_detection import is_feature_complete

    # Create feature with mixed lane statuses
    feature_dir = tmp_path / "020-my-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    (tasks_dir / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\nContent"
    )
    (tasks_dir / "WP02.md").write_text(
        "---\nwork_package_id: WP02\ntitle: Test\nlane: doing\n---\nContent"
    )

    assert is_feature_complete(feature_dir) is False


def test_is_feature_complete_no_tasks_dir(tmp_path: Path):
    """Test is_feature_complete when tasks directory doesn't exist."""
    from specify_cli.core.feature_detection import is_feature_complete

    feature_dir = tmp_path / "020-my-feature"
    feature_dir.mkdir()

    assert is_feature_complete(feature_dir) is False


def test_is_feature_complete_no_wp_files(tmp_path: Path):
    """Test is_feature_complete when no WP files exist."""
    from specify_cli.core.feature_detection import is_feature_complete

    feature_dir = tmp_path / "020-my-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    assert is_feature_complete(feature_dir) is False


def test_is_feature_complete_parse_error(tmp_path: Path):
    """Test is_feature_complete treats parse errors as incomplete (safe default)."""
    from specify_cli.core.feature_detection import is_feature_complete

    feature_dir = tmp_path / "020-my-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create malformed WP file
    (tasks_dir / "WP01.md").write_text("Invalid frontmatter")

    assert is_feature_complete(feature_dir) is False


def test_find_latest_incomplete_multiple(tmp_path: Path):
    """Test find_latest_incomplete_feature with multiple incomplete features."""
    from specify_cli.core.feature_detection import find_latest_incomplete_feature

    # Create repo with multiple features
    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir(parents=True)

    # Feature 001 - complete
    feature_001 = kitty_specs / "001-feature-a"
    tasks_001 = feature_001 / "tasks"
    tasks_001.mkdir(parents=True)
    (tasks_001 / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n"
    )

    # Feature 002 - incomplete
    feature_002 = kitty_specs / "002-feature-b"
    tasks_002 = feature_002 / "tasks"
    tasks_002.mkdir(parents=True)
    (tasks_002 / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: doing\n---\n"
    )

    # Feature 003 - incomplete (should be selected as latest)
    feature_003 = kitty_specs / "003-feature-c"
    tasks_003 = feature_003 / "tasks"
    tasks_003.mkdir(parents=True)
    (tasks_003 / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: planned\n---\n"
    )

    latest = find_latest_incomplete_feature(repo_root)
    assert latest == "003-feature-c"


def test_find_latest_incomplete_all_complete(tmp_path: Path):
    """Test find_latest_incomplete_feature when all features are complete."""
    from specify_cli.core.feature_detection import find_latest_incomplete_feature

    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir(parents=True)

    # Both features complete
    for slug in ["001-feature-a", "002-feature-b"]:
        feature_dir = kitty_specs / slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n"
        )

    latest = find_latest_incomplete_feature(repo_root)
    assert latest is None


def test_find_latest_incomplete_no_features(tmp_path: Path):
    """Test find_latest_incomplete_feature when no features exist."""
    from specify_cli.core.feature_detection import find_latest_incomplete_feature

    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir(parents=True)

    latest = find_latest_incomplete_feature(repo_root)
    assert latest is None


def test_detect_fallback_to_latest_incomplete(tmp_path: Path):
    """Test Priority 6: fallback to latest incomplete feature."""
    # Create repo with multiple features
    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir(parents=True)

    # Feature 020 - complete
    feature_020 = kitty_specs / "020-feature-a"
    tasks_020 = feature_020 / "tasks"
    tasks_020.mkdir(parents=True)
    (tasks_020 / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n"
    )

    # Feature 025 - incomplete (should be auto-selected)
    feature_025 = kitty_specs / "025-feature-b"
    tasks_025 = feature_025 / "tasks"
    tasks_025.mkdir(parents=True)
    (tasks_025 / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: doing\n---\n"
    )

    # Mock git to fail (force fallback)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        ctx = detect_feature(repo_root, cwd=repo_root, mode="strict")

        assert ctx is not None
        assert ctx.slug == "025-feature-b"
        assert ctx.detection_method == "fallback_latest_incomplete"


def test_detect_fallback_respects_explicit_feature(tmp_path: Path):
    """Test fallback does NOT activate when explicit feature is provided."""
    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir(parents=True)

    # Create complete and incomplete features
    feature_020 = kitty_specs / "020-complete"
    tasks_020 = feature_020 / "tasks"
    tasks_020.mkdir(parents=True)
    (tasks_020 / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n"
    )

    feature_025 = kitty_specs / "025-incomplete"
    tasks_025 = feature_025 / "tasks"
    tasks_025.mkdir(parents=True)
    (tasks_025 / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: doing\n---\n"
    )

    # Explicit feature should win (Priority 1), not fallback (Priority 6)
    ctx = detect_feature(repo_root, explicit_feature="020-complete")

    assert ctx.slug == "020-complete"
    assert ctx.detection_method == "explicit"


def test_detect_fallback_error_when_all_complete(tmp_path: Path):
    """Test Priority 7: error when all features complete (no fallback available)."""
    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir(parents=True)

    # Both features complete
    for slug in ["020-feature-a", "025-feature-b"]:
        feature_dir = kitty_specs / slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n"
        )

    # Mock git to fail (force fallback)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(MultipleFeaturesError) as exc_info:
            detect_feature(repo_root, cwd=repo_root, mode="strict")

        error_msg = str(exc_info.value)
        assert "All features are complete" in error_msg
        assert "spec-kitty specify" in error_msg


def test_detect_fallback_respects_priority_order(tmp_path: Path):
    """Test fallback (Priority 6) is lower than cwd detection (Priority 4)."""
    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir(parents=True)

    # Feature 020 - complete
    feature_020 = kitty_specs / "020-feature-a"
    tasks_020 = feature_020 / "tasks"
    tasks_020.mkdir(parents=True)
    (tasks_020 / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n"
    )

    # Feature 025 - incomplete
    feature_025 = kitty_specs / "025-feature-b"
    tasks_025 = feature_025 / "tasks"
    tasks_025.mkdir(parents=True)
    (tasks_025 / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: doing\n---\n"
    )

    # Mock git to fail (force cwd/fallback detection)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        # Running from inside complete feature directory
        # Should detect from cwd (Priority 4), NOT fallback to 025 (Priority 6)
        ctx = detect_feature(repo_root, cwd=feature_020, mode="strict")

        assert ctx.slug == "020-feature-a"
        assert ctx.detection_method == "cwd_path"

# ============================================================================
# Target Branch Detection Tests
# ============================================================================


def test_get_feature_target_branch_with_main(tmp_path: Path):
    """Test get_feature_target_branch returns 'main' for feature with target_branch='main'."""
    import json

    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    feature_dir = kitty_specs / "020-feature-a"
    feature_dir.mkdir(parents=True)

    # Create meta.json with target_branch='main'
    meta = {
        "feature_number": "020",
        "slug": "020-feature-a",
        "target_branch": "main",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta))

    target = get_feature_target_branch(repo_root, "020-feature-a")
    assert target == "main"


def test_get_feature_target_branch_with_2x(tmp_path: Path):
    """Test get_feature_target_branch returns '2.x' for feature with target_branch='2.x'."""
    import json

    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    feature_dir = kitty_specs / "025-cli-event-log-integration"
    feature_dir.mkdir(parents=True)

    # Create meta.json with target_branch='2.x'
    meta = {
        "feature_number": "025",
        "slug": "025-cli-event-log-integration",
        "target_branch": "2.x",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta))

    target = get_feature_target_branch(repo_root, "025-cli-event-log-integration")
    assert target == "2.x"


def test_get_feature_target_branch_missing_field(tmp_path: Path):
    """Test get_feature_target_branch defaults to 'main' when target_branch field missing."""
    import json

    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    feature_dir = kitty_specs / "020-feature-a"
    feature_dir.mkdir(parents=True)

    # Create meta.json WITHOUT target_branch field (legacy feature)
    meta = {
        "feature_number": "020",
        "slug": "020-feature-a",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta))

    target = get_feature_target_branch(repo_root, "020-feature-a")
    assert target == "main"  # Safe default


def test_get_feature_target_branch_missing_meta_file(tmp_path: Path):
    """Test get_feature_target_branch defaults to 'main' when meta.json doesn't exist."""
    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    feature_dir = kitty_specs / "020-feature-a"
    feature_dir.mkdir(parents=True)

    # No meta.json file created

    target = get_feature_target_branch(repo_root, "020-feature-a")
    assert target == "main"  # Safe default


def test_get_feature_target_branch_malformed_json(tmp_path: Path):
    """Test get_feature_target_branch defaults to 'main' when meta.json is malformed."""
    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    feature_dir = kitty_specs / "020-feature-a"
    feature_dir.mkdir(parents=True)

    # Create malformed JSON
    (feature_dir / "meta.json").write_text("{invalid json")

    target = get_feature_target_branch(repo_root, "020-feature-a")
    assert target == "main"  # Safe default


def test_get_feature_target_branch_from_worktree(tmp_path: Path):
    """Test get_feature_target_branch works from worktree context."""
    import json

    # Create main repo structure
    main_repo = tmp_path / "main"
    kitty_specs = main_repo / "kitty-specs"
    feature_dir = kitty_specs / "025-cli-event-log-integration"
    feature_dir.mkdir(parents=True)

    meta = {
        "feature_number": "025",
        "slug": "025-cli-event-log-integration",
        "target_branch": "2.x",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta))

    # Create worktree directory (simulated)
    worktree = tmp_path / "worktrees" / "025-cli-event-log-integration-WP01"
    worktree.mkdir(parents=True)
    git_file = worktree / ".git"
    git_file.write_text(f"gitdir: {main_repo}/.git/worktrees/025-cli-event-log-integration-WP01")

    # Call from worktree context (should resolve to main repo)
    target = get_feature_target_branch(worktree, "025-cli-event-log-integration")
    assert target == "2.x"
