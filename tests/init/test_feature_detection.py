"""

pytestmark = pytest.mark.fast

Comprehensive unit tests for centralized mission detection.

Tests cover all detection scenarios:
1. Explicit parameter (highest priority)
2. Environment variable
3. Git branch name (with/without WP suffix)
4. Current directory path
5. Single mission auto-detect
6. Multiple missions (strict/lenient modes)
7. No missions found
8. Invalid slug format
9. MissionContext dataclass fields
10. Error messages and guidance
"""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from specify_cli.core.mission_detection import (
    MissionDetectionError,
    MultipleMissionsError,
    NoMissionFoundError,
    detect_mission,
    detect_mission_slug,
    detect_mission_directory,
    get_mission_target_branch,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def repo_with_missions(tmp_path: Path) -> Path:
    """Create a temporary repository with multiple missions."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create kitty-specs directory
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir()

    # Create multiple mission directories
    (kitty_specs / "020-mission-a").mkdir()
    (kitty_specs / "021-mission-b").mkdir()
    (kitty_specs / "022-mission-c").mkdir()

    return repo_root


@pytest.fixture
def repo_with_single_mission(tmp_path: Path) -> Path:
    """Create a temporary repository with a single mission."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create kitty-specs directory
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir()

    # Create single mission directory
    (kitty_specs / "020-my-mission").mkdir()

    return repo_root


@pytest.fixture
def repo_empty(tmp_path: Path) -> Path:
    """Create a temporary repository with no missions."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create empty kitty-specs directory
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir()

    return repo_root


# ============================================================================
# Core Detection Tests
# ============================================================================


def test_detect_explicit_mission(repo_with_missions: Path):
    """Test explicit parameter wins (highest priority)."""
    ctx = detect_mission(repo_with_missions, explicit_mission="020-mission-a")

    assert ctx is not None
    assert ctx.slug == "020-mission-a"
    assert ctx.number == "020"
    assert ctx.name == "mission-a"
    assert ctx.directory == repo_with_missions / "kitty-specs" / "020-mission-a"
    assert ctx.detection_method == "explicit"


def test_detect_explicit_numeric_mission_id(repo_with_missions: Path):
    """Numeric --mission shorthand should resolve to full slug when unique."""
    ctx = detect_mission(repo_with_missions, explicit_mission="021")

    assert ctx is not None
    assert ctx.slug == "021-mission-b"
    assert ctx.detection_method == "explicit_number"


def test_detect_env_var(repo_with_missions: Path):
    """Test SPECIFY_MISSION env var."""
    env = {"SPECIFY_MISSION": "021-mission-b"}
    ctx = detect_mission(repo_with_missions, env=env)

    assert ctx is not None
    assert ctx.slug == "021-mission-b"
    assert ctx.detection_method == "env_var"


def test_detect_env_var_numeric_mission_id(repo_with_missions: Path):
    """Numeric SPECIFY_MISSION shorthand should resolve to full slug when unique."""
    env = {"SPECIFY_MISSION": "022"}
    ctx = detect_mission(repo_with_missions, env=env)

    assert ctx is not None
    assert ctx.slug == "022-mission-c"
    assert ctx.detection_method == "env_var_number"


def test_detect_explicit_numeric_mission_id_missing_strict_raises(
    repo_with_missions: Path,
):
    with pytest.raises(NoMissionFoundError) as exc_info:
        detect_mission(repo_with_missions, explicit_mission="099", mode="strict")
    assert "No mission found for number '099'" in str(exc_info.value)


def test_detect_explicit_numeric_mission_id_missing_lenient_returns_none(
    repo_with_missions: Path,
):
    assert detect_mission(repo_with_missions, explicit_mission="099", mode="lenient") is None


def test_detect_numeric_mission_id_ambiguous_strict_raises(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir()
    (kitty_specs / "020-alpha").mkdir()
    (kitty_specs / "020-beta").mkdir()

    with pytest.raises(MultipleMissionsError) as exc_info:
        detect_mission(repo_root, explicit_mission="020", mode="strict")
    assert "matches multiple missions" in str(exc_info.value)


def test_detect_numeric_mission_id_ambiguous_lenient_returns_none(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir()
    (kitty_specs / "020-alpha").mkdir()
    (kitty_specs / "020-beta").mkdir()

    assert detect_mission(repo_root, env={"SPECIFY_MISSION": "020"}, mode="lenient") is None


def test_detect_env_var_with_whitespace(repo_with_missions: Path):
    """Test SPECIFY_MISSION env var strips whitespace."""
    env = {"SPECIFY_MISSION": "  021-mission-b  "}
    ctx = detect_mission(repo_with_missions, env=env)

    assert ctx is not None
    assert ctx.slug == "021-mission-b"


def test_detect_git_branch(repo_with_missions: Path):
    """Test git branch name detection."""
    # Mock git command to return branch name
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="020-mission-a\n",
        )

        ctx = detect_mission(repo_with_missions)

        assert ctx is not None
        assert ctx.slug == "020-mission-a"
        assert ctx.detection_method == "git_branch"


def test_detect_git_branch_wp_suffix(repo_with_missions: Path):
    """Test git branch name detection strips -WP## suffix."""
    # Mock git command to return worktree branch name
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="020-mission-a-WP01\n",
        )

        ctx = detect_mission(repo_with_missions)

        assert ctx is not None
        assert ctx.slug == "020-mission-a"
        assert ctx.detection_method == "git_branch"


