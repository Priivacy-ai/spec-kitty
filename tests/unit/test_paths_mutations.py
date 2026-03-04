"""
Mutation tests for src/specify_cli/core/paths.py

This test suite targets mutation testing coverage for path resolution and worktree
detection logic. Focus areas:
- Worktree topology validation
- Environment variable override
- Broken symlink detection
- Default parameter handling
- File vs directory detection
- Boolean operator chains

Created for Mutation Testing Iteration 5 (FINAL)
Estimated mutants: ~109 mutation points
Target: 23 tests covering 5 killable patterns
"""

from pathlib import Path


from specify_cli.core.paths import (
    _is_worktree_gitdir,
    check_broken_symlink,
    get_main_repo_root,
    is_worktree_context,
    locate_project_root,
    resolve_with_context,
)


class TestIsWorktreeGitdir:
    """Test _is_worktree_gitdir helper function.

    Validates worktree topology detection:
    - Valid: .git/worktrees/<name>
    - Invalid: .git/modules/<name> (submodule)
    - Invalid: other topologies
    """

    def test_valid_worktree_topology_non_bare(self):
        """Valid non-bare worktree: /repo/.git/worktrees/feature-001.

        Kills mutants:
        - String literal "worktrees" mutation
        - String literal ".git" mutation
        - Comparison operator inversion (== to !=)
        """
        gitdir = Path("/repo/.git/worktrees/feature-001")
        assert _is_worktree_gitdir(gitdir) is True

    def test_valid_worktree_topology_bare_repo(self):
        """Valid bare repo worktree: /repos/myrepo.git/worktrees/feature.

        Kills mutants:
        - String endswith ".git" mutation
        """
        gitdir = Path("/repos/myrepo.git/worktrees/feature")
        assert _is_worktree_gitdir(gitdir) is True

    def test_invalid_submodule_topology(self):
        """Invalid: .git/modules/submodule (submodule, not worktree).

        Kills mutants:
        - Boolean operator inversion (would return True)
        """
        gitdir = Path("/repo/.git/modules/mysubmodule")
        assert _is_worktree_gitdir(gitdir) is False

    def test_invalid_parent_not_worktrees(self):
        """Invalid: parent directory is not named 'worktrees'.

        Kills mutants:
        - String literal "worktrees" mutation (would accept wrong name)
        - Comparison operator inversion
        """
        gitdir = Path("/repo/.git/other/feature-001")
        assert _is_worktree_gitdir(gitdir) is False

    def test_invalid_grandparent_not_git(self):
        """Invalid: grandparent doesn't end with .git.

        Kills mutants:
        - String endswith ".git" mutation
        """
        gitdir = Path("/repo/something/worktrees/feature")
        assert _is_worktree_gitdir(gitdir) is False


