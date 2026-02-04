"""Tests for the consolidated task_helpers_shared module.

Validates that the shared module provides consistent behavior for both the
installed package entrypoint (tasks_support) and the standalone script
entrypoint (scripts/tasks/task_helpers).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.task_helpers_shared import (
    LANES,
    TaskCliError,
    append_activity_log,
    activity_entries,
    build_document,
    detect_conflicting_wp_status,
    ensure_lane,
    extract_scalar,
    find_repo_root,
    get_lane_from_frontmatter,
    is_legacy_format,
    locate_work_package,
    path_has_changes,
    run_git,
    set_scalar,
    split_frontmatter,
)


# ---------------------------------------------------------------------------
# Worktree-aware repo root detection
# ---------------------------------------------------------------------------


class TestFindRepoRoot:
    """Tests for find_repo_root with worktree awareness."""

    def test_normal_repo(self, tmp_path: Path) -> None:
        """find_repo_root finds .git directory in a normal repo."""
        (tmp_path / ".git").mkdir()
        assert find_repo_root(tmp_path) == tmp_path

    def test_kittify_marker(self, tmp_path: Path) -> None:
        """find_repo_root falls back to .kittify marker."""
        (tmp_path / ".kittify").mkdir()
        assert find_repo_root(tmp_path) == tmp_path

    def test_worktree_follows_pointer(self, tmp_path: Path) -> None:
        """find_repo_root follows worktree .git file pointer to main repo."""
        main_repo = tmp_path / "main-repo"
        main_repo.mkdir()
        git_dir = main_repo / ".git"
        git_dir.mkdir()
        worktrees_dir = git_dir / "worktrees" / "feature-branch"
        worktrees_dir.mkdir(parents=True)

        worktree = tmp_path / "worktrees" / "feature-branch"
        worktree.mkdir(parents=True)
        (worktree / ".git").write_text(f"gitdir: {worktrees_dir}\n")

        result = find_repo_root(worktree)
        assert result == main_repo

    def test_walks_upward_from_subdirectory(self, tmp_path: Path) -> None:
        """find_repo_root walks up from deep subdirectory to find root."""
        main_repo = tmp_path / "main-repo"
        main_repo.mkdir()
        git_dir = main_repo / ".git"
        git_dir.mkdir()
        worktrees_dir = git_dir / "worktrees" / "feature-branch"
        worktrees_dir.mkdir(parents=True)

        worktree = tmp_path / "worktrees" / "feature-branch"
        worktree.mkdir(parents=True)
        (worktree / ".git").write_text(f"gitdir: {worktrees_dir}\n")

        subdir = worktree / "src" / "deep" / "path"
        subdir.mkdir(parents=True)
        result = find_repo_root(subdir)
        assert result == main_repo

    def test_no_git_raises(self, tmp_path: Path) -> None:
        """find_repo_root raises TaskCliError when no .git or .kittify found."""
        with pytest.raises(TaskCliError, match="Unable to locate repository root"):
            find_repo_root(tmp_path)

    def test_malformed_gitfile_raises(self, tmp_path: Path) -> None:
        """find_repo_root raises when .git file is malformed and no markers above."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        (worktree / ".git").write_text("invalid content\n")
        with pytest.raises(TaskCliError, match="Unable to locate repository root"):
            find_repo_root(worktree)

    def test_walks_upward_from_deep(self, tmp_path: Path) -> None:
        """find_repo_root walks upward through parent directories."""
        (tmp_path / ".git").mkdir()
        deep_dir = tmp_path / "a" / "b" / "c" / "d"
        deep_dir.mkdir(parents=True)
        assert find_repo_root(deep_dir) == tmp_path

    def test_worktree_and_main_parity(self, tmp_path: Path) -> None:
        """find_repo_root returns same root from both worktree and main repo."""
        main_repo = tmp_path / "main-repo"
        main_repo.mkdir()
        git_dir = main_repo / ".git"
        git_dir.mkdir()
        worktrees_dir = git_dir / "worktrees" / "feature"
        worktrees_dir.mkdir(parents=True)

        worktree = tmp_path / "worktrees" / "feature"
        worktree.mkdir(parents=True)
        (worktree / ".git").write_text(f"gitdir: {worktrees_dir}\n")

        main_root = find_repo_root(main_repo)
        worktree_root = find_repo_root(worktree)
        assert main_root == worktree_root == main_repo


# ---------------------------------------------------------------------------
# Conflict detection parity
# ---------------------------------------------------------------------------


