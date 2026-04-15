"""Tests for implementation crash recovery.

Uses real git repos (not mocks) since recovery exercises git worktree
and branch operations directly.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.status.models import TransitionRequest
from specify_cli.lanes.persistence import write_lanes_json
from specify_cli.lanes.recovery import (
    RECOVERY_ACTOR,
    RecoveryState,
    recover_context,
    reconcile_status,
    run_recovery,
    scan_recovery_state,
)
from specify_cli.lanes.worktree_allocator import _recover_lane_worktree
from specify_cli.workspace_context import (
    WorkspaceContext,
    load_context,
    save_context,
)

pytestmark = pytest.mark.git_repo


def _make_git_repo(path: Path) -> None:
    """Create a minimal git repo with an initial commit on 'main'."""
    subprocess.run(["git", "init", str(path)], capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(path), capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(path), capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "branch", "-M", "main"],
        cwd=str(path), capture_output=True, check=True,
    )
    (path / "README.md").write_text("init\n")
    subprocess.run(["git", "add", "."], cwd=str(path), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(path), capture_output=True, check=True,
    )


def _make_manifest(mission_slug: str = "010-feat") -> LanesManifest:
    return LanesManifest(
        version=1,
        mission_slug=mission_slug,
        mission_id=mission_slug,
        mission_branch=f"kitty/mission-{mission_slug}",
        target_branch="main",
        lanes=[
            ExecutionLane(
                lane_id="lane-a",
                wp_ids=("WP01", "WP02"),
                write_scope=("src/**",),
                predicted_surfaces=(),
                depends_on_lanes=(),
                parallel_group=0,
            ),
            ExecutionLane(
                lane_id="lane-b",
                wp_ids=("WP03",),
                write_scope=("tests/**",),
                predicted_surfaces=(),
                depends_on_lanes=(),
                parallel_group=0,
            ),
        ],
        computed_at="2026-04-03T12:00:00+00:00",
        computed_from="test",
    )


def _setup_feature(repo: Path, mission_slug: str = "010-feat") -> Path:
    """Set up kitty-specs feature directory with lanes.json and meta.json."""
    feature_dir = repo / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True, exist_ok=True)

    # Write lanes.json
    write_lanes_json(feature_dir, _make_manifest(mission_slug))

    # Write meta.json
    meta = {"mission_id": mission_slug, "mission_slug": mission_slug, "vcs": "git"}
    (feature_dir / "meta.json").write_text(json.dumps(meta))

    # Create tasks directory with WP files
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    for wp in ["WP01", "WP02", "WP03"]:
        (tasks_dir / f"{wp}-task.md").write_text(f"---\nwork_package_id: {wp}\n---\n# {wp}\n")

    # Create .kittify/workspaces directory
    (repo / ".kittify" / "workspaces").mkdir(parents=True, exist_ok=True)

    return feature_dir


def _create_lane_branch_with_commits(
    repo: Path,
    mission_slug: str = "010-feat",
    lane_id: str = "lane-a",
) -> str:
    """Create a lane branch with commits (simulating pre-crash state)."""
    # Create mission integration branch first (idempotent)
    mission_branch = f"kitty/mission-{mission_slug}"
    subprocess.run(
        ["git", "branch", mission_branch, "main"],
        cwd=str(repo), capture_output=True, check=False,  # ignore if exists
    )

    # Create lane branch from mission branch
    lane_branch = f"kitty/mission-{mission_slug}-{lane_id}"
    subprocess.run(
        ["git", "branch", lane_branch, mission_branch],
        cwd=str(repo), capture_output=True, check=True,
    )

    # Create a temporary worktree to make a commit on the lane branch
    tmp_worktree = repo / ".worktrees" / f"_tmp_{lane_id}"
    tmp_worktree.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "worktree", "add", str(tmp_worktree), lane_branch],
        cwd=str(repo), capture_output=True, check=True,
    )
    (tmp_worktree / "feature.py").write_text("# WP implementation\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp_worktree), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "feat: WP implementation"],
        cwd=str(tmp_worktree), capture_output=True, check=True,
    )

    # Remove the temporary worktree (simulating crash -- worktree lost)
    subprocess.run(
        ["git", "worktree", "remove", str(tmp_worktree), "--force"],
        cwd=str(repo), capture_output=True, check=True,
    )

    return lane_branch


class TestScanRecoveryState:
    """T007: Recovery scan tests."""

    def test_scan_detects_orphaned_branch(self, tmp_path: Path) -> None:
        """Branch exists but no worktree or context."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        _setup_feature(repo)
        _create_lane_branch_with_commits(repo)

        states = scan_recovery_state(repo, "010-feat")

        # Should detect lane-a WPs (WP01, WP02)
        lane_a_states = [s for s in states if s.lane_id == "lane-a"]
        assert len(lane_a_states) == 2
        assert all(s.branch_exists for s in lane_a_states)
        assert all(not s.worktree_exists for s in lane_a_states)
        assert all(not s.context_exists for s in lane_a_states)
        assert all(s.has_commits for s in lane_a_states)
        assert all(s.recovery_action == "recreate_worktree" for s in lane_a_states)

    def test_scan_detects_branch_with_no_context(self, tmp_path: Path) -> None:
        """Branch and worktree exist but no context file."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        _setup_feature(repo)

        # Create mission branch
        mission_branch = "kitty/mission-010-feat"
        subprocess.run(
            ["git", "branch", mission_branch, "main"],
            cwd=str(repo), capture_output=True, check=True,
        )

        # Create lane branch and worktree (but no context)
        lane_branch = "kitty/mission-010-feat-lane-a"
        worktree_path = repo / ".worktrees" / "010-feat-lane-a"
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "worktree", "add", "-b", lane_branch, str(worktree_path), mission_branch],
            cwd=str(repo), capture_output=True, check=True,
        )

        states = scan_recovery_state(repo, "010-feat")

        lane_a_states = [s for s in states if s.lane_id == "lane-a"]
        assert len(lane_a_states) == 2  # WP01, WP02
        assert all(s.worktree_exists for s in lane_a_states)
        assert all(not s.context_exists for s in lane_a_states)
        assert all(s.recovery_action == "recreate_context" for s in lane_a_states)

    def test_scan_detects_context_with_no_worktree(self, tmp_path: Path) -> None:
        """Context exists but worktree was lost."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        _setup_feature(repo)
        _create_lane_branch_with_commits(repo)

        # Create context manually (simulating state after worktree was removed)
        context = WorkspaceContext(
            wp_id="WP01",
            mission_slug="010-feat",
            worktree_path=".worktrees/010-feat-lane-a",
            branch_name="kitty/mission-010-feat-lane-a",
            base_branch="kitty/mission-010-feat",
            base_commit="abc123",
            dependencies=[],
            created_at="2026-01-01T00:00:00Z",
            created_by="implement-command-lane",
            vcs_backend="git",
            lane_id="lane-a",
            lane_wp_ids=["WP01", "WP02"],
            current_wp="WP01",
        )
        save_context(repo, context)

        states = scan_recovery_state(repo, "010-feat")

        lane_a_states = [s for s in states if s.lane_id == "lane-a"]
        assert len(lane_a_states) >= 1
        # At least one should need worktree recreation
        worktree_needed = [s for s in lane_a_states if s.recovery_action == "recreate_worktree"]
        assert len(worktree_needed) >= 1

    def test_scan_correctly_identifies_no_action(self, tmp_path: Path) -> None:
        """No branches means nothing to recover."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        _setup_feature(repo)

        states = scan_recovery_state(repo, "010-feat")

        # No lane branches exist, so nothing to scan
        assert len(states) == 0


class TestWorktreeRecovery:
    """T008: Worktree reconciliation tests."""

    def test_recover_worktree_from_existing_branch(self, tmp_path: Path) -> None:
        """Delete worktree, keep branch, run recovery, verify worktree recreated."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        _setup_feature(repo)
        lane_branch = _create_lane_branch_with_commits(repo)

        # Verify worktree doesn't exist yet
        worktree_path = repo / ".worktrees" / "010-feat-lane-a"
        assert not worktree_path.exists()

        # Recover the worktree
        _recover_lane_worktree(repo, worktree_path, lane_branch)

        # Verify worktree was recreated
        assert worktree_path.exists()
        assert (worktree_path / ".git").exists()
        assert (worktree_path / "feature.py").exists()

        # Verify the branch is correct
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(worktree_path), capture_output=True, text=True, check=True,
        )
        assert result.stdout.strip() == lane_branch

    def test_recover_worktree_without_b_flag(self, tmp_path: Path) -> None:
        """Verify recovery uses git worktree add (without -b) for existing branch."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        _setup_feature(repo)
        lane_branch = _create_lane_branch_with_commits(repo)

        worktree_path = repo / ".worktrees" / "010-feat-lane-a"

        # This should NOT fail even though the branch already exists
        # (because we use `git worktree add <path> <branch>` not `git worktree add -b`)
        _recover_lane_worktree(repo, worktree_path, lane_branch)
        assert worktree_path.exists()

    def test_recover_context_from_branch(self, tmp_path: Path) -> None:
        """Delete context, keep branch+worktree, verify context recreated."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        _setup_feature(repo)
        lane_branch = _create_lane_branch_with_commits(repo)

        # Recover worktree first
        worktree_path = repo / ".worktrees" / "010-feat-lane-a"
        _recover_lane_worktree(repo, worktree_path, lane_branch)

        # Build a RecoveryState to pass to recover_context
        state = RecoveryState(
            wp_id="WP01",
            lane_id="lane-a",
            branch_name=lane_branch,
            branch_exists=True,
            worktree_exists=True,
            context_exists=False,
            status_lane="planned",
            has_commits=True,
            recovery_action="recreate_context",
        )

        recover_context(repo, "010-feat", state)

        # Verify context was created
        loaded = load_context(repo, "010-feat-lane-a")
        assert loaded is not None
        assert loaded.mission_slug == "010-feat"
        assert loaded.lane_id == "lane-a"
        assert loaded.branch_name == lane_branch
        assert loaded.created_by == "recovery"
        assert loaded.lane_wp_ids == ["WP01", "WP02"]