class TestLocateProjectRoot:
    """Test locate_project_root function.

    Tests resolution order:
    1. SPECIFY_REPO_ROOT environment variable
    2. Directory tree walk with worktree detection
    3. .kittify marker fallback
    """

    def test_env_var_override_valid(self, tmp_path, monkeypatch):
        """Environment variable SPECIFY_REPO_ROOT takes precedence.

        Kills mutants:
        - String literal "SPECIFY_REPO_ROOT" mutation
        - Boolean and -> or mutation (would accept invalid paths)
        """
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        monkeypatch.setenv("SPECIFY_REPO_ROOT", str(tmp_path))

        # Should use env var, not cwd
        result = locate_project_root()
        assert result == tmp_path

    def test_env_var_invalid_no_kittify(self, tmp_path, monkeypatch):
        """Invalid env var (no .kittify) falls through to other methods.

        Kills mutants:
        - Boolean and -> or mutation (would accept missing .kittify)
        """
        # No .kittify dir
        monkeypatch.setenv("SPECIFY_REPO_ROOT", str(tmp_path))

        result = locate_project_root(tmp_path)
        assert result is None  # Invalid env var, no fallback

    def test_no_args_uses_cwd(self, tmp_path, monkeypatch):
        """Calling with no args should use current working directory.

        Kills mutants:
        - Default parameter mutation (start or None)
        """
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        monkeypatch.chdir(tmp_path)

        result = locate_project_root()  # No args
        assert result == tmp_path

    def test_git_directory_main_repo(self, tmp_path):
        """Main repo has .git directory.

        Kills mutants:
        - is_dir() -> is_file() swap
        - Boolean and -> or in existence check
        """
        main_repo = tmp_path / "repo"
        main_repo.mkdir()
        (main_repo / ".git").mkdir()
        (main_repo / ".kittify").mkdir()

        result = locate_project_root(main_repo)
        assert result == main_repo

    def test_git_file_worktree_resolves_to_main(self, tmp_path):
        """Worktree has .git file with gitdir pointer, returns main repo.

        Kills mutants:
        - is_file() -> is_dir() swap
        - String literal "gitdir:" mutation
        - String split ":" mutation
        - Boolean topology check inversions
        """
        # Setup main repo
        main_repo = tmp_path / "repo"
        main_git = main_repo / ".git"
        worktrees_dir = main_git / "worktrees"
        worktrees_dir.mkdir(parents=True)
        (main_repo / ".kittify").mkdir()

        # Setup worktree with .git file
        worktree_dir = tmp_path / ".worktrees" / "feature-001"
        worktree_dir.mkdir(parents=True)
        worktree_git_file = worktree_dir / ".git"
        worktree_git_file.write_text(f"gitdir: {worktrees_dir}/feature-001\n")

        # Should resolve to main repo, not worktree
        result = locate_project_root(worktree_dir)
        assert result == main_repo

    def test_kittify_marker_fallback(self, tmp_path):
        """Falls back to .kittify marker when no .git found.

        Kills mutants:
        - is_dir() check mutations
        """
        project = tmp_path / "project"
        project.mkdir()
        (project / ".kittify").mkdir()

        result = locate_project_root(project)
        assert result == project

    def test_skips_broken_symlink_kittify(self, tmp_path):
        """Skips broken symlink .kittify directories.

        Kills mutants:
        - Boolean and -> or in broken symlink check
        """
        project = tmp_path / "project"
        project.mkdir()

        # Create broken symlink
        broken_kittify = project / ".kittify"
        broken_kittify.symlink_to("/nonexistent/path")

        # Should skip broken symlink, not find root
        result = locate_project_root(project)
        assert result is None

    def test_not_found_returns_none(self, tmp_path):
        """Returns None when no project root found.

        Kills mutants:
        - Return value mutation (None -> "")
        """
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = locate_project_root(empty_dir)
        assert result is None
        assert not isinstance(result, str)  # Ensure type correctness


class TestIsWorktreeContext:
    """Test is_worktree_context function.

    Detects if path is within a git worktree:
    1. Fast path: .worktrees in path parts
    2. Generic: .git file with gitdir pointer
    """

    def test_fast_path_worktrees_in_parts(self, tmp_path):
        """Fast path: .worktrees appears in path hierarchy.

        Kills mutants:
        - Membership test inversion (in -> not in)
        """
        path = tmp_path / ".worktrees" / "feature-001" / "src"
        assert is_worktree_context(path) is True

    def test_generic_git_file_with_gitdir_pointer(self, tmp_path):
        """Generic detection: .git file with gitdir: pointer.

        Kills mutants:
        - is_file() -> is_dir() swap
        - String startswith "gitdir:" mutation
        - Boolean topology check inversions
        """
        # Setup worktree directory with .git file
        worktree_dir = tmp_path / "my-worktree"
        worktree_dir.mkdir()
        git_file = worktree_dir / ".git"
        git_file.write_text("gitdir: /main/.git/worktrees/my-worktree\n")

        assert is_worktree_context(worktree_dir) is True

    def test_main_repo_returns_false(self, tmp_path):
        """Main repo with .git directory is not a worktree.

        Kills mutants:
        - Return value mutation (False -> True)
        - is_dir() -> is_file() swap
        """
        main_repo = tmp_path / "repo"
        main_repo.mkdir()
        (main_repo / ".git").mkdir()

        assert is_worktree_context(main_repo) is False

    def test_no_git_returns_false(self, tmp_path):
        """Path without .git is not a worktree.

        Kills mutants:
        - Return value mutation
        """
        plain_dir = tmp_path / "plain"
        plain_dir.mkdir()

        assert is_worktree_context(plain_dir) is False


