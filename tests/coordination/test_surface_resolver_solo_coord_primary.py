"""WP08 T030 — solo PR-bound coord mission: read == write, killed by construction.

#2533: a solo (no-lanes) PR-bound ``--start-branch`` mission is forced onto
``MissionTopology.COORD`` by the (frozen, out-of-scope) ``if pr_bound: return
COORD`` derivation (#2581,
``test_create_pr_bound_on_non_primary_branch_still_defaults_to_coord``) even
though no lane worktree will ever write to the minted coordination branch.
Its coordination worktree ROOT gets materialized (``ensure_coordination_branch``
mints the branch; a first ``BookkeepingTransaction.acquire()`` — or an operator
running ``spec-kitty doctor workspaces --fix`` — materializes the worktree root)
but its mission dir never does, because nothing ever appends a status event
there. ``resolve_status_surface_with_anchor``'s ``CoordState.EMPTY`` arm
(WP08 T029) now routes this EXPECTED state to PRIMARY without warning.

This module is the **D4 same-path agreement regression**
(``kitty-specs/loop-friction-quickwins-2-01KXBWA4/tasks/WP08-solo-coord-
surface-routing.md``, "WP07 <-> WP08 boundary rule" item 3): it proves the fix
does not merely mute the READ-side warning while a write silently drifts to a
coordination branch nobody reads from again (the highest-listed WP08 risk —
"muting the READ warning while the WRITE still targets coord would MASK the
split-brain"). Four assertions, each load-bearing:

1. **READ surface** (:func:`resolve_status_surface`) resolves to the PRIMARY
   ``status.events.jsonl`` path — the WP08 T029 fix.
2. **WRITE commit-ref** (``mission_runtime.placement_seam(...)
   .write_target(MissionArtifactKind.STATUS_STATE)`` — the ONE kind-aware
   write-placement authority, contracts/seam-api.md; read here, never
   mutated) is READ and PINNED explicitly rather than ignored: for
   ``MissionTopology.COORD`` it is (by frozen, out-of-scope design,
   ``coordination/status_transition.py:_resolve_write_target``'s own
   docstring — "STATUS write target MUST keep resolving the coordination
   branch under coord topology") the coordination branch, NOT
   ``target_branch``. This is asserted OPENLY, not hidden, so a reviewer
   sees exactly what WP08 does and does not change.
3. **No-masking proof**: at this legitimate-empty moment the coordination
   branch has NOT diverged from ``target_branch`` — same commit SHA. Nothing
   has ever been committed to the coordination branch that the PRIMARY
   fallback could be silently hiding; a real mismatch (assertion 3 failing)
   would mean data exists on coordination that reads never surface — exactly
   the masked split-brain the WP08 risk note warns against.
4. **Self-healing regression**: once a real write lands under the coord
   worktree (mirroring ``BookkeepingTransaction.append_event()``'s
   ``feature_dir.mkdir()``), ``resolve_status_surface_with_anchor``
   immediately tracks it there (``CoordState.MATERIALIZED``) — the EMPTY-arm
   quiet-primary routing is a live, self-correcting reflection of on-disk
   state, never a cached/stale answer that could keep masking a write after
   one actually happens.

Fixture data mirrors ``tests/mission_runtime/test_placement_seam.py`` (real
git repo, real 26-char ULID ``mission_id``, canonical coordination-branch
naming via ``specify_cli.missions._create.coordination_branch_name`` —
realistic test data, no synthetic short IDs).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from mission_runtime import MissionArtifactKind, placement_seam
from specify_cli.coordination.surface_resolver import (
    resolve_status_surface,
    resolve_status_surface_with_anchor,
)
from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.missions._create import coordination_branch_name

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

# Production-shaped identity (Mission Identity Model 083+): a real 26-char ULID.
_MISSION_ID = "01KTDVJ2N8VZ0A5C1XKJH0Q9RB"
_MID8 = _MISSION_ID[:8]
_SLUG = f"solo-pr-bound-coord-mission-{_MID8}"
_TARGET_BRANCH = "main"
# The canonical naming seam (FR-010, no hand-rolled grammar).
_COORD_BRANCH = coordination_branch_name(_SLUG, _MISSION_ID)


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", _TARGET_BRANCH)
    _git(r, "config", "user.email", "solo-coord@example.test")
    _git(r, "config", "user.name", "Solo Coord Primary")
    _git(r, "config", "commit.gpgsign", "false")
    (r / ".kittify").mkdir()
    (r / ".kittify" / "config.yaml").write_text(
        "agents:\n  available:\n    - claude\n", encoding="utf-8"
    )
    return r


def _build_solo_pr_bound_coord_mission(repo_root: Path) -> Path:
    """Mint a solo PR-bound COORD-topology mission with a legitimately empty
    coordination worktree: no lanes, no coord-branch write ever happened.

    Mirrors the REAL create-time sequence (``core/mission_creation.py``):
    ``coordination_branch`` is minted off ``target_branch`` (#2581's frozen
    ``pr_bound -> COORD`` derivation) BEFORE the coord worktree is ever
    materialized, and the primary checkout commits ``meta.json`` +
    ``kitty-specs/<slug>/`` on ``target_branch`` — the coordination branch
    never receives a corresponding write. Returns the PRIMARY mission dir.
    """
    primary_dir = repo_root / "kitty-specs" / _SLUG
    primary_dir.mkdir(parents=True)
    meta: dict[str, object] = {
        "mission_id": _MISSION_ID,
        "mission_slug": _SLUG,
        "mission_type": "software-dev",
        "target_branch": _TARGET_BRANCH,
        "friendly_name": "Solo PR-bound coord mission",
        "topology": "coord",
        "coordination_branch": _COORD_BRANCH,
        "pr_bound": True,
    }
    (primary_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-q", "-m", "fixture: solo PR-bound coord mission")

    # Mint the coordination branch off the CURRENT target_branch tip (the real
    # ensure_coordination_branch contract) — it shares target_branch's commit
    # until something actually writes to it.
    _git(repo_root, "branch", _COORD_BRANCH)

    # Materialize the coord worktree ROOT only (mirrors BookkeepingTransaction
    # .acquire()'s CoordinationWorkspace.resolve() before append_event() ever
    # runs, and the existing coord-empty-warning fixture pattern) — the
    # kitty-specs/<slug> mission dir inside it is deliberately absent.
    coord_root = CoordinationWorkspace.worktree_path(repo_root, _SLUG, _MID8)
    coord_root.mkdir(parents=True)

    return primary_dir


def test_read_surface_resolves_primary(repo: Path) -> None:
    """Assertion 1: the READ authority resolves the legitimate-empty coord
    surface cleanly to PRIMARY (WP08 T029) — the same fixture T031/T032 pin
    the no-warning behaviour for in ``test_surface_resolver_coord_empty_
    warning.py``."""
    primary_dir = _build_solo_pr_bound_coord_mission(repo)

    resolved = resolve_status_surface_with_anchor(repo, _SLUG)

    assert resolved.read_dir.resolve() == primary_dir.resolve(), (
        "solo-empty coord must resolve READ to the PRIMARY checkout, not the "
        f"coord dir. Got: {resolved.read_dir}"
    )
    assert resolved.primary_anchor.resolve() == primary_dir.resolve()
    assert resolve_status_surface(repo, _SLUG).resolve() == (
        primary_dir / "status.events.jsonl"
    ).resolve()


def test_write_placement_ref_is_read_openly_not_masked(repo: Path) -> None:
    """Assertion 2: the WRITE placement authority is READ (never mutated) and
    its answer is pinned explicitly — proving WP08 does not silently ignore
    what the write side does while only patching the read side's noise."""
    _build_solo_pr_bound_coord_mission(repo)

    target = placement_seam(repo, _SLUG).write_target(MissionArtifactKind.STATUS_STATE)

    # Frozen, out-of-scope behaviour (status_transition.py's own docstring):
    # STATUS_STATE keeps resolving the coordination branch under COORD
    # topology regardless of on-disk materialization state — WP08 does not
    # touch this, and this test does not pretend otherwise.
    assert target.ref == _COORD_BRANCH, (
        "write placement must keep resolving the coordination branch for "
        f"COORD topology (frozen WP07-adjacent behaviour); got {target.ref!r}"
    )