def test_detect_git_branch_wp_suffix_multiple_digits(repo_with_missions: Path):
    """Test git branch name detection strips -WP## suffix (various formats)."""
    # Mock git command to return worktree branch name
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="020-mission-a-WP99\n",
        )

        ctx = detect_mission(repo_with_missions)

        assert ctx is not None
        assert ctx.slug == "020-mission-a"


def test_detect_cwd_path_inside_mission(repo_with_missions: Path):
    """Test detection from current directory (inside mission directory)."""
    mission_dir = repo_with_missions / "kitty-specs" / "021-mission-b"
    cwd = mission_dir / "some" / "nested" / "dir"
    cwd.mkdir(parents=True)

    # Mock git to fail (force cwd detection)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        ctx = detect_mission(repo_with_missions, cwd=cwd)

        assert ctx is not None
        assert ctx.slug == "021-mission-b"
        assert ctx.detection_method == "cwd_path"


def test_detect_cwd_path_inside_worktree(repo_with_missions: Path):
    """Test detection from current directory (inside worktree)."""
    worktree_dir = repo_with_missions / ".worktrees" / "020-mission-a-WP01"
    worktree_dir.mkdir(parents=True)
    cwd = worktree_dir / "some" / "nested" / "dir"
    cwd.mkdir(parents=True)

    # Mock git to fail (force cwd detection)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        ctx = detect_mission(repo_with_missions, cwd=cwd)

        assert ctx is not None
        assert ctx.slug == "020-mission-a"
        assert ctx.detection_method == "cwd_path"


def test_detect_cwd_path_at_worktree_root(repo_with_missions: Path):
    """Worktree root itself should still resolve via cwd detection."""
    worktree_dir = repo_with_missions / ".worktrees" / "020-mission-a-WP01"
    worktree_dir.mkdir(parents=True)

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        ctx = detect_mission(repo_with_missions, cwd=worktree_dir)

        assert ctx is not None
        assert ctx.slug == "020-mission-a"
        assert ctx.detection_method == "cwd_path"


def test_detect_single_mission_auto(repo_with_single_mission: Path):
    """Test single mission auto-detect (only one mission exists)."""
    # Mock git to fail (force auto-detect)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        ctx = detect_mission(repo_with_single_mission, cwd=repo_with_single_mission)

        assert ctx is not None
        assert ctx.slug == "020-my-mission"
        assert ctx.detection_method == "single_auto"


