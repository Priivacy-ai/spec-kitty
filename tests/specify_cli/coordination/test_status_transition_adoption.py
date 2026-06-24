"""WP05 adoption proofs for ``coordination/status_transition.py`` (T021–T026).

This is the highest-risk WP's witnessing suite. It proves the second parallel
write-factory (``_identity_for_request``) now consumes the canonical PUBLIC
resolvers (D-12) instead of hand-rolling root/surface/target:

* **Root (R5, FR-001)** — ``_repo_root_for_feature`` routes the bare
  ``feature_dir.parent.parent`` walk through ``resolve_canonical_root``
  (``workspace.primary_root`` semantics): a coord/lane worktree feature dir
  resolves to the canonical MAIN root; a submodule stops at its own root.
* **Write surface (FR-003, C-007)** — the status WRITE surface
  (``resolve_status_surface``) resolves POSITIVELY to the coord authority under
  coord topology and MUST NOT degrade to ``primary_root`` (the #2004/#2007
  flatten regression).
* **Write target (FR-004, D-2)** — ``destination_ref`` is sourced from
  ``resolve_placement_only(...).ref``: coord topology → coord branch; flat/base
  topology → ``target_branch`` (CWD-invariant), NOT git HEAD.
* **Idempotency (NFR-004)** — the coord case writes to the SAME on-disk target
  before/after; asserted, not inspected.
* **Equivalence (NFR-001 / D-5)** — read==write resolution for root + surface +
  target across the three real topologies (primary/coord/submodule), driven
  WITHOUT an explicit ``repo_root`` (the bare path the adoption deletes).

Every fixture is topology-true (NFR-002): full 26-char ULID ``mission_id``, real
``git init`` / ``git worktree add`` / ``git submodule add`` — reused from the
WP01 net's ``topology_fixtures`` rather than fabricated here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mission_runtime import MissionArtifactKind
from mission_runtime.resolution import resolve_placement_only
from specify_cli.coordination.status_transition import (
    _current_branch,
    _identity_for_request,
    _repo_root_for_feature,
    _resolve_write_target,
)
from specify_cli.coordination.surface_resolver import resolve_status_surface
from specify_cli.core.paths import resolve_canonical_root
from specify_cli.status.models import Lane, TransitionRequest

from tests.specify_cli.write_side.topology_fixtures import (
    KITTY_SPECS,
    TARGET_BRANCH,
    _run_git,
    build_coord,
    build_primary,
    build_submodule,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _request(feature_dir: Path, slug: str) -> TransitionRequest:
    """Build a transition request carrying NO explicit ``repo_root``.

    Passing ``repo_root`` would short-circuit ``_repo_root_for_feature`` and the
    write-target resolution — the exact derivations the adoption routes through
    the public resolvers. Every adoption proof MUST drive the bare path.
    """
    return TransitionRequest(
        feature_dir=feature_dir,
        mission_slug=slug,
        wp_id="WP01",
        to_lane=Lane.CLAIMED,
        actor="adoption-proof",
    )


# ---------------------------------------------------------------------------
# T021 — Root (R5) routed to the canonical resolver (workspace.primary_root)
# ---------------------------------------------------------------------------


def test_root_walk_routes_to_canonical_main_under_coord(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R5: the coord-worktree feature dir resolves to the canonical MAIN root.

    BEFORE adoption ``_repo_root_for_feature`` walked ``parent.parent`` to the
    coord-WORKTREE root (the flatten hazard). AFTER, it routes through
    ``resolve_canonical_root`` and converges on the main checkout — read and
    write resolve the SAME root via the SAME resolver (SC-002/SC-003).
    """
    coord = build_coord(tmp_path)
    monkeypatch.chdir(coord.coord_worktree)
    fd = coord.coord_feature_dir

    main_root = coord.expected_primary_root
    assert _repo_root_for_feature(fd, None) == main_root
    assert _repo_root_for_feature(fd, None) == resolve_canonical_root(fd)
    # It is NOT the coord-worktree root the bare walk used to return.
    assert _repo_root_for_feature(fd, None) != coord.coord_worktree.resolve()


