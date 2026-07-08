"""Unit tests for the placement seam (coord-primary-partition-lock WP01, T003).

The seam (``mission_runtime.placement_seam`` -> :class:`PlacementSeam`) is the
single kind-aware public authority over the existing ``resolve_action_context``
derivation root (contracts/seam-api.md): ``write_target(kind)`` projects
:func:`~mission_runtime.resolve_placement_only`; ``read_dir(kind)`` projects
:func:`~specify_cli.missions._read_path_resolver.resolve_planning_read_dir` for
every kind EXCEPT ``RETROSPECTIVE``, which routes to the dedicated single
authority :func:`~specify_cli.retrospective.writer.resolve_retrospective_home`
(squad finding H-1).

These tests pin:

* **T003** — the full 2x2 :class:`MissionTopology` grid x all 14
  :class:`MissionArtifactKind` members resolve partition-correct for BOTH
  projections (data-model.md Invariant P-1: the two partitions are disjoint
  and jointly exhaustive over the 14 members).
* **T002 (P-1)** — :func:`mission_runtime.artifacts.assert_partition_invariant`
  detects a corrupted partition (overlap or gap) and gates seam construction.
* **T002 (T-1)** — the seam's own source never inlines a
  ``topology == MissionTopology.COORD`` / ``coordination_branch is not None``
  check; coord-routing flows ONLY through the delegated resolvers' use of
  :func:`~mission_runtime.routes_through_coordination`.
* **H-1** — ``read_dir(RETROSPECTIVE)`` calls ``resolve_retrospective_home``
  and NEVER ``resolve_planning_read_dir`` (a parallel RETROSPECTIVE home would
  duplicate the single authority and fail its own dedicated structural test,
  ``tests/retrospective/test_home_resolution_single_authority.py``).

Fixture data uses a real 26-char ULID ``mission_id`` and the derived 8-char
``mid8`` so the resolver exercises real-shaped identity (realistic test data),
mirroring ``tests/mission_runtime/test_artifact_partition.py``.
"""
from __future__ import annotations

import inspect
import json
import subprocess
from pathlib import Path

import pytest

from mission_runtime import (
    CommitTarget,
    MissionArtifactKind,
    MissionTopology,
    is_primary_artifact_kind,
    placement_seam,
    routes_through_coordination,
)
from mission_runtime.artifacts import (
    _PLACEMENT_ARTIFACT_KINDS,
    _PRIMARY_ARTIFACT_KINDS,
    assert_partition_invariant,
)
from mission_runtime.resolution import PlacementSeam

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

# Realistic identity: a real 26-char Crockford ULID and its 8-char mid8 prefix
# (mirrors the mission's own identity shape).
_MISSION_ID = "01KWZ46V5P3QY7M8N0RAB4CDEF"
_MID8 = _MISSION_ID[:8]
_MISSION_SLUG = f"coord-primary-partition-lock-{_MID8}"
_TARGET_BRANCH = "design/coord-primary-partition-lock"
# A real-shaped coordination ref: ``kitty/mission-<slug>-<mid8>``.
_COORD_BRANCH = f"kitty/mission-{_MISSION_SLUG}-{_MID8}"

_ALL_TOPOLOGIES = (
    MissionTopology.SINGLE_BRANCH,
    MissionTopology.LANES,
    MissionTopology.COORD,
    MissionTopology.LANES_WITH_COORD,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "Test")
    _git(r, "config", "commit.gpgsign", "false")
    (r / ".kittify").mkdir()
    (r / ".kittify" / "config.yaml").write_text(
        "agents:\n  available:\n    - claude\n", encoding="utf-8"
    )
    return r