class TestStatusReconciliation:
    """T009: Status reconciliation tests."""

    def test_status_reconciliation_emits_transitions(self, tmp_path: Path) -> None:
        """Status is 'planned' for a WP with commits, should emit transitions."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        feature_dir = _setup_feature(repo)
        _create_lane_branch_with_commits(repo)

        state = RecoveryState(
            wp_id="WP01",
            lane_id="lane-a",
            branch_name="kitty/mission-010-feat-lane-a",
            branch_exists=True,
            worktree_exists=True,
            context_exists=True,
            status_lane="planned",
            has_commits=True,
            recovery_action="emit_transitions",
        )

        emitted = reconcile_status(repo, "010-feat", state)

        # Should emit planned->claimed and claimed->in_progress
        assert emitted == 2

        # Verify events were written
        from specify_cli.status.store import read_events

        events = read_events(feature_dir)
        wp_events = [e for e in events if e.wp_id == "WP01"]
        assert len(wp_events) == 2
        assert wp_events[0].actor == RECOVERY_ACTOR
        assert wp_events[1].actor == RECOVERY_ACTOR
        assert str(wp_events[0].from_lane) == "planned"
        assert str(wp_events[0].to_lane) == "claimed"
        assert str(wp_events[1].from_lane) == "claimed"
        assert str(wp_events[1].to_lane) == "in_progress"

    def test_recovery_does_not_advance_past_in_progress(self, tmp_path: Path) -> None:
        """Recovery never emits for_review, approved, or done transitions."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        feature_dir = _setup_feature(repo)
        _create_lane_branch_with_commits(repo)

        # Start from in_progress (already at ceiling)
        # First, emit events to get to in_progress
        from specify_cli.status.emit import emit_status_transition

        emit_status_transition(TransitionRequest(
            feature_dir=feature_dir,
            mission_slug="010-feat",
            wp_id="WP01",
            to_lane="claimed",
            actor="test",
        ))
        emit_status_transition(TransitionRequest(
            feature_dir=feature_dir,
            mission_slug="010-feat",
            wp_id="WP01",
            to_lane="in_progress",
            actor="test",
        ))

        state = RecoveryState(
            wp_id="WP01",
            lane_id="lane-a",
            branch_name="kitty/mission-010-feat-lane-a",
            branch_exists=True,
            worktree_exists=True,
            context_exists=True,
            status_lane="in_progress",
            has_commits=True,
            recovery_action="emit_transitions",
        )

        emitted = reconcile_status(repo, "010-feat", state)

        # Should NOT emit any transitions (already at in_progress)
        assert emitted == 0

    def test_recovery_uses_recovery_actor(self, tmp_path: Path) -> None:
        """All recovery transitions use actor='recovery'."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        feature_dir = _setup_feature(repo)
        _create_lane_branch_with_commits(repo)

        state = RecoveryState(
            wp_id="WP01",
            lane_id="lane-a",
            branch_name="kitty/mission-010-feat-lane-a",
            branch_exists=True,
            worktree_exists=True,
            context_exists=True,
            status_lane="planned",
            has_commits=True,
            recovery_action="emit_transitions",
        )

        reconcile_status(repo, "010-feat", state)

        from specify_cli.status.store import read_events

        events = read_events(feature_dir)
        for event in events:
            if event.wp_id == "WP01":
                assert event.actor == RECOVERY_ACTOR

    def test_recovery_from_claimed_emits_only_in_progress(self, tmp_path: Path) -> None:
        """When status is claimed, recovery only emits claimed->in_progress."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        feature_dir = _setup_feature(repo)
        _create_lane_branch_with_commits(repo)

        # Get to claimed first
        from specify_cli.status.emit import emit_status_transition

        emit_status_transition(TransitionRequest(
            feature_dir=feature_dir,
            mission_slug="010-feat",
            wp_id="WP01",
            to_lane="claimed",
            actor="test",
        ))

        state = RecoveryState(
            wp_id="WP01",
            lane_id="lane-a",
            branch_name="kitty/mission-010-feat-lane-a",
            branch_exists=True,
            worktree_exists=True,
            context_exists=True,
            status_lane="claimed",
            has_commits=True,
            recovery_action="emit_transitions",
        )

        emitted = reconcile_status(repo, "010-feat", state)

        assert emitted == 1

        from specify_cli.status.store import read_events

        events = read_events(feature_dir)
        recovery_events = [e for e in events if e.actor == RECOVERY_ACTOR]
        assert len(recovery_events) == 1
        assert str(recovery_events[0].from_lane) == "claimed"
        assert str(recovery_events[0].to_lane) == "in_progress"


