"""WP07 T033: behaviour-preservation + backfill-recovery pins for
``status/aggregate.py::MissionStatus._find_meta_path`` and ``MissionStatus.save``.

Mission ``read-side-seam-primary-primitive-closure-01KYKMMT`` WP07 (FR-001 /
FR-004 / NFR-001). ``_find_meta_path`` routed 2 of its 3 ``primary_feature_dir_
for_mission`` sites (``:499``, ``:543``) through ``placement_seam(...).
read_dir(MissionArtifactKind.PRIMARY_METADATA)``; ``save()``'s diagnostic-path
site was routed identically. The third site (``bare_dir_name = resolve_bare_
modern_mission_dir_name(...)``) is deliberately left calling the deprecated
wrapper — see the in-code rationale and the WP07 handoff report for why (a
PERMANENT canonicalizer-gate allow-list fixture predating this mission).

Since ``primary_feature_dir_for_mission`` already delegates to
``placement_seam(...).read_dir(PRIMARY_METADATA)`` (WP03 T019), routing a call
site to the seam directly is behaviourally a no-op TODAY — these tests exist to
PIN that equivalence (NFR-001) so a future change to either the wrapper or the
routed call sites cannot silently diverge, and to prove the ``:543``
backfill-recovery case (T033(b), US3 scenario 3) resolves an EXISTING
directory rather than a composed-but-absent one.

No resolver is patched — every scenario is a real git repository + real
filesystem state (production-shaped identities, NFR-003's test-data
convention), built under pytest's ``tmp_path``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.missions._read_path_resolver import _compose_primary_feature_dir
from specify_cli.status.aggregate import MissionStatus

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# Production-shaped identity (NFR-003: no fabricated short ids).
_MISSION_ID = "01KYKMMTWP070000000000001"
_MID8 = _MISSION_ID[:8]
_HUMAN_SLUG = "aggregate-seam-migration-fixture"
_COMPOSED = f"{_HUMAN_SLUG}-{_MID8}"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _make_git_repo(tmp_path: Path, name: str) -> Path:
    repo = tmp_path / name
    repo.mkdir(parents=True)
    subprocess.run(
        ["git", "init", "-b", "main", str(repo)], check=True, capture_output=True
    )
    _git(repo, "config", "user.email", "wp07-fixture@spec-kitty.test")
    _git(repo, "config", "user.name", "WP07 Fixture")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / ".kittify").mkdir()
    (repo / "kitty-specs").mkdir()
    (repo / "README.md").write_text("wp07 fixture repo\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")
    return repo


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


# --------------------------------------------------------------------------- #
# NFR-001 — identical directory for a materialized, non-backfilled mission.
# --------------------------------------------------------------------------- #
def test_find_meta_path_materialized_mission_resolves_identical_directory(
    tmp_path: Path,
) -> None:
    """The routed ``:499`` leg resolves the SAME primary dir the historical
    blind composition would have (NFR-001 baseline — no behaviour change for
    the common, non-backfilled case)."""
    repo = _make_git_repo(tmp_path, "flat")
    primary_dir = repo / "kitty-specs" / _COMPOSED
    _write_meta(
        primary_dir,
        slug=_COMPOSED,
        mission_id=_MISSION_ID,
        topology="single_branch",
        coordination_branch=None,
    )

    meta_path, resolved_primary_dir = MissionStatus._find_meta_path(repo, _COMPOSED)

    blind = _compose_primary_feature_dir(repo, _COMPOSED)
    assert resolved_primary_dir == blind == primary_dir
    assert meta_path == primary_dir / "meta.json"
    assert meta_path.exists()


# --------------------------------------------------------------------------- #
# T033(b) / US3 scenario 3 — the ``:543`` ``.name`` backfill-recovery pin.
# --------------------------------------------------------------------------- #
def test_find_meta_path_backfilled_mission_resolves_existing_bare_dir(
    tmp_path: Path,
) -> None:
    """A backfilled mission (bare ``<slug>`` primary dir on disk, composed
    ``<slug>-<mid8>`` coord side) must resolve to the EXISTING bare dir when
    queried with the COMPOSED handle -- never a non-existent composed path.

    ``:543`` (``canonical_primary = placement_seam(repo_root,
    candidate_dir.name).read_dir(PRIMARY_METADATA)``) is reached when the
    literal-slug happy path (``:499``/``raw_meta.exists()``) and the
    bare-modern-slug leg (``:522``, ``resolve_bare_modern_mission_dir_name``)
    both miss and ``candidate_feature_dir_for_mission`` resolves a dir whose
    ``.name`` is the COMPOSED form (e.g. because the coord worktree, not the
    primary checkout, was materialized under the composed name). Forcing this
    exact leg directly (bypassing the two earlier short-circuits) is the only
    way to exercise ``:543`` deterministically; calling the public
    ``MissionStatus._find_meta_path`` end-to-end on this fixture would return
    via the bare-modern-slug leg (``:522``) first, since
    ``resolve_bare_modern_mission_dir_name`` ALSO resolves the bare dir for a
    composed-looking bare human slug lookup -- proving the earlier legs are
    already correct is not what this test is for.
    """
    repo = _make_git_repo(tmp_path, "backfilled")
    branch = f"kitty/mission-{_COMPOSED}"
    _git(repo, "branch", branch)
    bare_dir = repo / "kitty-specs" / _HUMAN_SLUG  # bare -- no -<mid8> suffix
    _write_meta(
        bare_dir,
        slug=_HUMAN_SLUG,
        mission_id=_MISSION_ID,
        topology="coord",
        coordination_branch=branch,
    )
    composed_dir = repo / "kitty-specs" / _COMPOSED
    assert not composed_dir.exists(), "backfill fixture invariant: composed dir absent"

    # RED-FIRST evidence (DIRECTIVE_041): the historical blind composition
    # (the exact pre-WP03 body of ``primary_feature_dir_for_mission``, still
    # the module-private leaf today) returns the literal composed dir --
    # which does NOT exist. This is exactly the bug T033(b) closes; asserting
    # it here proves the fixture actually exercises the divergence rather
    # than vacuously matching by construction.
    blind = _compose_primary_feature_dir(repo, _COMPOSED)
    assert blind == composed_dir
    assert not blind.exists(), (
        "sanity check failed: the blind composition was expected to resolve "
        "a non-existent composed dir for a backfilled mission"
    )

    # The routed ``:543`` call shape, exercised directly: candidate_dir.name
    # is the COMPOSED form (mirroring a coord-worktree candidate whose dir
    # name already carries the mid8 suffix).
    from mission_runtime import MissionArtifactKind, placement_seam

    resolved = placement_seam(repo, _COMPOSED).read_dir(
        MissionArtifactKind.PRIMARY_METADATA
    )
    assert resolved == bare_dir
    assert resolved.exists(), (
        "the seam must recover the EXISTING bare-slug primary dir for a "
        "backfilled mission, never a non-existent composed path (NFR-001's "
        "one accepted divergence, US3 scenario 3)"
    )
    assert (resolved / "meta.json").exists()


# --------------------------------------------------------------------------- #
# NFR-002 — no new raise on husk / empty coord / deleted coord branch.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "coord_shape",
    ["husk", "branch_deleted", "worktree_empty"],
)
def test_find_meta_path_never_raises_coordination_branch_deleted(
    tmp_path: Path, coord_shape: str,
) -> None:
    """A PRIMARY-partition read must never raise ``CoordinationBranchDeleted``
    regardless of the coord side's shape (NFR-002) -- ``_find_meta_path``'s
    routed legs only ever request ``PRIMARY_METADATA``, which the seam
    resolves for every topology/coord state without a coord probe."""
    repo = _make_git_repo(tmp_path, f"coord-{coord_shape}")
    primary_dir = repo / "kitty-specs" / _COMPOSED
    branch = f"kitty/mission-{_COMPOSED}"
    if coord_shape != "branch_deleted":
        _git(repo, "branch", branch)
    _write_meta(
        primary_dir,
        slug=_COMPOSED,
        mission_id=_MISSION_ID,
        topology="coord",
        coordination_branch=branch,
    )
    if coord_shape == "husk":
        coord_root = repo / ".worktrees" / f"{_COMPOSED}-coord"
        coord_mission_dir = coord_root / "kitty-specs" / _COMPOSED
        coord_mission_dir.mkdir(parents=True)
        (coord_mission_dir / "status.events.jsonl").write_text("", encoding="utf-8")
    elif coord_shape == "worktree_empty":
        coord_root = repo / ".worktrees" / f"{_COMPOSED}-coord"
        coord_root.mkdir(parents=True)

    meta_path, resolved_primary_dir = MissionStatus._find_meta_path(repo, _COMPOSED)

    assert resolved_primary_dir == primary_dir
    assert meta_path == primary_dir / "meta.json"
    assert meta_path.exists()
