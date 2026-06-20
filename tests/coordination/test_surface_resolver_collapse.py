"""WP06 collapse + FR-006 coord-empty hard-fail (mutation-verified).

These tests pin the WP06 behavioral contract on the **single** canonical surface
resolver (``coordination.surface_resolver.resolve_status_surface_with_anchor`` —
FR-001/FR-007 sole authority):

* **FR-006 / #1716 coord-empty hard-fail.** A materialized-but-empty coordination
  worktree raises :class:`CoordinationWorktreeEmpty` whose message names BOTH
  operator recovery paths (collapse/flatten OR recreate/populate) and never
  silently falls back to primary. The assertions are *mutation-killing*: they
  pin the EXACT recovery-path wording, the ``error_code``, the subclass
  relationship, and the no-silent-fallback posture — not merely "something
  raised". The hard-fail fires for BOTH the bare-slug and the ``<slug>-<mid8>``
  handle forms (handle-invariant policy).
* **The two adjacent benign states still resolve to primary** (regression
  guards that the hard-fail did NOT over-reach): the no-coord state and the
  create→first-write window (coord declared, worktree NOT materialized).

ADR: ``architecture/3.x/adr/2026-06-19-1-coord-empty-surface-fallback.md``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.coordination.surface_resolver import (
    CoordinationWorktreeEmpty,
    resolve_status_surface_with_anchor,
)
from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.missions._read_path_resolver import (
    STATUS_READ_PATH_NOT_FOUND_CODE,
    StatusReadPathNotFound,
)

pytestmark = pytest.mark.git_repo

# Production-shaped identity (Mission Identity Model 083+): a real 26-char ULID.
MISSION_ID = "01KTDVHZKGCHCW6HQ4V577PNES"
MID8 = MISSION_ID[:8]
BARE_SLUG = "surface-collapse-mission"
SLUG_WITH_MID8 = f"{BARE_SLUG}-{MID8}"
COORD_BRANCH = f"kitty/mission-{SLUG_WITH_MID8}"


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(repo_root: Path) -> None:
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "collapse@example.test")
    _git(repo_root, "config", "user.name", "Collapse Gate")
    _git(repo_root, "commit", "--allow-empty", "-qm", "init")


def _write_meta(feature_dir: Path, **fields: object) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(json.dumps(fields), encoding="utf-8")


def _materialise_coord_empty(repo_root: Path, slug: str) -> None:
    """Primary declares coord branch; coord worktree ROOT exists but is empty."""
    _init_repo(repo_root)
    _write_meta(
        repo_root / "kitty-specs" / slug,
        mission_id=MISSION_ID,
        coordination_branch=COORD_BRANCH,
    )
    _git(repo_root, "branch", COORD_BRANCH)
    coord_root = CoordinationWorkspace.worktree_path(repo_root, slug, MID8)
    coord_root.mkdir(parents=True)  # materialised, NO mission dir inside


# ---------------------------------------------------------------------------
# FR-006 — coord-empty hard-fail (the centerpiece, mutation-verified)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slug", [BARE_SLUG, SLUG_WITH_MID8], ids=["bare", "slug-mid8"])
def test_coord_empty_hard_fails_with_two_path_message(tmp_path: Path, slug: str) -> None:
    """A materialized-but-empty coord worktree raises CoordinationWorktreeEmpty.

    Mutation-killing: pins the EXACT contract for BOTH handle forms — the
    subclass relationship, the preserved ``error_code``, the two named recovery
    paths, and the explicit no-silent-fallback posture. A regression that fell
    back to primary, dropped a recovery path, or changed the error_code is caught
    here.
    """
    _materialise_coord_empty(tmp_path, slug)

    with pytest.raises(CoordinationWorktreeEmpty) as excinfo:
        resolve_status_surface_with_anchor(tmp_path, slug)

    exc = excinfo.value
    # (1) Subclass + preserved error_code: existing fail-closed handlers and
    #     code-based routing keep working.
    assert isinstance(exc, StatusReadPathNotFound)
    assert exc.error_code == STATUS_READ_PATH_NOT_FOUND_CODE

    message = str(exc)
    lowered = message.lower()
    # (2) BOTH recovery paths are named (NFR-004). Pin the discriminating tokens
    #     of each path, not just "an error happened".
    assert "collaps" in lowered and "flatten" in lowered, (
        "coord-empty message must name recovery path (a): collapse/flatten the "
        f"mission. Got: {message!r}"
    )
    assert "coordination_branch" in message, (
        "recovery path (a) must tell the operator to remove the "
        f"coordination_branch key. Got: {message!r}"
    )
    assert "recreat" in lowered and "populat" in lowered, (
        "coord-empty message must name recovery path (b): recreate/populate the "
        f"coordination worktree. Got: {message!r}"
    )
    assert "spec-kitty agent worktree repair" in message, (
        "recovery path (b) must offer the concrete repair command. Got: "
        f"{message!r}"
    )
    # (3) Explicit no-silent-fallback posture (FR-006).
    assert "refuses to silently fall back" in message, (
        "coord-empty must explicitly state it does NOT fall back to primary "
        f"(no split-brain). Got: {message!r}"
    )


def test_coord_empty_caught_by_status_read_path_not_found_handler(
    tmp_path: Path,
) -> None:
    """Existing ``except StatusReadPathNotFound`` handlers still catch coord-empty.

    The carve-out must not break the fail-closed contract that callers rely on:
    catching the base class still catches the enriched subclass.
    """
    _materialise_coord_empty(tmp_path, SLUG_WITH_MID8)

    with pytest.raises(StatusReadPathNotFound):
        resolve_status_surface_with_anchor(tmp_path, SLUG_WITH_MID8)


# ---------------------------------------------------------------------------
# Regression guards — the hard-fail must NOT over-reach onto benign states
# ---------------------------------------------------------------------------


def test_no_coord_resolves_primary(tmp_path: Path) -> None:
    """A mission with no coordination_branch → primary surface, never a hard-fail."""
    _init_repo(tmp_path)
    _write_meta(tmp_path / "kitty-specs" / SLUG_WITH_MID8, mission_id=MISSION_ID)

    resolved = resolve_status_surface_with_anchor(tmp_path, SLUG_WITH_MID8)

    expected = (tmp_path / "kitty-specs" / SLUG_WITH_MID8).resolve()
    assert resolved.read_dir.resolve() == expected
    assert resolved.primary_anchor.resolve() == expected


def test_create_window_unmaterialized_coord_resolves_primary(tmp_path: Path) -> None:
    """Create→first-write window (coord declared, NOT materialized) → primary anchor.

    The companion to the coord-empty hard-fail: when ``coordination_branch`` is
    declared but the coord worktree root does NOT yet exist, the primary checkout
    stays authoritative for the create→first-write window (WP04 T016). A
    regression that hard-failed here would break first-write on a freshly created
    coord mission. The surface composes the coord path (the worktree will live
    there once materialised); the CWD-invariant primary anchor remains the
    primary dir.
    """
    _init_repo(tmp_path)
    _write_meta(
        tmp_path / "kitty-specs" / SLUG_WITH_MID8,
        mission_id=MISSION_ID,
        coordination_branch=COORD_BRANCH,
    )
    _git(tmp_path, "branch", COORD_BRANCH)
    # NB: no .worktrees/<slug>-<mid8>-coord/ root is materialised.

    resolved = resolve_status_surface_with_anchor(tmp_path, SLUG_WITH_MID8)

    expected_primary = (tmp_path / "kitty-specs" / SLUG_WITH_MID8).resolve()
    assert resolved.primary_anchor.resolve() == expected_primary, (
        "create→first-write window must keep the PRIMARY checkout as the "
        "anchor — coord-empty hard-fail must not over-reach here"
    )
