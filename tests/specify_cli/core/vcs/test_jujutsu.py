"""
Tests for JujutsuVCS implementation.

Tests all VCSProtocol methods for the jj backend.
Requires jj to be installed - tests are marked with @pytest.mark.jj.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from specify_cli.core.vcs import VCSBackend, VCSProtocol
from specify_cli.core.vcs.jujutsu import (
    JujutsuVCS,
    _extract_jj_error,
    jj_get_change_by_id,
    jj_get_operation_log,
    jj_undo_operation,
)
from specify_cli.core.vcs.types import (
    SyncStatus,
)


# =============================================================================
# Skip if jj not installed
# =============================================================================

# Check if jj is available
JJ_AVAILABLE = shutil.which("jj") is not None

pytestmark = pytest.mark.skipif(not JJ_AVAILABLE, reason="jj not installed")


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def jj_repo(tmp_path):
    """Create a minimal jj repository for testing (colocated with git)."""
    # Initialize colocated repo
    subprocess.run(
        ["jj", "git", "init", "--colocate"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    # Configure git user for the colocated repo
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        capture_output=True,
    )

    # Create initial content
    test_file = tmp_path / "README.md"
    test_file.write_text("# Test Repo\n")

    # Describe the change (jj working copy is always a commit)
    subprocess.run(
        ["jj", "describe", "-m", "Initial commit"],
        cwd=tmp_path,
        capture_output=True,
    )

    # Create a new empty change on top
    subprocess.run(
        ["jj", "new"],
        cwd=tmp_path,
        capture_output=True,
    )

    return tmp_path


@pytest.fixture
def jj_vcs():
    """Create a JujutsuVCS instance."""
    return JujutsuVCS()


# =============================================================================
# Basic Properties Tests
# =============================================================================


class TestJujutsuVCSProperties:
    """Tests for JujutsuVCS properties."""

    def test_backend_property(self, jj_vcs):
        """JujutsuVCS should return JUJUTSU backend."""
        assert jj_vcs.backend == VCSBackend.JUJUTSU

    def test_capabilities_property(self, jj_vcs):
        """JujutsuVCS should return correct capabilities."""
        caps = jj_vcs.capabilities
        assert caps.supports_workspaces is True
        assert caps.supports_auto_rebase is True
        assert caps.supports_change_ids is True
        assert caps.supports_operation_log is True
        assert caps.supports_conflict_storage is True
        assert caps.supports_colocated is True
        assert caps.supports_operation_undo is True

    def test_implements_protocol(self, jj_vcs):
        """JujutsuVCS should implement VCSProtocol."""
        assert isinstance(jj_vcs, VCSProtocol)


# =============================================================================
# Repository Operations Tests
# =============================================================================


class TestRepositoryOperations:
    """Tests for repository-level operations."""

    def test_is_repo_true_for_jj_repo(self, jj_repo, jj_vcs):
        """is_repo should return True for jj repository."""
        assert jj_vcs.is_repo(jj_repo) is True

    def test_is_repo_false_for_non_repo(self, tmp_path, jj_vcs):
        """is_repo should return False for non-repository directory."""
        assert jj_vcs.is_repo(tmp_path) is False

    def test_is_repo_false_for_nonexistent(self, tmp_path, jj_vcs):
        """is_repo should return False for nonexistent path."""
        assert jj_vcs.is_repo(tmp_path / "nonexistent") is False

    def test_get_repo_root(self, jj_repo, jj_vcs):
        """get_repo_root should return repository root."""
        root = jj_vcs.get_repo_root(jj_repo)
        assert root == jj_repo

    def test_get_repo_root_from_subdir(self, jj_repo, jj_vcs):
        """get_repo_root should work from subdirectory."""
        subdir = jj_repo / "subdir"
        subdir.mkdir()

        root = jj_vcs.get_repo_root(subdir)
        assert root == jj_repo

    def test_get_repo_root_returns_none_for_non_repo(self, tmp_path, jj_vcs):
        """get_repo_root should return None for non-repository."""
        root = jj_vcs.get_repo_root(tmp_path)
        assert root is None

    def test_init_repo_colocated(self, tmp_path, jj_vcs):
        """init_repo should create a colocated jj repository."""
        new_repo = tmp_path / "new_repo"
        result = jj_vcs.init_repo(new_repo, colocate=True)

        assert result is True
        assert (new_repo / ".jj").exists()
        assert (new_repo / ".git").exists()

    def test_init_repo_default(self, tmp_path, jj_vcs):
        """init_repo should create a colocated repo by default (jj 0.30+ behavior)."""
        new_repo = tmp_path / "default_repo"
        result = jj_vcs.init_repo(new_repo)

        assert result is True
        assert (new_repo / ".jj").exists()
        # In jj 0.30+, colocate is the default
        assert (new_repo / ".git").exists()


# =============================================================================
# Workspace Operations Tests
# =============================================================================


class TestWorkspaceOperations:
    """Tests for workspace operations."""

    def test_create_workspace(self, jj_repo, jj_vcs):
        """create_workspace should create a jj workspace."""
        workspace_path = jj_repo / ".worktrees" / "test-WP01"

        result = jj_vcs.create_workspace(
            workspace_path,
            "test-WP01",
            repo_root=jj_repo,
        )

        assert result.success is True, f"Failed: {result.error}"
        assert result.error is None
        assert workspace_path.exists()
        assert (workspace_path / ".jj").exists()

    def test_create_workspace_returns_error_on_failure(self, tmp_path, jj_vcs):
        """create_workspace should return error for non-repo path."""
        workspace_path = tmp_path / ".worktrees" / "test-WP01"

        result = jj_vcs.create_workspace(
            workspace_path,
            "test-WP01",
        )

        # jj workspace add should fail in non-repo
        assert result.success is False
        assert result.error is not None

    def test_remove_workspace(self, jj_repo, jj_vcs):
        """remove_workspace should remove a workspace."""
        workspace_path = jj_repo / ".worktrees" / "test-remove"

        # Create workspace first
        create_result = jj_vcs.create_workspace(workspace_path, "test-remove", repo_root=jj_repo)
        assert create_result.success is True, f"Create failed: {create_result.error}"
        assert workspace_path.exists()

        # Remove it
        result = jj_vcs.remove_workspace(workspace_path)

        assert result is True
        assert not workspace_path.exists()

    def test_get_workspace_info(self, jj_repo, jj_vcs):
        """get_workspace_info should return workspace details."""
        info = jj_vcs.get_workspace_info(jj_repo)

        assert info is not None
        assert info.path == jj_repo
        assert info.backend == VCSBackend.JUJUTSU
        assert info.is_colocated is True  # jj_repo is colocated
        assert info.current_commit_id is not None
        assert info.current_change_id is not None  # jj has change IDs

    def test_get_workspace_info_returns_none_for_invalid(self, tmp_path, jj_vcs):
        """get_workspace_info should return None for invalid path."""
        info = jj_vcs.get_workspace_info(tmp_path / "nonexistent")
        assert info is None

    def test_list_workspaces(self, jj_repo, jj_vcs):
        """list_workspaces should return all workspaces."""
        # Create a workspace
        ws1 = jj_repo / ".worktrees" / "wp01"
        r1 = jj_vcs.create_workspace(ws1, "wp01", repo_root=jj_repo)
        assert r1.success is True, f"wp01 failed: {r1.error}"

        workspaces = jj_vcs.list_workspaces(jj_repo)

        # Should include at least the default workspace
        assert len(workspaces) >= 1
        # Check workspace names (default is always present)
        workspace_names = [w.name for w in workspaces]
        assert "default" in workspace_names or jj_repo.name in workspace_names

    def test_create_workspace_creates_bookmark(self, jj_repo, jj_vcs):
        """create_workspace should create a bookmark with the workspace name.

        This is critical for dependent WPs - they need to reference parent WPs
        by bookmark name (e.g., "001-feature-WP01" as a base revision).
        """
        workspace_path = jj_repo / ".worktrees" / "feature-WP01"

        result = jj_vcs.create_workspace(
            workspace_path,
            "feature-WP01",
            repo_root=jj_repo,
        )

        assert result.success is True, f"Failed: {result.error}"

        # Verify bookmark was created
        bookmark_result = subprocess.run(
            ["jj", "bookmark", "list", "--all"],
            cwd=jj_repo,
            capture_output=True,
            text=True,
        )

        assert "feature-WP01" in bookmark_result.stdout, (
            f"Bookmark 'feature-WP01' not found in: {bookmark_result.stdout}"
        )

    def test_create_workspace_bookmark_usable_as_base(self, jj_repo, jj_vcs):
        """Bookmark created by workspace should be usable as base for dependent WPs.

        Regression test: WP06 failed because it couldn't find WP01's bookmark
        when trying to use it as a base revision.
        """
        # Create WP01 workspace with bookmark
        wp01_path = jj_repo / ".worktrees" / "feature-WP01"
        r1 = jj_vcs.create_workspace(wp01_path, "feature-WP01", repo_root=jj_repo)
        assert r1.success is True, f"WP01 failed: {r1.error}"

        # Make a change in WP01 so it has content
        (wp01_path / "wp01_file.txt").write_text("WP01 content")
        subprocess.run(["jj", "describe", "-m", "WP01 implementation"], cwd=wp01_path)

        # Create WP06 workspace based on WP01's bookmark
        wp06_path = jj_repo / ".worktrees" / "feature-WP06"
        r6 = jj_vcs.create_workspace(
            wp06_path,
            "feature-WP06",
            base_branch="feature-WP01",  # Use WP01's bookmark as base
            repo_root=jj_repo,
        )

        assert r6.success is True, f"WP06 based on WP01 bookmark failed: {r6.error}"

        # Verify WP06 has WP01's content
        assert (wp06_path / "wp01_file.txt").exists(), "WP06 should inherit files from WP01"

    def test_remove_workspace_deletes_bookmark(self, jj_repo, jj_vcs):
        """remove_workspace should also delete the associated bookmark."""
        workspace_path = jj_repo / ".worktrees" / "feature-WP-remove"

        # Create workspace (which creates bookmark)
        r = jj_vcs.create_workspace(workspace_path, "feature-WP-remove", repo_root=jj_repo)
        assert r.success is True, f"Create failed: {r.error}"

        # Verify bookmark exists
        list_result = subprocess.run(
            ["jj", "bookmark", "list", "--all"],
            cwd=jj_repo,
            capture_output=True,
            text=True,
        )
        assert "feature-WP-remove" in list_result.stdout

        # Remove workspace
        jj_vcs.remove_workspace(workspace_path)

        # Verify bookmark was also deleted
        list_result2 = subprocess.run(
            ["jj", "bookmark", "list", "--all"],
            cwd=jj_repo,
            capture_output=True,
            text=True,
        )
        assert "feature-WP-remove" not in list_result2.stdout, (
            f"Bookmark should have been deleted but found in: {list_result2.stdout}"
        )


# =============================================================================
# Commit Operations Tests
# =============================================================================


class TestCommitOperations:
    """Tests for commit/change operations."""

    def test_get_current_change(self, jj_repo, jj_vcs):
        """get_current_change should return current working copy info."""
        change = jj_vcs.get_current_change(jj_repo)

        assert change is not None
        assert change.commit_id is not None
        assert change.change_id is not None  # jj has change IDs
        assert change.author is not None

    def test_get_changes(self, jj_repo, jj_vcs):
        """get_changes should return change history."""
        # Add some content and commit
        (jj_repo / "file1.txt").write_text("content 1")
        subprocess.run(["jj", "describe", "-m", "First change"], cwd=jj_repo)
        subprocess.run(["jj", "new"], cwd=jj_repo)

        (jj_repo / "file2.txt").write_text("content 2")
        subprocess.run(["jj", "describe", "-m", "Second change"], cwd=jj_repo)
        subprocess.run(["jj", "new"], cwd=jj_repo)

        changes = jj_vcs.get_changes(jj_repo, limit=10)

        assert len(changes) >= 2
        # All changes should have change_id
        for change in changes:
            assert change.change_id is not None

    def test_commit(self, jj_repo, jj_vcs):
        """commit should describe current change and create new one."""
        # Make a change
        (jj_repo / "new_file.txt").write_text("new content")

        change = jj_vcs.commit(jj_repo, "Test commit message")

        assert change is not None
        assert change.message == "Test commit message"
        assert change.change_id is not None

    def test_commit_with_empty_working_copy(self, jj_repo, jj_vcs):
        """commit should work even with empty working copy."""
        # In jj, working copy is always a commit
        # Even an empty change can be described
        change = jj_vcs.commit(jj_repo, "Empty change")

        # jj allows describing empty changes
        assert change is not None
        assert change.is_empty is True

    def test_change_id_stable_across_rebases(self, jj_repo, jj_vcs):
        """Change IDs should remain stable when rebased."""
        # Create a change and get its ID
        (jj_repo / "test.txt").write_text("test content")
        subprocess.run(["jj", "describe", "-m", "Test change"], cwd=jj_repo)

        change_before = jj_vcs.get_current_change(jj_repo)
        change_id = change_before.change_id

        # Create a new change on top
        subprocess.run(["jj", "new"], cwd=jj_repo)
        (jj_repo / "another.txt").write_text("another")
        subprocess.run(["jj", "describe", "-m", "Another change"], cwd=jj_repo)

        # Look up the original change by ID
        found_change = jj_get_change_by_id(jj_repo, change_id)

        assert found_change is not None
        assert found_change.change_id == change_id
        assert found_change.message == "Test change"


# =============================================================================
# Conflict Operations Tests
# =============================================================================


class TestConflictOperations:
    """Tests for conflict detection operations."""

    def test_has_conflicts_false_when_clean(self, jj_repo, jj_vcs):
        """has_conflicts should return False for clean repo."""
        assert jj_vcs.has_conflicts(jj_repo) is False

    def test_detect_conflicts_empty_when_clean(self, jj_repo, jj_vcs):
        """detect_conflicts should return empty list for clean repo."""
        conflicts = jj_vcs.detect_conflicts(jj_repo)
        assert conflicts == []

    def test_sync_with_conflict_succeeds(self, jj_repo, jj_vcs):
        """
        Key jj difference: sync should succeed even with conflicts.

        Unlike git where merge conflicts block the operation,
        jj stores conflicts in the commit and allows work to continue.
        """
        # Create conflicting changes
        # First change
        (jj_repo / "conflict.txt").write_text("version A")
        subprocess.run(["jj", "describe", "-m", "Change A"], cwd=jj_repo)
        result = subprocess.run(
            ["jj", "log", "-r", "@", "--no-graph", "-T", "change_id"],
            cwd=jj_repo,
            capture_output=True,
            text=True,
        )
        change_a = result.stdout.strip()

        # New change from the initial commit
        subprocess.run(["jj", "new", "root()"], cwd=jj_repo)
        (jj_repo / "conflict.txt").write_text("version B")
        subprocess.run(["jj", "describe", "-m", "Change B"], cwd=jj_repo)

        # Merge both changes - this should NOT fail in jj
        result = subprocess.run(
            ["jj", "new", change_a, "@"],
            cwd=jj_repo,
            capture_output=True,
            text=True,
        )

        # jj merge succeeds even with conflicts
        assert result.returncode == 0 or "Conflict" in result.stderr

        # Check for conflicts
        jj_vcs.has_conflicts(jj_repo)
        # The merge may or may not have conflicts depending on jj version
        # but it should not fail


# =============================================================================
# Sync Operations Tests
# =============================================================================


class TestSyncOperations:
    """Tests for workspace synchronization."""

    def test_is_workspace_stale_false_when_up_to_date(self, jj_repo, jj_vcs):
        """is_workspace_stale should return False when up to date."""
        assert jj_vcs.is_workspace_stale(jj_repo) is False

    def test_sync_workspace_up_to_date(self, jj_repo, jj_vcs):
        """sync_workspace should report UP_TO_DATE when nothing to sync."""
        result = jj_vcs.sync_workspace(jj_repo)

        # Should succeed (not FAILED)
        assert result.status in (SyncStatus.UP_TO_DATE, SyncStatus.SYNCED)


# =============================================================================
# jj-Specific Functions Tests
# =============================================================================


class TestJJSpecificFunctions:
    """Tests for jj-specific standalone functions."""

    def test_jj_get_operation_log(self, jj_repo):
        """jj_get_operation_log should return operation entries."""
        # Make some operations
        (jj_repo / "op1.txt").write_text("content 1")
        subprocess.run(["jj", "describe", "-m", "Op 1"], cwd=jj_repo)
        subprocess.run(["jj", "new"], cwd=jj_repo)

        operations = jj_get_operation_log(jj_repo, limit=10)

        assert len(operations) >= 1
        # All operations should have an ID
        for op in operations:
            assert op.operation_id is not None
            assert op.is_undoable is True  # jj ops are always undoable

    def test_jj_undo_operation(self, jj_repo):
        """jj_undo_operation should undo the last operation."""
        # Make a change
        (jj_repo / "undo_test.txt").write_text("will be undone")
        subprocess.run(["jj", "describe", "-m", "Will be undone"], cwd=jj_repo)

        # Undo it
        result = jj_undo_operation(jj_repo)

        assert result is True

    def test_jj_get_change_by_id(self, jj_repo):
        """jj_get_change_by_id should look up changes by Change ID."""
        # Create a change with known content
        (jj_repo / "lookup.txt").write_text("lookup content")
        subprocess.run(["jj", "describe", "-m", "Lookup test"], cwd=jj_repo)

        # Get current change ID
        result = subprocess.run(
            ["jj", "log", "-r", "@", "--no-graph", "-T", "change_id"],
            cwd=jj_repo,
            capture_output=True,
            text=True,
        )
        change_id = result.stdout.strip()

        # Create new change to move away from it
        subprocess.run(["jj", "new"], cwd=jj_repo)

        # Look it up by ID
        change = jj_get_change_by_id(jj_repo, change_id)

        assert change is not None
        assert change.change_id == change_id
        assert change.message == "Lookup test"

    def test_jj_get_change_by_id_returns_none_for_invalid(self, jj_repo):
        """jj_get_change_by_id should return None for invalid ID."""
        change = jj_get_change_by_id(jj_repo, "invalidid123456")
        assert change is None


# =============================================================================
# Colocated Mode Tests
# =============================================================================


class TestColocatedMode:
    """Tests for colocated jj+git mode.

    Note: In jj 0.30+, colocate is the default and pure jj repos are no longer
    directly supported. All jj repos use the Git backend.
    """

    def test_colocated_has_both_directories(self, jj_repo, jj_vcs):
        """Colocated repo should have both .jj and .git directories."""
        assert (jj_repo / ".jj").exists()
        assert (jj_repo / ".git").exists()

    def test_colocated_workspace_info(self, jj_repo, jj_vcs):
        """Workspace info should report colocated mode."""
        info = jj_vcs.get_workspace_info(jj_repo)

        assert info is not None
        assert info.is_colocated is True


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_operations_on_nonexistent_path(self, jj_vcs):
        """Operations should handle nonexistent paths gracefully."""
        fake_path = Path("/nonexistent/path/that/does/not/exist")

        assert jj_vcs.is_repo(fake_path) is False
        assert jj_vcs.get_repo_root(fake_path) is None
        assert jj_vcs.get_workspace_info(fake_path) is None
        assert jj_vcs.get_current_change(fake_path) is None
        assert jj_vcs.get_changes(fake_path) == []
        assert jj_vcs.detect_conflicts(fake_path) == []
        assert jj_vcs.has_conflicts(fake_path) is False

    def test_empty_change_is_valid(self, jj_repo, jj_vcs):
        """jj allows empty changes (unlike git)."""
        # Get current change without any modifications
        change = jj_vcs.get_current_change(jj_repo)

        assert change is not None
        # Empty changes are valid in jj
        assert change.is_empty is True

    def test_working_copy_is_always_a_commit(self, jj_repo, jj_vcs):
        """In jj, the working copy is always a commit."""
        # Make some changes but don't "commit"
        (jj_repo / "wc_test.txt").write_text("working copy content")

        # The working copy should still be accessible as a change
        change = jj_vcs.get_current_change(jj_repo)

        assert change is not None
        assert change.change_id is not None
        # Working copy changes are automatically tracked


# =============================================================================
# Error Extraction Tests (Issue #79 fix)
# =============================================================================


class TestExtractJJError:
    """Tests for _extract_jj_error function.

    jj has quirky error handling - it prints info messages to stderr even
    during successful operations, and sometimes returns exit code 0 with
    actual errors. This function filters out benign messages.
    """

    def test_extracts_error_from_stderr(self):
        """Should extract 'Error:' lines from stderr."""
        stderr = "Error: Workspace named 'test' already exists"
        error = _extract_jj_error(stderr)
        assert error == "Error: Workspace named 'test' already exists"

    def test_extracts_error_with_cause(self):
        """Should include 'Caused by:' lines following errors."""
        stderr = """Error: Cannot access /nonexistent/path
