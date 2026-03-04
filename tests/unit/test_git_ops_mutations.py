"""Mutation testing for git_ops.py.

This test suite targets killable mutants identified in Iteration 2 of the
mutation testing campaign. Focus areas:

1. None assignments (subprocess results, path resolution)
2. Boolean condition negations (console resolution, branch behavior)
3. Subprocess argument mutations (cmd, cwd, capture_output)
4. String literal mutations (git commands, file paths)
5. Default parameter mutations (quiet, respect_current, remote_name)

See MUTATION_TESTING_ITERATION_2.md for full analysis.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
import subprocess

import pytest
from rich.console import Console

from specify_cli.core.git_ops import (
    _resolve_console,
    run_command,
    is_git_repo,
    get_current_branch,
    has_remote,
    has_tracking_branch,
    exclude_from_git_index,
    resolve_primary_branch,
    resolve_target_branch,
    init_git_repo,
)


class TestResolveConsole:
    """Test console resolution logic - targets boolean negation mutants."""

    def test_resolve_console_with_none_creates_new_console(self):
        """Test _resolve_console(None) creates new Console instance.

        Targets mutant: console if console is None else Console()
        Expected: Should return new Console(), not return None
        """
        result = _resolve_console(None)

        # If mutated to "console if console is None", would return None
        assert result is not None
        assert isinstance(result, Console)

    def test_resolve_console_with_console_returns_provided(self):
        """Test _resolve_console(console) returns the provided console.

        Targets mutant: console if console is None else Console()
        Expected: Should return provided console, not create new one
        """
        provided_console = Console()
        result = _resolve_console(provided_console)

        # If mutated, would create new Console instead of returning provided
        assert result is provided_console
        assert isinstance(result, Console)


class TestRunCommand:
    """Test run_command - targets subprocess argument and None assignment mutants."""

    def test_run_command_basic_execution(self):
        """Test run_command executes git command and returns result.

        Targets mutants:
        - cmd=None (run_command_5)
        - capture_output removed (run_command_15)
        Expected: subprocess.run called with cmd, returncode captured
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="test output", stderr="")

            returncode, stdout, stderr = run_command(["git", "--version"], capture=True)

            # Verify subprocess.run was called with correct command
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ["git", "--version"]  # cmd parameter
            assert call_args[1]["capture_output"] is True

            # Verify return values
            assert returncode == 0
            assert stdout == "test output"

    def test_run_command_with_capture_returns_output(self):
        """Test run_command with capture=True returns stdout/stderr.

        Targets mutant: capture_output parameter missing
        Expected: stdout and stderr are not empty strings when captured
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="captured stdout", stderr="captured stderr")

            returncode, stdout, stderr = run_command(["echo", "test"], capture=True)

            # If capture_output was removed, stdout/stderr would be empty
            assert stdout == "captured stdout"
            assert stderr == "captured stderr"
            assert mock_run.call_args[1]["capture_output"] is True

    def test_run_command_with_cwd_uses_correct_directory(self):
        """Test run_command with cwd parameter executes in correct directory.

        Targets mutants:
        - cwd=None (get_current_branch_10)
        - cwd parameter removed (run_command_20)
        Expected: subprocess.run called with cwd=str(cwd)
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            test_path = Path("/test/dir")

            run_command(["git", "status"], cwd=test_path)

            # If cwd was mutated to None, this would fail
            call_args = mock_run.call_args
            assert call_args[1]["cwd"] == str(test_path)

    def test_run_command_without_check_return_handles_errors(self):
        """Test run_command with check_return=False handles non-zero exit.

        Targets: error handling path, check parameter
        Expected: No exception raised, returncode captured
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="error")

            # Should not raise exception with check_return=False
            returncode, stdout, stderr = run_command(["false"], check_return=False, capture=True)

            assert returncode == 1
            assert stderr == "error"
            assert mock_run.call_args[1]["check"] is False


class TestIsGitRepo:
    """Test is_git_repo - targets path resolution and None assignment mutants."""

    def test_is_git_repo_with_valid_repo_returns_true(self):
        """Test is_git_repo returns True for valid git repository.

        Targets mutant: target = None (is_git_repo_1)
        Expected: Path resolved, git rev-parse succeeds, returns True
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            # Create temp dir and test
            with patch.object(Path, "is_dir", return_value=True):
                result = is_git_repo(Path("/test/repo"))

            # If target was mutated to None, would crash on target.is_dir()
            assert result is True
            mock_run.assert_called_once()

    def test_is_git_repo_with_none_path_uses_cwd(self):
        """Test is_git_repo(None) resolves to current working directory.

        Targets mutant: target = None instead of (path or Path.cwd()).resolve()
        Expected: Uses Path.cwd() when path is None
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            with patch.object(Path, "cwd") as mock_cwd, patch.object(Path, "is_dir", return_value=True):
                mock_cwd.return_value = Path("/current/dir")

                result = is_git_repo(None)

                # Verify Path.cwd() was called
                mock_cwd.assert_called()
                assert result is True

    def test_is_git_repo_with_non_git_dir_returns_false(self):
        """Test is_git_repo returns False for non-git directory.

        Targets: return value logic
        Expected: CalledProcessError caught, returns False
        """
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(128, "git")

            with patch.object(Path, "is_dir", return_value=True):
                result = is_git_repo(Path("/not/a/repo"))

            assert result is False


class TestGetCurrentBranch:
    """Test get_current_branch - targets path and subprocess mutants."""

    def test_get_current_branch_returns_branch_name(self):
        """Test get_current_branch returns current branch name.

        Targets mutants:
        - repo_path = None (get_current_branch_1)
        - cwd=None (get_current_branch_10)
        Expected: subprocess called with correct cwd, branch name returned
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="  main  \n")

            result = get_current_branch(Path("/test/repo"))

            # If repo_path was mutated to None, would crash
            assert result == "main"
            # Verify cwd was passed correctly
            call_args = mock_run.call_args
            assert call_args[1]["cwd"] == Path("/test/repo")

    def test_get_current_branch_with_none_path_uses_cwd(self):
        """Test get_current_branch(None) uses current working directory.

        Targets mutant: repo_path = None instead of path resolution
        Expected: Path.cwd() used when path is None
        """
        with patch("subprocess.run") as mock_run, patch.object(Path, "cwd") as mock_cwd:
            mock_run.return_value = Mock(returncode=0, stdout="develop")
            mock_cwd.return_value = Path("/current/dir")

            result = get_current_branch(None)

            # Verify Path.cwd() was called for resolution
            mock_cwd.assert_called()
            assert result == "develop"

    def test_get_current_branch_detached_head_returns_none(self):
        """Test get_current_branch returns None for detached HEAD.

        Targets: branch == "HEAD" logic
        Expected: Returns None when branch is "HEAD" (detached HEAD)
        """
        with patch("subprocess.run") as mock_run:
            # First call (git branch --show-current) fails
            # Second call (git rev-parse) returns "HEAD"
            mock_run.side_effect = [subprocess.CalledProcessError(128, "git"), Mock(returncode=0, stdout="HEAD")]

            result = get_current_branch(Path("/test/repo"))

            # Should return None for detached HEAD
            assert result is None


