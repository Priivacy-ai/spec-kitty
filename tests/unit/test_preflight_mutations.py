"""Mutation testing for merge/preflight.py

This test suite targets killable mutants in preflight validation logic.
Focuses on 5 key patterns identified in MUTATION_TESTING_ITERATION_4.md:
1. Git status detection logic
2. Target branch divergence detection
3. Missing worktree detection
4. Lane value parsing from frontmatter
5. PreflightResult state accumulation
"""

from unittest.mock import Mock, patch

import pytest

from specify_cli.merge.preflight import (
    WPStatus,
    _wp_lane_from_feature,
    check_target_divergence,
    check_worktree_status,
    run_preflight,
)


class TestCheckWorktreeStatus:
    """Pattern 1: Git status detection logic.

    Targets mutants in subprocess.run() calls, boolean logic,
    path handling, and error message construction.
    """

    def test_clean_worktree_returns_clean_status(self, tmp_path):
        """Verify clean worktree detected correctly.

        Kills mutants:
        - `is_clean = result.stdout.strip()` (boolean negation)
        - `error = None` (always None mutation)
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="", returncode=0)

            result = check_worktree_status(tmp_path, "WP01", "feature-WP01")

            assert result.is_clean is True
            assert result.error is None
            assert result.wp_id == "WP01"
            assert result.branch_name == "feature-WP01"

    def test_dirty_worktree_returns_unclean_status_with_error(self, tmp_path):
        """Verify dirty worktree detected with error message.

        Kills mutants:
        - `is_clean = not result.stdout.strip()` → `is_clean = result.stdout.strip()`
        - `error = None if is_clean else ...` → `error = None` (always None)
        - Error message format mutations
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=" M file.py\n", returncode=0)

            result = check_worktree_status(tmp_path, "WP02", "feature-WP02")

            assert result.is_clean is False
            assert result.error is not None
            assert "Uncommitted changes" in result.error
            assert tmp_path.name in result.error

    def test_subprocess_failure_returns_unclean_with_exception_message(self, tmp_path):
        """Verify subprocess failures handled gracefully.

        Kills mutants:
        - Exception handling logic
        - `is_clean=False` in except block
        - `error=str(e)` mutations
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Command not found")

            result = check_worktree_status(tmp_path, "WP03", "feature-WP03")

            assert result.is_clean is False
            assert result.error == "Command not found"

    def test_git_runs_in_correct_directory(self, tmp_path):
        """Verify git status command runs in worktree directory.

        Kills mutants:
        - `cwd=str(worktree_path)` removal
        - `cwd` parameter mutations
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="", returncode=0)

            check_worktree_status(tmp_path, "WP01", "branch")

            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["cwd"] == str(tmp_path)

    def test_git_command_correct_arguments(self, tmp_path):
        """Verify git status called with correct arguments.

        Kills mutants:
        - `["git", "status", "--porcelain"]` mutations
        - Argument string mutations
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="", returncode=0)

            check_worktree_status(tmp_path, "WP01", "branch")

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args == ["git", "status", "--porcelain"]

    def test_subprocess_text_mode_enabled(self, tmp_path):
        """Verify subprocess runs in text mode.

        Kills mutants:
        - `text=True` → `text=None` or `text=False`
        - `encoding="utf-8"` mutations
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="", returncode=0)

            check_worktree_status(tmp_path, "WP01", "branch")

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["text"] is True
            assert call_kwargs["encoding"] == "utf-8"

    def test_subprocess_run_not_nullified(self, tmp_path):
        """Verify subprocess.run() is actually called.

        Kills mutants:
        - `result = subprocess.run(...)` → `result = None`
        """
        with patch("subprocess.run") as mock_run:
            # If result=None mutant, this will fail with AttributeError
            mock_run.return_value = Mock(stdout="test", returncode=0)

            result = check_worktree_status(tmp_path, "WP01", "branch")

            # Should not raise AttributeError accessing result.stdout
            assert result.is_clean is not None