def test_no_masking_coordination_branch_has_not_diverged(repo: Path) -> None:
    """Assertion 3: the coordination branch the write side names has NOT
    diverged from the primary branch the read side resolves — so falling
    back to PRIMARY cannot silently hide committed coordination-branch data.

    This is the concrete "do not mask a mismatch" proof (WP08's highest-
    listed risk): if the coordination branch carried ANY commit beyond
    ``target_branch``'s tip, this assertion would fail, flagging a REAL
    split-brain rather than the legitimate empty-before-first-write state.
    """
    _build_solo_pr_bound_coord_mission(repo)

    target_sha = _git(repo, "rev-parse", _TARGET_BRANCH)
    coord_sha = _git(repo, "rev-parse", _COORD_BRANCH)

    assert coord_sha == target_sha, (
        "the coordination branch must not have diverged from target_branch "
        "for the legitimate-empty case — a divergence here would mean the "
        "PRIMARY fallback is masking real coordination-branch data "
        f"(target={target_sha!r}, coord={coord_sha!r})"
    )


def test_read_tracks_write_once_coord_worktree_is_populated(repo: Path) -> None:
    """Assertion 4: the quiet-primary routing is a live reflection of on-disk
    state, not a sticky/cached answer — the moment a real write lands under
    the coord worktree (mirroring ``BookkeepingTransaction.append_event()``'s
    ``feature_dir.mkdir()``), reads track it there immediately. Reads can
    never permanently mask a write that has actually happened.
    """
    _build_solo_pr_bound_coord_mission(repo)

    # Sanity: still EMPTY -> PRIMARY before any write.
    pre_write = resolve_status_surface_with_anchor(repo, _SLUG)
    assert pre_write.read_dir.resolve() == (repo / "kitty-specs" / _SLUG).resolve()

    # Simulate the first real coordination-branch write materializing the
    # mission dir under the (already-rooted) coord worktree.
    coord_mission_dir = (
        CoordinationWorkspace.worktree_path(repo, _SLUG, _MID8)
        / "kitty-specs"
        / _SLUG
    )
    coord_mission_dir.mkdir(parents=True)
    (coord_mission_dir / "status.events.jsonl").write_text("", encoding="utf-8")

    post_write = resolve_status_surface_with_anchor(repo, _SLUG)

    assert post_write.read_dir.resolve() == coord_mission_dir.resolve(), (
        "once the coord worktree is populated, reads must track it "
        f"immediately (CoordState.MATERIALIZED) — got {post_write.read_dir}"
    )
