"""The ``accept`` birth-cutover COORD leg anchors on the surface seam's own answer.

``_stamp_birth_cutover_for_accept`` hands ``stamp_accept_cutover`` a ``status_feature_dir``
-- documented as "the COORD-partition mission directory, the seed event
write/verify anchor". It used to *re-compose* that directory: take the
coordination mission dir the surface seam already resolved, walk up to the
worktree root with ``git rev-parse --show-toplevel``, then re-join
``kitty-specs/<handle>`` onto it. The round trip is lossy in both directions --
it drops the seam's canonical ``<slug>-<mid8>`` dir name in favour of whatever
handle the caller happened to hold, and it fails soft to the PRIMARY dir
whenever the ``git`` call does not answer, writing the status seed onto the
wrong partition.

These tests pin the anchor to the seam's answer. They were RED before the
routing change (the re-composed join produced the handle-named dir, and the
git-free case produced ``None``) and need no git at all now.

Rationale for the ``KITTY_SPECS_DIR`` join's removal is architectural too:
``tests/architectural/test_no_raw_mission_spec_paths.py`` confines mission-spec
path assembly to a sanctioned constructor inventory, and a CLI command module is
not one. Consuming the seam is the fix that gate asks for -- not an allowlist row.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mission_runtime import (
    MissionArtifactKind,
    ResolvedSurface,
    TopologySurface,
)
from specify_cli.cli.commands import accept as accept_mod


_HANDLE = "demo-mission"
#: What the seam resolves to: the canonical ``<slug>-<mid8>`` dir, which is
#: deliberately NOT the handle the caller holds. A test whose two names agreed
#: could not tell the seam's answer from a re-composed join.
_CANONICAL_DIR_NAME = "demo-mission-01KYJGCQ"


@pytest.fixture
def surfaces(tmp_path: Path) -> dict[str, Path]:
    repo_root = tmp_path / "repo"
    coord_dir = repo_root / ".worktrees" / f"{_CANONICAL_DIR_NAME}-coord" / "kitty-specs" / _CANONICAL_DIR_NAME
    primary_dir = repo_root / "kitty-specs" / _CANONICAL_DIR_NAME
    coord_dir.mkdir(parents=True)
    primary_dir.mkdir(parents=True)
    return {"repo_root": repo_root, "coord": coord_dir, "primary": primary_dir}


def _install_stubs(
    monkeypatch: pytest.MonkeyPatch,
    surfaces: dict[str, Path],
    *,
    surface_kind: TopologySurface,
) -> list[Path | None]:
    """Stub the three seams around the COORD leg; capture the stamp's anchor."""
    import mission_runtime
    from specify_cli.migration import runtime_state_cutover

    monkeypatch.setattr(
        accept_mod, "primary_feature_dir_for_mission", lambda *_a, **_k: surfaces["primary"]
    )
    monkeypatch.setattr(accept_mod, "_canonicalize_primary_read_handle", lambda _r, h: h)
    monkeypatch.setattr(
        mission_runtime,
        "resolve_artifact_surface",
        lambda *_a, **_k: ResolvedSurface(path=surfaces["coord"], surface_kind=surface_kind),
    )

    captured: list[Path | None] = []

    def _stamp(_feature_dir: Path, *, status_feature_dir: Path | None = None) -> Any:
        captured.append(status_feature_dir)
        raise RuntimeError("stop after capture")  # absorbed by the best-effort guard

    monkeypatch.setattr(runtime_state_cutover, "stamp_accept_cutover", _stamp)
    return captured


def test_coord_stamp_anchor_is_the_seam_surface_dir(
    monkeypatch: pytest.MonkeyPatch, surfaces: dict[str, Path]
) -> None:
    """The seed anchor is the coordination mission dir the seam resolved.

    The ``git rev-parse`` the old code ran is stubbed to SUCCEED here, returning
    the correct worktree root -- so this test isolates the dir-*name* claim
    rather than riding on the git call. RED before the routing change even with
    a perfect git answer: re-joining the raw handle yielded
    ``<coord worktree>/kitty-specs/demo-mission``, the handle-named sibling of
    the real ``demo-mission-01KYJGCQ`` dir, a path that does not exist.
    """
    worktree_root = surfaces["coord"].parent.parent

    class _Completed:
        stdout = f"{worktree_root}\n"

    monkeypatch.setattr(accept_mod, "run_git", lambda *_a, **_k: _Completed())
    captured = _install_stubs(monkeypatch, surfaces, surface_kind=TopologySurface.COORD)

    accept_mod._stamp_birth_cutover_for_accept(surfaces["repo_root"], _HANDLE)

    assert captured == [surfaces["coord"]]


