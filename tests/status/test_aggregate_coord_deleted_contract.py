"""WP05 (T026) — coord-deleted convergence contract: all three legs hard-fail.

Mission ``mission-surface-resolver-safety-net-01KVN754`` WP05 drains the last
equivalence-gate cells by converging the **coord-deleted** topology onto ONE loud
hard-fail. A coordination branch declared in ``meta.json`` but DELETED from git,
with no coord worktree on disk, is *data loss* (#1848 / FR-005) — never a silent
stale-primary read. After WP05 every read-side resolution leg raises the SAME
distinct type and ``error_code``:

* ``missions._read_path_resolver.resolve_handle_to_read_path`` (``require_exists=True``)
  — T022 read-path fold (probe ``DELETED`` arm → hard-fail).
* ``coordination.surface_resolver.resolve_status_surface_with_anchor`` — the
  canonical surface (already hard-failed ``DELETED`` pre-WP05).
* ``status.aggregate.MissionStatus.load`` — T023: the aggregate now propagates the
  deleted-branch type VERBATIM via a more-specific ``except`` AHEAD of the
  ``StatusReadPathNotFound`` → ``CoordAuthorityUnavailable`` re-wrap.

All three must raise :class:`CoordinationBranchDeleted` with
``error_code == "COORDINATION_BRANCH_DELETED"``. Production-shaped identity: a real
26-char ULID (Mission Identity Model 083+), the first 8 chars as the ``mid8``
disambiguator, and the real on-disk ``kitty-specs/<slug>-<mid8>/`` layout.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.coordination.surface_resolver import (
    CoordinationBranchDeleted,
    resolve_status_surface_with_anchor,
)
from specify_cli.missions._read_path_resolver import resolve_handle_to_read_path
from specify_cli.status.aggregate import MissionStatus

pytestmark = pytest.mark.git_repo

# Production-shaped identity: a real 26-char ULID, mid8 = first 8 chars.
MISSION_ID = "01KVN754TY9CVJ8G10ERTMPVRH"
MID8 = MISSION_ID[:8]
MISSION_SLUG = "coord-deleted-contract"
SLUG_WITH_MID8 = f"{MISSION_SLUG}-{MID8}"
COORD_BRANCH = f"kitty/mission-{SLUG_WITH_MID8}"


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _build_coord_deleted(repo_root: Path) -> None:
    """Real git repo: primary declares the coord branch, but it is gone from git.

    ``coordination_branch`` is recorded in ``meta.json`` while the branch is never
    created in git and no coord worktree exists → the DELETED topology state (R3).
    """
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "coord-deleted@example.test")
    _git(repo_root, "config", "user.name", "Coord Deleted Contract")
    _git(repo_root, "commit", "--allow-empty", "-qm", "init")

    feature_dir = repo_root / "kitty-specs" / SLUG_WITH_MID8
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {"mission_id": MISSION_ID, "coordination_branch": COORD_BRANCH}
        ),
        encoding="utf-8",
    )


# Handle forms that resolve onto the on-disk composed primary dir and therefore
# MUST converge on the coord-deleted hard-fail across all three legs: the canonical
# ``<slug>-<mid8>`` literal, the bare ``mid8``, and the full ULID. The non-composed
# forms (bare mid8 / full ULID) exercise the ``read_primary_meta`` canonicalize-on-
# miss path: without it the raw handle finds no primary meta, ``coordination_branch``
# is never learned, the DELETED gate is skipped, and the read-path leg leaks a STALE
# PRIMARY dir while the surface leg hard-fails — the #1848 data-loss divergence this
# contract guards (caught live by debugger-debbie on PR #2065).
#
# The bare *human* slug is deliberately excluded: its on-disk dir carries the
# composed ``<slug>-<mid8>`` name, so bare→composed resolution is the separate #2050
# concern, not the coord-deleted convergence.
_RESOLVING_HANDLES = [SLUG_WITH_MID8, MID8, MISSION_ID]


@pytest.mark.parametrize("handle", _RESOLVING_HANDLES)
def test_read_path_leg_hard_fails_coord_deleted(tmp_path: Path, handle: str) -> None:
    """T022: the read-path leg hard-fails ``CoordinationBranchDeleted``."""
    _build_coord_deleted(tmp_path)
    with pytest.raises(CoordinationBranchDeleted) as excinfo:
        resolve_handle_to_read_path(tmp_path, handle, require_exists=True)
    assert excinfo.value.error_code == "COORDINATION_BRANCH_DELETED"


@pytest.mark.parametrize("handle", _RESOLVING_HANDLES)
def test_surface_leg_hard_fails_coord_deleted(tmp_path: Path, handle: str) -> None:
    """The canonical surface hard-fails ``CoordinationBranchDeleted``."""
    _build_coord_deleted(tmp_path)
    with pytest.raises(CoordinationBranchDeleted) as excinfo:
        resolve_status_surface_with_anchor(tmp_path, handle)
    assert excinfo.value.error_code == "COORDINATION_BRANCH_DELETED"


@pytest.mark.parametrize("handle", _RESOLVING_HANDLES)
def test_aggregate_leg_hard_fails_coord_deleted(tmp_path: Path, handle: str) -> None:
    """T023: the aggregate propagates ``CoordinationBranchDeleted`` VERBATIM.

    Mutation: dropping the more-specific ``except CoordinationBranchDeleted: raise``
    (or placing it AFTER the ``StatusReadPathNotFound`` re-wrap) re-spells the error
    ``CoordAuthorityUnavailable`` and this test fails — the precise ordering trap.
    """
    _build_coord_deleted(tmp_path)
    with pytest.raises(CoordinationBranchDeleted) as excinfo:
        MissionStatus.load(repo_root=tmp_path, mission_slug=handle)
    assert excinfo.value.error_code == "COORDINATION_BRANCH_DELETED"
    assert excinfo.value.coordination_branch == COORD_BRANCH