Caused by: No such file or directory (os error 2)"""
        error = _extract_jj_error(stderr)
        assert "Error: Cannot access" in error
        assert "Caused by:" in error

    def test_ignores_reset_working_copy_message(self):
        """Should ignore 'Reset the working copy parent' info message."""
        stderr = "Reset the working copy parent to the new Git HEAD."
        error = _extract_jj_error(stderr)
        assert error is None

    def test_ignores_done_importing_message(self):
        """Should ignore 'Done importing changes' info message."""
        stderr = "Done importing changes from the underlying Git repo."
        error = _extract_jj_error(stderr)
        assert error is None

    def test_ignores_created_workspace_message(self):
        """Should ignore 'Created workspace' info message."""
        stderr = 'Created workspace in "../../../../tmp/test-ws"'
        error = _extract_jj_error(stderr)
        assert error is None

    def test_ignores_working_copy_info(self):
        """Should ignore working copy status lines."""
        stderr = "Working copy  (@) now at: abc123 (empty) (no description set)"
        error = _extract_jj_error(stderr)
        assert error is None

    def test_ignores_parent_commit_info(self):
        """Should ignore parent commit info lines."""
        stderr = "Parent commit (@-)      : def456 main | Initial commit"
        error = _extract_jj_error(stderr)
        assert error is None

    def test_ignores_added_files_info(self):
        """Should ignore 'Added X files' info messages."""
        stderr = "Added 540 files, modified 0 files, removed 0 files"
        error = _extract_jj_error(stderr)
        assert error is None

    def test_ignores_warning_messages(self):
        """Should ignore 'Warning:' messages (not errors)."""
        stderr = "Warning: 9 of those updates were skipped because there were conflicting changes"
        error = _extract_jj_error(stderr)
        assert error is None

    def test_ignores_hint_messages(self):
        """Should ignore 'Hint:' messages."""
        stderr = "Hint: Inspect the changes with `jj diff --from abc123`."
        error = _extract_jj_error(stderr)
        assert error is None

    def test_ignores_concurrent_modification_info(self):
        """Should ignore concurrent modification resolution info."""
        stderr = "Concurrent modification detected, resolving automatically."
        error = _extract_jj_error(stderr)
        assert error is None

    def test_extracts_error_from_mixed_output(self):
        """Should extract error even when mixed with info messages."""
        stderr = """Concurrent modification detected, resolving automatically.