def test_detect_multiple_missions_error_strict(repo_with_missions: Path):
    """Test error when multiple missions exist and all are complete (strict mode)."""
    # Make all missions complete so fallback doesn't activate
    for mission_name in ["020-mission-a", "021-mission-b", "022-mission-c"]:
        tasks_dir = repo_with_missions / "kitty-specs" / mission_name / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n"
        )

    # Mock git to fail (force auto-detect)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(MultipleMissionsError) as exc_info:
            detect_mission(repo_with_missions, cwd=repo_with_missions, mode="strict")

        error = exc_info.value
        assert len(error.missions) == 3
        assert "020-mission-a" in error.missions
        assert "021-mission-b" in error.missions
        assert "022-mission-c" in error.missions
        assert "All missions are complete" in str(error)


def test_detect_multiple_missions_none_lenient(repo_with_missions: Path):
    """Test returns None when multiple missions exist and all are complete (lenient mode)."""
    # Make all missions complete so fallback doesn't activate
    for mission_name in ["020-mission-a", "021-mission-b", "022-mission-c"]:
        tasks_dir = repo_with_missions / "kitty-specs" / mission_name / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n"
        )

    # Mock git to fail (force auto-detect)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        ctx = detect_mission(repo_with_missions, cwd=repo_with_missions, mode="lenient")

        assert ctx is None


def test_detect_no_missions_error(repo_empty: Path):
    """Test error when no missions found."""
    # Mock git to fail
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(NoMissionFoundError) as exc_info:
            detect_mission(repo_empty, cwd=repo_empty, mode="strict")

        error = str(exc_info.value)
        assert "No missions found" in error
        assert "spec-kitty specify" in error


def test_detect_no_missions_none_lenient(repo_empty: Path):
    """Test returns None when no missions found (lenient mode)."""
    # Mock git to fail
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        ctx = detect_mission(repo_empty, cwd=repo_empty, mode="lenient")

        assert ctx is None


def test_invalid_slug_format_explicit(repo_with_missions: Path):
    """Test error for invalid slug format (explicit parameter)."""
    with pytest.raises(MissionDetectionError) as exc_info:
        detect_mission(repo_with_missions, explicit_mission="invalid-slug")

    error = str(exc_info.value)
    assert "Invalid mission slug format" in error
    assert "###-mission-name" in error


def test_mission_not_found_explicit(repo_with_missions: Path):
    """Test error when explicitly specified mission doesn't exist."""
    with pytest.raises(NoMissionFoundError) as exc_info:
        detect_mission(repo_with_missions, explicit_mission="999-nonexistent")

    error = str(exc_info.value)
    assert "Mission directory not found" in error
    assert "999-nonexistent" in error


def test_mission_context_dataclass_fields(repo_with_missions: Path):
    """Test MissionContext dataclass has all expected fields."""
    ctx = detect_mission(repo_with_missions, explicit_mission="020-mission-a")

    # Check all fields are populated
    assert isinstance(ctx.slug, str)
    assert isinstance(ctx.number, str)
    assert isinstance(ctx.name, str)
    assert isinstance(ctx.directory, Path)
    assert isinstance(ctx.detection_method, str)

    # Check field values
    assert ctx.slug == "020-mission-a"
    assert ctx.number == "020"
    assert ctx.name == "mission-a"
    assert ctx.directory.name == "020-mission-a"
    assert ctx.detection_method == "explicit"


# ============================================================================
# Priority Order Tests
# ============================================================================


def test_priority_explicit_over_env(repo_with_missions: Path):
    """Test explicit parameter takes priority over env var."""
    env = {"SPECIFY_MISSION": "021-mission-b"}
    ctx = detect_mission(repo_with_missions, explicit_mission="020-mission-a", env=env)

    assert ctx.slug == "020-mission-a"
    assert ctx.detection_method == "explicit"