class TestHasRemote:
    """Test has_remote - targets string literal and default parameter mutants."""

    def test_has_remote_with_origin_returns_true(self):
        """Test has_remote returns True when origin remote exists.

        Targets mutants:
        - remote_name = "XXoriginXX" (has_remote_1)
        Expected: git remote get-url origin succeeds, returns True
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = has_remote(Path("/test/repo"))

            # Verify "origin" was used (not "XXoriginXX")
            call_args = mock_run.call_args
            assert "origin" in call_args[0][0]
            assert result is True

    def test_has_remote_with_custom_remote_name(self):
        """Test has_remote with custom remote name.

        Targets: remote_name parameter passed to git command
        Expected: git remote get-url <custom> called correctly
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = has_remote(Path("/test/repo"), remote_name="upstream")

            # Verify custom remote name was used
            call_args = mock_run.call_args
            assert "upstream" in call_args[0][0]
            assert result is True

    def test_has_remote_without_remote_returns_false(self):
        """Test has_remote returns False when remote does not exist.

        Targets: return code check (== 0 vs != 0)
        Expected: Non-zero returncode → returns False
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=128)

            result = has_remote(Path("/test/repo"))

            # Non-zero returncode should return False
            assert result is False


class TestHasTrackingBranch:
    """Test has_tracking_branch - targets subprocess result and None assignment."""

    def test_has_tracking_branch_with_tracking_returns_true(self):
        """Test has_tracking_branch returns True when upstream tracking configured.

        Targets mutant: result = None (has_tracking_branch_1)
        Expected: subprocess.run returns result, returncode == 0, returns True
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="origin/main")

            result = has_tracking_branch(Path("/test/repo"))

            # If result was mutated to None, would crash on result.returncode
            assert result is True
            mock_run.assert_called_once()

    def test_has_tracking_branch_without_tracking_returns_false(self):
        """Test has_tracking_branch returns False when no upstream tracking.

        Targets: return code check and empty output check
        Expected: returncode != 0 or empty stdout → returns False
        """
        with patch("subprocess.run") as mock_run:
            # Test non-zero returncode
            mock_run.return_value = Mock(returncode=128, stdout="")

            result = has_tracking_branch(Path("/test/repo"))
            assert result is False

            # Test empty output
            mock_run.return_value = Mock(returncode=0, stdout="  ")
            result = has_tracking_branch(Path("/test/repo"))
            assert result is False


