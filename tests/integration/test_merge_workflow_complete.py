"""Complete merge workflow integration tests.

Tests the end-to-end merge workflow including:
- Preflight validation blocking scenarios
- Dry-run conflict forecasting
- Resume after interruption
- Abort functionality
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.merge.preflight import run_preflight
from specify_cli.merge.forecast import predict_conflicts
from specify_cli.merge.state import (
    MergeState,
    save_state,
    load_state,
    clear_state,
    has_active_merge,
)


class TestPreflightBlocking:
    """Tests for preflight validation blocking merge operations."""

    def test_preflight_blocks_dirty_worktree(self, dirty_worktree_repo: tuple[Path, Path]):
        """Test that preflight blocks merge when worktree has uncommitted changes."""
        repo_root, dirty_worktree = dirty_worktree_repo

        # Create feature directory for preflight
        feature_slug = "019-dirty-test"
        repo_root / "kitty-specs" / feature_slug

        wp_workspaces = [(dirty_worktree, "WP01", f"{feature_slug}-WP01")]

        result = run_preflight(
            feature_slug=feature_slug,
            target_branch="main",
            repo_root=repo_root,
            wp_workspaces=wp_workspaces,
        )

        assert result.passed is False
        assert len(result.wp_statuses) == 1
        assert result.wp_statuses[0].is_clean is False
        assert "Uncommitted changes" in result.wp_statuses[0].error
        assert len(result.errors) >= 1

    def test_preflight_blocks_missing_wp(self, tmp_path: Path):
        """Test that preflight blocks merge when expected WP worktree is missing."""
        # Create git repo
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        (repo / "README.md").write_text("test")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Create feature directory with 2 WP tasks
        feature_slug = "020-missing-test"
        feature_dir = repo / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        for wp_num in [1, 2]:
            wp_file = tasks_dir / f"WP0{wp_num}.md"
            wp_file.write_text(
                f"""---
work_package_id: WP0{wp_num}
title: Test WP {wp_num}
lane: doing
dependencies: []
---

# WP0{wp_num} Content
"""
            )

        # Only provide WP01 worktree (WP02 is missing)
        worktree_dir = repo / ".worktrees" / f"{feature_slug}-WP01"
        subprocess.run(
            ["git", "worktree", "add", str(worktree_dir), "-b", f"{feature_slug}-WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (worktree_dir / "WP01.txt").write_text("WP01 work")
        subprocess.run(["git", "add", "."], cwd=worktree_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP01"],
            cwd=worktree_dir,
            check=True,
            capture_output=True,
        )

        wp_workspaces = [(worktree_dir, "WP01", f"{feature_slug}-WP01")]

        result = run_preflight(
            feature_slug=feature_slug,
            target_branch="master",
            repo_root=repo,
            wp_workspaces=wp_workspaces,
        )

        assert result.passed is False
        # Should detect WP02 is missing
        wp02_statuses = [s for s in result.wp_statuses if s.wp_id == "WP02"]
        assert len(wp02_statuses) == 1
        assert wp02_statuses[0].is_clean is False
        assert "Missing worktree" in wp02_statuses[0].error

    @pytest.mark.xfail(reason="CI git environment does not have user configured for commits")
    def test_preflight_blocks_diverged_target(self, tmp_path: Path):
        """Test that preflight blocks merge when target branch is behind origin."""
        # Create origin repo
        origin = tmp_path / "origin"
        origin.mkdir()
        subprocess.run(["git", "init"], cwd=origin, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=origin,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=origin,
            check=True,
            capture_output=True,
        )
        (origin / "README.md").write_text("test")
        subprocess.run(["git", "add", "."], cwd=origin, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=origin,
            check=True,
            capture_output=True,
        )

        # Clone to local
        local = tmp_path / "local"
        subprocess.run(
            ["git", "clone", str(origin), str(local)],
            check=True,
            capture_output=True,
        )

        # Add commit to origin (making local behind)
        (origin / "new.txt").write_text("ahead")
        subprocess.run(["git", "add", "."], cwd=origin, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "ahead"],
            cwd=origin,
            check=True,
            capture_output=True,
        )

        # Fetch in local
        subprocess.run(
            ["git", "fetch", "origin"],
            cwd=local,
            check=True,
            capture_output=True,
        )

        # Create feature and worktree
        feature_slug = "021-diverged-test"
        feature_dir = local / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        wp_file = tasks_dir / "WP01.md"
        wp_file.write_text(
            """---
work_package_id: WP01
title: Test WP
lane: doing
dependencies: []
---