class TestDetectConflictingWpStatus:
    """Tests for detect_conflicting_wp_status with delete suffix handling."""

    def test_no_conflicts(self) -> None:
        """Empty status lines produce no conflicts."""
        result = detect_conflicting_wp_status(
            [],
            "001-feature",
            Path("kitty-specs/001-feature/tasks/WP01.md"),
            Path("kitty-specs/001-feature/tasks/WP01.md"),
        )
        assert result == []

    def test_allowed_paths_not_conflicting(self) -> None:
        """Exact old/new path matches are not conflicts."""
        status = [
            " M kitty-specs/001-feature/tasks/WP01.md",
        ]
        result = detect_conflicting_wp_status(
            status,
            "001-feature",
            Path("kitty-specs/001-feature/tasks/WP01.md"),
            Path("kitty-specs/001-feature/tasks/WP01.md"),
        )
        assert result == []

    def test_other_wp_is_conflict(self) -> None:
        """A change to a different WP file is detected as conflict."""
        status = [
            " M kitty-specs/001-feature/tasks/WP02.md",
        ]
        result = detect_conflicting_wp_status(
            status,
            "001-feature",
            Path("kitty-specs/001-feature/tasks/WP01.md"),
            Path("kitty-specs/001-feature/tasks/WP01.md"),
        )
        assert len(result) == 1
        assert "WP02" in result[0]

    def test_delete_suffix_not_conflicting(self) -> None:
        """A delete (D) status for the same WP suffix is not a conflict.

        This validates parity with the script's enhanced logic for handling
        file deletions during lane moves (legacy format).
        """
        old_path = Path("kitty-specs/001-feature/tasks/planned/WP01.md")
        new_path = Path("kitty-specs/001-feature/tasks/doing/WP01.md")
        status = [
            "D  kitty-specs/001-feature/tasks/planned/WP01.md",
        ]
        result = detect_conflicting_wp_status(
            status,
            "001-feature",
            old_path,
            new_path,
        )
        assert result == []

    def test_delete_different_suffix_is_conflict(self) -> None:
        """A delete of a different WP suffix IS a conflict."""
        old_path = Path("kitty-specs/001-feature/tasks/planned/WP01.md")
        new_path = Path("kitty-specs/001-feature/tasks/doing/WP01.md")
        status = [
            "D  kitty-specs/001-feature/tasks/planned/WP02.md",
        ]
        result = detect_conflicting_wp_status(
            status,
            "001-feature",
            old_path,
            new_path,
        )
        assert len(result) == 1

    def test_non_task_paths_ignored(self) -> None:
        """Status lines for non-task paths are ignored."""
        status = [
            " M src/main.py",
            " M kitty-specs/001-feature/spec.md",
        ]
        result = detect_conflicting_wp_status(
            status,
            "001-feature",
            Path("kitty-specs/001-feature/tasks/WP01.md"),
            Path("kitty-specs/001-feature/tasks/WP01.md"),
        )
        assert result == []


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------


class TestFrontmatterHelpers:
    """Tests for frontmatter parsing and manipulation."""

    def test_split_frontmatter_basic(self) -> None:
        text = "---\nkey: value\n---\n\nBody text\n"
        front, body, padding = split_frontmatter(text)
        assert front == "key: value"
        assert body == "Body text\n"
        assert padding == "\n\n"

    def test_split_frontmatter_no_frontmatter(self) -> None:
        text = "Just body text\n"
        front, body, padding = split_frontmatter(text)
        assert front == ""
        assert body == text
        assert padding == ""

    def test_set_scalar_replaces_existing(self) -> None:
        front = 'lane: "planned"\nkey: "val"'
        result = set_scalar(front, "lane", "doing")
        assert '"doing"' in result
        assert '"planned"' not in result

    def test_set_scalar_inserts_new(self) -> None:
        front = 'key: "val"'
        result = set_scalar(front, "lane", "doing")
        assert 'lane: "doing"' in result

    def test_extract_scalar_quoted(self) -> None:
        front = 'lane: "planned"'
        assert extract_scalar(front, "lane") == "planned"

    def test_extract_scalar_single_quoted(self) -> None:
        front = "lane: 'planned'"
        assert extract_scalar(front, "lane") == "planned"

    def test_extract_scalar_unquoted(self) -> None:
        front = "lane: planned"
        assert extract_scalar(front, "lane") == "planned"

    def test_extract_scalar_missing(self) -> None:
        front = "other: value"
        assert extract_scalar(front, "lane") is None

    def test_build_document_roundtrip(self) -> None:
        front = 'lane: "planned"'
        body = "Body text\n"
        padding = "\n"
        doc = build_document(front, body, padding)
        f2, b2, p2 = split_frontmatter(doc)
        assert f2 == front
        assert b2 == body
        assert p2 == padding


