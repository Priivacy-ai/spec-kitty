"""FR-015 regression: move-task --to planned (reject) must not trip the guard
when the only untracked content in the lane worktree is spec-kitty's own
review-lock state.

Mirrors ``test_approve_without_force.py`` but for the rejection-back-to-planned
code path. Also proves that the retry hint names ``planned`` (the caller's
target lane) when genuine drift blocks, not the legacy hard-coded
``for_review`` string.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from specify_cli.cli.commands.agent.tasks import _validate_ready_for_review
from specify_cli.review.lock import LOCK_DIR, LOCK_FILE, ReviewLock
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event
from tests.lane_test_utils import lane_branch_name, lane_worktree_path, write_single_lane_manifest

pytestmark = pytest.mark.git_repo


@pytest.fixture
def lane_worktree_repo(tmp_path: Path) -> tuple[Path, Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True)

    (repo / ".kittify").mkdir()
    (repo / ".kittify" / "config.yaml").write_text("# config\n")

    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, check=True, capture_output=True)

    mission_slug = "wp06-reject-guard"
    feature_dir = repo / "kitty-specs" / mission_slug
    (feature_dir / "tasks").mkdir(parents=True)
    write_single_lane_manifest(feature_dir, wp_ids=("WP01",))

    (feature_dir / "tasks" / "WP01-feature.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Feature\nagent: test\nshell_pid: ''\n---\n\n"
        "# WP01\n\n## Activity Log\n\n- 2025-01-01T00:00:00Z – system – lane=planned\n",
        encoding="utf-8",
    )

    for lane_val in ("planned", "in_progress", "for_review"):
        append_event(
            feature_dir,
            StatusEvent(
                event_id=f"seed-WP01-{lane_val}",
                mission_slug=mission_slug,
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane(lane_val),
                at="2025-01-01T00:00:00+00:00",
                actor="test-fixture",
                force=True,
                execution_mode="worktree",
            ),
        )

    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Seed mission"], cwd=repo, check=True, capture_output=True)

    worktree = lane_worktree_path(repo, mission_slug)
    subprocess.run(
        ["git", "worktree", "add", "-b", lane_branch_name(mission_slug), str(worktree), "main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    (worktree / "feature.py").write_text("# implementation\n")
    subprocess.run(["git", "add", "."], cwd=worktree, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat(WP01): implement"], cwd=worktree, check=True, capture_output=True)

    return repo, worktree, mission_slug


# ---------------------------------------------------------------------------
# Happy path: reject (move to planned) passes without --force
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.agent.tasks.get_mission_type", return_value="software-dev")
def test_reject_passes_without_force_when_only_spec_kitty_dirty(
    _mock_mission: Mock,
    lane_worktree_repo: tuple[Path, Path, str],
) -> None:
    _, worktree, mission_slug = lane_worktree_repo

    ReviewLock.acquire(worktree, wp_id="WP01", agent="reviewer")
    assert (worktree / LOCK_DIR / LOCK_FILE).exists()

    is_valid, guidance = _validate_ready_for_review(
        repo_root=worktree,
        mission_slug=mission_slug,
        wp_id="WP01",
        force=False,
        target_lane="planned",
    )
    assert is_valid is True, f"Guidance unexpectedly blocked reject: {guidance}"
    assert guidance == []


# ---------------------------------------------------------------------------
# Post-transition: .spec-kitty/ cleaned up after reject + release
# ---------------------------------------------------------------------------


def test_spec_kitty_dir_removed_after_release_on_reject_path(
    lane_worktree_repo: tuple[Path, Path, str],
) -> None:
    _, worktree, _ = lane_worktree_repo

    ReviewLock.acquire(worktree, wp_id="WP01", agent="reviewer")
    assert (worktree / LOCK_DIR).is_dir()

    ReviewLock.release(worktree)
    assert not (worktree / LOCK_DIR).exists()


# ---------------------------------------------------------------------------
# Genuine drift still blocks, and retry text names 'planned'
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.agent.tasks.get_mission_type", return_value="software-dev")
def test_genuine_drift_still_blocks_reject_and_retry_says_planned(
    _mock_mission: Mock,
    lane_worktree_repo: tuple[Path, Path, str],
) -> None:
    _, worktree, mission_slug = lane_worktree_repo

    ReviewLock.acquire(worktree, wp_id="WP01", agent="reviewer")
    (worktree / "uncommitted.py").write_text("# genuine drift\n")

    is_valid, guidance = _validate_ready_for_review(
        repo_root=worktree,
        mission_slug=mission_slug,
        wp_id="WP01",
        force=False,
        target_lane="planned",
    )

    assert is_valid is False
    joined = "\n".join(guidance)
    assert "uncommitted.py" in joined
    assert ".spec-kitty/" not in joined
    # FR-015: retry hint uses the caller's actual target_lane
    assert "--to planned" in joined
    assert "--to for_review" not in joined


# ---------------------------------------------------------------------------
# Extra regression: default target_lane falls back to for_review for callers
# that haven't migrated (backward compatibility).
# ---------------------------------------------------------------------------


@patch("specify_cli.cli.commands.agent.tasks.get_mission_type", return_value="software-dev")
def test_default_target_lane_is_for_review(
    _mock_mission: Mock,
    lane_worktree_repo: tuple[Path, Path, str],
) -> None:
    _, worktree, mission_slug = lane_worktree_repo
    (worktree / "drift.py").write_text("# drift\n")

    is_valid, guidance = _validate_ready_for_review(
        repo_root=worktree,
        mission_slug=mission_slug,
        wp_id="WP01",
        force=False,
    )
    assert is_valid is False
    joined = "\n".join(guidance)
    assert "--to for_review" in joined