def test_priority_env_over_git(repo_with_missions: Path):
    """Test env var takes priority over git branch."""
    env = {"SPECIFY_MISSION": "021-mission-b"}

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="020-mission-a\n",
        )

        ctx = detect_mission(repo_with_missions, env=env)

        assert ctx.slug == "021-mission-b"
        assert ctx.detection_method == "env_var"


def test_priority_git_over_cwd(repo_with_missions: Path):
    """Test git branch takes priority over cwd."""
    mission_dir = repo_with_missions / "kitty-specs" / "021-mission-b"
    cwd = mission_dir

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="020-mission-a\n",
        )

        ctx = detect_mission(repo_with_missions, cwd=cwd)

        assert ctx.slug == "020-mission-a"
        assert ctx.detection_method == "git_branch"


def test_priority_cwd_over_single_auto(repo_with_single_mission: Path):
    """Test cwd takes priority over single auto-detect."""
    mission_dir = repo_with_single_mission / "kitty-specs" / "020-my-mission"

    # Create a second mission to make cwd detection meaningful
    (repo_with_single_mission / "kitty-specs" / "021-other").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        ctx = detect_mission(repo_with_single_mission, cwd=mission_dir)

        assert ctx.slug == "020-my-mission"
        assert ctx.detection_method == "cwd_path"


# ============================================================================
# Simplified Wrapper Tests
# ============================================================================


def test_detect_mission_slug_wrapper(repo_with_missions: Path):
    """Test detect_mission_slug() wrapper returns just the slug."""
    slug = detect_mission_slug(repo_with_missions, explicit_mission="020-mission-a")

    assert isinstance(slug, str)
    assert slug == "020-mission-a"


def test_detect_mission_slug_wrapper_raises_on_error(repo_empty: Path):
    """Test detect_mission_slug() wrapper raises on error (strict mode)."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(NoMissionFoundError):
            detect_mission_slug(repo_empty, cwd=repo_empty)


def test_detect_mission_directory_wrapper(repo_with_missions: Path):
    """Test detect_mission_directory() wrapper returns just the Path."""
    directory = detect_mission_directory(repo_with_missions, explicit_mission="020-mission-a")

    assert isinstance(directory, Path)
    assert directory.name == "020-mission-a"
    assert directory.parent.name == "kitty-specs"


def test_detect_mission_directory_wrapper_raises_on_error(repo_empty: Path):
    """Test detect_mission_directory() wrapper raises on error (strict mode)."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(NoMissionFoundError):
            detect_mission_directory(repo_empty, cwd=repo_empty)


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_allow_single_auto_disabled(repo_with_single_mission: Path):
    """Test single auto-detect can be disabled."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(NoMissionFoundError):
            detect_mission(
                repo_with_single_mission,
                cwd=repo_with_single_mission,
                allow_single_auto=False
            )


def test_empty_env_var_ignored(repo_with_missions: Path):
    """Test empty SPECIFY_MISSION env var is ignored."""
    env = {"SPECIFY_MISSION": "   "}  # Only whitespace

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="020-mission-a\n",
        )

        ctx = detect_mission(repo_with_missions, env=env)

        # Should fall through to git branch detection
        assert ctx.detection_method == "git_branch"


def test_git_command_not_found(repo_with_single_mission: Path):
    """Test graceful handling when git command not found."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError()

        # Should fall through to single auto-detect
        ctx = detect_mission(repo_with_single_mission, cwd=repo_with_single_mission)

        assert ctx.slug == "020-my-mission"
        assert ctx.detection_method == "single_auto"