# ---------------------------------------------------------------------------
# Legacy format detection
# ---------------------------------------------------------------------------


class TestIsLegacyFormat:
    """Tests for is_legacy_format."""

    def test_no_tasks_dir(self, tmp_path: Path) -> None:
        assert is_legacy_format(tmp_path) is False

    def test_empty_lane_dirs(self, tmp_path: Path) -> None:
        """Empty lane directories are not legacy format."""
        tasks = tmp_path / "tasks"
        (tasks / "planned").mkdir(parents=True)
        (tasks / "planned" / ".gitkeep").touch()
        assert is_legacy_format(tmp_path) is False

    def test_lane_dirs_with_md(self, tmp_path: Path) -> None:
        """Lane directories with .md files are legacy format."""
        tasks = tmp_path / "tasks"
        lane_dir = tasks / "doing"
        lane_dir.mkdir(parents=True)
        (lane_dir / "WP01.md").write_text("---\nlane: doing\n---\n")
        assert is_legacy_format(tmp_path) is True

    def test_flat_tasks_not_legacy(self, tmp_path: Path) -> None:
        """Flat tasks directory with no lane subdirs is not legacy."""
        tasks = tmp_path / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "WP01.md").write_text("---\nlane: planned\n---\n")
        assert is_legacy_format(tmp_path) is False


# ---------------------------------------------------------------------------
# path_has_changes
# ---------------------------------------------------------------------------


class TestPathHasChanges:
    """Tests for path_has_changes helper."""

    def test_detects_modification(self) -> None:
        status = [" M src/main.py"]
        assert path_has_changes(status, Path("src/main.py")) is True

    def test_no_match(self) -> None:
        status = [" M src/other.py"]
        assert path_has_changes(status, Path("src/main.py")) is False

    def test_handles_short_lines(self) -> None:
        status = ["??"]
        assert path_has_changes(status, Path("src/main.py")) is False


# ---------------------------------------------------------------------------
# Lane validation
# ---------------------------------------------------------------------------


class TestEnsureLane:
    """Tests for ensure_lane."""

    def test_valid_lanes(self) -> None:
        for lane in LANES:
            assert ensure_lane(lane) == lane
            assert ensure_lane(f" {lane.upper()} ") == lane

    def test_invalid_lane(self) -> None:
        with pytest.raises(TaskCliError, match="Invalid lane"):
            ensure_lane("invalid")


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


class TestRunGit:
    """Tests for run_git helper."""

    def test_git_not_on_path(self, tmp_path: Path) -> None:
        """run_git raises TaskCliError when git is missing."""
        with patch("specify_cli.task_helpers_shared.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git not found")
            with pytest.raises(TaskCliError, match="git is not available on PATH"):
                run_git(["status"], cwd=tmp_path)

    def test_git_failure_check_true(self, tmp_path: Path) -> None:
        """run_git raises TaskCliError on command failure with check=True."""
        with patch("specify_cli.task_helpers_shared.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, ["git"], stderr="fatal: not a git repo"
            )
            with pytest.raises(TaskCliError, match="not a git repo"):
                run_git(["status"], cwd=tmp_path, check=True)

    def test_git_failure_check_false(self, tmp_path: Path) -> None:
        """run_git returns CompletedProcess on failure with check=False."""
        error = subprocess.CalledProcessError(
            1, ["git"], stderr="error"
        )
        with patch("specify_cli.task_helpers_shared.subprocess.run") as mock_run:
            mock_run.side_effect = error
            result = run_git(["status"], cwd=tmp_path, check=False)
            # Should return the error (CalledProcessError), not raise
            assert result is error


# ---------------------------------------------------------------------------
# Import parity: tasks_support and script task_helpers expose same API
# ---------------------------------------------------------------------------