def test_coord_stamp_does_not_round_trip_through_git(
    monkeypatch: pytest.MonkeyPatch, surfaces: dict[str, Path]
) -> None:
    """The anchor comes straight off the seam -- no walk up to the worktree root.

    The structural half of the same fix: the seam already holds the mission dir,
    so the ``git rev-parse --show-toplevel`` round trip is not merely redundant,
    it is the failure mode (a non-answering ``git`` silently downgraded the seed
    write to the PRIMARY partition).
    """
    monkeypatch.setattr(
        accept_mod,
        "run_git",
        lambda *_a, **_k: pytest.fail("the COORD stamp leg must not shell out to git"),
    )
    captured = _install_stubs(monkeypatch, surfaces, surface_kind=TopologySurface.COORD)

    accept_mod._stamp_birth_cutover_for_accept(surfaces["repo_root"], _HANDLE)

    assert captured == [surfaces["coord"]]


def test_coord_stamp_anchor_is_none_off_the_coordination_surface(
    monkeypatch: pytest.MonkeyPatch, surfaces: dict[str, Path]
) -> None:
    """A non-COORD stamp means "no coordination partition" -- the anchor stays
    ``None`` so ``stamp_accept_cutover`` defaults it to the PRIMARY dir."""
    captured = _install_stubs(monkeypatch, surfaces, surface_kind=TopologySurface.PRIMARY)

    accept_mod._stamp_birth_cutover_for_accept(surfaces["repo_root"], _HANDLE)

    assert captured == [None]


def test_coord_mission_dir_propagates_a_deleted_coordination_branch(
    monkeypatch: pytest.MonkeyPatch, surfaces: dict[str, Path]
) -> None:
    """C3 fail-loud survives the extraction: a deleted coordination branch at
    accept time carries unmerged status, so the refusal must not be absorbed
    into a ``None`` the way ``coord_read_dir_for`` absorbs it."""
    import mission_runtime
    from specify_cli.coordination.surface_resolver import CoordinationBranchDeleted

    def _raise(*_a: object, **_k: object) -> ResolvedSurface:
        raise CoordinationBranchDeleted(
            repo_root=surfaces["repo_root"],
            mission_slug=_HANDLE,
            mid8="01KYJGCQ",
            coord_candidate=surfaces["coord"],
            primary_candidate=surfaces["primary"],
            coordination_branch="kitty/mission-demo-01KYJGCQ-coord",
        )

    monkeypatch.setattr(mission_runtime, "resolve_artifact_surface", _raise)

    with pytest.raises(CoordinationBranchDeleted):
        accept_mod._coord_mission_dir(surfaces["repo_root"], _HANDLE)


def test_unsafe_mission_handle_still_refuses_before_any_stamp(
    monkeypatch: pytest.MonkeyPatch, surfaces: dict[str, Path]
) -> None:
    """The traversal guard survives the removal of the call-site
    ``assert_safe_path_segment``.

    It was already redundant there: the surface seam canonicalizes the handle
    through ``primary_feature_dir_for_mission``, which applies the guard, and the
    seam runs first. This pins that the refusal is real rather than inherited
    from the deleted line -- the real seam is used here, unstubbed.
    """
    from specify_cli.migration import runtime_state_cutover

    monkeypatch.setattr(
        runtime_state_cutover,
        "stamp_accept_cutover",
        lambda *_a, **_k: pytest.fail("an unsafe handle must never reach the stamp"),
    )

    with pytest.raises(ValueError):
        accept_mod._coord_mission_dir(surfaces["repo_root"], "../escape")


def test_coord_mission_dir_asks_the_seam_for_the_acceptance_partition(
    monkeypatch: pytest.MonkeyPatch, surfaces: dict[str, Path]
) -> None:
    """The kind passed to the seam is what classifies the partition; pin it so a
    silent swap to a PRIMARY-partition kind (which always stamps PRIMARY, hence
    always yields ``None``) cannot quietly disable the whole COORD leg."""
    import mission_runtime

    seen: list[object] = []

    def _spy(_root: Path, _slug: str, kind: MissionArtifactKind, **_k: object) -> ResolvedSurface:
        seen.append(kind)
        return ResolvedSurface(path=surfaces["coord"], surface_kind=TopologySurface.COORD)

    monkeypatch.setattr(mission_runtime, "resolve_artifact_surface", _spy)

    assert accept_mod._coord_mission_dir(surfaces["repo_root"], _HANDLE) == surfaces["coord"]
    assert seen == [MissionArtifactKind.ACCEPTANCE_MATRIX]