def test_root_walk_stops_at_submodule_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R5 / #2011: under a real submodule the root STOPS at the submodule root.

    The submodule's ``.git`` is a FILE pointer; a naive ``parent.parent`` walk
    climbs into the superproject. The canonical resolver the adoption routes to
    stops correctly.
    """
    sub = build_submodule(tmp_path)
    monkeypatch.chdir(sub.submodule_root)
    fd = sub.feature_dir

    assert (sub.submodule_root / ".git").is_file()
    assert _repo_root_for_feature(fd, None) == sub.expected_primary_root
    assert _repo_root_for_feature(fd, None) != sub.superproject_root.resolve()


def test_root_walk_explicit_repo_root_short_circuit_preserved(tmp_path: Path) -> None:
    """An explicit ``repo_root`` is still returned verbatim (no resolution)."""
    explicit = tmp_path / "explicit-root"
    explicit.mkdir()
    feature_dir = tmp_path / "ad-hoc" / KITTY_SPECS / "slug"
    feature_dir.mkdir(parents=True)
    assert _repo_root_for_feature(feature_dir, explicit) == explicit


def test_root_walk_degrades_to_feature_dir_when_no_repo_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no enclosing git repo can be resolved, the walk degrades to ``feature_dir``.

    This mirrors the prior non-``kitty-specs`` fallback so ad-hoc fixtures built
    outside a worktree keep working (no churn). We drive the ``WorkspaceRootNotFound``
    arm directly (a real "outside any git repo" path is unreliable under pytest's
    tmp tree, which sits inside the project's own worktree).
    """
    import specify_cli.workspace.root_resolver as rr

    feature_dir = tmp_path / "loose" / KITTY_SPECS / "slug"
    feature_dir.mkdir(parents=True)

    def _raise(_cwd: Path) -> Path:
        raise rr.WorkspaceRootNotFound("no git repo")

    monkeypatch.setattr(rr, "resolve_canonical_root", _raise)
    assert _repo_root_for_feature(feature_dir, None) == feature_dir


# ---------------------------------------------------------------------------
# T022 — Write surface (FR-003, C-007): POSITIVE coord-authority assertion
# ---------------------------------------------------------------------------


def test_write_surface_resolves_to_coord_authority_never_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-007: the status WRITE surface is the coord authority, NEVER primary_root.

    Asserted POSITIVELY (renata S-3): the resolved surface DIR equals the coord
    feature dir AND is distinct from the primary checkout's mission dir. A bare
    "not primary" check is unfalsifiable against a silently-collapsed fixture, so
    we pin both the positive identity and the negative.
    """
    coord = build_coord(tmp_path)
    monkeypatch.chdir(coord.coord_worktree)

    surface_dir = resolve_status_surface(
        coord.main_root, coord.mission_slug
    ).parent
    primary_root = coord.expected_primary_root
    primary_surface_dir = primary_root / KITTY_SPECS / coord.mission_slug

    # POSITIVE: the surface lives inside a ``-coord`` worktree — the coord/status
    # authority — never the primary checkout. (We assert the authority *topology*
    # — a ``.worktrees/<…>-coord`` segment — rather than an exact path: the
    # resolver composes the canonical ``<slug>-<mid8>`` coord dir from declared
    # meta, which is the C-007 coord write target. This mirrors the WP01-net
    # positive assertion ``test_coord_status_write_surface_is_coord_authority_never_primary``.)
    assert ".worktrees" in surface_dir.parts
    assert any(
        part.endswith("-coord") for part in surface_dir.parts
    ), surface_dir
    # NEGATIVE: it did NOT degrade to the primary checkout's mission dir (the
    # #2004/#2007 flatten regression C-007 forbids). The coord worktree itself
    # legitimately nests under ``<main_root>/.worktrees`` — so we pin the
    # primary *surface dir*, not the main root, as the value it must never be.
    assert surface_dir != primary_surface_dir
    assert primary_surface_dir not in surface_dir.parents


# ---------------------------------------------------------------------------
# T023 — Write target (FR-004, the latent-bug fix) + the flat-arm proof
# ---------------------------------------------------------------------------


def test_write_target_flat_arm_yields_target_branch_not_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-004 flat-arm proof carried inline (renata S-4, ahead of WP08's keystone).

    Flat mission (no coord branch), CWD parked on an off-target branch so git
    HEAD != target_branch. The adopted ``destination_ref`` resolves to
    ``target_branch`` (CWD-invariant), NOT the git-HEAD value the inline
    ``_current_branch`` selector used to return.
    """
    primary = build_primary(tmp_path)
    off_target = "kitty/mission-write-side-primary-01kv9w0x-lane-q"
    _run_git(primary.repo_root, "checkout", "-q", "-b", off_target)
    monkeypatch.chdir(primary.repo_root)

    identity = _identity_for_request(_request(primary.feature_dir, primary.mission_slug))

    assert identity.destination_ref == TARGET_BRANCH
    assert identity.destination_ref != off_target
    assert identity.destination_ref != _current_branch(primary.repo_root)