class TestImportParity:
    """Verify both consumer modules expose the same public symbols."""

    def test_tasks_support_reexports(self) -> None:
        """tasks_support re-exports all shared symbols."""
        import specify_cli.tasks_support as ts
        import specify_cli.task_helpers_shared as shared

        shared_names = set(shared.__all__)
        ts_names = set(ts.__all__)
        # tasks_support should have at least everything in shared
        missing = shared_names - ts_names
        assert not missing, f"tasks_support missing: {missing}"

    def test_script_task_helpers_reexports(self) -> None:
        """Script task_helpers re-exports all shared symbols."""
        import sys
        script_dir = str(
            Path(__file__).resolve().parents[2]
            / "src"
            / "specify_cli"
            / "scripts"
            / "tasks"
        )
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)

        import task_helpers as th
        import specify_cli.task_helpers_shared as shared

        shared_names = set(shared.__all__)
        th_names = set(th.__all__)
        missing = shared_names - th_names
        assert not missing, f"script task_helpers missing: {missing}"


# ---------------------------------------------------------------------------
# Activity log helpers
# ---------------------------------------------------------------------------


class TestActivityLog:
    """Tests for activity log append and parse."""

    def test_append_creates_section(self) -> None:
        body = "# Some content\n"
        entry = "- 2026-01-01T00:00:00Z - system - lane=planned - Created"
        result = append_activity_log(body, entry)
        assert "## Activity Log" in result
        assert entry in result

    def test_append_to_existing_section(self) -> None:
        body = "## Activity Log\n\n- entry1\n"
        entry = "- entry2"
        result = append_activity_log(body, entry)
        assert "- entry1" in result
        assert "- entry2" in result

    def test_entries_parse_hyphenated_agent(self) -> None:
        body = (
            "## Activity Log\n\n"
            "- 2026-01-26T14:00:00Z \u2013 cursor-agent \u2013 "
            "shell_pid=12345 \u2013 lane=doing \u2013 Started work\n"
        )
        entries = activity_entries(body)
        assert len(entries) == 1
        assert entries[0]["agent"] == "cursor-agent"
        assert entries[0]["lane"] == "doing"

    def test_entries_without_shell_pid(self) -> None:
        body = (
            "- 2026-01-26T12:00:00Z \u2013 system \u2013 "
            "lane=planned \u2013 Auto-generated\n"
        )
        entries = activity_entries(body)
        assert len(entries) == 1
        assert entries[0]["shell_pid"] == ""


# ---------------------------------------------------------------------------
# get_lane_from_frontmatter
# ---------------------------------------------------------------------------


class TestGetLaneFromFrontmatter:
    """Tests for get_lane_from_frontmatter."""

    def test_extracts_lane(self, tmp_path: Path) -> None:
        wp = tmp_path / "WP01.md"
        wp.write_text('---\nlane: "doing"\n---\nBody\n')
        assert get_lane_from_frontmatter(wp) == "doing"

    def test_defaults_to_planned(self, tmp_path: Path) -> None:
        wp = tmp_path / "WP01.md"
        wp.write_text("---\ntitle: test\n---\nBody\n")
        assert get_lane_from_frontmatter(wp, warn_on_missing=False) == "planned"

    def test_invalid_lane_raises(self, tmp_path: Path) -> None:
        wp = tmp_path / "WP01.md"
        wp.write_text('---\nlane: "invalid"\n---\nBody\n')
        with pytest.raises(ValueError, match="Invalid lane"):
            get_lane_from_frontmatter(wp)


# ---------------------------------------------------------------------------
# locate_work_package
# ---------------------------------------------------------------------------


class TestLocateWorkPackage:
    """Tests for locate_work_package."""

    def test_flat_format(self, tmp_path: Path) -> None:
        """Locate WP in flat tasks/ directory."""
        feature = "001-test"
        tasks = tmp_path / "kitty-specs" / feature / "tasks"
        tasks.mkdir(parents=True)
        wp_file = tasks / "WP01.md"
        wp_file.write_text(
            '---\nwork_package_id: "WP01"\nlane: "planned"\n---\nBody\n'
        )
        wp = locate_work_package(tmp_path, feature, "WP01")
        assert wp.feature == feature
        assert wp.current_lane == "planned"
        assert wp.work_package_id == "WP01"

    def test_not_found_raises(self, tmp_path: Path) -> None:
        """Raise TaskCliError when WP not found."""
        feature = "001-test"
        tasks = tmp_path / "kitty-specs" / feature / "tasks"
        tasks.mkdir(parents=True)
        with pytest.raises(TaskCliError, match="not found"):
            locate_work_package(tmp_path, feature, "WP99")

    def test_no_tasks_dir_raises(self, tmp_path: Path) -> None:
        """Raise TaskCliError when tasks directory missing."""
        feature = "001-test"
        (tmp_path / "kitty-specs" / feature).mkdir(parents=True)
        with pytest.raises(TaskCliError, match="no tasks directory"):
            locate_work_package(tmp_path, feature, "WP01")
