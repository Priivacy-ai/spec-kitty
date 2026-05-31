"""Integration tests for WP08 legacy mission fallback (#1348).

These tests verify two contracts that close #1348 for missions created
before the coord-branch topology landed:

1. **Legacy detection routes bookkeeping to the lane worktree** (T035,
   FR-017): when ``meta.json`` lacks ``coordination_branch``,
   ``BookkeepingTransaction.acquire()`` resolves to the operator's
   current lane worktree + its checked-out branch.

2. **The atomicity invariants apply uniformly** (T036, SC-11): the
   pre-flight policy gate, surgical-truncate rollback, and lock
   serialisation work identically in legacy mode.  A forced commit
   failure leaves ``status.events.jsonl`` byte-identical (SHA-256
   match), exactly as the new-topology path does.

The tests intentionally use the real git surface — no monkey-patching —
because the contract under test is the on-disk behaviour of the
transaction layer.

Spec source: FR-017, FR-027, SC-11.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

from specify_cli.coordination.transaction import (
    BookkeepingCommitFailed,
    BookkeepingPolicyRefused,
    BookkeepingTransaction,
)
from specify_cli.status.emit import build_status_event


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
    )


def _init_git_repo(repo_root: Path) -> None:
    _run(repo_root, "git", "init", "--initial-branch=main")
    _run(repo_root, "git", "config", "user.email", "test@example.invalid")
    _run(repo_root, "git", "config", "user.name", "WP08 Test")
    _run(repo_root, "git", "config", "commit.gpgsign", "false")
    (repo_root / "README.md").write_text("seed\n", encoding="utf-8")
    _run(repo_root, "git", "add", "README.md")
    _run(repo_root, "git", "commit", "-m", "seed")


def _make_legacy_mission(
    repo_root: Path,
    *,
    mission_slug: str = "wp08-legacy-mission",
    mission_id: str = "01KLEGACYZZZZZZZZZZZZZZZZZ",
) -> dict[str, Any]:
    """Create a mission emulating the pre-PR2 (pre-coord) topology.

    Legacy state:
      * ``meta.json`` carries identity but **no** ``coordination_branch``
      * No coord branch / worktree exists; only a lane branch off main
      * ``kitty-specs/<slug>/`` lives in the primary checkout (no
        sparse-checkout exclusion).
    """
    mid8 = mission_id[:8]
    feature_dir = repo_root / "kitty-specs" / f"{mission_slug}-{mid8}"
    feature_dir.mkdir(parents=True, exist_ok=True)

    # Legacy meta.json — no coordination_branch field.
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": mission_id,
                "mission_slug": mission_slug,
                "mid8": mid8,
                "mission_type": "software-dev",
                "target_branch": "main",
                "created_at": "2026-05-28T00:00:00+00:00",
                "friendly_name": "WP08 legacy mission",
                # NOTE: coordination_branch deliberately absent
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    # Commit the meta + scaffold so the lane worktree sees them.
    _run(repo_root, "git", "add", "kitty-specs")
    _run(repo_root, "git", "commit", "-m", "seed legacy mission scaffold")

    # Build a lane worktree on a lane branch parented off main.
    lane_branch = f"kitty/mission-{mission_slug}-{mid8}-lane-a"
    _run(repo_root, "git", "branch", lane_branch, "main")
    lane_worktree = repo_root / ".worktrees" / f"{mission_slug}-{mid8}-lane-a"
    lane_worktree.parent.mkdir(parents=True, exist_ok=True)
    _run(repo_root, "git", "worktree", "add", str(lane_worktree), lane_branch)

    return {
        "feature_dir": feature_dir,
        "mission_slug": mission_slug,
        "mission_id": mission_id,
        "mid8": mid8,
        "lane_branch": lane_branch,
        "lane_worktree": lane_worktree,
    }


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: TID251 — file-integrity checksum of read_bytes(), not charter freshness hashing


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo_root(tmp_path: Path) -> Path:
    _init_git_repo(tmp_path)
    return tmp_path


@pytest.fixture()
def legacy_mission(repo_root: Path) -> dict[str, Any]:
    return _make_legacy_mission(repo_root)


@pytest.fixture()
def lane_cwd(legacy_mission: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pretend the operator is standing inside the legacy mission's lane worktree."""
    lane_worktree = legacy_mission["lane_worktree"]
    monkeypatch.chdir(lane_worktree)
    return lane_worktree


# ---------------------------------------------------------------------------
# T038 / SC-11: legacy mission tests
# ---------------------------------------------------------------------------


def test_legacy_mission_implement_uses_lane_destination(
    repo_root: Path,
    legacy_mission: dict[str, Any],
    lane_cwd: Path,
) -> None:
    """``acquire()`` resolves to the lane worktree + lane branch."""
    with BookkeepingTransaction.acquire(
        repo_root=repo_root,
        mission_id=legacy_mission["mission_id"],
        mission_slug=legacy_mission["mission_slug"],
        mid8=legacy_mission["mid8"],
        # Caller may have requested the "intended" coord ref; legacy
        # detection overrides to the actual lane HEAD.
        destination_ref=f"kitty/mission-{legacy_mission['mission_slug']}-{legacy_mission['mid8']}",
        operation="legacy_implement_smoke",
    ) as txn:
        # The transaction now points at the lane worktree we cd'd into.
        assert txn.worktree_root == lane_cwd
        # And destination_ref was rewritten to the lane branch HEAD.
        assert txn.destination_ref == legacy_mission["lane_branch"]