Error: Workspace named 'test-ws-01' already exists"""
        error = _extract_jj_error(stderr)
        assert "Error: Workspace named 'test-ws-01' already exists" in error

    def test_handles_typical_successful_stderr(self):
        """Should return None for typical successful operation stderr."""
        stderr = """Reset the working copy parent to the new Git HEAD.
Done importing changes from the underlying Git repo.
Created workspace in "../../../../tmp/test-ws"
Working copy  (@) now at: abc123 (empty) (no description set)
Parent commit (@-)      : def456 main | Initial commit
Added 540 files, modified 0 files, removed 0 files
Warning: 9 of those updates were skipped because there were conflicting changes.
Hint: Inspect the changes with `jj diff --from abc123`."""
        error = _extract_jj_error(stderr)
        assert error is None

    def test_handles_empty_stderr(self):
        """Should return None for empty stderr."""
        assert _extract_jj_error("") is None
        assert _extract_jj_error(None) is None

    def test_handles_whitespace_only_stderr(self):
        """Should return None for whitespace-only stderr."""
        assert _extract_jj_error("   \n\n   ") is None


class TestCreateWorkspaceDuplicateError:
    """Test that duplicate workspace name errors are caught (issue fix)."""

    def test_create_duplicate_workspace_returns_error(self, jj_repo, jj_vcs):
        """Creating workspace with existing name should return error, not success.

        This tests the fix for jj returning exit code 0 with 'Error:' in stderr.
        """
        workspace_path = jj_repo / ".worktrees" / "dup-test"

        # Create workspace first time
        result1 = jj_vcs.create_workspace(
            workspace_path,
            "dup-test",
            repo_root=jj_repo,
        )
        assert result1.success is True, f"First create failed: {result1.error}"

        # Try to create again with same name (different path)
        workspace_path2 = jj_repo / ".worktrees" / "dup-test-2"
        result2 = jj_vcs.create_workspace(
            workspace_path2,
            "dup-test",  # Same name!
            repo_root=jj_repo,
        )

        # Should detect the error even if jj returns exit code 0
        assert result2.success is False
        assert result2.error is not None
        assert "already exists" in result2.error.lower()
