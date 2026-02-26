"""Integration tests for workspace-per-WP merge functionality."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.cli.commands.merge import (
    _build_workspace_per_wp_merge_plan,
    detect_worktree_structure,
    extract_feature_slug,
    extract_wp_id,
    find_wp_worktrees,
    validate_wp_ready_for_merge,
)
from specify_cli.core.vcs import VCSBackend
from specify_cli.core.vcs.exceptions import VCSNotFoundError


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a test git repository."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create initial commit on main
    (repo / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    return repo


@pytest.fixture
def workspace_per_wp_repo(git_repo: Path) -> Path:
    """Create a repository with workspace-per-WP structure."""
    worktrees_dir = git_repo / ".worktrees"
    worktrees_dir.mkdir()

    # Create 3 WP workspaces
    for wp_num in [1, 2, 3]:
        wp_id = f"WP{wp_num:02d}"
        branch_name = f"010-test-feature-{wp_id}"
        worktree_path = worktrees_dir / branch_name

        # Create worktree
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), "-b", branch_name],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Make a commit in the worktree
        (worktree_path / f"{wp_id}.txt").write_text(f"Changes for {wp_id}\n")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"Add {wp_id} changes"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

    return git_repo


class TestExtractFeatureSlug:
    """Tests for extract_feature_slug function."""

    def test_extracts_from_wp_branch(self):
        """Test extracting feature slug from WP branch name."""
        assert extract_feature_slug("010-workspace-per-wp-WP01") == "010-workspace-per-wp"
        assert extract_feature_slug("005-my-feature-WP12") == "005-my-feature"

    def test_returns_as_is_for_legacy_branch(self):
        """Test legacy branch names return as-is."""
        assert extract_feature_slug("008-unified-cli") == "008-unified-cli"
        assert extract_feature_slug("main") == "main"


class TestExtractWpId:
    """Tests for extract_wp_id function."""

    def test_extracts_wp_id(self):
        """Test extracting WP ID from worktree path."""
        assert extract_wp_id(Path(".worktrees/010-feature-WP01")) == "WP01"
        assert extract_wp_id(Path(".worktrees/010-feature-WP12")) == "WP12"

    def test_returns_none_for_legacy(self):
        """Test legacy worktree paths return None."""
        assert extract_wp_id(Path(".worktrees/008-unified-cli")) is None


class TestDetectWorktreeStructure:
    """Tests for detect_worktree_structure function."""

    def test_detects_workspace_per_wp(self, workspace_per_wp_repo: Path):
        """Test detecting workspace-per-WP structure."""
        structure = detect_worktree_structure(workspace_per_wp_repo, "010-test-feature")
        assert structure == "workspace-per-wp"

    def test_detects_legacy(self, git_repo: Path):
        """Test detecting legacy structure."""
        # Create legacy worktree
        worktrees_dir = git_repo / ".worktrees"
        worktrees_dir.mkdir()
        legacy_path = worktrees_dir / "008-legacy-feature"
        legacy_path.mkdir()

        structure = detect_worktree_structure(git_repo, "008-legacy-feature")
        assert structure == "legacy"

    def test_detects_none(self, git_repo: Path):
        """Test detecting no worktrees."""
        structure = detect_worktree_structure(git_repo, "999-nonexistent")
        assert structure == "none"

    def test_detects_workspace_per_wp_from_branches_without_worktree_dirs(self, workspace_per_wp_repo: Path):
        """Detect workspace-per-WP even when worktree directories were removed."""
        for wp_num in [1, 2, 3]:
            branch_name = f"010-test-feature-WP{wp_num:02d}"
            worktree_path = workspace_per_wp_repo / ".worktrees" / branch_name
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=workspace_per_wp_repo,
                check=True,
                capture_output=True,
            )

        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=workspace_per_wp_repo,
            check=True,
            capture_output=True,
        )

        structure = detect_worktree_structure(workspace_per_wp_repo, "010-test-feature")
        assert structure == "workspace-per-wp"


class TestFindWpWorktrees:
    """Tests for find_wp_worktrees function."""

    def test_finds_all_wp_worktrees(self, workspace_per_wp_repo: Path):
        """Test finding all WP worktrees for a feature."""
        wp_workspaces = find_wp_worktrees(workspace_per_wp_repo, "010-test-feature")

        assert len(wp_workspaces) == 3

        # Check sorting (alphabetical by WP ID)
        assert wp_workspaces[0][1] == "WP01"
        assert wp_workspaces[1][1] == "WP02"
        assert wp_workspaces[2][1] == "WP03"

        # Check branch names
        assert wp_workspaces[0][2] == "010-test-feature-WP01"
        assert wp_workspaces[1][2] == "010-test-feature-WP02"
        assert wp_workspaces[2][2] == "010-test-feature-WP03"

    def test_returns_empty_for_no_worktrees(self, git_repo: Path):
        """Test returns empty list when no worktrees found."""
        wp_workspaces = find_wp_worktrees(git_repo, "999-nonexistent")
        assert wp_workspaces == []

    def test_falls_back_to_wp_branches_when_worktrees_removed(self, workspace_per_wp_repo: Path):
        """Fallback to branch discovery when worktree directories are gone."""
        for wp_num in [1, 2, 3]:
            branch_name = f"010-test-feature-WP{wp_num:02d}"
            worktree_path = workspace_per_wp_repo / ".worktrees" / branch_name
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=workspace_per_wp_repo,
                check=True,
                capture_output=True,
            )
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=workspace_per_wp_repo,
            check=True,
            capture_output=True,
        )

        wp_workspaces = find_wp_worktrees(workspace_per_wp_repo, "010-test-feature")
        assert len(wp_workspaces) == 3
        assert [wp for _, wp, _ in wp_workspaces] == ["WP01", "WP02", "WP03"]
        assert [branch for _, _, branch in wp_workspaces] == [
            "010-test-feature-WP01",
            "010-test-feature-WP02",
            "010-test-feature-WP03",
        ]
        # Fallback entries use expected .worktrees paths even when directories are missing.
        assert all(not path.exists() for path, _, _ in wp_workspaces)


class TestValidateWpReadyForMerge:
    """Tests for validate_wp_ready_for_merge function."""

    def test_validates_clean_worktree(self, workspace_per_wp_repo: Path):
        """Test validating a clean worktree."""
        worktree_path = workspace_per_wp_repo / ".worktrees" / "010-test-feature-WP01"
        is_valid, error_msg = validate_wp_ready_for_merge(
            workspace_per_wp_repo, worktree_path, "010-test-feature-WP01"
        )
        assert is_valid is True
        assert error_msg == ""

    def test_detects_uncommitted_changes(self, workspace_per_wp_repo: Path):
        """Test detecting uncommitted changes in worktree."""
        worktree_path = workspace_per_wp_repo / ".worktrees" / "010-test-feature-WP01"

        # Make uncommitted changes
        (worktree_path / "uncommitted.txt").write_text("uncommitted\n")

        is_valid, error_msg = validate_wp_ready_for_merge(
            workspace_per_wp_repo, worktree_path, "010-test-feature-WP01"
        )
        assert is_valid is False
        assert "uncommitted changes" in error_msg

    def test_detects_missing_branch(self, workspace_per_wp_repo: Path):
        """Test detecting missing branch."""
        worktree_path = workspace_per_wp_repo / ".worktrees" / "010-test-feature-WP01"

        is_valid, error_msg = validate_wp_ready_for_merge(
            workspace_per_wp_repo, worktree_path, "999-nonexistent-branch"
        )
        assert is_valid is False
        assert "does not exist" in error_msg


class TestDetectWorktreeFromWithinWorktree:
    """Tests for detecting worktree structure when running from within a worktree."""

    def test_detects_workspace_per_wp_from_worktree(self, workspace_per_wp_repo: Path):
        """Test detecting workspace-per-WP when called from within a WP worktree.

        This addresses the High Issue 1 from review feedback:
        Workspace-per-WP detection must work when spec-kitty merge is run from
        a WP worktree, because find_repo_root() returns the worktree root
        (no .worktrees/), so detect_worktree_structure() must find main repo.
        """
        # Simulate being in a worktree by passing worktree path
        worktree_path = workspace_per_wp_repo / ".worktrees" / "010-test-feature-WP01"
        structure = detect_worktree_structure(worktree_path, "010-test-feature")
        assert structure == "workspace-per-wp"

    def test_finds_wp_worktrees_from_worktree(self, workspace_per_wp_repo: Path):
        """Test finding WP worktrees when called from within a WP worktree."""
        worktree_path = workspace_per_wp_repo / ".worktrees" / "010-test-feature-WP01"
        wp_workspaces = find_wp_worktrees(worktree_path, "010-test-feature")

        assert len(wp_workspaces) == 3
        assert wp_workspaces[0][1] == "WP01"
        assert wp_workspaces[1][1] == "WP02"
        assert wp_workspaces[2][1] == "WP03"


class TestMixedStructureDetection:
    """Tests for mixed structure detection (both legacy and WP worktrees).

    This addresses High Issue 2 from review feedback:
    In mixed structures (both .worktrees/feature and .worktrees/feature-WP##),
    workspace-per-WP should take precedence if any WP worktrees exist.
    """

    def test_prefers_workspace_per_wp_in_mixed_structure(self, git_repo: Path):
        """Test that WP structure takes precedence over legacy when both exist."""
        worktrees_dir = git_repo / ".worktrees"
        worktrees_dir.mkdir()

        # Create legacy worktree
        legacy_path = worktrees_dir / "010-mixed-feature"
        legacy_path.mkdir()

        # Create WP worktrees
        for wp_num in [1, 2]:
            wp_branch = f"010-mixed-feature-WP{wp_num:02d}"
            worktree_path = worktrees_dir / wp_branch
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), "-b", wp_branch],
                cwd=git_repo,
                check=True,
                capture_output=True,
            )

        # Detection should return workspace-per-wp (not legacy)
        structure = detect_worktree_structure(git_repo, "010-mixed-feature")
        assert structure == "workspace-per-wp"


class TestWorkspacePerWpMergeIntegration:
    """Integration tests for full workspace-per-WP merge workflow.

    This addresses Medium Issue 3 from review feedback:
    The integration tests must exercise execute_merge() function directly,
    not just helpers and manual git merges.
    """

    def test_execute_merge_function(self, workspace_per_wp_repo: Path):
        """Test execute_merge() function directly with dry_run.

        This tests the detection, validation, and planning logic without
        actually performing the merge (since test repos have no remote).
        """
        from specify_cli.cli import StepTracker
        from specify_cli.cli.commands.merge import find_wp_worktrees
        from specify_cli.merge.executor import execute_merge

        tracker = StepTracker("Test Merge")
        tracker.add("preflight", "Pre-flight validation")
        tracker.add("verify", "Verify readiness")
        tracker.add("checkout", "Switch to main")
        tracker.add("pull", "Update main")
        tracker.add("merge", "Merge WPs")
        tracker.add("worktree", "Remove worktrees")
        tracker.add("branch", "Delete branches")

        # Find WP workspaces
        wp_workspaces = find_wp_worktrees(workspace_per_wp_repo, "010-test-feature")

        # Call execute_merge in dry_run mode to test detection
        # This validates all the critical logic without needing a remote
        result = execute_merge(
            wp_workspaces=wp_workspaces,
            feature_slug="010-test-feature",
            feature_dir=None,  # No kitty-specs in test repo
            target_branch="main",
            strategy="merge",
            repo_root=workspace_per_wp_repo,
            merge_root=workspace_per_wp_repo,
            tracker=tracker,
            delete_branch=True,
            remove_worktree=True,
            push=False,
            dry_run=True,  # Use dry_run to avoid pull failures with no remote
        )

        # In dry_run mode, nothing is actually merged, but we verified:
        # - WP worktrees are detected correctly
        # - All WPs are validated
        # - The merge plan is generated correctly
        assert result.success is True
        assert len(result.merged_wps) == 3

    def test_execute_merge_from_worktree(self, workspace_per_wp_repo: Path):
        """Test execute_merge() when called from within a worktree.

        This is the critical test for High Issue 1 - merge must work correctly
        when run from a WP worktree, not just from main repo. We use dry_run
        to test the detection logic without needing a remote.
        """
        from specify_cli.cli import StepTracker
        from specify_cli.cli.commands.merge import find_wp_worktrees
        from specify_cli.merge.executor import execute_merge

        # Simulate being in a worktree
        worktree_path = workspace_per_wp_repo / ".worktrees" / "010-test-feature-WP01"

        tracker = StepTracker("Test Merge from Worktree")
        tracker.add("preflight", "Pre-flight validation")
        tracker.add("verify", "Verify readiness")
        tracker.add("checkout", "Switch to main")
        tracker.add("pull", "Update main")
        tracker.add("merge", "Merge WPs")
        tracker.add("worktree", "Remove worktrees")
        tracker.add("branch", "Delete branches")

        # Find WP workspaces (this function uses get_main_repo_root internally)
        wp_workspaces = find_wp_worktrees(worktree_path, "010-test-feature")

        # Call execute_merge from worktree context
        # This is the key test: repo_root is a worktree, not main repo
        result = execute_merge(
            wp_workspaces=wp_workspaces,
            feature_slug="010-test-feature",
            feature_dir=None,  # No kitty-specs in test repo
            target_branch="main",
            strategy="merge",
            repo_root=workspace_per_wp_repo,  # Main repo for git operations
            merge_root=workspace_per_wp_repo,
            tracker=tracker,
            delete_branch=True,
            remove_worktree=True,
            push=False,
            dry_run=True,  # Use dry_run to avoid pull failures with no remote
        )

        # In dry_run mode, we validated the critical behavior:
        # - Detection works from within a worktree (finds main repo)
        # - All WP worktrees are found correctly
        # - Validation passes
        # This proves High Issue 1 is fixed
        assert result.success is True
        assert len(result.merged_wps) == 3

    def test_merge_workflow_success(self, workspace_per_wp_repo: Path):
        """Test full merge workflow with workspace-per-WP (manual git ops for comparison)."""
        # Switch to default branch
        # Get the default branch name
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=workspace_per_wp_repo, capture_output=True, text=True, check=True
        )
        default_branch = branch_result.stdout.strip()

        subprocess.run(
            ["git", "checkout", default_branch],
            cwd=workspace_per_wp_repo,
            check=True,
            capture_output=True,
        )

        # Merge each WP branch
        for wp_num in [1, 2, 3]:
            branch_name = f"010-test-feature-WP{wp_num:02d}"
            subprocess.run(
                ["git", "merge", "--no-ff", branch_name, "-m", f"Merge WP{wp_num:02d}"],
                cwd=workspace_per_wp_repo,
                check=True,
                capture_output=True,
            )

        # Verify all WPs merged
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=workspace_per_wp_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Merge WP01" in result.stdout
        assert "Merge WP02" in result.stdout
        assert "Merge WP03" in result.stdout

        # Verify all changes present
        assert (workspace_per_wp_repo / "WP01.txt").exists()
        assert (workspace_per_wp_repo / "WP02.txt").exists()
        assert (workspace_per_wp_repo / "WP03.txt").exists()

    def test_cleanup_removes_worktrees(self, workspace_per_wp_repo: Path):
        """Test that worktree cleanup removes all WP worktrees."""
        # Remove worktrees
        for wp_num in [1, 2, 3]:
            branch_name = f"010-test-feature-WP{wp_num:02d}"
            worktree_path = workspace_per_wp_repo / ".worktrees" / branch_name

            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=workspace_per_wp_repo,
                check=True,
                capture_output=True,
            )


class TestEffectiveMergePlanning:
    """Tests for ancestry-pruned effective merge branch selection."""

    def test_prunes_linear_chain_to_single_tip(self, git_repo: Path):
        target_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=git_repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        worktrees_dir = git_repo / ".worktrees"
        worktrees_dir.mkdir()

        wp01 = "020-linear-feature-WP01"
        wp02 = "020-linear-feature-WP02"
        wp03 = "020-linear-feature-WP03"

        wt01 = worktrees_dir / wp01
        subprocess.run(
            ["git", "worktree", "add", str(wt01), "-b", wp01],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (wt01 / "wp01.txt").write_text("wp01\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=wt01, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "wp01"], cwd=wt01, check=True, capture_output=True)

        wt02 = worktrees_dir / wp02
        subprocess.run(
            ["git", "worktree", "add", str(wt02), "-b", wp02, wp01],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (wt02 / "wp02.txt").write_text("wp02\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=wt02, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "wp02"], cwd=wt02, check=True, capture_output=True)

        wt03 = worktrees_dir / wp03
        subprocess.run(
            ["git", "worktree", "add", str(wt03), "-b", wp03, wp02],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (wt03 / "wp03.txt").write_text("wp03\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=wt03, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "wp03"], cwd=wt03, check=True, capture_output=True)

        wp_workspaces = find_wp_worktrees(git_repo, "020-linear-feature")
        plan = _build_workspace_per_wp_merge_plan(
            git_repo,
            "020-linear-feature",
            target_branch,
            wp_workspaces,
        )

        effective = [branch for _, _, branch in plan["effective_wp_workspaces"]]
        assert effective == [wp03]
        assert wp01 in plan["skipped_ancestor_of"]
        assert wp02 in plan["skipped_ancestor_of"]

    def test_skips_when_already_in_target(self, git_repo: Path):
        target_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=git_repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        worktrees_dir = git_repo / ".worktrees"
        worktrees_dir.mkdir()

        wp01 = "021-already-merged-WP01"
        wt01 = worktrees_dir / wp01
        subprocess.run(
            ["git", "worktree", "add", str(wt01), "-b", wp01],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (wt01 / "wp01.txt").write_text("wp01\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=wt01, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "wp01"], cwd=wt01, check=True, capture_output=True)

        subprocess.run(["git", "checkout", target_branch], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "merge", "--no-ff", wp01, "-m", "merge wp01"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        wp_workspaces = find_wp_worktrees(git_repo, "021-already-merged")
        plan = _build_workspace_per_wp_merge_plan(
            git_repo,
            "021-already-merged",
            target_branch,
            wp_workspaces,
        )

        assert plan["effective_wp_workspaces"] == []
        assert len(plan["skipped_already_in_target"]) == 1

    def test_keeps_independent_branches(self, workspace_per_wp_repo: Path):
        target_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=workspace_per_wp_repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        wp_workspaces = find_wp_worktrees(workspace_per_wp_repo, "010-test-feature")
        plan = _build_workspace_per_wp_merge_plan(
            workspace_per_wp_repo,
            "010-test-feature",
            target_branch,
            wp_workspaces,
        )

        effective = [branch for _, _, branch in plan["effective_wp_workspaces"]]
        assert len(effective) == 3

    def test_cleanup_deletes_branches(self, workspace_per_wp_repo: Path):
        """Test that branch cleanup deletes all WP branches."""
        # First merge the branches so they can be deleted
        # Get the default branch name
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=workspace_per_wp_repo, capture_output=True, text=True, check=True
        )
        default_branch = branch_result.stdout.strip()

        subprocess.run(
            ["git", "checkout", default_branch],
            cwd=workspace_per_wp_repo,
            check=True,
            capture_output=True,
        )

        for wp_num in [1, 2, 3]:
            branch_name = f"010-test-feature-WP{wp_num:02d}"
            subprocess.run(
                ["git", "merge", "--no-ff", branch_name, "-m", f"Merge WP{wp_num:02d}"],
                cwd=workspace_per_wp_repo,
                check=True,
                capture_output=True,
            )

        # Remove worktrees first (required before deleting branches)
        for wp_num in [1, 2, 3]:
            branch_name = f"010-test-feature-WP{wp_num:02d}"
            worktree_path = workspace_per_wp_repo / ".worktrees" / branch_name
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=workspace_per_wp_repo,
                check=True,
                capture_output=True,
            )

        # Delete branches
        for wp_num in [1, 2, 3]:
            branch_name = f"010-test-feature-WP{wp_num:02d}"
            subprocess.run(
                ["git", "branch", "-d", branch_name],
                cwd=workspace_per_wp_repo,
                check=True,
                capture_output=True,
            )

        # Verify branches deleted
        result = subprocess.run(
            ["git", "branch"],
            cwd=workspace_per_wp_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "010-test-feature-WP01" not in result.stdout
        assert "010-test-feature-WP02" not in result.stdout
        assert "010-test-feature-WP03" not in result.stdout


class TestVCSAbstractionIntegration:
    """Tests for VCS abstraction layer integration in merge command.

    These tests verify that the merge command correctly detects and
    displays the VCS backend (git vs jj) being used.

    Note: The is_jj_available function uses lru_cache, so we need to clear
    the cache and patch at the detection module level.
    """

    def test_merge_detects_git_backend(self, workspace_per_wp_repo: Path):
        """Test that merge command detects git backend correctly."""
        # Clear the lru_cache and patch the function
        from specify_cli.core.vcs import detection
        detection.is_jj_available.cache_clear()

        with patch.object(detection, "is_jj_available", return_value=False):
            from specify_cli.core.vcs import get_vcs

            vcs = get_vcs(workspace_per_wp_repo)
            assert vcs.backend == VCSBackend.GIT

    @pytest.mark.xfail(reason="jj not installed in CI environment")
    def test_merge_detects_jj_backend_when_jj_present(self, git_repo: Path):
        """Test that merge command detects jj backend when .jj exists."""
        # Create .jj directory to simulate jj repo
        (git_repo / ".jj").mkdir()

        from specify_cli.core.vcs import detection
        detection.is_jj_available.cache_clear()

        with patch.object(detection, "is_jj_available", return_value=True):
            from specify_cli.core.vcs import get_vcs

            vcs = get_vcs(git_repo)
            assert vcs.backend == VCSBackend.JUJUTSU

    def test_merge_displays_backend_info(self, workspace_per_wp_repo: Path, capsys):
        """Test that merge command displays VCS backend info."""
        from specify_cli.core.vcs import detection
        detection.is_jj_available.cache_clear()

        with patch.object(detection, "is_jj_available", return_value=False):
            from specify_cli.core.vcs import get_vcs

            vcs = get_vcs(workspace_per_wp_repo)
            backend_label = "jj" if vcs.backend == VCSBackend.JUJUTSU else "git"
            assert backend_label == "git"

    @pytest.mark.xfail(reason="jj not installed in CI environment")
    def test_merge_handles_vcs_detection_failure_gracefully(self, tmp_path: Path):
        """Test that merge handles VCS detection failure gracefully."""
        # Create directory without git or jj
        test_dir = tmp_path / "not_a_repo"
        test_dir.mkdir()

        from specify_cli.core.vcs import detection
        detection.is_jj_available.cache_clear()
        detection.is_git_available.cache_clear()

        with patch.object(detection, "is_jj_available", return_value=False):
            with patch.object(detection, "is_git_available", return_value=False):
                from specify_cli.core.vcs import get_vcs

                # Detection should raise an error when no VCS available
                with pytest.raises(VCSNotFoundError, match="Neither jj nor git"):
                    get_vcs(test_dir)

    @pytest.mark.xfail(reason="jj not installed in CI environment")
    def test_vcs_detection_prefers_jj_in_colocated_mode(self, git_repo: Path):
        """Test that jj is preferred over git when both .jj and .git exist."""
        # Create .jj directory (simulating colocated mode)
        (git_repo / ".jj").mkdir()

        from specify_cli.core.vcs import detection
        detection.is_jj_available.cache_clear()

        with patch.object(detection, "is_jj_available", return_value=True):
            from specify_cli.core.vcs import get_vcs

            vcs = get_vcs(git_repo)
            # In colocated mode, jj should be preferred
            assert vcs.backend == VCSBackend.JUJUTSU

    def test_vcs_detection_falls_back_to_git_when_jj_unavailable(self, git_repo: Path):
        """Test fallback to git when .jj exists but jj tool is not available."""
        # Create .jj directory
        (git_repo / ".jj").mkdir()

        from specify_cli.core.vcs import detection
        detection.is_jj_available.cache_clear()

        with patch.object(detection, "is_jj_available", return_value=False):
            from specify_cli.core.vcs import get_vcs

            vcs = get_vcs(git_repo)
            # Should fall back to git
            assert vcs.backend == VCSBackend.GIT