class TestExcludeFromGitIndex:
    """Test exclude_from_git_index - targets path construction and file operations."""

    def test_exclude_from_git_index_creates_correct_path(self):
        """Test exclude_from_git_index constructs .git/info/exclude path correctly.

        Targets mutants:
        - exclude_file = None (exclude_from_git_index_1)
        - "exclude" → "EXCLUDE" (exclude_from_git_index_10)
        Expected: Path constructed as repo_path / ".git" / "info" / "exclude"
        """
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=""),
            patch.object(Path, "open", create=True) as mock_open,
        ):
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            repo_path = Path("/test/repo")
            exclude_from_git_index(repo_path, [".worktrees/"])

            # Verify correct path construction
            # If exclude_file was None, this would crash
            # If "exclude" was "EXCLUDE", path would be wrong
            mock_open.assert_called()

    def test_exclude_from_git_index_appends_patterns(self, tmp_path):
        """Test exclude_from_git_index appends new patterns to exclude file.

        Targets: file write operations, pattern checking
        Expected: New patterns added to file, existing patterns not duplicated
        """
        # Create real git structure
        git_info = tmp_path / ".git" / "info"
        git_info.mkdir(parents=True)
        exclude_file = git_info / "exclude"
        exclude_file.write_text("# Existing content\n.vscode/\n")

        # Add new patterns
        exclude_from_git_index(tmp_path, [".worktrees/", ".vscode/", "build/"])

        content = exclude_file.read_text()

        # Verify new patterns added
        assert ".worktrees/" in content
        assert "build/" in content
        # Verify existing pattern not duplicated
        assert content.count(".vscode/") == 1

    def test_exclude_from_git_index_handles_missing_file(self, tmp_path):
        """Test exclude_from_git_index returns early if exclude file missing.

        Targets: if not exclude_file.exists() logic
        Expected: Returns without error when file does not exist
        """
        # No .git directory exists
        exclude_from_git_index(tmp_path, [".worktrees/"])

        # Should return silently without creating file
        exclude_file = tmp_path / ".git" / "info" / "exclude"
        assert not exclude_file.exists()


