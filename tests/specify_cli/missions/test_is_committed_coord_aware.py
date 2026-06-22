"""Tests for the single read-surface ``is_committed()`` check (FR-011 collapse).

WP01 (#1884) once made ``is_committed`` a 3-leg OR over (coordination-ref / HEAD /
primary-target-branch) parameterised by a ``placement: CommitTarget``. WP07
(FR-011) **collapsed** that OR to a single check: a file is committed iff it is
tracked AND present at the ``HEAD`` of the git surface it physically lives on.
The collapse is safe because the sole non-test caller (setup-plan) feeds the
READ-resolved ``spec_file``: the coord worktree dir for a materialized
coordination topology, the primary dir for the #1718 create-window, and the
#1848 coord-deleted case never reaches the check (the read path raises
``CoordinationBranchDeleted`` upstream).

Covers:
- Flat topology: file on HEAD → True, absent → False, outside repo → False.
- The file's own surface decides: a spec on the coord-worktree HEAD reads
  committed when checked at the coord-worktree path; the same spec uncommitted
  on the primary checkout reads NOT committed when checked at the primary path.
- The parametrized FR-011 envelope (``test_is_committed_fr011_parity``): for
  every (topology × transient) cell it resolves the READ surface exactly as the
  caller does, asserts the new single-surface verdict matches the retired 3-leg
  OR verdict (parity), and pins the #1848 coord-deleted upstream short-circuit.

Issue #1884 / #1954 / FR-003 (WP01) → FR-011 (WP07).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.missions._substantive import (
    _git_commit_check_context,
    _head_carries_path,
    is_committed,
)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_repo(tmp_path: Path) -> str:
    """Set up a minimal git repository with an initial commit.

    Returns the default branch name (``main``).
    """
    subprocess.run(
        ["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "commit.gpgsign", "false"],
        check=True,
        capture_output=True,
    )
    # Create an initial commit so HEAD exists.
    readme = tmp_path / "README.md"
    readme.write_text("init\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "README.md"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "init"],
        check=True,
        capture_output=True,
    )
    return "main"


def _commit_file(tmp_path: Path, file_path: Path, message: str) -> None:
    """Stage and commit ``file_path`` in ``tmp_path``."""
    rel = str(file_path.relative_to(tmp_path))
    subprocess.run(["git", "-C", str(tmp_path), "add", rel], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", message],
        check=True,
        capture_output=True,
    )


# ---------------------------------------------------------------------------
# Flat-topology: the file's own HEAD decides
# ---------------------------------------------------------------------------


def test_file_committed_on_head_returns_true(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _commit_file(tmp_path, spec, "add spec")

    assert is_committed(spec, tmp_path) is True


def test_file_not_committed_returns_false(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    # Not committed — only written to disk.

    assert is_committed(spec, tmp_path) is False


def test_file_outside_repo_returns_false(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    outside = tmp_path.parent / f"outside_{tmp_path.name}.md"
    outside.write_text("x\n", encoding="utf-8")
    try:
        assert is_committed(outside, tmp_path) is False
    finally:
        outside.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# The file's own surface decides (coord-worktree vs primary checkout)
# ---------------------------------------------------------------------------


def test_spec_committed_only_on_coord_worktree_surface(tmp_path: Path) -> None:
    """A spec committed in the coord worktree reads committed at its worktree path.

    This is the surface the read path resolves to for a materialized
    coordination topology — the path the setup-plan caller actually feeds.
    """
    _init_repo(tmp_path)

    coord_ref = "kitty/mission-test-WORKTREE"
    subprocess.run(
        ["git", "-C", str(tmp_path), "branch", coord_ref, "main"],
        check=True,
        capture_output=True,
    )
    coord_worktree = tmp_path / ".worktrees" / "test-coord"
    coord_worktree.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "worktree", "add", str(coord_worktree), coord_ref],
        check=True,
        capture_output=True,
    )

    spec = coord_worktree / "kitty-specs" / "test" / "spec.md"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("# Spec\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(coord_worktree), "add", "kitty-specs/test/spec.md"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(coord_worktree), "commit", "-m", "add spec on coord worktree"],
        check=True,
        capture_output=True,
    )

    # The coord-worktree surface carries the spec at HEAD.
    assert is_committed(spec, tmp_path) is True


def test_spec_uncommitted_on_primary_surface_returns_false(tmp_path: Path) -> None:
    """A spec on the coord branch but NOT on primary HEAD reads False at the primary path.

    Pins the FR-011 boundary: the primary-checkout path is the surface the read
    path never resolves to for a materialized coordination topology, so the
    single-surface check on it correctly returns False (no false positive).
    """
    _init_repo(tmp_path)

    coord_ref = "kitty/mission-test-ABCD1234"
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", "-b", coord_ref],
        check=True,
        capture_output=True,
    )
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _commit_file(tmp_path, spec, "add spec on coord")
    # Switch back to main so spec.md is NOT on the primary HEAD; leave it on disk.
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", "main"],
        check=True,
        capture_output=True,
    )
    spec.write_text("# Spec\n", encoding="utf-8")  # present on disk, not on primary HEAD

    assert is_committed(spec, tmp_path) is False


# ---------------------------------------------------------------------------
# WP07 / FR-011 — single-surface parity with the retired 3-leg OR.
#
# Each row builds a realistic on-disk topology, then:
#   1. resolves the READ surface exactly as the setup-plan caller does
#      (``resolve_handle_to_read_path(require_exists=True)``), and
#   2. asserts the NEW single-surface ``is_committed`` verdict on the
#      read-resolved spec equals the RETIRED 3-leg OR verdict (reconstructed
#      locally) — PROVING the collapse is behaviour-preserving on every
#      reachable cell.
#
# The #1848 coord-deleted row is special: ``is_committed`` is NEVER REACHED at
# the caller — the read path raises ``CoordinationBranchDeleted`` (a
# ``StatusReadPathNotFound``) first. That row pins the UPSTREAM short-circuit,
# not an ``is_committed`` verdict.
# ---------------------------------------------------------------------------

_ENVELOPE_MISSION_ID = "01KTDVHZKGCHCW6HQ4V577PNES"
_ENVELOPE_MID8 = _ENVELOPE_MISSION_ID[:8]
_ENVELOPE_SLUG = "single-surface-resolver"
_ENVELOPE_SLUG_MID8 = f"{_ENVELOPE_SLUG}-{_ENVELOPE_MID8}"
_ENVELOPE_COORD = f"kitty/mission-{_ENVELOPE_SLUG_MID8}"
_ENVELOPE_TARGET = "main"


def _envelope_meta(coordination_branch: str | None) -> dict[str, object]:
    meta: dict[str, object] = {
        "mission_id": _ENVELOPE_MISSION_ID,
        "mission_slug": _ENVELOPE_SLUG,
        "mid8": _ENVELOPE_MID8,
        "mission_type": "software-dev",
        "target_branch": _ENVELOPE_TARGET,
    }
    if coordination_branch is not None:
        meta["coordination_branch"] = coordination_branch
    return meta


def _write_envelope_meta(feature_dir: Path, coordination_branch: str | None) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(_envelope_meta(coordination_branch)), encoding="utf-8"
    )


def _git_q(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _ref_carries_path(git_cwd: Path, ref: str, tree_path: str) -> bool:
    """Reconstruct the retired coord/target-branch leg: ``ref:tree_path`` resolves."""
    try:
        subprocess.run(
            ["git", "-C", str(git_cwd), "cat-file", "-e", f"{ref}:{tree_path}"],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _retired_or_verdict(
    spec: Path,
    repo_root: Path,
    *,
    placement_ref: str | None,
    target_branch: str | None,
    primary_repo_root: Path,
) -> bool:
    """Reconstruct the WP01 3-leg OR verdict for parity comparison.

    Leg 1 (coord ref, when a COORDINATION placement ref is supplied) OR
    Leg 2 (the file's own surface HEAD) OR
    Leg 3 (primary-target-branch against the primary root + primary tree-path).
    """
    ctx = _git_commit_check_context(spec, repo_root)
    if ctx is None:
        return False
    git_cwd, tree_path = ctx
    if placement_ref is not None and _ref_carries_path(git_cwd, placement_ref, tree_path):
        return True
    if _head_carries_path(git_cwd, tree_path):
        return True
    if not target_branch:
        return False
    return _ref_carries_path(primary_repo_root, target_branch, tree_path)


def _build_single_branch_committed(repo_root: Path) -> Path:
    fd = repo_root / "kitty-specs" / _ENVELOPE_SLUG_MID8
    _write_envelope_meta(fd, coordination_branch=None)
    spec = fd / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _git_q(repo_root, "add", "-A")
    _git_q(repo_root, "commit", "-m", "spec on primary")
    return spec


def _build_single_branch_uncommitted(repo_root: Path) -> Path:
    fd = repo_root / "kitty-specs" / _ENVELOPE_SLUG_MID8
    _write_envelope_meta(fd, coordination_branch=None)
    _git_q(repo_root, "add", "-A")
    _git_q(repo_root, "commit", "-m", "meta on primary")
    spec = fd / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")  # on disk only, never committed
    return spec


def _build_lanes(repo_root: Path) -> Path:
    # LANES flattens to a primary/FLATTENED placement; artifact on the target ref.
    return _build_single_branch_committed(repo_root)


def _build_coord(repo_root: Path) -> Path:
    # Coord branch materialised; spec committed ONLY on the coord worktree.
    fd = repo_root / "kitty-specs" / _ENVELOPE_SLUG_MID8
    _write_envelope_meta(fd, coordination_branch=_ENVELOPE_COORD)
    _git_q(repo_root, "add", "-A")
    _git_q(repo_root, "commit", "-m", "meta on primary")
    coord_root = repo_root / ".worktrees" / f"{_ENVELOPE_SLUG_MID8}-coord"
    coord_root.parent.mkdir(parents=True, exist_ok=True)
    _git_q(repo_root, "branch", _ENVELOPE_COORD, "main")
    _git_q(repo_root, "worktree", "add", str(coord_root), _ENVELOPE_COORD)
    coord_fd = coord_root / "kitty-specs" / _ENVELOPE_SLUG_MID8
    coord_fd.mkdir(parents=True, exist_ok=True)
    _write_envelope_meta(coord_fd, coordination_branch=_ENVELOPE_COORD)
    spec = coord_fd / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _git_q(coord_root, "add", "-A")
    _git_q(coord_root, "commit", "-m", "spec on coord")
    return spec


def _build_lanes_with_coord(repo_root: Path) -> Path:
    return _build_coord(repo_root)


def _build_create_window(repo_root: Path) -> Path:
    # #1718: coord branch DECLARED + exists, worktree NOT materialised; spec on
    # PRIMARY HEAD. The read path resolves to the PRIMARY dir.
    fd = repo_root / "kitty-specs" / _ENVELOPE_SLUG_MID8
    _write_envelope_meta(fd, coordination_branch=_ENVELOPE_COORD)
    spec = fd / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _git_q(repo_root, "add", "-A")
    _git_q(repo_root, "commit", "-m", "spec on primary (create-window)")
    _git_q(repo_root, "branch", _ENVELOPE_COORD, "main")  # exists, no worktree
    return spec


def _build_coord_deleted(repo_root: Path) -> Path:
    # #1848: coord branch declared but NEVER created → the read path raises
    # CoordinationBranchDeleted; is_committed is never reached.
    fd = repo_root / "kitty-specs" / _ENVELOPE_SLUG_MID8
    _write_envelope_meta(fd, coordination_branch=_ENVELOPE_COORD)
    spec = fd / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _git_q(repo_root, "add", "-A")
    _git_q(repo_root, "commit", "-m", "spec on primary (coord declared, branch gone)")
    return spec


# Rows whose READ surface materialises a spec ``is_committed`` actually checks.
_REACHABLE_BUILDERS = {
    "SINGLE_BRANCH-committed": _build_single_branch_committed,
    "SINGLE_BRANCH-uncommitted": _build_single_branch_uncommitted,
    "LANES": _build_lanes,
    "COORD": _build_coord,
    "LANES_WITH_COORD": _build_lanes_with_coord,
    "create-window-1718": _build_create_window,
}


def _resolve_read_surface_like_caller(repo_root: Path, handle: str) -> Path:
    """Resolve the spec_file exactly as setup-plan does (read path, require_exists)."""
    from specify_cli.missions._read_path_resolver import resolve_handle_to_read_path

    feature_dir = resolve_handle_to_read_path(repo_root, handle, require_exists=True)
    return feature_dir / "spec.md"


def _retired_placement_ref(repo_root: Path, handle: str) -> str | None:
    """The coord ref the retired OR would have used (via resolve_placement_only)."""
    from mission_runtime import resolve_placement_only, routes_through_coordination

    try:
        placement = resolve_placement_only(repo_root, handle)
    except Exception:  # noqa: BLE001 — mirror the retired caller's broad catch
        return None
    try:
        return placement.ref if routes_through_coordination(placement) else None
    except AttributeError:
        return None


@pytest.mark.parametrize(
    ("row", "expected_verdict"),
    [
        ("SINGLE_BRANCH-committed", True),
        ("SINGLE_BRANCH-uncommitted", False),
        ("LANES", True),
        ("COORD", True),
        ("LANES_WITH_COORD", True),
        ("create-window-1718", True),
    ],
)
def test_is_committed_fr011_parity(
    tmp_path: Path, row: str, expected_verdict: bool
) -> None:
    """FR-011: single-surface verdict == retired 3-leg OR verdict, on the read surface.

    For each reachable cell, resolve the READ surface like the caller, then
    assert the NEW single-surface ``is_committed`` verdict equals BOTH the
    expected verdict AND the reconstructed retired-OR verdict (parity). This is
    the equivalence evidence the FR-011 collapse rests on.
    """
    _init_repo(tmp_path)
    _REACHABLE_BUILDERS[row](tmp_path)

    spec = _resolve_read_surface_like_caller(tmp_path, _ENVELOPE_SLUG_MID8)

    diagnostics: list[str] = []
    single_surface = is_committed(spec, tmp_path, diagnostics=diagnostics)

    # Parity: reconstruct the retired OR over the SAME read-resolved spec.
    retired = _retired_or_verdict(
        spec,
        tmp_path,
        placement_ref=_retired_placement_ref(tmp_path, _ENVELOPE_SLUG_MID8),
        target_branch=_ENVELOPE_TARGET,
        primary_repo_root=tmp_path,
    )

    assert single_surface is expected_verdict, (
        f"[{row}] single-surface is_committed returned {single_surface}, "
        f"expected {expected_verdict}; diagnostics={diagnostics}"
    )
    assert single_surface is retired, (
        f"[{row}] PARITY FAILURE: single-surface={single_surface} but "
        f"retired-OR={retired} on the read-resolved spec {spec}"
    )
    assert diagnostics, f"[{row}] diagnostics sink must enumerate the checked surface(s)"


def test_is_committed_never_reached_for_coord_deleted_1848(tmp_path: Path) -> None:
    """#1848: the read path raises before ``is_committed`` for a deleted coord branch.

    Pins the UPSTREAM short-circuit (not an ``is_committed`` verdict): a mission
    declaring a coordination_branch whose ref was never created resolves through
    ``resolve_handle_to_read_path(require_exists=True)`` to a
    ``CoordinationBranchDeleted`` (a ``StatusReadPathNotFound`` subclass), so the
    setup-plan caller exits BEFORE reaching the commit check. Switching
    ``is_committed`` to the read surface therefore cannot regress coord-deleted.
    """
    from specify_cli.coordination.surface_resolver import (
        CoordinationBranchDeleted,
        StatusReadPathNotFound,
    )
    from specify_cli.missions._read_path_resolver import resolve_handle_to_read_path

    _init_repo(tmp_path)
    _build_coord_deleted(tmp_path)

    with pytest.raises(StatusReadPathNotFound) as exc_info:
        resolve_handle_to_read_path(tmp_path, _ENVELOPE_SLUG_MID8, require_exists=True)

    # Specifically the data-loss-guarding subclass (#1848), confirming the
    # caller's ``except StatusReadPathNotFound`` (→ ActionContextError → Exit(1))
    # fires before ``is_committed``.
    assert isinstance(exc_info.value, CoordinationBranchDeleted)