def test_mission_slug_with_hyphens(tmp_path: Path):
    """Test mission slug with multiple hyphens in name."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir()
    (kitty_specs / "020-my-complex-mission-name").mkdir()

    ctx = detect_mission(repo_root, explicit_mission="020-my-complex-mission-name")

    assert ctx.slug == "020-my-complex-mission-name"
    assert ctx.number == "020"
    assert ctx.name == "my-complex-mission-name"


def test_worktree_context_with_main_repo_root(tmp_path: Path):
    """Test detection works in worktree context (simulated)."""
    # Create main repo
    main_repo = tmp_path / "main"
    main_repo.mkdir()
    kitty_specs = main_repo / "kitty-specs"
    kitty_specs.mkdir()
    (kitty_specs / "020-mission-a").mkdir()

    # Create worktree-like structure
    worktree = tmp_path / "worktrees" / "020-mission-a-WP01"
    worktree.mkdir(parents=True)

    # Create .git file pointing to main repo (simulates worktree)
    git_file = worktree / ".git"
    git_file.write_text(f"gitdir: {main_repo / '.git' / 'worktrees' / '020-mission-a-WP01'}")

    # Mock git command
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="020-mission-a-WP01\n",
        )

        ctx = detect_mission(worktree, cwd=worktree)

        # Should detect from git branch and strip WP suffix
        assert ctx.slug == "020-mission-a"


# ============================================================================
# Error Message Quality Tests
# ============================================================================


def test_error_message_multiple_missions_includes_guidance(repo_with_missions: Path):
    """Test error message when all missions are complete includes helpful guidance."""
    # Make all missions complete so fallback doesn't activate and error is raised
    for mission_name in ["020-mission-a", "021-mission-b", "022-mission-c"]:
        tasks_dir = repo_with_missions / "kitty-specs" / mission_name / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n"
        )

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(MultipleMissionsError) as exc_info:
            detect_mission(repo_with_missions, cwd=repo_with_missions)

        error_msg = str(exc_info.value)
        assert "--mission" in error_msg
        assert "SPECIFY_MISSION" in error_msg
        assert "All missions are complete" in error_msg


def test_error_message_no_missions_includes_creation_command(repo_empty: Path):
    """Test error message for no missions includes creation command."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(NoMissionFoundError) as exc_info:
            detect_mission(repo_empty, cwd=repo_empty)

        error_msg = str(exc_info.value)
        assert "spec-kitty specify" in error_msg
        assert "/spec-kitty.specify" in error_msg


def test_error_message_mission_not_found_lists_available(repo_with_missions: Path):
    """Test error message for nonexistent mission lists available missions."""
    with pytest.raises(NoMissionFoundError) as exc_info:
        detect_mission(repo_with_missions, explicit_mission="999-nonexistent")

    error_msg = str(exc_info.value)
    assert "Available missions:" in error_msg
    assert "020-mission-a" in error_msg
    assert "021-mission-b" in error_msg


# ============================================================================
# Completion Detection Tests (Priority 6 Fallback)
# ============================================================================


def test_is_mission_complete_all_done(tmp_path: Path):
    """Test is_mission_complete when all WPs have lane: 'done'."""
    from specify_cli.core.mission_detection import is_mission_complete

    # Create mission with all WPs done
    mission_dir = tmp_path / "020-my-mission"
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create WP files with lane: done
    (tasks_dir / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\nContent"
    )
    (tasks_dir / "WP02.md").write_text(
        "---\nwork_package_id: WP02\ntitle: Test\nlane: done\n---\nContent"
    )

    assert is_mission_complete(mission_dir) is True


def test_is_mission_complete_has_incomplete(tmp_path: Path):
    """Test is_mission_complete when some WPs are not done."""
    from specify_cli.core.mission_detection import is_mission_complete

    # Create mission with mixed lane statuses
    mission_dir = tmp_path / "020-my-mission"
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    (tasks_dir / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\nContent"
    )
    (tasks_dir / "WP02.md").write_text(
        "---\nwork_package_id: WP02\ntitle: Test\nlane: doing\n---\nContent"
    )

    assert is_mission_complete(mission_dir) is False


def test_is_mission_complete_no_tasks_dir(tmp_path: Path):
    """Test is_mission_complete when tasks directory doesn't exist."""
    from specify_cli.core.mission_detection import is_mission_complete

    mission_dir = tmp_path / "020-my-mission"
    mission_dir.mkdir()

    assert is_mission_complete(mission_dir) is False


