"""Tests for the topology authority seam (WP03, FR-005 / FR-008).

`classify_worktree_topology` / `is_registered_coord_worktree` are the single
authority for "is this a coord worktree / what surface am I on" decisions. The
``-coord`` suffix only *proposes* coord topology; the ``git worktree list
--porcelain`` registry *disposes*.

These tests pin:
* the four ``WorktreeTopology`` outcomes (PRIMARY / COORD_WORKTREE /
  LANE_WORKTREE / UNREGISTERED);
* the F-005 husk case — a ``-coord``-NAMED plain directory that git does NOT
  register is UNREGISTERED, never COORD_WORKTREE;
* fail-closed registry-read failure;
* injected-registry plumbing (no per-path shell-out).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.coordination.surface_resolver import (
    WorktreeTopology,
    classify_worktree_topology,
    is_registered_coord_worktree,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(repo_root: Path) -> None:
    repo_root.mkdir(parents=True, exist_ok=True)
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test")
    (repo_root / "README.md").write_text("seed\n", encoding="utf-8")
    _git(repo_root, "add", "README.md")
    _git(repo_root, "commit", "-q", "-m", "seed")


def _add_worktree(repo_root: Path, rel_path: str, branch: str) -> Path:
    target = repo_root / rel_path
    _git(repo_root, "worktree", "add", "-q", "-b", branch, str(target))
    return target


# ---------------------------------------------------------------------------
# classify_worktree_topology — the four outcomes
# ---------------------------------------------------------------------------


def test_primary_checkout_is_primary(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    feature_dir = repo_root / "kitty-specs" / "my-mission"
    feature_dir.mkdir(parents=True)

    assert (
        classify_worktree_topology(feature_dir, repo_root=repo_root)
        is WorktreeTopology.PRIMARY
    )


def test_registered_coord_worktree_is_coord(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    coord = _add_worktree(
        repo_root,
        ".worktrees/my-mission-ABCD1234-coord",
        "kitty/mission-my-mission-ABCD1234",
    )
    feature_dir = coord / "kitty-specs" / "my-mission-ABCD1234"
    feature_dir.mkdir(parents=True)

    assert (
        classify_worktree_topology(feature_dir, repo_root=repo_root)
        is WorktreeTopology.COORD_WORKTREE
    )


def test_registered_lane_worktree_is_lane(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    lane = _add_worktree(
        repo_root,
        ".worktrees/my-mission-ABCD1234-lane-a",
        "kitty/mission-my-mission-ABCD1234-lane-a",
    )
    feature_dir = lane / "kitty-specs" / "my-mission-ABCD1234"
    feature_dir.mkdir(parents=True)

    assert (
        classify_worktree_topology(feature_dir, repo_root=repo_root)
        is WorktreeTopology.LANE_WORKTREE
    )


def test_unregistered_worktree_dir_is_unregistered(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    # A plain directory under .worktrees that git never registered.
    feature_dir = (
        repo_root / ".worktrees" / "my-mission-ABCD1234-lane-a"
        / "kitty-specs" / "my-mission-ABCD1234"
    )
    feature_dir.mkdir(parents=True)

    assert (
        classify_worktree_topology(feature_dir, repo_root=repo_root)
        is WorktreeTopology.UNREGISTERED
    )


def test_coord_named_husk_is_unregistered_never_coord(tmp_path: Path) -> None:
    """F-005: a ``-coord``-NAMED plain dir (no git registration) is a husk.

    Name proposes COORD; the registry disposes — it is UNREGISTERED, never
    COORD_WORKTREE. This is the split-brain a name-only predicate falls for.
    """
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    husk = (
        repo_root / ".worktrees" / "my-mission-ABCD1234-coord"
        / "kitty-specs" / "my-mission-ABCD1234"
    )
    husk.mkdir(parents=True)

    assert (
        classify_worktree_topology(husk, repo_root=repo_root)
        is WorktreeTopology.UNREGISTERED
    )
    assert not is_registered_coord_worktree(husk, repo_root=repo_root)


# ---------------------------------------------------------------------------
# is_registered_coord_worktree — the convenience predicate
# ---------------------------------------------------------------------------


def test_is_registered_coord_true_only_for_registered_coord(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    coord = _add_worktree(
        repo_root,
        ".worktrees/my-mission-ABCD1234-coord",
        "kitty/mission-my-mission-ABCD1234",
    )
    feature_dir = coord / "kitty-specs" / "my-mission-ABCD1234"
    feature_dir.mkdir(parents=True)

    assert is_registered_coord_worktree(feature_dir, repo_root=repo_root)


def test_is_registered_coord_false_for_lane(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    lane = _add_worktree(
        repo_root,
        ".worktrees/my-mission-ABCD1234-lane-a",
        "kitty/mission-my-mission-ABCD1234-lane-a",
    )
    feature_dir = lane / "kitty-specs" / "my-mission-ABCD1234"
    feature_dir.mkdir(parents=True)

    assert not is_registered_coord_worktree(feature_dir, repo_root=repo_root)


def test_is_registered_coord_false_for_primary(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    feature_dir = repo_root / "kitty-specs" / "my-mission"
    feature_dir.mkdir(parents=True)

    assert not is_registered_coord_worktree(feature_dir, repo_root=repo_root)


# ---------------------------------------------------------------------------
# Fail-closed posture + injected registry
# ---------------------------------------------------------------------------


def test_registry_unreadable_fails_closed(tmp_path: Path) -> None:
    """No git repo at repo_root → the registry cannot be read → raise.

    Name proposes coord; with no registry to dispose, fail closed rather than
    guess (NFR-003).
    """
    non_repo = tmp_path / "not-a-repo"
    feature_dir = (
        non_repo / ".worktrees" / "my-mission-coord" / "kitty-specs" / "my-mission"
    )
    feature_dir.mkdir(parents=True)

    with pytest.raises(WorktreeRegistryUnavailable):
        classify_worktree_topology(feature_dir, repo_root=non_repo)


def test_injected_registry_skips_shell_out(tmp_path: Path) -> None:
    """A caller holding the porcelain set passes it; no git is consulted.

    repo_root is a non-repo (a shell-out would raise); the injected registry
    proves the path is honoured.
    """
    non_repo = tmp_path / "not-a-repo"
    coord = (
        non_repo / ".worktrees" / "my-mission-ABCD1234-coord"
    )
    feature_dir = coord / "kitty-specs" / "my-mission-ABCD1234"
    feature_dir.mkdir(parents=True)
    registry = frozenset({coord.resolve()})

    assert (
        classify_worktree_topology(
            feature_dir, repo_root=non_repo, registry=registry
        )
        is WorktreeTopology.COORD_WORKTREE
    )
    assert is_registered_coord_worktree(
        feature_dir, repo_root=non_repo, registry=registry
    )


def test_injected_empty_registry_classifies_unregistered(tmp_path: Path) -> None:
    non_repo = tmp_path / "not-a-repo"
    feature_dir = (
        non_repo / ".worktrees" / "my-mission-ABCD1234-coord"
        / "kitty-specs" / "my-mission-ABCD1234"
    )
    feature_dir.mkdir(parents=True)

    assert (
        classify_worktree_topology(
            feature_dir, repo_root=non_repo, registry=frozenset()
        )
        is WorktreeTopology.UNREGISTERED
    )


# ---------------------------------------------------------------------------
# Lock-root flip — registered COORD/LANE worktree feature dirs must lock against
# the CANONICAL primary root, not the worktree-local ``parent.parent`` (WP03).
#
# This is the concurrency-correctness branch in
# ``status.emit._feature_status_lock_root`` and
# ``status.work_package_lifecycle._repo_root_for_lock``: two processes anchored
# on one mission via different worktrees must agree on a single lock root, else
# there is no mutual exclusion. The pre-existing contract test uses a worktree
# NOT under ``.worktrees/`` (classified PRIMARY), so it bypasses this branch.
# These tests place a REGISTERED worktree UNDER ``.worktrees/`` so the
# COORD/LANE branch is actually exercised, and assert primary-context and
# worktree-context resolutions agree on the same lock root.
# ---------------------------------------------------------------------------


def _coord_worktree_feature_dir(repo_root: Path) -> Path:
    """Register a ``.worktrees/<...>-coord`` worktree and return its feature dir."""
    coord = _add_worktree(
        repo_root,
        ".worktrees/my-mission-ABCD1234-coord",
        "kitty/mission-my-mission-ABCD1234",
    )
    feature_dir = coord / "kitty-specs" / "my-mission-ABCD1234"
    feature_dir.mkdir(parents=True)
    return feature_dir


def test_emit_lock_root_for_coord_worktree_is_canonical_primary(
    tmp_path: Path,
) -> None:
    from specify_cli.workspace.root_resolver import resolve_status_lock_root

    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    worktree_feature_dir = _coord_worktree_feature_dir(repo_root)

    primary_feature_dir = repo_root / "kitty-specs" / "my-mission-ABCD1234"
    primary_feature_dir.mkdir(parents=True)

    worktree_lock_root = resolve_status_lock_root(
        worktree_feature_dir, repo_root=None
    )
    primary_lock_root = resolve_status_lock_root(
        primary_feature_dir, repo_root=None
    )

    # The whole point of the flip: the coord-worktree feature dir resolves to
    # the canonical primary root (NOT the worktree-local parent.parent), so it
    # agrees with the primary-checkout resolution for the same mission.
    assert worktree_lock_root == repo_root.resolve()
    assert worktree_lock_root != worktree_feature_dir.parent.parent
    assert worktree_lock_root == primary_lock_root


def test_lifecycle_lock_root_for_coord_worktree_is_canonical_primary(
    tmp_path: Path,
) -> None:
    from specify_cli.workspace.root_resolver import resolve_status_lock_root

    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    worktree_feature_dir = _coord_worktree_feature_dir(repo_root)

    primary_feature_dir = repo_root / "kitty-specs" / "my-mission-ABCD1234"
    primary_feature_dir.mkdir(parents=True)

    worktree_lock_root = resolve_status_lock_root(worktree_feature_dir, repo_root=None)
    primary_lock_root = resolve_status_lock_root(primary_feature_dir, repo_root=None)

    assert worktree_lock_root == repo_root.resolve()
    assert worktree_lock_root != worktree_feature_dir.parent.parent
    assert worktree_lock_root == primary_lock_root


def _non_git_kitty_specs_feature_dir(tmp_path: Path) -> Path:
    """A ``kitty-specs/<mission>`` feature dir with a ``.worktrees`` ancestor in a
    NON-git tree.

    The ``.worktrees`` ancestor makes ``classify_worktree_topology`` proceed past
    its PRIMARY short-circuit to read the git registry; the absence of any git
    repo then makes ``read_worktree_registry`` fail closed with
    ``WorktreeRegistryUnavailable``. This is the real trigger for the lock-root
    helpers' first degradation branch (no mock).
    """
    feature_dir = (
        tmp_path / ".worktrees" / "m-ABCD1234-coord" / "kitty-specs" / "m-ABCD1234"
    )
    feature_dir.mkdir(parents=True)
    return feature_dir


def test_lock_root_degrades_to_parent_parent_when_canonical_root_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``resolve_status_lock_root`` degrades to ``feature_dir.parent.parent`` when
    ``resolve_canonical_root`` raises ``WorkspaceRootNotFound`` (no git repo
    anywhere up the tree). This is the WP02-consolidated fallback path.

    The topology-classifier-based ``WorktreeRegistryUnavailable`` path from the
    pre-WP02 private helpers no longer applies; the new shared helper routes
    directly through ``resolve_canonical_root`` (D-12 / SC-002). The degradation
    trigger is therefore ``WorkspaceRootNotFound``, not ``WorktreeRegistryUnavailable``.

    The monkeypatch is necessary because pytest's ``tmp_path`` ancestor may contain
    a real ``.git`` directory (e.g. ``/tmp/.git``), which would prevent
    ``WorkspaceRootNotFound`` from being raised in a bare walk. Injecting the
    exception exercises the documented fallback unconditionally (C-008: fix, not
    litigate the host-path dependency).
    """
    from specify_cli.core.paths import WorkspaceRootNotFound
    from specify_cli.workspace.root_resolver import resolve_status_lock_root
    import specify_cli.workspace.root_resolver as rr_mod

    feature_dir = _non_git_kitty_specs_feature_dir(tmp_path)

    def _raise_not_found(_: object) -> Path:
        raise WorkspaceRootNotFound(feature_dir)

    monkeypatch.setattr(rr_mod, "resolve_canonical_root", _raise_not_found)

    lock_root = resolve_status_lock_root(feature_dir, repo_root=None)

    assert lock_root == feature_dir.parent.parent


# Imported lazily so the module import above already proves the public symbol
# exists; this keeps the failure mode explicit if the error class is dropped.
from specify_cli.coordination.surface_resolver import (  # noqa: E402
    WorktreeRegistryUnavailable,
)
