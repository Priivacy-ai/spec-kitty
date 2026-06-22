"""Tests for the coordination-topology-aware ``is_committed()`` overload.

Covers:
- Flat topology (no placement): original HEAD-only behaviour preserved.
- Coord topology: file found on coord branch returns True even when absent on HEAD.
- Coord topology: file absent on both coord branch and HEAD returns False.
- Coord topology: coord branch lookup fails gracefully, falls back to HEAD.
- Non-COORDINATION placement kind: HEAD-only check used (FLATTENED / PRIMARY).

Issue #1884 / FR-003 / WP01.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.missions._substantive import is_committed

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_repo(tmp_path: Path) -> str:
    """Set up a minimal git repository with an initial commit.

    Returns the default branch name (``main`` or ``master`` depending on git config).
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


def _make_commit_target(ref: str, kind_str: str) -> object:
    """Construct a CommitTarget using the mission_runtime dataclass."""
    from mission_runtime import CommitTarget, CommitTargetKind

    kind = CommitTargetKind[kind_str]
    return CommitTarget(ref=ref, kind=kind)


# ---------------------------------------------------------------------------
# Flat-topology (no placement): original HEAD-only behaviour
# ---------------------------------------------------------------------------


def test_no_placement_file_committed_on_head_returns_true(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _commit_file(tmp_path, spec, "add spec")

    assert is_committed(spec, tmp_path) is True


def test_no_placement_file_not_committed_returns_false(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    # Not committed — only written to disk.

    assert is_committed(spec, tmp_path) is False


def test_no_placement_file_outside_repo_returns_false(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    # Use a file that lives outside tmp_path entirely.
    outside = tmp_path.parent / f"outside_{tmp_path.name}.md"
    outside.write_text("x\n", encoding="utf-8")
    try:
        assert is_committed(outside, tmp_path) is False
    finally:
        outside.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Coord-topology: file on coord branch, absent from HEAD
# ---------------------------------------------------------------------------


def test_coord_placement_file_on_coord_branch_returns_true(tmp_path: Path) -> None:
    """Spec committed only to the coordination branch satisfies the gate."""
    _init_repo(tmp_path)

    # Create a coordination branch and commit spec.md there.
    coord_ref = "kitty/mission-test-ABCD1234"
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", "-b", coord_ref],
        check=True,
        capture_output=True,
    )
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _commit_file(tmp_path, spec, "add spec on coord")

    # Switch back to main so spec.md is NOT on HEAD.
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", "main"],
        check=True,
        capture_output=True,
    )
    # Confirm the file is absent from HEAD.
    result = subprocess.run(
        ["git", "-C", str(tmp_path), "cat-file", "-e", "HEAD:spec.md"],
        capture_output=True,
    )
    assert result.returncode != 0, "Precondition: spec.md must NOT be on HEAD"

    placement = _make_commit_target(coord_ref, "COORDINATION")
    assert is_committed(spec, tmp_path, placement=placement) is True  # type: ignore[arg-type]


def test_coord_placement_file_in_coord_worktree_returns_true(tmp_path: Path) -> None:
    """A spec path under .worktrees resolves against the coord branch tree."""
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

    placement = _make_commit_target(coord_ref, "COORDINATION")
    assert is_committed(spec, tmp_path, placement=placement) is True  # type: ignore[arg-type]


def test_coord_placement_file_on_both_branches_returns_true(tmp_path: Path) -> None:
    """File on HEAD AND coord branch: still True (OR logic)."""
    _init_repo(tmp_path)
    coord_ref = "kitty/mission-test-BBBB2222"

    # Commit spec.md on main (HEAD).
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _commit_file(tmp_path, spec, "add spec on main")

    # Also commit a version on the coord branch.
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", "-b", coord_ref],
        check=True,
        capture_output=True,
    )
    spec.write_text("# Spec (coord version)\n", encoding="utf-8")
    _commit_file(tmp_path, spec, "update spec on coord")
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", "main"],
        check=True,
        capture_output=True,
    )

    placement = _make_commit_target(coord_ref, "COORDINATION")
    assert is_committed(spec, tmp_path, placement=placement) is True  # type: ignore[arg-type]


def test_coord_placement_file_absent_from_both_branches_returns_false(tmp_path: Path) -> None:
    """File absent from both coord branch and HEAD: False."""
    _init_repo(tmp_path)
    coord_ref = "kitty/mission-test-CCCC3333"

    # Create the coord branch without spec.md.
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", "-b", coord_ref],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", "main"],
        check=True,
        capture_output=True,
    )

    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")  # on disk but never committed

    placement = _make_commit_target(coord_ref, "COORDINATION")
    assert is_committed(spec, tmp_path, placement=placement) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Coord-topology: invalid / non-existent coord branch falls back to HEAD
