"""Regression: ``resolve_artifact_surface`` on a BACKFILLED mission (bare primary dir).

The read-seam migration replaced the lenient ``candidate_feature_dir_for_mission``
leg with ``resolve_planning_read_dir(..., PRIMARY_METADATA)``, which
LITERAL-COMPOSES ``<slug>-<mid8>``. For a **backfilled** mission — primary dir on
disk carries the BARE ``<slug>`` while the coord worktree carries the composed
``<slug>-<mid8>`` — an already-composed handle produced a ``primary_dir`` that does
not exist. ``declared_read_surface`` then found no ``meta.json``, read no topology,
and short-circuited to ``PRIMARY`` before ``probe_coord_state`` ran, so the seam
answered a path that is **not on disk** — a silent wrong answer.

The load-bearing property these tests pin is **idempotence under the seam's own
output**: feeding ``read_dir(kind)`` the canonical name it just produced must return
the same path. The pre-existing ``_build_deleted_coord_mission`` fixtures only ever
build the composed-primary shape, which is exactly why this class slipped through.

Real git repo (``probe_coord_state`` shells out to ``git rev-parse``), hence the
``git_repo`` marker.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from mission_runtime.artifacts import MissionArtifactKind, TopologySurface
from mission_runtime.resolution import _backfilled_primary_dir, resolve_artifact_surface

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


MISSION_ID = "01KV8NPCDEBBIE0REPRO0COORD"
MID8 = MISSION_ID[:8]  # "01KV8NPC"
SLUG = f"backfilled-coord-repro-{MID8.lower()}"
COMPOSED = f"{SLUG}-{MID8}"
COORD_BRANCH = f"kitty/mission-{SLUG}-coord"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _write_meta(mission_dir: Path, *, mission_id: str, slug: str) -> None:
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": mission_id,
                "mission_slug": slug,
                "coordination_branch": COORD_BRANCH,
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture()
def backfilled_coord_repo(tmp_path: Path) -> Path:
    """The backfilled shape: BARE primary dir + COMPOSED materialized coord dir.

    Deliberately NOT the PR's ``_build_deleted_coord_mission`` helper, which only
    builds the composed-primary shape and therefore cannot observe this defect.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    _git(repo, "config", "user.email", "t@t.invalid")
    _git(repo, "config", "user.name", "t")
    (repo / ".kittify").mkdir(parents=True, exist_ok=True)

    # Primary dir: BARE name (the backfill signature — no ``-<mid8>`` tail).
    _write_meta(repo / "kitty-specs" / SLUG, mission_id=MISSION_ID, slug=SLUG)
    # Coord worktree: COMPOSED name, materialized on disk.
    _write_meta(
        repo / ".worktrees" / f"{COMPOSED}-coord" / "kitty-specs" / COMPOSED,
        mission_id=MISSION_ID,
        slug=SLUG,
    )
    return repo


def _expected_coord_dir(repo: Path) -> Path:
    return repo / ".worktrees" / f"{COMPOSED}-coord" / "kitty-specs" / COMPOSED


@pytest.mark.parametrize("handle", [SLUG, COMPOSED], ids=["bare", "composed"])
def test_status_read_resolves_coord_dir_for_both_handle_forms(
    backfilled_coord_repo: Path, handle: str
) -> None:
    """BOTH handle forms must land on the materialized coord dir that EXISTS.

    Pre-fix, the composed handle answered ``kitty-specs/<slug>-<mid8>`` stamped
    PRIMARY — a path that is not on disk.
    """
    resolved = resolve_artifact_surface(
        backfilled_coord_repo, handle, MissionArtifactKind.STATUS_STATE
    )

    assert resolved.path == _expected_coord_dir(backfilled_coord_repo)
    assert resolved.surface_kind is TopologySurface.COORD
    assert resolved.path.is_dir(), "seam returned a path that does not exist on disk"


def test_seam_is_idempotent_under_its_own_canonical_output(
    backfilled_coord_repo: Path,
) -> None:
    """``read_dir`` fed the canonical name it produced returns the SAME path."""
    first = resolve_artifact_surface(
        backfilled_coord_repo, SLUG, MissionArtifactKind.STATUS_STATE
    )
    # Feed the seam the mission-dir NAME it just emitted.
    second = resolve_artifact_surface(
        backfilled_coord_repo, first.path.name, MissionArtifactKind.STATUS_STATE
    )

    assert second.path == first.path
    assert second.surface_kind is first.surface_kind


def test_primary_partition_read_lands_on_the_bare_primary_dir(
    backfilled_coord_repo: Path,
) -> None:
    """A PRIMARY-partition kind resolves the EXISTING bare primary dir for both forms.

    The same defect in its second mask: pre-fix the composed handle answered the
    literal-composed ``kitty-specs/<slug>-<mid8>``, which is not on disk either.
    """
    for handle in (SLUG, COMPOSED):
        resolved = resolve_artifact_surface(
            backfilled_coord_repo, handle, MissionArtifactKind.PRIMARY_METADATA
        )
        assert resolved.path == backfilled_coord_repo / "kitty-specs" / SLUG
        assert resolved.surface_kind is TopologySurface.PRIMARY


def test_recovery_declines_a_coincidental_mid8_shaped_tail(
    backfilled_coord_repo: Path,
) -> None:
    """Identity confirmation: an unrelated 8-Crockford-char tail is NOT un-composed.

    ``mid8_from_slug`` is an explicitly heuristic tail detector. The recovery leg
    must confirm the stripped tail against the mission's DECLARED mid8, or it would
    trade one silent wrong answer for another.
    """
    bogus = f"{SLUG}-0ZZZZZZZ"  # well-formed mid8 shape, wrong identity
    composed_dir = backfilled_coord_repo / "kitty-specs" / bogus

    assert (
        _backfilled_primary_dir(
            backfilled_coord_repo, bogus, composed_dir, resolver=None
        )
        is None
    )


def test_recovery_is_a_noop_when_the_composed_primary_dir_exists(
    tmp_path: Path,
) -> None:
    """The ordinary (non-backfilled) shape must not be rewritten."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    _git(repo, "config", "user.email", "t@t.invalid")
    _git(repo, "config", "user.name", "t")
    composed_dir = repo / "kitty-specs" / COMPOSED
    _write_meta(composed_dir, mission_id=MISSION_ID, slug=SLUG)

    assert (
        _backfilled_primary_dir(repo, COMPOSED, composed_dir, resolver=None) is None
    )


def test_recovery_declines_a_handle_with_no_mid8_tail(
    backfilled_coord_repo: Path,
) -> None:
    """No parseable mid8 tail → nothing to un-compose, caller's answer stands."""
    missing = backfilled_coord_repo / "kitty-specs" / "no-tail-here"

    assert (
        _backfilled_primary_dir(
            backfilled_coord_repo, "no-tail-here", missing, resolver=None
        )
        is None
    )