def test_legacy_mission_warning_emitted_once(
    repo_root: Path,
    legacy_mission: dict[str, Any],
    lane_cwd: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """First invocation prints a deprecation warning; subsequent calls suppress."""
    # First acquire — warning expected on stderr.
    with BookkeepingTransaction.acquire(
        repo_root=repo_root,
        mission_id=legacy_mission["mission_id"],
        mission_slug=legacy_mission["mission_slug"],
        mid8=legacy_mission["mid8"],
        destination_ref="kitty/x",
        operation="legacy_first_emit",
    ):
        pass
    first_capture = capsys.readouterr()
    assert "legacy topology" in first_capture.err
    assert "migrating" in first_capture.err

    # Marker file exists.
    marker = repo_root / ".kittify" / f"legacy-warning-shown-{legacy_mission['mission_id']}"
    assert marker.exists(), "legacy-warning marker must be persisted under .kittify/"

    # Second acquire — warning suppressed.
    with BookkeepingTransaction.acquire(
        repo_root=repo_root,
        mission_id=legacy_mission["mission_id"],
        mission_slug=legacy_mission["mission_slug"],
        mid8=legacy_mission["mid8"],
        destination_ref="kitty/x",
        operation="legacy_second_emit",
    ):
        pass
    second_capture = capsys.readouterr()
    assert "legacy topology" not in second_capture.err


def test_legacy_mission_forced_commit_failure_rolls_back(
    repo_root: Path,
    legacy_mission: dict[str, Any],
    lane_cwd: Path,
) -> None:
    """SC-11: forced commit failure leaves status.events.jsonl byte-identical.

    Installs a real ``pre-commit`` hook in the lane worktree that exits 1
    so the failure is genuine (not mocked).  After the transaction
    raises ``BookkeepingCommitFailed``, the SHA-256 of the event log
    must equal its pre-emit digest — proving the surgical-truncate
    rollback works on a legacy lane worktree exactly as it does on a
    coord worktree.
    """
    feature_dir_in_lane = (
        lane_cwd
        / "kitty-specs"
        / f"{legacy_mission['mission_slug']}-{legacy_mission['mid8']}"
    )
    feature_dir_in_lane.mkdir(parents=True, exist_ok=True)
    events_path = feature_dir_in_lane / "status.events.jsonl"
    # Pre-existing content to verify byte-identical rollback.  Use a
    # well-formed StatusEvent so the readback verifier accepts it on
    # the next append.
    seed_event = build_status_event(
        mission_slug=legacy_mission["mission_slug"],
        mission_id=legacy_mission["mission_id"],
        wp_id="WP00",
        from_lane="planned",
        to_lane="claimed",
        actor="seed",
    )
    seed_line = json.dumps(seed_event.to_dict(), sort_keys=True) + "\n"
    events_path.write_text(seed_line, encoding="utf-8")
    pre_digest = _sha256(events_path)
    assert pre_digest is not None

    # Install a failing pre-commit hook on the lane worktree.  In linked
    # worktrees, hooks live in the per-worktree gitdir.
    raw = subprocess.check_output(
        ["git", "-C", str(lane_cwd), "rev-parse", "--git-path", "hooks"],
        text=True,
    ).strip()
    hooks_dir = Path(raw)
    if not hooks_dir.is_absolute():
        hooks_dir = lane_cwd / hooks_dir
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook = hooks_dir / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)

    event = build_status_event(
        mission_slug=legacy_mission["mission_slug"],
        mission_id=legacy_mission["mission_id"],
        wp_id="WP01",
        from_lane="planned",
        to_lane="claimed",
        actor="claude",
    )

    with pytest.raises(BookkeepingCommitFailed), BookkeepingTransaction.acquire(
        repo_root=repo_root,
        mission_id=legacy_mission["mission_id"],
        mission_slug=legacy_mission["mission_slug"],
        mid8=legacy_mission["mid8"],
        destination_ref="kitty/x",
        operation="legacy_forced_failure",
    ) as txn:
        txn.append_event(event)
        txn.commit("chore: legacy rollback regression test")

    # SHA-256 must match pre-emit: rollback is byte-identical.
    post_digest = _sha256(events_path)
    assert post_digest == pre_digest, (
        f"SC-11 regression: legacy event log digest drifted "
        f"({pre_digest!r} -> {post_digest!r})"
    )


def test_legacy_mission_protected_lane_branch_refused(
    repo_root: Path,
    legacy_mission: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A legacy mission whose lane worktree happens to sit on a protected
    ref must be refused by the pre-flight policy gate.

    Simulates an operator who has accidentally checked out ``main``
    inside what would otherwise be a lane worktree.  The legacy fallback
    resolves the lane branch from HEAD, sees ``main``, and the
    pre-flight ``WorkflowMutationPolicy`` refuses.  This is the
    legacy-mode equivalent of SC-08's protected-ref refusal.
    """
    # cd into the main repo root (not the lane worktree).  The legacy
    # fallback will resolve HEAD = main from here.
    monkeypatch.chdir(repo_root)

    with pytest.raises(BookkeepingPolicyRefused):
        BookkeepingTransaction.acquire(
            repo_root=repo_root,
            mission_id=legacy_mission["mission_id"],
            mission_slug=legacy_mission["mission_slug"],
            mid8=legacy_mission["mid8"],
            destination_ref="kitty/x",
            operation="legacy_protected_refusal",
        )