def test_is_mission_complete_no_wp_files(tmp_path: Path):
    """Test is_mission_complete when no WP files exist."""
    from specify_cli.core.mission_detection import is_mission_complete

    mission_dir = tmp_path / "020-my-mission"
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    assert is_mission_complete(mission_dir) is False


def test_is_mission_complete_parse_error(tmp_path: Path):
    """Test is_mission_complete treats parse errors as incomplete (safe default)."""
    from specify_cli.core.mission_detection import is_mission_complete

    mission_dir = tmp_path / "020-my-mission"
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create malformed WP file
    (tasks_dir / "WP01.md").write_text("Invalid frontmatter")

    assert is_mission_complete(mission_dir) is False


def test_detect_multiple_missions_falls_back_to_latest_incomplete(tmp_path: Path):
    """Latest-incomplete fallback is available when callers opt in."""
    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir(parents=True)

    # Mission 020 - complete
    mission_020 = kitty_specs / "020-mission-a"
    tasks_020 = mission_020 / "tasks"
    tasks_020.mkdir(parents=True)
    (tasks_020 / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n"
    )

    # Mission 025 - incomplete
    mission_025 = kitty_specs / "025-mission-b"
    tasks_025 = mission_025 / "tasks"
    tasks_025.mkdir(parents=True)
    (tasks_025 / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: doing\n---\n"
    )

    # Mock git to fail (no branch/cwd context)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        ctx = detect_mission(
            repo_root,
            cwd=repo_root,
            mode="strict",
            allow_latest_incomplete=True,
        )

        assert ctx is not None
        assert ctx.slug == "025-mission-b"
        assert ctx.detection_method == "latest_incomplete"


def test_detect_explicit_mission_wins_over_ambiguity(tmp_path: Path):
    """Explicit --mission resolves correctly even with multiple missions."""
    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir(parents=True)

    mission_020 = kitty_specs / "020-complete"
    tasks_020 = mission_020 / "tasks"
    tasks_020.mkdir(parents=True)
    (tasks_020 / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n"
    )

    mission_025 = kitty_specs / "025-incomplete"
    tasks_025 = mission_025 / "tasks"
    tasks_025.mkdir(parents=True)
    (tasks_025 / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: doing\n---\n"
    )

    ctx = detect_mission(repo_root, explicit_mission="020-complete")

    assert ctx.slug == "020-complete"
    assert ctx.detection_method == "explicit"


def test_detect_fallback_error_when_all_complete(tmp_path: Path):
    """Test Priority 7: error when all missions complete (no fallback available)."""
    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir(parents=True)

    # Both missions complete
    for slug in ["020-mission-a", "025-mission-b"]:
        mission_dir = kitty_specs / slug
        tasks_dir = mission_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text(
            "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n"
        )

    # Mock git to fail (force fallback)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(MultipleMissionsError) as exc_info:
            detect_mission(repo_root, cwd=repo_root, mode="strict")

        error_msg = str(exc_info.value)
        assert "All missions are complete" in error_msg
        assert "spec-kitty specify" in error_msg


def test_detect_fallback_respects_priority_order(tmp_path: Path):
    """Test fallback (Priority 6) is lower than cwd detection (Priority 4)."""
    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir(parents=True)

    # Mission 020 - complete
    mission_020 = kitty_specs / "020-mission-a"
    tasks_020 = mission_020 / "tasks"
    tasks_020.mkdir(parents=True)
    (tasks_020 / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n"
    )

    # Mission 025 - incomplete
    mission_025 = kitty_specs / "025-mission-b"
    tasks_025 = mission_025 / "tasks"
    tasks_025.mkdir(parents=True)
    (tasks_025 / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: doing\n---\n"
    )

    # Mock git to fail (force cwd/fallback detection)
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        # Running from inside complete mission directory
        # Should detect from cwd (Priority 4), NOT fallback to 025 (Priority 6)
        ctx = detect_mission(repo_root, cwd=mission_020, mode="strict")

        assert ctx.slug == "020-mission-a"
        assert ctx.detection_method == "cwd_path"