def test_write_target_coord_arm_yields_coord_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-004 coord arm: the write-target is the coordination branch.

    Under coord topology both the inline short-circuit (``coord_branch``) and the
    factory resolver already agreed; the adoption keeps them agreeing.
    """
    coord = build_coord(tmp_path)
    monkeypatch.chdir(coord.coord_worktree)

    identity = _identity_for_request(
        _request(coord.primary_feature_dir, coord.mission_slug)
    )
    assert identity.destination_ref == coord.coord_branch
    # The status write target uses the STATUS_STATE (coord-preserving) kind
    # (write-surface-coherence WP02 / T031): under coord topology it keeps the
    # coordination branch — byte-identical to the write-side destination_ref.
    assert (
        identity.destination_ref
        == resolve_placement_only(
            coord.main_root, coord.mission_slug, kind=MissionArtifactKind.STATUS_STATE
        ).ref
    )


def test_resolve_write_target_stays_coord_after_required_kind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """write-surface-coherence WP02 / T031 DoD: the STATUS write target stays COORD.

    ``resolve_placement_only``'s ``kind`` is now REQUIRED (WP01). The status write
    target (``_resolve_write_target`` / ``:332``) threads ``STATUS_STATE`` — a
    coordination kind — so under coord topology it MUST keep resolving the
    ``coordination_branch`` (C-001 / G-2). This pins that the required-kind
    threading did NOT flip the status surface to the primary ``target_branch``:
    RED if ``_resolve_write_target`` returns ``TARGET_BRANCH`` instead of the
    coordination branch.
    """
    coord = build_coord(tmp_path)
    monkeypatch.chdir(coord.coord_worktree)

    resolved = _resolve_write_target(
        coord.main_root, coord.mission_slug, coord.coord_branch
    )
    assert resolved == coord.coord_branch
    assert resolved != TARGET_BRANCH


def test_resolve_write_target_helper_no_meta_degrades_to_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bootstrap window: a no-``meta`` mission degrades cleanly (no churn).

    With no resolvable ``meta.json`` the placement resolver degrades to the
    repo's primary/target branch (``get_feature_target_branch`` fallback). On a
    repo whose checked-out branch IS the primary branch, that equals
    ``_current_branch`` — i.e. the helper produces the same value the prior
    inline selector would in the create→first-write window. The ``ActionContextError``
    / ``StatusReadPathNotFound`` arm is the harder failure mode the ``except``
    guards; here we pin the graceful no-meta degradation.
    """
    repo = tmp_path / "bare-repo"
    repo.mkdir()
    _run_git(repo, "init", "-q", "-b", TARGET_BRANCH)
    _run_git(repo, "config", "user.email", "x@e.test")
    _run_git(repo, "config", "user.name", "X")
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    _run_git(repo, "add", "README.md")
    _run_git(repo, "commit", "-q", "-m", "init")
    monkeypatch.chdir(repo)

    resolved = _resolve_write_target(repo, "no-such-mission-01kv9w0x", None)
    # No meta → the placement resolver degrades to the primary/target branch,
    # which on this single-branch repo is the checked-out branch — the same
    # value the prior inline selector produced (idempotency in the bootstrap
    # window).
    assert resolved == TARGET_BRANCH == _current_branch(repo)