class TestCheckTargetDivergence:
    """Pattern 2: Target branch divergence detection.

    Targets mutants in comparison operators, return value logic,
    parsing logic, and error handling.
    """

    def test_branches_in_sync_returns_no_divergence(self, tmp_path):
        """Verify no divergence when behind=0.

        Kills mutants:
        - `if behind > 0:` → `if behind >= 0:` (comparison mutation)
        - Return value inversions
        """
        with patch("subprocess.run") as mock_run:
            # First call: git fetch (ignored)
            # Second call: git rev-list returns "0\t0" (ahead=0, behind=0)
            mock_run.side_effect = [
                Mock(returncode=0),  # fetch
                Mock(stdout="0\t0\n", returncode=0),  # rev-list
            ]

            diverged, msg = check_target_divergence("main", tmp_path)

            assert diverged is False
            assert msg is None

    def test_behind_origin_returns_divergence_with_message(self, tmp_path):
        """Verify divergence detected when behind > 0.

        Kills mutants:
        - `if behind > 0:` boundary conditions
        - Return value mutations
        - Message format mutations
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0),  # fetch
                Mock(stdout="0\t3\n", returncode=0),  # ahead=0, behind=3
            ]

            diverged, msg = check_target_divergence("main", tmp_path)

            assert diverged is True
            assert msg is not None
            assert "3 commit(s) behind" in msg
            assert "main" in msg
            assert "git pull" in msg

    def test_ahead_of_origin_no_divergence(self, tmp_path):
        """Verify no divergence when ahead but not behind.

        Kills mutants:
        - Logic for ahead vs behind comparison
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0),  # fetch
                Mock(stdout="5\t0\n", returncode=0),  # ahead=5, behind=0
            ]

            diverged, msg = check_target_divergence("main", tmp_path)

            assert diverged is False
            assert msg is None

    def test_no_remote_tracking_returns_false_gracefully(self, tmp_path):
        """Verify graceful handling when remote tracking missing.

        Kills mutants:
        - `if result.returncode != 0: return False, None` → `return True, None`
        - Non-fatal error handling logic
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0),  # fetch succeeds
                Mock(stdout="", returncode=128),  # rev-list fails (no remote)
            ]

            diverged, msg = check_target_divergence("main", tmp_path)

            # Should return False (assume OK) not True
            assert diverged is False
            assert msg is None

    def test_git_command_failure_graceful_degradation(self, tmp_path):
        """Verify exceptions handled gracefully.

        Kills mutants:
        - Exception handling → raises
        - Return values in except block
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Network error")

            diverged, msg = check_target_divergence("main", tmp_path)

            # Should not raise, returns (False, None)
            assert diverged is False
            assert msg is None

    def test_malformed_output_returns_false_gracefully(self, tmp_path):
        """Verify malformed git output handled gracefully.

        Kills mutants:
        - `if len(parts) != 2: return False, None` → other returns
        - Parsing logic mutations
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0),  # fetch
                Mock(stdout="invalid output\n", returncode=0),  # malformed
            ]

            diverged, msg = check_target_divergence("main", tmp_path)

            assert diverged is False
            assert msg is None

    def test_git_fetch_uses_correct_arguments(self, tmp_path):
        """Verify git fetch command correct.

        Kills mutants:
        - `["git", "fetch", "origin", target_branch]` mutations
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0),
                Mock(stdout="0\t0\n", returncode=0),
            ]

            check_target_divergence("develop", tmp_path)

            fetch_call = mock_run.call_args_list[0]
            assert fetch_call[0][0] == ["git", "fetch", "origin", "develop"]

    def test_git_rev_list_uses_correct_format(self, tmp_path):
        """Verify git rev-list command format.

        Kills mutants:
        - `--left-right` → `--LEFT-RIGHT`
        - `--count` → `--COUNT`
        - f-string format mutations
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0),
                Mock(stdout="0\t0\n", returncode=0),
            ]

            check_target_divergence("main", tmp_path)

            revlist_call = mock_run.call_args_list[1]
            args = revlist_call[0][0]
            assert "--left-right" in args
            assert "--count" in args
            assert "main...origin/main" in args

    def test_parsing_ahead_behind_values(self, tmp_path):
        """Verify ahead/behind values parsed correctly.

        Kills mutants:
        - `map(int, parts)` mutations
        - Variable assignment mutations
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0),
                Mock(stdout="7\t2\n", returncode=0),  # ahead=7, behind=2
            ]

            diverged, msg = check_target_divergence("main", tmp_path)

            # behind=2 > 0, so should diverge
            assert diverged is True
            assert "2 commit(s) behind" in msg


