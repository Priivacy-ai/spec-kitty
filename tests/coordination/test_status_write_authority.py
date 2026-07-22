"""WP04 (FR-004) — single status write-authority.

Pins the topology-conditional non-transactional fallback (contract rows 7-8):

* **Coord topology** — a status write in the ``_transaction_topology_available``
  False arm materializes/targets the coord worktree via
  ``CoordinationWorkspace.resolve`` and COMMITS the event there (never a
  primary-only-uncommitted write that leaves the coord log stale).
* **Coord-less topology** (``SINGLE_BRANCH``/``LANES``/flat, or a coord mission
  whose worktree cannot be materialized) — the primary-uncommitted write path is
  PRESERVED; no coord path is forced and no error is raised.

Plus the T015 campsite: the auto-rebase lane-sync ``_git_stdout`` helper must
tolerate a not-yet-materialized lane worktree (its documented "Returns None when
... no lane worktree exists" contract) instead of crashing with a raw
``FileNotFoundError``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.coordination import status_transition as st
from specify_cli.status.models import Lane, TransitionRequest
from tests.characterization.test_trio_json_envelope import _build_mission_repo


def _git_show(repo_root: Path, ref: str, rel_path: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"{ref}:{rel_path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def _claim_request(
    feature_dir: Path, repo_root: Path, mission_slug: str
) -> TransitionRequest:
    return TransitionRequest(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id="WP01",
        to_lane=Lane.CLAIMED,
        actor="claude",
        reason="write-authority test claim",
        execution_mode="worktree",
        repo_root=repo_root,
    )


# ---------------------------------------------------------------------------
# (a) Coord topology → the fallback commits the event to the coord worktree.
# ---------------------------------------------------------------------------


@pytest.mark.git_repo
def test_fallback_commits_status_to_coord_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-004 row 7: a coord-topology fallback write lands on the coord branch."""
    repo_root, mission_slug = _build_mission_repo(
        tmp_path,
        monkeypatch,
        coord=True,
        mission_slug="write-authority-coord",
        wp_lane="planned",
        materialize_coord=True,
    )
    feature_dir = repo_root / "kitty-specs" / mission_slug
    coord_branch = st.load_meta(feature_dir)["coordination_branch"]

    request = _claim_request(feature_dir, repo_root, mission_slug)
    identity = st._identity_for_request(request)
    # Precondition: this IS a coord topology the fallback recognizes.
    assert identity.coordination_branch is not None

    event = st._fallback_emit_single(
        identity,
        request,
        mission_slug,
        ensure_sync_daemon=False,
        sync_dossier=False,
    )

    assert str(event.to_lane) == str(Lane.CLAIMED)
    # The event is COMMITTED to the coord branch (not merely written to a
    # primary-uncommitted working copy).
    committed_log = _git_show(
        repo_root, coord_branch, f"kitty-specs/{mission_slug}/status.events.jsonl"
    )
    assert "claimed" in committed_log, committed_log
    assert event.event_id in committed_log, committed_log


# ---------------------------------------------------------------------------
# (b) Two-sided coord-less coverage: the primary write path is PRESERVED.
# ---------------------------------------------------------------------------


@pytest.mark.git_repo
def test_fallback_preserves_primary_for_flat_topology(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-004 row 8: a coord-LESS (flat) mission keeps the primary write path."""
    repo_root, mission_slug = _build_mission_repo(
        tmp_path,
        monkeypatch,
        coord=False,
        mission_slug="write-authority-flat",
        wp_lane="planned",
    )
    feature_dir = repo_root / "kitty-specs" / mission_slug

    request = _claim_request(feature_dir, repo_root, mission_slug)
    identity = st._identity_for_request(request)
    # A flat mission declares no coordination branch → coord-less.
    assert identity.coordination_branch is None
    assert st._resolve_fallback_coord_worktree(identity, mission_slug) is None

    event = st._fallback_emit_single(
        identity,
        request,
        mission_slug,
        ensure_sync_daemon=False,
        sync_dossier=False,
    )

    # The primary event log records the transition (primary write path), and no
    # coord worktree was forced into existence.
    assert str(event.to_lane) == str(Lane.CLAIMED)
    primary_log = (feature_dir / "status.events.jsonl").read_text(encoding="utf-8")
    assert event.event_id in primary_log
    assert not (repo_root / ".worktrees").exists()


@pytest.mark.git_repo
def test_fallback_does_not_force_coord_when_worktree_unresolvable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-004 row 8 (edge): coordination_branch present but the coord worktree
    cannot be materialized (transactional arm unavailable) → the fallback must
    NOT force a coord path; it degrades cleanly to the primary write, no error.
    """
    repo_root, mission_slug = _build_mission_repo(
        tmp_path,
        monkeypatch,
        coord=True,
        mission_slug="write-authority-unresolvable",
        wp_lane="planned",
        materialize_coord=True,
    )
    feature_dir = repo_root / "kitty-specs" / mission_slug

    request = _claim_request(feature_dir, repo_root, mission_slug)
    identity = st._identity_for_request(request)
    assert identity.coordination_branch is not None

    # Force the coord worktree resolution to fail (e.g. repo root is not a work
    # tree / worktree add refuses) — the fallback must degrade to primary.
    from specify_cli.coordination.workspace import CoordinationWorkspace

    def _boom(*_a: object, **_k: object) -> Path:
        raise RuntimeError("simulated: coord worktree cannot be materialized")

    monkeypatch.setattr(CoordinationWorkspace, "resolve", staticmethod(_boom))

    # The decision helper reports "no coord target" rather than raising.
    assert st._resolve_fallback_coord_worktree(identity, mission_slug) is None

    event = st._fallback_emit_single(
        identity,
        request,
        mission_slug,
        ensure_sync_daemon=False,
        sync_dossier=False,
    )
    # Primary write succeeded (no coord path forced, no error surfaced).
    assert str(event.to_lane) == str(Lane.CLAIMED)
    primary_log = (feature_dir / "status.events.jsonl").read_text(encoding="utf-8")
    assert event.event_id in primary_log


# ---------------------------------------------------------------------------
# T015 campsite: auto-rebase lane-sync must not crash on an absent lane worktree.
# ---------------------------------------------------------------------------


def test_git_stdout_tolerates_missing_worktree_cwd(tmp_path: Path) -> None:
    """A non-existent ``cwd`` yields ``None`` (documented contract), not a raw
    ``FileNotFoundError`` — the crash that surfaced once #2861's empty second
    commit no longer short-circuited the auto-rebase sync.
    """
    from specify_cli.lanes import lifecycle_sync

    missing = tmp_path / "does-not-exist-lane-worktree"
    assert not missing.exists()
    assert lifecycle_sync._git_stdout(missing, "rev-parse", "--abbrev-ref", "HEAD") is None