# ---------------------------------------------------------------------------


def test_coord_placement_nonexistent_branch_falls_back_to_head(tmp_path: Path) -> None:
    """Non-existent coord branch: cat-file fails, falls back to HEAD check."""
    _init_repo(tmp_path)

    # Commit spec.md to HEAD (no coord branch exists at all).
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _commit_file(tmp_path, spec, "add spec")

    # Reference a branch that does not exist.
    placement = _make_commit_target("kitty/nonexistent-DEADBEEF", "COORDINATION")
    # Falls back to HEAD — spec IS on HEAD, so returns True.
    assert is_committed(spec, tmp_path, placement=placement) is True  # type: ignore[arg-type]


def test_coord_placement_nonexistent_branch_file_absent_from_head_returns_false(
    tmp_path: Path,
) -> None:
    """Non-existent coord branch AND file absent from HEAD: False."""
    _init_repo(tmp_path)
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")  # on disk, not committed

    placement = _make_commit_target("kitty/nonexistent-DEADBEEF", "COORDINATION")
    assert is_committed(spec, tmp_path, placement=placement) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Non-COORDINATION placement kinds: HEAD-only check
# ---------------------------------------------------------------------------


def test_flattened_placement_uses_head_check(tmp_path: Path) -> None:
    """FLATTENED placement: coord fast-path is skipped, falls back to HEAD."""
    _init_repo(tmp_path)
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _commit_file(tmp_path, spec, "add spec")

    placement = _make_commit_target("main", "FLATTENED")
    assert is_committed(spec, tmp_path, placement=placement) is True  # type: ignore[arg-type]


def test_primary_placement_uses_head_check(tmp_path: Path) -> None:
    """PRIMARY placement: coord fast-path is skipped, falls back to HEAD."""
    _init_repo(tmp_path)
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _commit_file(tmp_path, spec, "add spec")

    placement = _make_commit_target("main", "PRIMARY")
    assert is_committed(spec, tmp_path, placement=placement) is True  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# WP07 / T035 (FR-011) — protected behavioral envelope, parametrized.
#
# The randy-reducer equivalence-evidence base for the (deferred, gated) FR-011
# collapse of the ``is_committed`` 3-leg OR. Each row builds a realistic on-disk
# topology, resolves the ``placement`` THROUGH the live ``resolve_placement_only``
# seam EXACTLY as the ``setup-plan`` caller does (including its broad-catch
# fallback to ``placement=None`` when resolution hard-fails), and pins the
# ``is_committed`` verdict for that (topology × transient). This is the envelope a
# single-surface check would have to reproduce IDENTICALLY before the OR can be
# collapsed.
#
# Witnessed gate finding (2026-06-22, randy-reducer): the FR-011 collapse is NOT
# yet safe. For the #1718 create-window the resolved placement is COORDINATION
# (coord branch declared; materialisation deferred to the commit boundary) while
# the artifact is committed on PRIMARY — so a single-surface check on the coord
# ref returns ``False`` where the 3-leg OR (via the HEAD leg) returns ``True``.
# The HEAD leg is therefore STILL load-bearing for the create-window: the surface
# is not yet structurally single. These rows pin that envelope so a future
# collapse that regresses any row goes red (and the create-window row in
# particular guards the TOP mission risk).
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


def _resolve_placement_like_caller(repo_root: Path, handle: str) -> object | None:
    """Mirror the ``setup-plan`` placement resolution + its broad-catch fallback.

    The live caller (``cli/commands/agent/mission.py``) wraps
    ``resolve_placement_only`` in ``except Exception: placement = None`` (C-004
    strangler safety) — a coord-deleted mission therefore reaches ``is_committed``
    with ``placement=None`` rather than a stale COORDINATION ref.
    """
    from mission_runtime import resolve_placement_only

    try:
        return resolve_placement_only(repo_root, handle)
    except Exception:  # noqa: BLE001 — mirror the caller's deliberate broad catch
        return None


def _build_single_branch_committed(repo_root: Path) -> tuple[Path, bool]:
    fd = repo_root / "kitty-specs" / _ENVELOPE_SLUG_MID8
    _write_envelope_meta(fd, coordination_branch=None)
    spec = fd / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _git_q(repo_root, "add", "-A")
    _git_q(repo_root, "commit", "-m", "spec on primary")
    return spec, True


def _build_single_branch_uncommitted(repo_root: Path) -> tuple[Path, bool]:
    fd = repo_root / "kitty-specs" / _ENVELOPE_SLUG_MID8
    _write_envelope_meta(fd, coordination_branch=None)
    spec = fd / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")  # on disk only, never committed
    return spec, False


