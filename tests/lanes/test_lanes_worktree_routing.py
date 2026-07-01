"""Byte-identical routing assertions for WP04 (mission 01KV6510).

For each of the 4 routed files, we verify that the seam function
``worktree_path`` / ``worktree_dir_name`` (with ``mission_id=None``)
reproduces EXACTLY the old f-string ``f"{slug}-{lane_id}"`` grammar.

We import GOLDEN_ROWS from the WP01 oracle so these assertions are
pinned to the same reference values that seam tests use.

T020: routing call-site byte-identical proof.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.lanes.branch_naming import worktree_dir_name, worktree_path
from tests.lanes.test_branch_naming_seam import GOLDEN_ROWS, GoldenRow

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _legacy_row() -> GoldenRow:
    return next(r for r in GOLDEN_ROWS if r.mission_id is None)


# ---------------------------------------------------------------------------
# T020-A: worktree_path(mission_id=None) is byte-identical to the old f-strings
# in merge.py, recovery.py (×2), and lifecycle_sync.py (×2).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("row", GOLDEN_ROWS, ids=lambda r: r.label)
def test_worktree_path_mission_id_none_matches_golden(
    row: GoldenRow,
    tmp_path: Path,
) -> None:
    """worktree_path(..., mission_id=None) reproduces the on-disk dir name.

    This is the routing contract for T016 (merge.py), T017 (recovery.py ×2)
    and T018 (lifecycle_sync.py ×2): each site now calls
    ``worktree_path(repo_root, mission_slug, mission_id=None, lane_id=…)``
    instead of ``repo_root / ".worktrees" / f"{mission_slug}-{lane_id}"``.
    """
    seam_path = worktree_path(
        tmp_path, row.mission_slug, mission_id=None, lane_id=row.lane_id
    )
    # The expected path is the old f-string, unchanged:
    expected = tmp_path / ".worktrees" / f"{row.mission_slug}-{row.lane_id}"
    assert seam_path == expected, (
        f"[{row.label}] worktree_path mismatch: {seam_path!r} != {expected!r}"
    )


@pytest.mark.parametrize("row", GOLDEN_ROWS, ids=lambda r: r.label)
def test_worktree_path_mission_id_none_matches_worktree_dir(
    row: GoldenRow,
    tmp_path: Path,
) -> None:
    """worktree_path(..., mission_id=None).name == worktree_dir_name(..., mission_id=None).

    Proves the two seam functions are consistent with each other.
    """
    path = worktree_path(
        tmp_path, row.mission_slug, mission_id=None, lane_id=row.lane_id
    )
    dir_name = worktree_dir_name(row.mission_slug, mission_id=None, lane_id=row.lane_id)
    assert path.name == dir_name


# ---------------------------------------------------------------------------
# T020-B: worktree_dir_name(mission_id=None) is byte-identical to the old
# context_name f-string in implement_support.py:120.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("row", GOLDEN_ROWS, ids=lambda r: r.label)
def test_worktree_dir_name_mission_id_none_matches_context_name_fstring(
    row: GoldenRow,
) -> None:
    """worktree_dir_name(..., mission_id=None) reproduces context_name f-string.

    T019 routing contract: implement_support.py used
    ``context_name = f"{mission_slug}-{lane_id}"``.
    The seam call ``worktree_dir_name(mission_slug, mission_id=None, lane_id=lane_id)``
    must return the SAME string.
    """
    seam_name = worktree_dir_name(
        row.mission_slug, mission_id=None, lane_id=row.lane_id
    )
    expected = f"{row.mission_slug}-{row.lane_id}"
    assert seam_name == expected, (
        f"[{row.label}] context_name mismatch: {seam_name!r} != {expected!r}"
    )


# ---------------------------------------------------------------------------
# T020-C: golden-table legacy row — explicit cross-check of worktree_dir value.
# ---------------------------------------------------------------------------


def test_legacy_row_worktree_dir_is_slug_dash_lane() -> None:
    """The legacy golden row's worktree_dir == '<slug>-<lane_id>' — no mid8."""
    row = _legacy_row()
    assert row.worktree_dir == f"{row.mission_slug}-{row.lane_id}"
    # And the seam agrees:
    assert (
        worktree_dir_name(row.mission_slug, mission_id=None, lane_id=row.lane_id)
        == row.worktree_dir
    )


# ---------------------------------------------------------------------------
# T020-D: confirm the seam preserves path under `.worktrees/` (grep-clean proof).
# ---------------------------------------------------------------------------


def test_worktree_path_places_dir_under_dot_worktrees(tmp_path: Path) -> None:
    """The seam always emits ``<repo_root>/.worktrees/<dir>``.

    Regression-lock: the old f-string sites joined with ``/ ".worktrees" /``;
    this test confirms the seam preserves that invariant.
    """
    slug = "057-example"
    lane = "lane-b"
    p = worktree_path(tmp_path, slug, mission_id=None, lane_id=lane)
    assert p.parent == tmp_path / ".worktrees"
    assert p.name == f"{slug}-{lane}"
