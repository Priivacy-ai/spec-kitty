"""#1718 Fix C — transitional coord-topology read-path resolution.

Covers the window between ``mission create`` (which declares a
``coordination_branch`` in ``meta.json``) and the first coord write (which
materializes the ``-coord`` worktree). A *read* in that window must resolve to
the primary checkout — where the bootstrap status events live — rather than
fail closed because the declared coord worktree does not exist yet.

WP05 (coord-empty Option B / #1716 / FR-003): the materialized-but-empty coord
worktree NO LONGER fails closed. The read-path leg adopts WP01's
``probe_coord_state`` (the same discriminator the canonical surface uses) and
returns the PRIMARY checkout for the EMPTY state — matching the surface's loud
primary fallback — so every resolver leg converges. The genuine data-loss hazard
(the declared coord branch DELETED from git) is the case that still hard-fails,
now via the distinct ``CoordinationBranchDeleted`` type.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.missions._read_path_resolver import (
    _resolve_mission_read_path as resolve_mission_read_path,
)

pytestmark = [pytest.mark.fast]

_SLUG = "demo-feature"
_MID8 = "01ABCDEF"
_MISSION_DIR = f"{_SLUG}-{_MID8}"


def _seed_primary(tmp_path: Path) -> Path:
    """Create the primary mission dir declaring coord topology (as scaffold does)."""
    primary = tmp_path / "kitty-specs" / _MISSION_DIR
    primary.mkdir(parents=True)
    (primary / "meta.json").write_text(
        '{"coordination_branch": "kitty/mission-demo-feature-01ABCDEF",'
        ' "mission_slug": "demo-feature-01ABCDEF"}',
        encoding="utf-8",
    )
    (primary / "status.events.jsonl").write_text("", encoding="utf-8")
    return primary


def test_resolve_reads_primary_when_coord_declared_but_not_materialized(
    tmp_path: Path,
) -> None:
    """Declared-but-unmaterialized coord worktree → resolve to primary, not raise."""
    primary = _seed_primary(tmp_path)
    # No .worktrees/<mission>-coord/ exists.
    resolved = resolve_mission_read_path(tmp_path, _SLUG, _MID8, require_exists=True)
    assert resolved == primary, (
        "a coord_branch declared in meta.json but with no materialized worktree "
        "must read the primary checkout, not fail closed (#1718)"
    )


def test_resolve_reads_primary_when_coord_worktree_materialized_but_empty(
    tmp_path: Path,
) -> None:
    """WP05 Option B (inverted #1718 guard): a materialized coord worktree lacking
    the mission dir (the EMPTY state) now resolves to PRIMARY, not fail-closed.

    WP05 folds the read-path coord discriminator onto WP01's ``probe_coord_state``
    so the read path agrees with the canonical surface, which returns PRIMARY (with
    a loud warning) for coord-empty. The genuine data-loss hazard is the DELETED
    branch (covered by the equivalence gate's coord-deleted cells), NOT the EMPTY
    worktree — reading primary in the EMPTY window is the operator-decided Option B.
    """
    primary = _seed_primary(tmp_path)
    coord_root = CoordinationWorkspace.worktree_path(tmp_path, _SLUG, _MID8)
    coord_root.mkdir(parents=True)  # worktree materialized, but no mission dir inside
    resolved = resolve_mission_read_path(tmp_path, _SLUG, _MID8, require_exists=True)
    assert resolved == primary, (
        "a materialized-but-empty coord worktree must resolve to the PRIMARY "
        "checkout (WP05 Option B / #1716), not fail closed"
    )