# ============================================================================
# Target Branch Detection Tests
# ============================================================================


def test_get_mission_target_branch_with_main(tmp_path: Path):
    """Test get_mission_target_branch returns 'main' for mission with target_branch='main'."""
    import json

    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    mission_dir = kitty_specs / "020-mission-a"
    mission_dir.mkdir(parents=True)

    # Create meta.json with target_branch='main'
    meta = {
        "mission_number": "020",
        "slug": "020-mission-a",
        "target_branch": "main",
    }
    (mission_dir / "meta.json").write_text(json.dumps(meta))

    target = get_mission_target_branch(repo_root, "020-mission-a")
    assert target == "main"


def test_get_mission_target_branch_with_2x(tmp_path: Path):
    """Test get_mission_target_branch returns '2.x' for mission with target_branch='2.x'."""
    import json

    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    mission_dir = kitty_specs / "025-cli-event-log-integration"
    mission_dir.mkdir(parents=True)

    # Create meta.json with target_branch='2.x'
    meta = {
        "mission_number": "025",
        "slug": "025-cli-event-log-integration",
        "target_branch": "2.x",
    }
    (mission_dir / "meta.json").write_text(json.dumps(meta))

    target = get_mission_target_branch(repo_root, "025-cli-event-log-integration")
    assert target == "2.x"


def test_get_mission_target_branch_missing_field(tmp_path: Path):
    """Test get_mission_target_branch defaults to 'main' when target_branch field missing."""
    import json

    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    mission_dir = kitty_specs / "020-mission-a"
    mission_dir.mkdir(parents=True)

    # Create meta.json WITHOUT target_branch field (legacy mission)
    meta = {
        "mission_number": "020",
        "slug": "020-mission-a",
    }
    (mission_dir / "meta.json").write_text(json.dumps(meta))

    target = get_mission_target_branch(repo_root, "020-mission-a")
    assert target == "main"  # Safe default


def test_get_mission_target_branch_missing_meta_file(tmp_path: Path):
    """Test get_mission_target_branch defaults to 'main' when meta.json doesn't exist."""
    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    mission_dir = kitty_specs / "020-mission-a"
    mission_dir.mkdir(parents=True)

    # No meta.json file created

    target = get_mission_target_branch(repo_root, "020-mission-a")
    assert target == "main"  # Safe default


def test_get_mission_target_branch_malformed_json(tmp_path: Path):
    """Test get_mission_target_branch defaults to 'main' when meta.json is malformed."""
    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    mission_dir = kitty_specs / "020-mission-a"
    mission_dir.mkdir(parents=True)

    # Create malformed JSON
    (mission_dir / "meta.json").write_text("{invalid json")

    target = get_mission_target_branch(repo_root, "020-mission-a")
    assert target == "main"  # Safe default


def test_get_mission_target_branch_from_worktree(tmp_path: Path):
    """Test get_mission_target_branch works from worktree context."""
    import json


    # Create main repo structure
    main_repo = tmp_path / "main"
    kitty_specs = main_repo / "kitty-specs"
    mission_dir = kitty_specs / "025-cli-event-log-integration"
    mission_dir.mkdir(parents=True)

    meta = {
        "mission_number": "025",
        "slug": "025-cli-event-log-integration",
        "target_branch": "2.x",
    }
    (mission_dir / "meta.json").write_text(json.dumps(meta))

    # Create worktree directory (simulated)
    worktree = tmp_path / "worktrees" / "025-cli-event-log-integration-WP01"
    worktree.mkdir(parents=True)
    git_file = worktree / ".git"
    git_file.write_text(f"gitdir: {main_repo}/.git/worktrees/025-cli-event-log-integration-WP01")

    # Call from worktree context (should resolve to main repo)
    target = get_mission_target_branch(worktree, "025-cli-event-log-integration")
    assert target == "2.x"