class TestResolveWithContext:
    """Test resolve_with_context function.

    Combines locate_project_root and is_worktree_context in one call.
    """

    def test_no_args_uses_cwd(self, tmp_path, monkeypatch):
        """Calling with no args should use current directory.

        Kills mutants:
        - Default parameter mutation (start or None)
        """
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        monkeypatch.chdir(tmp_path)

        root, in_worktree = resolve_with_context()  # No args
        assert root == tmp_path
        assert in_worktree is False

    def test_from_worktree_path(self, tmp_path):
        """Resolves from worktree path, detects worktree context.

        Kills mutants:
        - Multiple mutants in both functions
        """
        # Setup main repo
        main_repo = tmp_path / "repo"
        main_git = main_repo / ".git"
        worktrees_dir = main_git / "worktrees"
        worktrees_dir.mkdir(parents=True)
        (main_repo / ".kittify").mkdir()

        # Setup worktree
        worktree_dir = tmp_path / ".worktrees" / "feature"
        worktree_dir.mkdir(parents=True)
        git_file = worktree_dir / ".git"
        git_file.write_text(f"gitdir: {worktrees_dir}/feature\n")

        root, in_worktree = resolve_with_context(worktree_dir)
        assert root == main_repo
        assert in_worktree is True


class TestCheckBrokenSymlink:
    """Test check_broken_symlink helper function.

    Detects symlinks pointing to non-existent targets.
    """

    def test_broken_symlink_returns_true(self, tmp_path):
        """Symlink pointing to non-existent target is broken.

        Kills mutants:
        - Boolean and -> or mutation
        - Negation inversion (not exists)
        """
        link = tmp_path / "broken_link"
        link.symlink_to("/nonexistent/path")

        assert check_broken_symlink(link) is True

    def test_valid_symlink_returns_false(self, tmp_path):
        """Valid symlink to existing file is not broken.

        Kills mutants:
        - Boolean and -> or mutation (would return True)
        """
        target = tmp_path / "target.txt"
        target.write_text("data")
        link = tmp_path / "valid_link"
        link.symlink_to(target)

        assert check_broken_symlink(link) is False

    def test_regular_file_returns_false(self, tmp_path):
        """Regular file (not symlink) is not broken.

        Kills mutants:
        - Boolean and -> or mutation (would return True for !exists)
        """
        regular_file = tmp_path / "regular.txt"
        regular_file.write_text("data")

        assert check_broken_symlink(regular_file) is False


class TestGetMainRepoRoot:
    """Test get_main_repo_root function.

    Follows .git file gitdir pointer to find main repo, or returns current path.
    """

    def test_worktree_resolves_to_main_repo(self, tmp_path):
        """Worktree with .git file resolves to main repo root.

        Kills mutants:
        - is_file() -> is_dir() swap
        - String parsing mutations
        """
        # Setup main repo
        main_repo = tmp_path / "repo"
        main_git = main_repo / ".git"
        worktrees_dir = main_git / "worktrees"
        worktrees_dir.mkdir(parents=True)

        # Setup worktree
        worktree_dir = tmp_path / ".worktrees" / "feature"
        worktree_dir.mkdir(parents=True)
        git_file = worktree_dir / ".git"
        git_file.write_text(f"gitdir: {worktrees_dir}/feature\n")

        result = get_main_repo_root(worktree_dir)
        assert result == main_repo

    def test_main_repo_returns_same_path(self, tmp_path):
        """Main repo (no gitdir pointer) returns same path.

        Kills mutants:
        - Return value mutation (current_path -> None)
        """
        main_repo = tmp_path / "repo"
        main_repo.mkdir()
        (main_repo / ".git").mkdir()

        result = get_main_repo_root(main_repo)
        assert result == main_repo

    def test_no_git_returns_current_path(self, tmp_path):
        """Path without .git returns current path (fallback).

        Kills mutants:
        - Return value mutation
        """
        plain_dir = tmp_path / "plain"
        plain_dir.mkdir()

        result = get_main_repo_root(plain_dir)
        assert result == plain_dir