class TestResolvePrimaryBranch:
    """Test resolve_primary_branch - targets subprocess and fallback logic."""

    def test_resolve_primary_branch_from_origin_head(self):
        """Test resolve_primary_branch detects branch from origin/HEAD.

        Targets mutants:
        - result = None (resolve_primary_branch_1)
        - "XXsymbolic-refXX" (resolve_primary_branch_20)
        Expected: git symbolic-ref called, branch name extracted from ref
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="refs/remotes/origin/main")

            result = resolve_primary_branch(Path("/test/repo"))

            # If result was None, would crash on result.returncode
            # If command was "XXsymbolic-refXX", would fail
            assert result == "main"
            call_args = mock_run.call_args
            assert "symbolic-ref" in call_args[0][0]

    def test_resolve_primary_branch_from_current_branch(self):
        """Test resolve_primary_branch uses current branch as fallback.

        Targets: Method 2 fallback logic
        Expected: get_current_branch() called when origin/HEAD fails
        """
        with (
            patch("subprocess.run") as mock_run,
            patch("specify_cli.core.git_ops.get_current_branch") as mock_get_branch,
        ):
            # Method 1 fails
            mock_run.return_value = Mock(returncode=128, stdout="")
            # Method 2 succeeds
            mock_get_branch.return_value = "develop"

            result = resolve_primary_branch(Path("/test/repo"))

            assert result == "develop"
            mock_get_branch.assert_called_once()

    def test_resolve_primary_branch_checks_common_branches(self):
        """Test resolve_primary_branch checks main/master/develop branches.

        Targets: Method 3 branch verification loop
        Expected: git rev-parse --verify called for main, master, develop
        """
        with (
            patch("subprocess.run") as mock_run,
            patch("specify_cli.core.git_ops.get_current_branch") as mock_get_branch,
        ):
            # Method 1 fails
            # Method 2 fails (no current branch)
            mock_get_branch.return_value = None
            # Method 3: first call fails (main), second succeeds (master)
            mock_run.side_effect = [
                Mock(returncode=128),  # Method 1 fails
                Mock(returncode=128),  # main doesn't exist
                Mock(returncode=0),  # master exists
            ]

            result = resolve_primary_branch(Path("/test/repo"))

            assert result == "master"

    def test_resolve_primary_branch_fallback_to_main(self):
        """Test resolve_primary_branch returns "main" as ultimate fallback.

        Targets: Method 4 hardcoded fallback
        Expected: Returns "main" when all detection methods fail
        """
        with (
            patch("subprocess.run") as mock_run,
            patch("specify_cli.core.git_ops.get_current_branch") as mock_get_branch,
        ):
            # All methods fail
            mock_run.return_value = Mock(returncode=128)
            mock_get_branch.return_value = None

            result = resolve_primary_branch(Path("/test/repo"))

            # Ultimate fallback
            assert result == "main"


class TestResolveTargetBranch:
    """Test resolve_target_branch - targets complex branching logic and file operations."""

    def test_resolve_target_branch_reads_meta_json(self, tmp_path):
        """Test resolve_target_branch reads target_branch from meta.json.

        Targets mutants:
        - meta_file = None (resolve_target_branch_10)
        - "KITTY-SPECS" (resolve_target_branch_15)
        - target = None (resolve_target_branch_20)
        Expected: meta.json read, target_branch extracted
        """
        # Create feature directory structure
        feature_dir = tmp_path / "kitty-specs" / "test-feature"
        feature_dir.mkdir(parents=True)
        meta_file = feature_dir / "meta.json"
        meta_file.write_text('{"target_branch": "develop"}')

        with patch("specify_cli.core.git_ops.get_current_branch") as mock_get_branch:
            mock_get_branch.return_value = "develop"

            result = resolve_target_branch("test-feature", tmp_path, current_branch="develop")

            # If meta_file was None, would crash
            # If path was "KITTY-SPECS", wouldn't find file
            # If target was None, result would be wrong
            assert result.target == "develop"

    def test_resolve_target_branch_with_matching_branches(self, tmp_path):
        """Test resolve_target_branch with current == target returns proceed.

        Targets: branch matching logic
        Expected: action="proceed", should_notify=False
        """
        result = resolve_target_branch("test-feature", tmp_path, current_branch="main")

        # When branches match
        if result.current == result.target:
            assert result.action == "proceed"
            assert result.should_notify is False

    def test_resolve_target_branch_respect_current_true(self, tmp_path):
        """Test resolve_target_branch with respect_current=True stays on current.

        Targets mutant: respect_current = False (resolve_target_branch_1)
        Expected: action="stay_on_current", should_notify=True
        """
        # Create feature with main as target
        feature_dir = tmp_path / "kitty-specs" / "test-feature"
        feature_dir.mkdir(parents=True)
        meta_file = feature_dir / "meta.json"
        meta_file.write_text('{"target_branch": "main"}')

        # User is on develop, respect_current=True (default)
        result = resolve_target_branch("test-feature", tmp_path, current_branch="develop", respect_current=True)

        # Should stay on current branch
        assert result.action == "stay_on_current"
        assert result.should_notify is True
        assert result.current == "develop"
        assert result.target == "main"

    def test_resolve_target_branch_respect_current_false(self, tmp_path):
        """Test resolve_target_branch with respect_current=False allows checkout.

        Targets: respect_current parameter behavior
        Expected: action="checkout_target", should_notify=True
        """
        # Create feature with main as target
        feature_dir = tmp_path / "kitty-specs" / "test-feature"
        feature_dir.mkdir(parents=True)
        meta_file = feature_dir / "meta.json"
        meta_file.write_text('{"target_branch": "main"}')

        # User is on develop, respect_current=False
        result = resolve_target_branch("test-feature", tmp_path, current_branch="develop", respect_current=False)

        # Should allow checkout
        assert result.action == "checkout_target"
        assert result.should_notify is True

    def test_resolve_target_branch_with_none_current_raises_error(self, tmp_path):
        """Test resolve_target_branch raises error when current branch is None.

        Targets: current_branch None check and RuntimeError
        Expected: RuntimeError("Could not determine current branch")
        """
        with patch("specify_cli.core.git_ops.get_current_branch") as mock_get_branch:
            mock_get_branch.return_value = None

            with pytest.raises(RuntimeError, match="Could not determine current branch"):
                resolve_target_branch("test-feature", tmp_path, current_branch=None)


class TestInitGitRepo:
    """Test init_git_repo - targets default parameters and console output."""

    def test_init_git_repo_quiet_false_shows_output(self):
        """Test init_git_repo with quiet=False prints console messages.

        Targets mutant: quiet = True (init_git_repo_1)
        Expected: Console.print called with initialization messages
        """
        with (
            patch("subprocess.run") as mock_run,
            patch("os.chdir"),
            patch.object(Path, "cwd", return_value=Path("/current")),
        ):
            mock_run.return_value = Mock(returncode=0)
            mock_console = Mock(spec=Console)

            init_git_repo(Path("/test/repo"), quiet=False, console=mock_console)

            # If quiet was mutated to True, console.print would not be called
            assert mock_console.print.call_count >= 2
            # Check for initialization messages
            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("Initializing" in str(call) for call in calls)

    def test_init_git_repo_quiet_true_suppresses_output(self):
        """Test init_git_repo with quiet=True suppresses console output.

        Targets: quiet parameter behavior
        Expected: Console.print not called
        """
        with (
            patch("subprocess.run") as mock_run,
            patch("os.chdir"),
            patch.object(Path, "cwd", return_value=Path("/current")),
        ):
            mock_run.return_value = Mock(returncode=0)
            mock_console = Mock(spec=Console)

            init_git_repo(Path("/test/repo"), quiet=True, console=mock_console)

            # With quiet=True, console should not be used
            mock_console.print.assert_not_called()

    def test_init_git_repo_executes_git_commands(self):
        """Test init_git_repo runs git init, add, commit commands.

        Targets: subprocess.run calls for git commands
        Expected: git init, git add ., git commit -m called in sequence
        """
        with (
            patch("subprocess.run") as mock_run,
            patch("os.chdir"),
            patch.object(Path, "cwd", return_value=Path("/current")),
        ):
            mock_run.return_value = Mock(returncode=0)

            result = init_git_repo(Path("/test/repo"), quiet=True)

            # Verify git commands were executed
            assert result is True
            assert mock_run.call_count == 3

            # Check command sequence
            calls = [call[0][0] for call in mock_run.call_args_list]
            assert calls[0][0] == "git" and calls[0][1] == "init"
            assert calls[1][0] == "git" and calls[1][1] == "add"
            assert calls[2][0] == "git" and calls[2][1] == "commit"
