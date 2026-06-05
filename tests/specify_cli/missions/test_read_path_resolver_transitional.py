"""#1718 Fix C — transitional coord-topology read-path resolution.

Covers the window between ``mission create`` (which declares a
``coordination_branch`` in ``meta.json``) and the first coord write (which
materializes the ``-coord`` worktree). A *read* in that window must resolve to
the primary checkout — where the bootstrap status events live — rather than
fail closed because the declared coord worktree does not exist yet.

The fail-closed behaviour is still correct once the worktree IS materialized but
its mission dir is empty/stale (the genuine hazard the original guard targeted).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.missions._read_path_resolver import (
    StatusReadPathNotFound,
    resolve_mission_read_path,
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


def test_resolve_fails_closed_when_coord_worktree_materialized_but_empty(
    tmp_path: Path,
) -> None:
    """Guard preserved: a materialized coord worktree lacking the mission dir is
    the genuine stale/empty hazard and must still fail closed."""
    _seed_primary(tmp_path)
    coord_root = CoordinationWorkspace.worktree_path(tmp_path, _SLUG, _MID8)
    coord_root.mkdir(parents=True)  # worktree materialized, but no mission dir inside
    with pytest.raises(StatusReadPathNotFound):
        resolve_mission_read_path(tmp_path, _SLUG, _MID8, require_exists=True)