class TestRunRecovery:
    """Integration tests for the full recovery orchestration."""

    def test_full_recovery_flow(self, tmp_path: Path) -> None:
        """Branch exists, worktree lost, context lost -- full recovery."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        _setup_feature(repo)
        _create_lane_branch_with_commits(repo)

        report = run_recovery(repo, "010-feat")

        # Should recover WP01 and WP02 (both in lane-a)
        assert "WP01" in report.recovered_wps or "WP02" in report.recovered_wps
        assert report.worktrees_recreated >= 1
        assert report.transitions_emitted >= 2  # planned->claimed, claimed->in_progress per WP
        assert report.errors == []

        # Verify worktree was recreated
        worktree_path = repo / ".worktrees" / "010-feat-lane-a"
        assert worktree_path.exists()

    def test_no_recovery_needed(self, tmp_path: Path) -> None:
        """Clean state produces empty recovery report."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        _setup_feature(repo)

        report = run_recovery(repo, "010-feat")

        assert report.recovered_wps == []
        assert report.worktrees_recreated == 0
        assert report.transitions_emitted == 0
        assert report.errors == []

    def test_recovery_partial_failure_continues(self, tmp_path: Path) -> None:
        """If one WP recovery fails, the others still proceed."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        _setup_feature(repo)

        # Create lane-a and lane-b branches
        _create_lane_branch_with_commits(repo, lane_id="lane-a")
        _create_lane_branch_with_commits(repo, lane_id="lane-b")

        report = run_recovery(repo, "010-feat")

        # Both lanes should have been attempted
        # Even if one worktree recovery somehow conflicted, the other should succeed
        assert report.worktrees_recreated >= 1
        # The report should have results for WPs from multiple lanes
        total = report.worktrees_recreated + len(report.errors)
        assert total >= 1


class TestRecoverLaneWorktree:
    """Direct tests for _recover_lane_worktree."""

    def test_fails_when_branch_does_not_exist(self, tmp_path: Path) -> None:
        """Recovery fails if the branch doesn't exist."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)

        worktree_path = repo / ".worktrees" / "010-feat-lane-a"
        with pytest.raises(RuntimeError, match="Failed to recover worktree"):
            _recover_lane_worktree(repo, worktree_path, "kitty/mission-010-feat-nonexistent")

    def test_recovered_worktree_has_correct_branch(self, tmp_path: Path) -> None:
        """Recovered worktree is on the correct branch."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        _setup_feature(repo)
        lane_branch = _create_lane_branch_with_commits(repo)

        worktree_path = repo / ".worktrees" / "010-feat-lane-a"
        _recover_lane_worktree(repo, worktree_path, lane_branch)

        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(worktree_path), capture_output=True, text=True, check=True,
        )
        assert result.stdout.strip() == lane_branch
