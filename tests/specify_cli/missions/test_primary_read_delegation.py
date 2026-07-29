"""WP03 T020 (WP08 T035 update): equivalence + divergence pins for the PRIMARY read seam.

Mission ``read-side-seam-primary-primitive-closure-01KYKMMT`` WP03 (Half B,
FR-003 / NFR-001 / NFR-002 / NFR-003). After T019, the (now-deleted, WP08
T035) public wrapper ``primary_feature_dir_for_mission`` delegated to
``mission_runtime.placement_seam(...).read_dir(PRIMARY_METADATA)`` instead of
composing the ``KITTY_SPECS_DIR`` join itself. This module proves that
delegation answer-preserving across the eight real-repo fixtures from
``quickstart.md`` §4, by comparing:

* the **blind composition** — the module-private leaf
  :func:`~specify_cli.missions._read_path_resolver._compose_primary_feature_dir`,
  which is the EXACT pre-T019 body of the (now-deleted) wrapper
  (topology-blind, handle-blind, no recovery); against
* the **seam's answer** — ``placement_seam(...).read_dir(PRIMARY_METADATA)``
  directly (:func:`_seam_read` below) — the ONLY spelling of "the topology-
  aware PRIMARY read" after WP08 deletes the wrapper it used to reach through.

Every divergence is attributed to exactly one of: **anchoring / backfill
recovery / husk / raising** (never absorbed silently). The single ACCEPTED
behavioural delta is the seam's bare-``<slug>`` backfill recovery (NFR-003) —
every other fixture must resolve IDENTICALLY, and a PRIMARY-partition kind
must never raise on husk / empty-coord / deleted-coord (NFR-002).

read-side-seam-primary-primitive-closure-01KYKMMT WP08 (T035): the wrapper
itself is deleted (SC-001), so the two tests whose ENTIRE subject was the
wrapper's own delegation identity/code-object (rather than the surviving
seam's behaviour) were DELETED per DIRECTIVE_041 (PATCHWORK — the shape they
pinned no longer exists to be pinned):

* ``test_backfill_recovery_pin_is_red_under_the_pre_delegation_wrapper_body``
  monkeypatched THIS module's own ``primary_feature_dir_for_mission`` binding
  to prove the backfill-recovery assertion above was genuinely falsifiable
  under the pre-delegation (Half A) body. With the wrapper gone there is no
  module-level binding left to revert or patch.
* ``test_read_dir_never_enters_the_public_wrapper_for_any_kind`` traced
  ``primary_feature_dir_for_mission.__code__`` via ``sys.setprofile`` to prove
  ``read_dir`` never re-entered the wrapper (the NFR-009 cycle WP03 closed).
  There is no wrapper code object left to trace, and the cycle it guarded
  against is now structurally impossible: every site that used to reach the
  wrapper either calls the seam directly (which never calls back to a
  deleted name) or calls the leaf directly (which imports no seam at all).

No resolver is patched anywhere in the equivalence fixtures below — every
scenario is a real git repository + real filesystem state (production-shaped
identities, per the project's NFR-003 test-data convention), built under
pytest's ``tmp_path`` (never a bare ``/tmp`` path).
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from mission_runtime import MissionArtifactKind, placement_seam
from specify_cli.missions._read_path_resolver import _compose_primary_feature_dir
from tests.specify_cli._read_seam_migration_fixtures import (
    build_coord_branch_deleted,
    build_coord_husk,
    build_coord_materialized,
    build_coord_worktree_empty,
    build_flat,
    coord_branch_name,
    coord_worktree_root,
    git_cmd as _git,
    make_git_repo,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# Production-shaped identity (NFR-003: no fabricated short ids).
_MISSION_ID = "01KYKMMTFC0000000000000001"
_MID8 = _MISSION_ID[:8]
_HUMAN_SLUG = "primary-read-delegation-fixture"
_COMPOSED = f"{_HUMAN_SLUG}-{_MID8}"


def _make_git_repo(tmp_path: Path, name: str) -> Path:
    """A minimal real git repo with the ``.kittify`` marker + ``kitty-specs/``."""
    return make_git_repo(
        tmp_path,
        name,
        user_email="wp03-fixture@spec-kitty.test",
        user_name="WP03 Fixture",
        readme_text="wp03 fixture repo\n",
    )


def _write_meta(
    feature_dir: Path,
    *,
    slug: str,
    mission_id: str,
    topology: str,
    coordination_branch: str | None,
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {
        "mission_id": mission_id,
        "mission_slug": slug,
        "slug": slug,
        "mission_type": "software-dev",
        "target_branch": "main",
        "vcs": "git",
        "topology": topology,
    }
    if coordination_branch is not None:
        meta["coordination_branch"] = coordination_branch
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


@dataclass(frozen=True)
class Fixture:
    repo: Path
    handle: str
    primary_dir: Path


# --------------------------------------------------------------------------- #
# Fixture builders — one per quickstart.md §4 row.
# --------------------------------------------------------------------------- #
def _primary_meta_writer(
    *, topology: str, coordination_branch: str | None
) -> Callable[[Path], None]:
    def _write(feature_dir: Path) -> None:
        _write_meta(
            feature_dir,
            slug=_COMPOSED,
            mission_id=_MISSION_ID,
            topology=topology,
            coordination_branch=coordination_branch,
        )

    return _write


def _flat_no_coord(tmp_path: Path) -> Fixture:
    repo = _make_git_repo(tmp_path, "flat")
    primary_dir = build_flat(
        repo,
        _COMPOSED,
        write_primary_meta=_primary_meta_writer(
            topology="single_branch", coordination_branch=None
        ),
    )
    return Fixture(repo=repo, handle=_COMPOSED, primary_dir=primary_dir)


def _coord_materialized(tmp_path: Path) -> Fixture:
    repo = _make_git_repo(tmp_path, "coord-materialized")
    branch = coord_branch_name(_COMPOSED)
    # Materialize the coord worktree dir + a mission dir WITH its own meta.json
    # (a genuinely populated coord side). Coord-state classification is pure
    # Path.exists() (probe_coord_state) — a real `git worktree add` checkout is
    # not required to exercise the on-disk shape it inspects.
    writer = _primary_meta_writer(topology="coord", coordination_branch=branch)
    primary_dir, _coord_mission_dir = build_coord_materialized(
        repo,
        _COMPOSED,
        branch,
        coord_worktree_root(repo, _COMPOSED),
        write_primary_meta=writer,
        write_coord_meta=writer,
    )
    return Fixture(repo=repo, handle=_COMPOSED, primary_dir=primary_dir)


def _coord_husk(tmp_path: Path) -> Fixture:
    """Coord worktree materialized, but its mission dir has NO meta.json (husk)."""
    repo = _make_git_repo(tmp_path, "coord-husk")
    branch = coord_branch_name(_COMPOSED)
    primary_dir = build_coord_husk(
        repo,
        _COMPOSED,
        branch,
        coord_worktree_root(repo, _COMPOSED),
        write_primary_meta=_primary_meta_writer(topology="coord", coordination_branch=branch),
    )
    return Fixture(repo=repo, handle=_COMPOSED, primary_dir=primary_dir)


def _coord_branch_deleted(tmp_path: Path) -> Fixture:
    """meta.json declares a coordination_branch that was never created in git."""
    repo = _make_git_repo(tmp_path, "coord-deleted")
    branch = coord_branch_name(_COMPOSED)  # deliberately never `git branch`-ed
    primary_dir = build_coord_branch_deleted(
        repo,
        _COMPOSED,
        branch,
        write_primary_meta=_primary_meta_writer(topology="coord", coordination_branch=branch),
    )
    return Fixture(repo=repo, handle=_COMPOSED, primary_dir=primary_dir)


def _coord_worktree_empty(tmp_path: Path) -> Fixture:
    """Coord root materialized (create window) but no mission dir under it yet."""
    repo = _make_git_repo(tmp_path, "coord-empty")
    branch = coord_branch_name(_COMPOSED)
    primary_dir = build_coord_worktree_empty(
        repo,
        _COMPOSED,
        branch,
        coord_worktree_root(repo, _COMPOSED),
        write_primary_meta=_primary_meta_writer(topology="coord", coordination_branch=branch),
    )
    return Fixture(repo=repo, handle=_COMPOSED, primary_dir=primary_dir)


def _mission_absent(tmp_path: Path) -> Fixture:
    repo = _make_git_repo(tmp_path, "absent")
    primary_dir = repo / "kitty-specs" / _COMPOSED  # never created
    return Fixture(repo=repo, handle=_COMPOSED, primary_dir=primary_dir)


def _backfilled(tmp_path: Path) -> tuple[Fixture, Path]:
    """Bare ``<slug>`` primary dir (no ``-<mid8>`` suffix); composed coord side.

    The defect this fixture exercises: the primary checkout was never
    backfilled to the composed ``<slug>-<mid8>`` name, but the coord side (and
    every caller's literal handle) already uses the composed form. Returns the
    fixture keyed on the COMPOSED handle plus the actual bare dir the seam must
    recover to.
    """
    repo = _make_git_repo(tmp_path, "backfilled")
    branch = f"kitty/mission-{_COMPOSED}"
    _git(repo, "branch", branch)
    bare_dir = repo / "kitty-specs" / _HUMAN_SLUG  # bare — no -<mid8> suffix
    _write_meta(
        bare_dir,
        slug=_HUMAN_SLUG,
        mission_id=_MISSION_ID,
        topology="coord",
        coordination_branch=branch,
    )
    # The composed dir name (what the blind literal join would compute) does
    # NOT exist on the primary side — that absence is the backfill defect.
    composed_dir = repo / "kitty-specs" / _COMPOSED
    assert not composed_dir.exists(), "backfill fixture invariant: composed dir absent"
    return Fixture(repo=repo, handle=_COMPOSED, primary_dir=composed_dir), bare_dir


def _seam_read(repo: Path, handle: str) -> Path:
    resolved: Path = placement_seam(repo, handle).read_dir(
        MissionArtifactKind.PRIMARY_METADATA
    )
    return resolved


# --------------------------------------------------------------------------- #
# T020 table — equal cells (7 of 8 fixtures).
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "builder",
    [
        _flat_no_coord,
        _coord_materialized,
        _coord_husk,
        _coord_branch_deleted,
        _coord_worktree_empty,
        _mission_absent,
    ],
    ids=[
        "flat_no_coord",
        "coord_materialized",
        "coord_husk",
        "coord_branch_deleted",
        "coord_worktree_empty",
        "mission_absent",
    ],
)
def test_seam_matches_blind_composition_for_materialized_or_absent_mission(
    tmp_path: Path, builder: object,
) -> None:
    """Anchoring: for every non-backfilled fixture the seam and the blind

    composition resolve the IDENTICAL directory (NFR-001) — and neither
    raises for a PRIMARY-partition kind, regardless of coord-side shape
    (NFR-002: no raise on husk / empty-coord / deleted-coord).
    """
    fx = builder(tmp_path)  # type: ignore[operator]
    blind = _compose_primary_feature_dir(fx.repo, fx.handle)
    seam = _seam_read(fx.repo, fx.handle)
    assert blind == seam == fx.primary_dir


def test_husk_primary_read_does_not_raise_and_resolves_primary_anchor(
    tmp_path: Path,
) -> None:
    """Explicit husk pin (T020 step 2): a PRIMARY-kind read on a husk mission

    resolves the primary anchor and does NOT raise — even though the coord
    worktree is materialized with no meta.json under its mission dir.
    """
    fx = _coord_husk(tmp_path)
    resolved = _seam_read(fx.repo, fx.handle)
    assert resolved == fx.primary_dir
    assert ".worktrees" not in str(resolved), (
        "a PRIMARY-partition read must never resolve into the coord husk"
    )


def test_deleted_coord_branch_does_not_raise_for_primary_kind(tmp_path: Path) -> None:
    """NFR-002: a COORD kind raises CoordinationBranchDeleted on this fixture

    (see the write-side / status-surface suites for that positive proof); a
    PRIMARY kind must not begin raising just because this mission's coord
    branch is gone.
    """
    fx = _coord_branch_deleted(tmp_path)
    resolved = _seam_read(fx.repo, fx.handle)
    assert resolved == fx.primary_dir


def test_repo_root_as_lane_worktree_is_checkout_invariant(tmp_path: Path) -> None:
    """A PRIMARY-partition read is CWD/checkout-invariant: calling with

    ``repo_root`` pointed at a lane worktree of the SAME repo resolves the
    identical directory as calling with the main checkout (C-CTX-2).
    """
    fx = _flat_no_coord(tmp_path)
    lane_branch = "kitty/mission-lane-a"
    _git(fx.repo, "branch", lane_branch)
    lane_worktree = fx.repo.parent / "lane-worktree"
    subprocess.run(
        ["git", "-C", str(fx.repo), "worktree", "add", str(lane_worktree), lane_branch],
        check=True,
        capture_output=True,
    )
    try:
        from_main = _seam_read(fx.repo, fx.handle)
        from_lane = _seam_read(lane_worktree, fx.handle)
        assert from_main == from_lane == fx.primary_dir
    finally:
        subprocess.run(
            ["git", "-C", str(fx.repo), "worktree", "remove", "--force", str(lane_worktree)],
            check=True,
            capture_output=True,
        )


# --------------------------------------------------------------------------- #
# T020 — the ONE accepted behavioural delta: backfill recovery.
# --------------------------------------------------------------------------- #
def test_backfill_recovery_is_the_one_accepted_divergence(tmp_path: Path) -> None:
    """Backfill recovery: the seam recovers the EXISTING bare-slug dir; the

    blind composition returns a path that does not exist (NFR-001's named
    exception). This is the mission's single accepted behavioural delta.
    """
    fx, bare_dir = _backfilled(tmp_path)

    blind = _compose_primary_feature_dir(fx.repo, fx.handle)
    seam = _seam_read(fx.repo, fx.handle)

    # The blind composition never recovers: it returns the non-existent
    # composed path verbatim.
    assert blind == fx.primary_dir
    assert not blind.exists()

    # The seam recovers the REAL, existing bare dir.
    assert seam == bare_dir
    assert seam.exists()
    assert seam != blind