class TestWPLaneFromFeature:
    """Pattern 4: Lane value parsing from frontmatter.

    Targets mutants in path construction, file I/O,
    regex matching, and return value logic.
    """

    def test_valid_frontmatter_returns_lane(self, tmp_path):
        """Verify lane extracted from valid frontmatter.

        Kills mutants:
        - Return None mutations
        - Regex pattern mutations
        - .strip().lower() mutations
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        task_file = tasks_dir / "WP01-setup.md"
        task_file.write_text("---\nlane: planned\n---\n# Task content\n", encoding="utf-8")

        lane = _wp_lane_from_feature(tmp_path, "001-feature", "WP01")

        assert lane == "planned"

    def test_missing_tasks_directory_returns_none(self, tmp_path):
        """Verify None returned when tasks dir missing.

        Kills mutants:
        - `if not tasks_dir.exists(): return None` logic mutations
        """
        lane = _wp_lane_from_feature(tmp_path, "nonexistent", "WP01")
        assert lane is None

    def test_no_matching_task_file_returns_none(self, tmp_path):
        """Verify None returned when no matching task file.

        Kills mutants:
        - `if not candidates: return None` mutations
        - glob pattern mutations
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        lane = _wp_lane_from_feature(tmp_path, "001-feature", "WP99")
        assert lane is None

    def test_no_frontmatter_returns_none(self, tmp_path):
        """Verify None returned when file has no frontmatter.

        Kills mutants:
        - `if not content.startswith("---"):` logic mutations
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        task_file = tasks_dir / "WP01-setup.md"
        task_file.write_text("# No frontmatter\nJust content", encoding="utf-8")

        lane = _wp_lane_from_feature(tmp_path, "001-feature", "WP01")
        assert lane is None

    def test_no_lane_field_returns_none(self, tmp_path):
        """Verify None returned when frontmatter has no lane field.

        Kills mutants:
        - `if not match: return None` mutations
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        task_file = tasks_dir / "WP01-setup.md"
        task_file.write_text("---\ntitle: Some task\n---\n", encoding="utf-8")

        lane = _wp_lane_from_feature(tmp_path, "001-feature", "WP01")
        assert lane is None

    def test_lane_extracted_case_insensitive(self, tmp_path):
        """Verify lane value lowercased.

        Kills mutants:
        - `.lower()` removal
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        task_file = tasks_dir / "WP01-setup.md"
        task_file.write_text("---\nlane: PLANNED\n---\n", encoding="utf-8")

        lane = _wp_lane_from_feature(tmp_path, "001-feature", "WP01")
        assert lane == "planned"

    def test_lane_with_quotes_stripped(self, tmp_path):
        """Verify quotes stripped from lane value.

        Kills mutants:
        - Regex capture group mutations
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        task_file = tasks_dir / "WP01-setup.md"
        task_file.write_text('---\nlane: "doing"\n---\n', encoding="utf-8")

        lane = _wp_lane_from_feature(tmp_path, "001-feature", "WP01")
        assert lane == "doing"

    def test_multiple_matching_files_uses_first_sorted(self, tmp_path):
        """Verify first file used when multiple match.

        Kills mutants:
        - `sorted()` removal
        - `candidates[0]` indexing mutations
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create multiple files that match WP01*
        (tasks_dir / "WP01-a-first.md").write_text("---\nlane: planned\n---\n", encoding="utf-8")
        (tasks_dir / "WP01-z-last.md").write_text("---\nlane: done\n---\n", encoding="utf-8")

        lane = _wp_lane_from_feature(tmp_path, "001-feature", "WP01")
        # Should use first alphabetically
        assert lane == "planned"

    def test_tasks_path_construction(self, tmp_path):
        """Verify correct path construction.

        Kills mutants:
        - `tasks_dir = None`
        - "/" vs path component mutations
        - "tasks" → "XXtasksXX" string mutations
        """
        feature_dir = tmp_path / "kitty-specs" / "002-test"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        task_file = tasks_dir / "WP05.md"
        task_file.write_text("---\nlane: for_review\n---\n", encoding="utf-8")

        lane = _wp_lane_from_feature(tmp_path, "002-test", "WP05")
        assert lane == "for_review"

    def test_glob_pattern_correct(self, tmp_path):
        """Verify glob pattern matches WP ID correctly.

        Kills mutants:
        - `tasks_dir.glob(f"{wp_id}*.md")` → `glob(None)`
        - Pattern string mutations
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create files with different WP IDs
        (tasks_dir / "WP01-task.md").write_text("---\nlane: doing\n---\n")
        (tasks_dir / "WP02-task.md").write_text("---\nlane: planned\n---\n")

        lane = _wp_lane_from_feature(tmp_path, "001-feature", "WP02")
        assert lane == "planned"  # Should match WP02, not WP01