def _build_mission(repo_root: Path, *, topology: MissionTopology) -> Path:
    """Build a mission whose STORED topology is ``topology`` (data-model.md T-2).

    ``topology`` is written explicitly to ``meta.json`` so ``read_topology``
    honours the stored value directly rather than deriving it from
    ``(coordination_branch, has_lanes)`` — a real backfilled mission carries an
    explicit stored value, and this sidesteps needing a genuine ``lanes.json``
    to exercise the ``LANES`` / ``LANES_WITH_COORD`` cells.

    For a coord-routing topology, also declares the branch AND materializes the
    coordination-worktree mission dir on disk (a plain directory suffices — the
    read-path primitive is pure-path, ``Path.exists()`` stats only) so
    ``read_dir`` for a coordination-partition kind resolves the coord surface
    rather than the transient create-window primary fallback (#1718 KEEP).

    Returns the primary feature dir.
    """
    from specify_cli.missions._read_path_resolver import coord_feature_dir

    feature_dir = repo_root / "kitty-specs" / _MISSION_SLUG
    feature_dir.mkdir(parents=True)
    meta: dict[str, object] = {
        "mission_id": _MISSION_ID,
        "mission_slug": _MISSION_SLUG,
        "mission_type": "software-dev",
        "target_branch": _TARGET_BRANCH,
        "friendly_name": "Coord/primary partition lock",
        "topology": topology.value,
    }
    if routes_through_coordination(topology):
        meta["coordination_branch"] = _COORD_BRANCH
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (feature_dir / "tasks").mkdir()
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-q", "-m", "fixture")

    if routes_through_coordination(topology):
        _git(repo_root, "branch", _COORD_BRANCH)
        coord_dir = coord_feature_dir(repo_root, _MISSION_SLUG, _MID8)
        coord_dir.mkdir(parents=True)
        (coord_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    return feature_dir


# ---------------------------------------------------------------------------
# T003 -- 2x2 topology grid x all 14 MissionArtifactKind members
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("topology", _ALL_TOPOLOGIES, ids=lambda t: t.value)
@pytest.mark.parametrize("kind", list(MissionArtifactKind), ids=lambda k: k.value)
def test_write_target_lands_partition_correct(
    repo: Path, topology: MissionTopology, kind: MissionArtifactKind
) -> None:
    """``write_target(kind)`` lands on the primary ref, or coord ref when routed.

    Primary kinds always land on ``target_branch`` (every topology, INV-5
    symmetry). Coordination kinds land on the coordination ref ONLY when the
    topology routes through coordination; otherwise they too fall back to
    ``target_branch`` (the coord-less cells have no primary<->coordination
    split, C-001).
    """
    _build_mission(repo, topology=topology)
    seam = placement_seam(repo, _MISSION_SLUG)

    result = seam.write_target(kind)

    if is_primary_artifact_kind(kind) or not routes_through_coordination(topology):
        assert result == CommitTarget(ref=_TARGET_BRANCH), (kind.value, topology.value)
    else:
        assert result == CommitTarget(ref=_COORD_BRANCH), (kind.value, topology.value)


@pytest.mark.parametrize("topology", _ALL_TOPOLOGIES, ids=lambda t: t.value)
@pytest.mark.parametrize("kind", list(MissionArtifactKind), ids=lambda k: k.value)
def test_read_dir_lands_partition_correct(
    repo: Path, topology: MissionTopology, kind: MissionArtifactKind
) -> None:
    """``read_dir(kind)`` resolves the primary dir, or coord dir when routed.

    Primary kinds (including ``RETROSPECTIVE``, H-1) always resolve the
    primary feature dir for every topology. Coordination kinds resolve the
    materialized coordination-worktree mission dir ONLY when the topology
    routes through coordination; the coord-less cells have no split, so they
    resolve primary too.
    """
    primary_dir = _build_mission(repo, topology=topology)
    seam = placement_seam(repo, _MISSION_SLUG)

    result = seam.read_dir(kind)

    if is_primary_artifact_kind(kind) or not routes_through_coordination(topology):
        assert result == primary_dir, (kind.value, topology.value)
    else:
        from specify_cli.missions._read_path_resolver import coord_feature_dir

        assert result == coord_feature_dir(repo, _MISSION_SLUG, _MID8), (
            kind.value,
            topology.value,
        )
        assert result != primary_dir, (kind.value, topology.value)


# ---------------------------------------------------------------------------
# H-1 -- RETROSPECTIVE delegates to resolve_retrospective_home, never a
# second computed home (squad finding; single-authority guard).
# ---------------------------------------------------------------------------


def test_read_dir_retrospective_delegates_to_resolve_retrospective_home(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``read_dir(RETROSPECTIVE)`` calls the dedicated home authority, not the
    generic planning-read seam — computing a second RETROSPECTIVE home here
    would violate the single-authority contract H-1 relies on."""
    primary_dir = _build_mission(repo, topology=MissionTopology.SINGLE_BRANCH)

    import specify_cli.missions._read_path_resolver as read_path_resolver_mod
    import specify_cli.retrospective.writer as writer_mod

    calls: list[tuple[Path, str]] = []
    original_home = writer_mod.resolve_retrospective_home

    def _spy_home(repo_root: Path, mission_slug: str) -> Path:
        calls.append((repo_root, mission_slug))
        home: Path = original_home(repo_root, mission_slug)
        return home

    def _forbidden(*_args: object, **_kwargs: object) -> Path:
        raise AssertionError(
            "H-1 violated: read_dir(RETROSPECTIVE) called resolve_planning_read_dir "
            "— it must delegate to resolve_retrospective_home only."
        )

    monkeypatch.setattr(writer_mod, "resolve_retrospective_home", _spy_home)
    monkeypatch.setattr(read_path_resolver_mod, "resolve_planning_read_dir", _forbidden)

    seam = placement_seam(repo, _MISSION_SLUG)
    result = seam.read_dir(MissionArtifactKind.RETROSPECTIVE)

    assert calls == [(repo, _MISSION_SLUG)]
    assert result == primary_dir


def test_read_dir_non_retrospective_uses_resolve_planning_read_dir(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-RETROSPECTIVE kind routes through ``resolve_planning_read_dir`` —
    the RETROSPECTIVE special-case does not silently swallow every kind."""
    _build_mission(repo, topology=MissionTopology.SINGLE_BRANCH)

    import specify_cli.retrospective.writer as writer_mod

    def _forbidden(*_args: object, **_kwargs: object) -> Path:
        raise AssertionError(
            "resolve_retrospective_home must only be called for RETROSPECTIVE."
        )

    monkeypatch.setattr(writer_mod, "resolve_retrospective_home", _forbidden)

    seam = placement_seam(repo, _MISSION_SLUG)
    result = seam.read_dir(MissionArtifactKind.SPEC)

    assert result == repo / "kitty-specs" / _MISSION_SLUG


# ---------------------------------------------------------------------------
# T002 -- P-1 partition invariant (disjoint + total)
# ---------------------------------------------------------------------------


def test_assert_partition_invariant_passes_for_the_real_partition() -> None:
    """The production partition is disjoint and jointly exhaustive today."""
    assert_partition_invariant()  # must not raise


def test_assert_partition_invariant_detects_overlap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A kind classified in BOTH partitions fails loud (the double-classify bug)."""
    import mission_runtime.artifacts as artifacts_mod

    overlapping = frozenset(_PRIMARY_ARTIFACT_KINDS | {MissionArtifactKind.STATUS_STATE})
    monkeypatch.setattr(artifacts_mod, "_PRIMARY_ARTIFACT_KINDS", overlapping)

    with pytest.raises(AssertionError, match="P-1 violated"):
        assert_partition_invariant()


def test_assert_partition_invariant_detects_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    """A kind classified in NEITHER partition fails loud (the future-kind bug)."""
    import mission_runtime.artifacts as artifacts_mod

    shrunk = frozenset(_PLACEMENT_ARTIFACT_KINDS - {MissionArtifactKind.STATUS_STATE})
    monkeypatch.setattr(artifacts_mod, "_PLACEMENT_ARTIFACT_KINDS", shrunk)

    with pytest.raises(AssertionError, match="P-1 violated"):
        assert_partition_invariant()


def test_placement_seam_asserts_partition_invariant_at_construction(
    monkeypatch: pytest.MonkeyPatch, repo: Path
) -> None:
    """``placement_seam()`` runs the P-1 guard before returning (T002 wiring)."""
    import mission_runtime.resolution as resolution_mod

    def _boom() -> None:
        raise AssertionError("P-1 violated: injected for this test")

    monkeypatch.setattr(resolution_mod, "assert_partition_invariant", _boom)

    with pytest.raises(AssertionError, match="P-1 violated"):
        placement_seam(repo, _MISSION_SLUG)


# ---------------------------------------------------------------------------
# T002 -- T-1 (coord-routing binds to routes_through_coordination only; the
# seam itself never inlines a topology == COORD / coordination_branch is not
# None check).
# ---------------------------------------------------------------------------


def test_seam_never_inlines_coord_topology_equality() -> None:
    """The seam's own source never restates the coord-routing predicate inline.

    Coord-routing decisions are made ONLY by the delegated leaf resolvers via
    :func:`routes_through_coordination` over the stored topology — the seam
    forwards ``kind`` and lets the existing authority decide (data-model.md
    Invariant T-1 / C-001).
    """
    source = inspect.getsource(PlacementSeam) + "\n" + inspect.getsource(placement_seam)
    forbidden = (
        "== MissionTopology.COORD",
        "is MissionTopology.COORD",
        "coordination_branch is not None",
        "coordination_branch is None",
    )
    for pattern in forbidden:
        assert pattern not in source, f"T-1 violated: seam source inlines {pattern!r}"


# ---------------------------------------------------------------------------
# Kind is a required positional argument -- no silent default kind.
# ---------------------------------------------------------------------------


def test_write_target_requires_kind(repo: Path) -> None:
    _build_mission(repo, topology=MissionTopology.SINGLE_BRANCH)
    seam = placement_seam(repo, _MISSION_SLUG)

    with pytest.raises(TypeError):
        seam.write_target()  # type: ignore[call-arg]


def test_read_dir_requires_kind(repo: Path) -> None:
    _build_mission(repo, topology=MissionTopology.SINGLE_BRANCH)
    seam = placement_seam(repo, _MISSION_SLUG)

    with pytest.raises(TypeError):
        seam.read_dir()  # type: ignore[call-arg]
