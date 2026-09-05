"""Unit tests for the checkout-identity guard (mission
``worktree-root-resolution-01M0B59R`` WP01, FR-001 / FR-008).

These tests exercise :func:`resolve_checkout_identity` against REAL temporary
git repositories/worktrees (``tmp_path`` + real ``git init`` / ``git worktree
add`` subprocess calls) — no mocked git output — mirroring the house pattern in
``tests/core/test_checkout_ownership.py``.

The ownership matrix under test is {owner-primary, foreign-lane-worktree,
nested-clone} × {WRITE, PRIMARY_READ}:

* owner-primary — invoked from the primary checkout (its ``.git`` is a
  directory): owner; a WRITE proceeds.
* foreign-lane-worktree — invoked from a linked worktree (``.git`` is a
  ``gitdir:`` pointer with ``.git/worktrees/<name>`` topology): NON-owner; a
  WRITE fails closed naming the primary it would otherwise have acted on.
* nested-clone — a second, independent ``git init`` nested INSIDE the primary
  tree (its ``.git`` is a directory): owner of itself; a WRITE proceeds. This
  is the case that stays satisfiable without WP07 precisely because the guard
  parses ``.git`` directly instead of re-anchoring through
  ``get_main_repo_root`` / ``locate_project_root``.

INV-2 (FR-008): ``PRIMARY_READ`` returns ``canonical_target`` unchanged
regardless of ``cwd`` — the deliberate #2320/#3328 anchors are never flipped.
"""

from __future__ import annotations

import subprocess
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from specify_cli.core.checkout_identity import (
    CheckoutIdentity,
    FailClosedRefusal,
    Intent,
    resolve_checkout_identity,
)

pytestmark = [pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Fixtures — real git repositories/worktrees/nested clones.
# ---------------------------------------------------------------------------


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _run_git(["init"], cwd=path)
    _run_git(["config", "user.email", "test@example.com"], cwd=path)
    _run_git(["config", "user.name", "Test User"], cwd=path)
    (path / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    _run_git(["add", "README.md"], cwd=path)
    _run_git(["commit", "-m", "Initial commit"], cwd=path)
    _run_git(["branch", "-M", "main"], cwd=path)
    return path


@pytest.fixture
def primary(tmp_path: Path) -> Path:
    """A real, initialized primary git repository (its ``.git`` is a dir)."""
    return _init_repo(tmp_path / "primary")


@pytest.fixture
def lane_worktree(primary: Path, tmp_path: Path) -> Path:
    """A real linked worktree of ``primary`` (its ``.git`` is a pointer file)."""
    wt = tmp_path / "lane-a"
    _run_git(["worktree", "add", "-b", "lane-a", str(wt)], cwd=primary)
    return wt


@pytest.fixture
def nested_clone(primary: Path) -> Path:
    """A second independent repo nested INSIDE ``primary`` (its ``.git`` is a dir)."""
    nested = primary / "vendor" / "nested-clone"
    return _init_repo(nested)


# ---------------------------------------------------------------------------
# owner-primary
# ---------------------------------------------------------------------------


def test_owner_primary_write_is_owner(primary: Path) -> None:
    identity = resolve_checkout_identity(primary, Intent.WRITE)

    assert isinstance(identity, CheckoutIdentity)
    assert identity.is_owner is True
    assert identity.invoking_root == primary.resolve()
    assert identity.canonical_target == primary.resolve()
    assert identity.intent is Intent.WRITE
    # An owner WRITE never yields a refusal (INV-6).
    assert identity.write_refusal() is None


def test_owner_primary_primary_read_returns_target_unchanged(primary: Path) -> None:
    identity = resolve_checkout_identity(primary, Intent.PRIMARY_READ)

    assert identity.canonical_target == primary.resolve()
    assert identity.write_refusal() is None


# ---------------------------------------------------------------------------
# foreign-lane-worktree
# ---------------------------------------------------------------------------


def test_foreign_lane_worktree_write_is_non_owner_and_refuses(primary: Path, lane_worktree: Path) -> None:
    identity = resolve_checkout_identity(lane_worktree, Intent.WRITE)

    assert identity.is_owner is False
    assert identity.invoking_root == lane_worktree.resolve()
    # canonical_target is the primary the worktree would otherwise act on.
    assert identity.canonical_target == primary.resolve()

    refusal = identity.write_refusal()
    assert isinstance(refusal, FailClosedRefusal)
    assert refusal.refusal_path == primary.resolve()
    # NFR-003 / INV-5: the target path appears verbatim in the message.
    assert str(primary.resolve()) in refusal.message()


def test_foreign_lane_worktree_primary_read_never_flips(primary: Path, lane_worktree: Path) -> None:
    identity = resolve_checkout_identity(lane_worktree, Intent.PRIMARY_READ)

    # INV-2: PRIMARY_READ returns canonical_target (the primary) unchanged and
    # never redirects to invoking_root; ownership is informational only.
    assert identity.canonical_target == primary.resolve()
    assert identity.canonical_target != identity.invoking_root
    assert identity.write_refusal() is None


# ---------------------------------------------------------------------------
# nested-clone (owner of itself — decidable from a bare ``.git`` directory)
# ---------------------------------------------------------------------------


def test_nested_clone_write_is_owner_writes_self(nested_clone: Path) -> None:
    identity = resolve_checkout_identity(nested_clone, Intent.WRITE)

    # The nested clone owns itself: parsing ``.git`` directly sees a directory,
    # so the guard does NOT re-anchor to the outer primary (that is the WP07
    # defect). Owner ⇒ no refusal.
    assert identity.is_owner is True
    assert identity.invoking_root == nested_clone.resolve()
    assert identity.canonical_target == nested_clone.resolve()
    assert identity.write_refusal() is None


def test_nested_clone_primary_read_targets_self(nested_clone: Path) -> None:
    identity = resolve_checkout_identity(nested_clone, Intent.PRIMARY_READ)

    assert identity.canonical_target == nested_clone.resolve()
    assert identity.write_refusal() is None


# ---------------------------------------------------------------------------
# Value-object shape
# ---------------------------------------------------------------------------


def test_checkout_identity_is_frozen(primary: Path) -> None:
    identity = resolve_checkout_identity(primary, Intent.WRITE)
    with pytest.raises(FrozenInstanceError):
        identity.is_owner = False  # type: ignore[misc]


def test_fail_closed_refusal_message_embeds_path(tmp_path: Path) -> None:
    refusal = FailClosedRefusal(refusal_path=tmp_path)
    assert str(tmp_path) in refusal.message()