# WP01 Content
"""
        )

        worktree_dir = local / ".worktrees" / f"{feature_slug}-WP01"
        subprocess.run(
            ["git", "worktree", "add", str(worktree_dir), "-b", f"{feature_slug}-WP01"],
            cwd=local,
            check=True,
            capture_output=True,
        )
        (worktree_dir / "WP01.txt").write_text("work")
        subprocess.run(["git", "add", "."], cwd=worktree_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP01"],
            cwd=worktree_dir,
            check=True,
            capture_output=True,
        )

        # Get default branch name
        result_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=local,
            capture_output=True,
            text=True,
            check=True,
        )
        default_branch = result_branch.stdout.strip()

        wp_workspaces = [(worktree_dir, "WP01", f"{feature_slug}-WP01")]

        result = run_preflight(
            feature_slug=feature_slug,
            target_branch=default_branch,
            repo_root=local,
            wp_workspaces=wp_workspaces,
        )

        assert result.passed is False
        assert result.target_diverged is True
        assert result.target_divergence_msg is not None
        assert "behind origin" in result.target_divergence_msg


class TestDryRunConflictForecasting:
    """Tests for dry-run conflict forecasting."""

    def test_dry_run_shows_conflict_forecast(self, conflicting_wps_repo: tuple[Path, list]):
        """Test that dry-run mode shows conflict predictions."""
        repo_root, wp_workspaces = conflicting_wps_repo

        predictions = predict_conflicts(wp_workspaces, "main", repo_root)

        # Should predict conflict on shared.txt (modified by all 3 WPs)
        assert len(predictions) >= 1

        shared_conflicts = [p for p in predictions if "shared.txt" in p.file_path]
        assert len(shared_conflicts) == 1

        conflict = shared_conflicts[0]
        assert len(conflict.conflicting_wps) == 3
        assert set(conflict.conflicting_wps) == {"WP01", "WP02", "WP03"}

    def test_dry_run_identifies_status_files(self, tmp_path: Path):
        """Test that dry-run identifies status files as auto-resolvable."""
        # Create repo with status file conflicts
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Create initial status file
        feature_slug = "022-status-test"
        status_dir = repo / "kitty-specs" / feature_slug / "tasks"
        status_dir.mkdir(parents=True)
        (status_dir / "WP01.md").write_text("---\nlane: planned\n---")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Get default branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        main_branch = result.stdout.strip()

        # WP01 updates status
        subprocess.run(
            ["git", "checkout", "-b", f"{feature_slug}-WP01"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (status_dir / "WP01.md").write_text("---\nlane: doing\n---")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP01 status"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # WP02 also updates status
        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", f"{feature_slug}-WP02"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        (status_dir / "WP01.md").write_text("---\nlane: for_review\n---")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "WP02 status"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        wp_workspaces = [
            (repo, "WP01", f"{feature_slug}-WP01"),
            (repo, "WP02", f"{feature_slug}-WP02"),
        ]

        predictions = predict_conflicts(wp_workspaces, main_branch, repo)

        assert len(predictions) == 1
        pred = predictions[0]
        assert pred.is_status_file is True
        assert pred.auto_resolvable is True


class TestResumeInterruption:
    """Tests for resuming interrupted merge operations."""

    def test_resume_after_interruption(self, tmp_path: Path):
        """Test resuming merge after interruption."""
        repo = tmp_path / "repo"

        # Create merge state
        state = MergeState(
            feature_slug="023-resume-test",
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03"],
            completed_wps=["WP01"],
            current_wp="WP02",
            strategy="merge",
        )

        save_state(state, repo)

        # Verify state is saved
        assert has_active_merge(repo) is True

        # Load state
        loaded = load_state(repo)
        assert loaded is not None
        assert loaded.feature_slug == "023-resume-test"
        assert loaded.completed_wps == ["WP01"]
        assert loaded.remaining_wps == ["WP02", "WP03"]
        assert loaded.current_wp == "WP02"

    def test_resume_continues_from_current_wp(self, tmp_path: Path):
        """Test that resume continues from current WP, not from beginning."""
        repo = tmp_path / "repo"

        # Create state with WP01, WP02 complete, WP03 in progress
        state = MergeState(
            feature_slug="024-continue-test",
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03", "WP04"],
            completed_wps=["WP01", "WP02"],
            current_wp="WP03",
            strategy="merge",
        )

        save_state(state, repo)

        # Load and verify
        loaded = load_state(repo)
        assert loaded is not None
        assert loaded.completed_wps == ["WP01", "WP02"]
        assert loaded.current_wp == "WP03"
        assert loaded.remaining_wps == ["WP03", "WP04"]

        # Simulate completing WP03
        loaded.mark_wp_complete("WP03")
        save_state(loaded, repo)

        # Reload and verify progress
        loaded2 = load_state(repo)
        assert loaded2 is not None
        assert loaded2.completed_wps == ["WP01", "WP02", "WP03"]
        assert loaded2.remaining_wps == ["WP04"]
        assert loaded2.current_wp is None


class TestAbortFunctionality:
    """Tests for aborting merge operations."""

    def test_abort_cleans_merge_state(self, tmp_path: Path):
        """Test that abort removes merge state file."""
        repo = tmp_path / "repo"

        # Create merge state
        state = MergeState(
            feature_slug="025-abort-test",
            target_branch="main",
            wp_order=["WP01", "WP02"],
            completed_wps=["WP01"],
            strategy="merge",
        )

        save_state(state, repo)

        # Verify state exists
        assert has_active_merge(repo) is True

        # Clear state (abort)
        cleared = clear_state(repo)
        assert cleared is True

        # Verify state is removed
        assert has_active_merge(repo) is False
        assert load_state(repo) is None

    def test_abort_on_nonexistent_state(self, tmp_path: Path):
        """Test that abort handles non-existent state gracefully."""
        repo = tmp_path / "repo"

        # No state exists
        assert has_active_merge(repo) is False

        # Clear should return False (nothing to clear)
        cleared = clear_state(repo)
        assert cleared is False

    def test_abort_after_conflict(self, tmp_path: Path):
        """Test aborting merge after encountering conflicts."""
        repo = tmp_path / "repo"

        # Create state with pending conflicts
        state = MergeState(
            feature_slug="026-conflict-abort-test",
            target_branch="main",
            wp_order=["WP01", "WP02"],
            completed_wps=[],
            current_wp="WP01",
            has_pending_conflicts=True,
            strategy="merge",
        )

        save_state(state, repo)

        # Verify conflict state
        loaded = load_state(repo)
        assert loaded is not None
        assert loaded.has_pending_conflicts is True

        # Abort
        clear_state(repo)

        # State should be removed
        assert load_state(repo) is None