class TestRunPreflight:
    """Pattern 3 & 5: Missing worktree detection and result accumulation.

    Targets mutants in set operations, conditional logic, error/warning
    accumulation, and PreflightResult state management.
    """

    def test_all_checks_pass_returns_passed_true(self, tmp_path):
        """Verify all checks passing returns passed=True.

        Kills mutants:
        - `result = PreflightResult(passed=True)` → `result = None`
        - `result.passed` mutations
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create task file so expected_wps has WP01
        (tasks_dir / "WP01.md").write_text("content")

        worktree_path = tmp_path / ".worktrees" / "001-feature-WP01"
        worktree_path.mkdir(parents=True)

        with patch("specify_cli.merge.preflight.check_worktree_status") as mock_check:  # noqa: SIM117
            with patch("specify_cli.merge.preflight.check_target_divergence") as mock_diverge:
                mock_check.return_value = WPStatus(
                    wp_id="WP01",
                    worktree_path=worktree_path,
                    branch_name="branch",
                    is_clean=True,
                    error=None,
                )
                mock_diverge.return_value = (False, None)

                result = run_preflight(
                    "001-feature",
                    "main",
                    tmp_path,
                    [(worktree_path, "WP01", "branch")],
                )

                assert result.passed is True
                assert len(result.errors) == 0

    def test_missing_worktree_not_done_fails_validation(self, tmp_path):
        """Verify missing worktree (not done) causes failure.

        Kills mutants:
        - `result.passed = False` removals
        - `if missing_wps:` logic mutations
        - Error message mutations
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create task file with lane != done
        (tasks_dir / "WP01.md").write_text("---\nlane: planned\n---\n")

        with patch("specify_cli.merge.preflight.check_target_divergence") as mock_diverge:
            mock_diverge.return_value = (False, None)

            # No worktrees provided, WP01 is missing
            result = run_preflight("001-feature", "main", tmp_path, [])

            assert result.passed is False
            assert any("Missing worktree for WP01" in e for e in result.errors)

    def test_missing_worktree_done_lane_only_warning(self, tmp_path):
        """Verify missing worktree with lane=done only warns.

        Kills mutants:
        - `if lane == "done":` → `if lane == "XXdoneXX":`
        - `result.warnings.append(...)` mutations
        - `continue` statement removals
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create task file with lane=done
        (tasks_dir / "WP01.md").write_text("---\nlane: done\n---\n")

        with patch("specify_cli.merge.preflight.check_target_divergence") as mock_diverge:
            mock_diverge.return_value = (False, None)

            result = run_preflight("001-feature", "main", tmp_path, [])

            # Should pass (warning only, not error)
            assert result.passed is True
            assert any("lane=done" in w for w in result.warnings)
            assert len(result.errors) == 0

    def test_dirty_worktree_fails_validation(self, tmp_path):
        """Verify dirty worktree causes validation failure.

        Kills mutants:
        - `if not status.is_clean:` logic mutations
        - `result.passed = False` mutations
        - Error accumulation mutations
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text("content")

        worktree_path = tmp_path / ".worktrees" / "001-feature-WP01"

        with patch("specify_cli.merge.preflight.check_worktree_status") as mock_check:  # noqa: SIM117
            with patch("specify_cli.merge.preflight.check_target_divergence") as mock_diverge:
                mock_check.return_value = WPStatus(
                    wp_id="WP01",
                    worktree_path=worktree_path,
                    branch_name="branch",
                    is_clean=False,
                    error="Uncommitted changes",
                )
                mock_diverge.return_value = (False, None)

                result = run_preflight(
                    "001-feature",
                    "main",
                    tmp_path,
                    [(worktree_path, "WP01", "branch")],
                )

                assert result.passed is False
                assert any("Uncommitted changes" in e or "uncommitted changes" in e for e in result.errors)

    def test_target_diverged_fails_validation(self, tmp_path):
        """Verify target divergence causes validation failure.

        Kills mutants:
        - `result.target_diverged = diverged` mutations
        - `if diverged:` logic mutations
        - Error message mutations
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text("content")

        worktree_path = tmp_path / ".worktrees" / "001-feature-WP01"

        with patch("specify_cli.merge.preflight.check_worktree_status") as mock_check:  # noqa: SIM117
            with patch("specify_cli.merge.preflight.check_target_divergence") as mock_diverge:
                mock_check.return_value = WPStatus(
                    wp_id="WP01",
                    worktree_path=worktree_path,
                    branch_name="branch",
                    is_clean=True,
                    error=None,
                )
                mock_diverge.return_value = (True, "main is 2 commits behind")

                result = run_preflight(
                    "001-feature",
                    "main",
                    tmp_path,
                    [(worktree_path, "WP01", "branch")],
                )

                assert result.passed is False
                assert result.target_diverged is True
                assert result.target_divergence_msg == "main is 2 commits behind"
                assert any("behind" in e for e in result.errors)

    def test_multiple_failures_accumulated(self, tmp_path):
        """Verify multiple failures all accumulated in errors list.

        Kills mutants:
        - `result.errors.append(...)` mutations
        - Error list accumulation logic
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text("---\nlane: planned\n---\n")
        (tasks_dir / "WP02.md").write_text("content")

        wt1 = tmp_path / ".worktrees" / "001-feature-WP02"

        with patch("specify_cli.merge.preflight.check_worktree_status") as mock_check:  # noqa: SIM117
            with patch("specify_cli.merge.preflight.check_target_divergence") as mock_diverge:
                mock_check.return_value = WPStatus(
                    wp_id="WP02",
                    worktree_path=wt1,
                    branch_name="branch",
                    is_clean=False,
                    error="Dirty worktree",
                )
                mock_diverge.return_value = (True, "Behind origin")

                result = run_preflight(
                    "001-feature",
                    "main",
                    tmp_path,
                    [(wt1, "WP02", "branch")],
                )

                # Should have 3 errors: missing WP01, dirty WP02, target diverged
                assert result.passed is False
                assert len(result.errors) == 3

    def test_wp_statuses_populated(self, tmp_path):
        """Verify wp_statuses list populated correctly.

        Kills mutants:
        - `result.wp_statuses.append(...)` mutations
        - WPStatus object creation mutations
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text("content")
        (tasks_dir / "WP02.md").write_text("content")

        wt1 = tmp_path / ".worktrees" / "001-feature-WP01"
        wt2 = tmp_path / ".worktrees" / "001-feature-WP02"

        with patch("specify_cli.merge.preflight.check_worktree_status") as mock_check:  # noqa: SIM117
            with patch("specify_cli.merge.preflight.check_target_divergence") as mock_diverge:
                mock_check.side_effect = [
                    WPStatus("WP01", wt1, "b1", True, None),
                    WPStatus("WP02", wt2, "b2", False, "Error"),
                ]
                mock_diverge.return_value = (False, None)

                result = run_preflight(
                    "001-feature",
                    "main",
                    tmp_path,
                    [(wt1, "WP01", "b1"), (wt2, "WP02", "b2")],
                )

                assert len(result.wp_statuses) == 2
                assert result.wp_statuses[0].wp_id == "WP01"
                assert result.wp_statuses[1].wp_id == "WP02"

    def test_discovered_wps_set_comprehension(self, tmp_path):
        """Verify discovered_wps set built correctly.

        Kills mutants:
        - `discovered_wps = {wp_id for _, wp_id, _ in wp_workspaces}` → `None`
        - Set comprehension logic mutations
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text("content")
        (tasks_dir / "WP02.md").write_text("content")

        wt1 = tmp_path / ".worktrees" / "001-feature-WP01"
        wt2 = tmp_path / ".worktrees" / "001-feature-WP02"

        with patch("specify_cli.merge.preflight.check_worktree_status") as mock_check:  # noqa: SIM117
            with patch("specify_cli.merge.preflight.check_target_divergence") as mock_diverge:
                mock_check.return_value = WPStatus("WP", wt1, "b", True, None)
                mock_diverge.return_value = (False, None)

                # Provide both WPs - should have no missing
                result = run_preflight(
                    "001-feature",
                    "main",
                    tmp_path,
                    [(wt1, "WP01", "b1"), (wt2, "WP02", "b2")],
                )

                # If discovered_wps = None, this would fail with TypeError
                assert result.passed is True

    def test_missing_wps_calculation(self, tmp_path):
        """Verify missing_wps set difference calculated correctly.

        Kills mutants:
        - `missing_wps = sorted(expected_wps - discovered_wps)` → `sorted(None)`
        - Set difference operation mutations
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text("---\nlane: planned\n---\n")
        (tasks_dir / "WP02.md").write_text("---\nlane: planned\n---\n")
        (tasks_dir / "WP03.md").write_text("---\nlane: planned\n---\n")

        wt1 = tmp_path / ".worktrees" / "001-feature-WP01"

        with patch("specify_cli.merge.preflight.check_worktree_status") as mock_check:  # noqa: SIM117
            with patch("specify_cli.merge.preflight.check_target_divergence") as mock_diverge:
                mock_check.return_value = WPStatus("WP01", wt1, "b", True, None)
                mock_diverge.return_value = (False, None)

                # Only WP01 provided, WP02 and WP03 missing
                result = run_preflight(
                    "001-feature",
                    "main",
                    tmp_path,
                    [(wt1, "WP01", "b1")],
                )

                # Should detect 2 missing worktrees
                assert result.passed is False
                missing_errors = [e for e in result.errors if "Missing worktree" in e]
                assert len(missing_errors) == 2

    def test_error_message_correctness(self, tmp_path):
        """Verify error messages contain expected information.

        Kills mutants:
        - Error message f-string mutations
        - Variable substitution mutations
        """
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP99.md").write_text("---\nlane: planned\n---\n")

        with patch("specify_cli.merge.preflight.check_target_divergence") as mock_diverge:
            mock_diverge.return_value = (False, None)

            result = run_preflight("001-feature", "main", tmp_path, [])

            # Error should mention WP99 and expected path
            assert any("WP99" in e for e in result.errors)
            assert any("spec-kitty agent workflow implement" in e for e in result.errors)


class TestEdgeCases:
    """Additional edge cases and integration scenarios."""

    def test_empty_worktree_list_with_no_expected_wps(self, tmp_path):
        """Verify empty feature (no tasks) passes validation."""
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        # No task files created

        with patch("specify_cli.merge.preflight.check_target_divergence") as mock_diverge:
            mock_diverge.return_value = (False, None)

            result = run_preflight("001-feature", "main", tmp_path, [])

            assert result.passed is True

    def test_subprocess_error_in_lane_check_handled(self, tmp_path):
        """Verify file read errors in lane check don't crash."""
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create a file that will cause read error
        task_file = tasks_dir / "WP01.md"
        task_file.write_text("---\nlane: planned\n---\n")

        # The function doesn't currently catch read_text() exceptions
        # This test verifies the current behavior (exception propagates)
        with patch("pathlib.Path.read_text") as mock_read:
            mock_read.side_effect = OSError("Permission denied")

            # Should raise OSError (current implementation doesn't catch it)
            with pytest.raises(OSError):
                _wp_lane_from_feature(tmp_path, "001-feature", "WP01")

    def test_result_passed_logic_with_warnings_but_no_errors(self, tmp_path):
        """Verify warnings don't cause validation failure."""
        feature_dir = tmp_path / "kitty-specs" / "001-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01.md").write_text("---\nlane: done\n---\n")

        with patch("specify_cli.merge.preflight.check_target_divergence") as mock_diverge:
            mock_diverge.return_value = (False, None)

            result = run_preflight("001-feature", "main", tmp_path, [])

            # Should pass despite warnings
            assert result.passed is True
            assert len(result.warnings) > 0
            assert len(result.errors) == 0