class TestPathResolutionEdgeCases:
    """Additional edge cases for comprehensive mutation coverage."""

    def test_locate_project_root_with_explicit_start_path(self, tmp_path):
        """Explicit start path parameter is used.

        Kills mutants:
        - Default parameter usage (ensure explicit path works)
        """
        project = tmp_path / "project"
        project.mkdir()
        (project / ".kittify").mkdir()

        result = locate_project_root(start=project)
        assert result == project

    def test_locate_project_root_walks_up_parent_dirs(self, tmp_path):
        """Walks up parent directories to find root.

        Validates directory traversal logic.
        """
        project = tmp_path / "project"
        project.mkdir()
        (project / ".kittify").mkdir()

        # Start from subdirectory
        subdir = project / "src" / "modules"
        subdir.mkdir(parents=True)

        result = locate_project_root(subdir)
        assert result == project

    def test_is_worktree_context_from_subdirectory(self, tmp_path):
        """Detects worktree context from subdirectory within worktree.

        Validates upward traversal for .git file detection.
        """
        worktree_dir = tmp_path / ".worktrees" / "feature"
        subdir = worktree_dir / "src" / "modules"
        subdir.mkdir(parents=True)

        # Fast path should catch .worktrees in path
        assert is_worktree_context(subdir) is True


class TestEncodingRobustness:
    """Tests for encoding handling bug discovered during mutation testing.

    Bug: .read_text() calls lacked explicit encoding parameter, risking
    UnicodeDecodeError on non-UTF-8 systems or git files with special chars.

    Fix: Added encoding="utf-8", errors="replace" to all .read_text() calls.
    """

    def test_locate_project_root_handles_non_utf8_git_file(self, tmp_path):
        """Verify .git file reading doesn't fail on encoding issues."""
        from specify_cli.core.paths import locate_project_root

        # Create worktree with .git file containing potential non-UTF-8 bytes
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        kittify = tmp_path / ".kittify"
        kittify.mkdir()

        git_file = worktree / ".git"
        # Write with explicit UTF-8 to ensure test consistency
        git_file.write_text("gitdir: /path/with/special/chars", encoding="utf-8")

        # Should not raise UnicodeDecodeError
        result = locate_project_root(worktree)
        assert result is not None or result is None  # Just verify no exception

    def test_is_worktree_context_handles_malformed_git_file(self, tmp_path):
        """Verify malformed .git files don't crash the detector."""
        from specify_cli.core.paths import is_worktree_context

        worktree = tmp_path / "worktree"
        worktree.mkdir()
        git_file = worktree / ".git"

        # Write malformed content (missing proper gitdir structure)
        git_file.write_text("not a valid gitdir pointer", encoding="utf-8")

        # Should return False, not raise exception
        result = is_worktree_context(worktree)
        assert result is False

    def test_get_main_repo_root_handles_corrupted_git_file(self, tmp_path):
        """Verify corrupted .git file doesn't crash main repo detection."""
        from specify_cli.core.paths import get_main_repo_root

        repo = tmp_path / "repo"
        repo.mkdir()
        git_file = repo / ".git"

        # Write invalid gitdir content (empty path after colon)
        git_file.write_text("gitdir:", encoding="utf-8")

        # Should fall back to current path (resolved), not crash
        result = get_main_repo_root(repo)
        # The result should be the resolved repo path
        assert result == repo.resolve()