def _build_lanes(repo_root: Path) -> tuple[Path, bool]:
    # LANES flattens to a primary/FLATTENED placement; artifact on the target ref.
    return _build_single_branch_committed(repo_root)


def _build_coord(repo_root: Path) -> tuple[Path, bool]:
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
    _write_envelope_meta(coord_fd, coordination_branch=_ENVELOPE_COORD)
    spec = coord_fd / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _git_q(coord_root, "add", "-A")
    _git_q(coord_root, "commit", "-m", "spec on coord")
    return spec, True


def _build_lanes_with_coord(repo_root: Path) -> tuple[Path, bool]:
    return _build_coord(repo_root)


def _build_create_window(repo_root: Path) -> tuple[Path, bool]:
    # #1718: coord branch DECLARED + exists, worktree NOT materialised; spec on
    # PRIMARY HEAD. The resolved placement is COORDINATION (materialisation
    # deferred to the commit boundary) — the HEAD leg is what carries the verdict.
    fd = repo_root / "kitty-specs" / _ENVELOPE_SLUG_MID8
    _write_envelope_meta(fd, coordination_branch=_ENVELOPE_COORD)
    spec = fd / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _git_q(repo_root, "add", "-A")
    _git_q(repo_root, "commit", "-m", "spec on primary (create-window)")
    _git_q(repo_root, "branch", _ENVELOPE_COORD, "main")  # exists, no worktree
    return spec, True


def _build_coord_deleted(repo_root: Path) -> tuple[Path, bool]:
    # #1848: coord branch declared but NEVER created → resolve_placement_only
    # hard-fails COORDINATION_BRANCH_DELETED → caller falls to placement=None;
    # spec is on PRIMARY HEAD so the verdict is True via the HEAD/primary surface.
    fd = repo_root / "kitty-specs" / _ENVELOPE_SLUG_MID8
    _write_envelope_meta(fd, coordination_branch=_ENVELOPE_COORD)
    spec = fd / "spec.md"
    spec.write_text("# Spec\n", encoding="utf-8")
    _git_q(repo_root, "add", "-A")
    _git_q(repo_root, "commit", "-m", "spec on primary (coord declared, branch gone)")
    return spec, True


_ENVELOPE_BUILDERS = {
    "SINGLE_BRANCH-committed": _build_single_branch_committed,
    "SINGLE_BRANCH-uncommitted": _build_single_branch_uncommitted,
    "LANES": _build_lanes,
    "COORD": _build_coord,
    "LANES_WITH_COORD": _build_lanes_with_coord,
    "create-window-1718": _build_create_window,
    "coord-deleted-1848": _build_coord_deleted,
}


@pytest.mark.parametrize(
    ("row", "expected_verdict"),
    [
        ("SINGLE_BRANCH-committed", True),
        ("SINGLE_BRANCH-uncommitted", False),
        ("LANES", True),
        ("COORD", True),
        ("LANES_WITH_COORD", True),
        ("create-window-1718", True),
        ("coord-deleted-1848", True),
    ],
)
def test_is_committed_protected_envelope(
    tmp_path: Path, row: str, expected_verdict: bool
) -> None:
    """T035 (FR-011): pin ``is_committed`` per (topology × transient) via the live seam.

    Resolves ``placement`` through ``resolve_placement_only`` exactly as the
    ``setup-plan`` caller does, then asserts the ``is_committed`` verdict. The
    rows are the 4 ``MissionTopology`` cells plus the #1718 create-window and
    #1848 coord-deleted transients. A single-surface reduction of the OR MUST
    reproduce every verdict here — the create-window row in particular guards
    against a collapse that drops the still-load-bearing HEAD leg.
    """
    _init_repo(tmp_path)
    spec, _ = _ENVELOPE_BUILDERS[row](tmp_path)

    placement = _resolve_placement_like_caller(tmp_path, _ENVELOPE_SLUG_MID8)
    diagnostics: list[str] = []
    verdict = is_committed(
        spec,
        tmp_path,
        placement=placement,  # type: ignore[arg-type]
        target_branch=_ENVELOPE_TARGET,
        primary_repo_root=tmp_path,
        diagnostics=diagnostics,
    )

    assert verdict is expected_verdict, (
        f"[{row}] is_committed returned {verdict}, expected {expected_verdict}; "
        f"placement={placement}; diagnostics={diagnostics}"
    )
    # The diagnostics sink MUST stay populated (the setup-plan caller surfaces
    # this as ``spec_commit_surfaces_checked``).
    assert diagnostics, f"[{row}] diagnostics sink must enumerate the checked surface(s)"