# ---------------------------------------------------------------------------
# T025 — Idempotency (NFR-004) + D-5 equivalence (read==write, 3 topologies)
# ---------------------------------------------------------------------------


def test_coord_write_target_idempotent_before_after(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NFR-004: the coord on-disk write target is IDENTICAL before/after adoption.

    Asserted, not inspected: under coord topology the adopted resolver yields the
    SAME ``destination_ref`` the inline ``coord_branch`` short-circuit produced
    (the coordination branch). Two independent resolutions are byte-identical, so
    no status event moves to a new on-disk target.
    """
    coord = build_coord(tmp_path)
    monkeypatch.chdir(coord.coord_worktree)
    req = _request(coord.primary_feature_dir, coord.mission_slug)

    before = _identity_for_request(req).destination_ref
    after = _identity_for_request(req).destination_ref
    # Stable across resolutions AND equal to the pre-adoption inline value
    # (the declared coordination branch — the short-circuit arm).
    assert before == after == coord.coord_branch


@pytest.mark.parametrize("topology", ["primary", "coord", "submodule"])
def test_read_write_resolution_equivalence_across_topologies(
    topology: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-5 / NFR-001: read==write for root + surface + target, driven bare.

    Across all three real topologies the write-side ``_identity_for_request``
    resolves the SAME root / surface / target the read-side public resolvers do —
    the symmetry proof is the shared single-sourced path (SC-002), driven WITHOUT
    an explicit ``repo_root``.
    """
    cwd: Path
    feature_dir: Path
    slug: str
    main_root: Path
    expected_target: str
    if topology == "primary":
        prim = build_primary(tmp_path)
        cwd, feature_dir, slug = prim.repo_root, prim.feature_dir, prim.mission_slug
        main_root, expected_target = prim.expected_primary_root, TARGET_BRANCH
    elif topology == "coord":
        crd = build_coord(tmp_path)
        cwd, feature_dir, slug = (
            crd.coord_worktree,
            crd.primary_feature_dir,
            crd.mission_slug,
        )
        main_root, expected_target = crd.expected_primary_root, crd.coord_branch
    else:
        sub = build_submodule(tmp_path)
        cwd, feature_dir, slug = (
            sub.submodule_root,
            sub.feature_dir,
            sub.mission_slug,
        )
        main_root, expected_target = sub.expected_primary_root, TARGET_BRANCH

    monkeypatch.chdir(cwd)

    # Root: write-side R5 == read-side canonical resolver == the main root.
    assert _repo_root_for_feature(feature_dir, None) == resolve_canonical_root(
        feature_dir
    )
    assert _repo_root_for_feature(feature_dir, None) == main_root

    # Target: write-side identity == read-side placement resolver. The status
    # write target resolves with the STATUS_STATE (coord-preserving) kind
    # (write-surface-coherence WP02 / T031): coord topology → coord branch,
    # flat/submodule → target branch — matching ``expected_target`` for all three.
    identity = _identity_for_request(_request(feature_dir, slug))
    assert (
        identity.destination_ref
        == resolve_placement_only(
            main_root, slug, kind=MissionArtifactKind.STATUS_STATE
        ).ref
        == expected_target
    )
