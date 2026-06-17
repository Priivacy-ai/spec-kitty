"""Public lock-root behavioral invariant (T006, paula S-4 / S-9).

The existing lock-root tests (``test_emit_lock_root_*`` / ``test_lifecycle_lock_root_*``)
assert the **private helper by name** (``_feature_status_lock_root`` /
``_repo_root_for_lock``). FR-001 deletes those helpers (routes them to
``workspace.primary_root``), so by-name tests break on deletion and form-couple
the suite to a symbol the adoption removes.

This module adds the PUBLIC behavioral invariant the private tests were really
guarding, so WP02 can retire the by-name coverage without losing it:

    Two processes anchored on ONE mission — one via the primary checkout CWD,
    one via the coordination-worktree CWD — must acquire the SAME status lock
    (mutual exclusion). Concretely, the lock PATH (``feature_status_lock_path``
    over the resolved lock root) is byte-identical no matter which worktree the
    process anchored from.

It is expressed through the **public** lock surface
(``feature_status_lock_path``) and the canonical resolver the adoption routes
to — never by naming the private helper — so it is invariant across the swap.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.coordination.status_transition import _repo_root_for_feature
from specify_cli.core.paths import resolve_canonical_root
from specify_cli.status.locking import feature_status_lock, feature_status_lock_path
from specify_cli.workspace.root_resolver import resolve_status_lock_root

from .topology_fixtures import build_coord, build_primary, build_submodule

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _lock_root(feature_dir: Path) -> Path:
    """Resolve the lock root the way the adoption WILL — via the canonical
    resolver, with NO explicit ``repo_root`` (the swap target). The public
    invariant must hold whether the lock root comes from the legacy walk or the
    resolver, so this is the post-adoption form.
    """
    resolved: Path = resolve_canonical_root(feature_dir)
    return resolved


def test_lock_path_is_identical_from_primary_and_coord_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The behavioral invariant: one mission → one lock path across worktrees.

    A process anchored at the primary checkout and a process anchored at the
    coord worktree must compute the SAME ``feature_status_lock_path`` — otherwise
    they would not mutually exclude (the concurrency defect S-4 guards). Driven
    bare (no explicit ``repo_root``), via the canonical resolver.
    """
    coord = build_coord(tmp_path)

    # Process 1: anchored from the primary checkout.
    monkeypatch.chdir(coord.main_root)
    root_from_primary = _lock_root(coord.primary_feature_dir)
    path_from_primary = feature_status_lock_path(root_from_primary, coord.mission_slug)

    # Process 2: anchored from the coord worktree.
    monkeypatch.chdir(coord.coord_worktree)
    root_from_coord = _lock_root(coord.coord_feature_dir)
    path_from_coord = feature_status_lock_path(root_from_coord, coord.mission_slug)

    # Same canonical root → same lock file → real mutual exclusion.
    assert root_from_primary == root_from_coord == coord.expected_primary_root
    assert path_from_primary == path_from_coord


def test_shared_resolver_and_canonical_resolver_agree_on_lock_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Equivalence (D-5 / WP02): the consolidated ``resolve_status_lock_root``
    and the canonical resolver resolve the SAME lock root — so FR-001's swap is
    a behavior no-op and the public lock path is identical across callers.

    (WP01 name: ``test_legacy_walk_and_canonical_resolver_agree_on_lock_root``.
    Renamed in WP02 after the private helpers were consolidated into the shared
    resolver — the assertion now expresses the post-consolidation invariant.)
    """
    coord = build_coord(tmp_path)
    monkeypatch.chdir(coord.coord_worktree)
    fd = coord.coord_feature_dir

    shared = resolve_status_lock_root(fd, None)
    canonical = resolve_canonical_root(fd)

    # The consolidated resolver and the canonical resolver agree — the public
    # lock path is identical.
    assert shared == canonical
    assert feature_status_lock_path(shared, coord.mission_slug) == (
        feature_status_lock_path(canonical, coord.mission_slug)
    )

    # before→after (WP05): the coord ``_repo_root_for_feature`` used to walk to
    # the COORD-WORKTREE root (the divergence the adoption unifies). After the
    # WP05 R5 adoption it routes through the canonical worktree-pointer resolver,
    # so it now CONVERGES on the same canonical root as the lock sites — the
    # public lock path is finally derivable from the coord helper too (the
    # convergence this invariant predicted as "the adoption").
    adopted_coord = _repo_root_for_feature(fd, None)
    assert adopted_coord == canonical
    assert feature_status_lock_path(adopted_coord, coord.mission_slug) == (
        feature_status_lock_path(canonical, coord.mission_slug)
    )


def test_lock_path_invariant_holds_for_submodule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The lock-root invariant holds for the submodule class too (NFR-001/002).

    Anchored inside a real submodule, the lock root resolves to the submodule's
    own root — not the superproject — so a submodule mission locks against itself.
    """
    sub = build_submodule(tmp_path)
    monkeypatch.chdir(sub.submodule_root)

    root = _lock_root(sub.feature_dir)
    assert root == sub.expected_primary_root
    assert root != sub.superproject_root.resolve()
    lock_path = feature_status_lock_path(root, sub.mission_slug)
    assert lock_path.name == f"{sub.mission_slug}.status.lock"


def test_lock_is_reentrant_and_acquirable_on_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end public behavior: the lock is actually acquirable (and
    re-entrant) on a primary checkout via the resolved root — the observable the
    private smoke tests (S-9) approximated on synthetic dirs.
    """
    primary = build_primary(tmp_path)
    monkeypatch.chdir(primary.repo_root)
    root = _lock_root(primary.feature_dir)

    with feature_status_lock(root, primary.mission_slug) as outer:
        # Re-entrant within the same thread (a transaction wrapping a helper that
        # re-locks must not deadlock).
        with feature_status_lock(root, primary.mission_slug) as inner:
            assert outer == inner
        assert outer.name == f"{primary.mission_slug}.status.lock"
