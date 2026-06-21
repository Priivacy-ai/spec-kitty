"""Zero-mock unit tests for the WP01 shared coord helpers (T006).

Covers the two helpers extracted in WP01 so the three read-path legs call ONE
body instead of hand-building the coord compose / probe inline:

* :func:`coord_feature_dir` — the single coord-candidate compose grammar
  (``CoordinationWorkspace.worktree_path / KITTY_SPECS_DIR / <slug>-<mid8>``),
  paula C1.
* :func:`probe_coord_state` — the single topology probe discriminating
  ``MATERIALIZED | EMPTY | UNMATERIALIZED | DELETED`` (and ``NONE`` for the
  no-mid8 case), paula C2. The ``DELETED`` arm reuses
  ``surface_resolver._coord_branch_exists`` (one ``git rev-parse``) verbatim.

No mocks: a real ``git init`` repo and real ``Path.mkdir`` materialization drive
every branch, including the deleted-branch ``DELETED`` verdict via a real
``git branch -D``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.missions._read_path_resolver import (
    CoordState,
    coord_feature_dir,
    probe_coord_state,
)

pytestmark = pytest.mark.git_repo  # exercises a real ``git init`` repo via subprocess

_SLUG = "demo-feature"
_MID8 = "01KVN754"
_COORD_BRANCH = f"kitty/mission-{_SLUG}-{_MID8}-coord"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def real_git_repo(tmp_path: Path) -> Path:
    """A real git repo with one commit on a real branch (deletable)."""
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@test.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / ".kittify").mkdir()
    (tmp_path / "kitty-specs").mkdir()
    (tmp_path / "README.md").write_text("seed\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "seed")
    return tmp_path


def _materialize_coord_root(repo: Path) -> Path:
    coord_root = CoordinationWorkspace.worktree_path(repo, _SLUG, _MID8)
    coord_root.mkdir(parents=True)
    return coord_root


# --------------------------------------------------------------------------- #
# coord_feature_dir — path shape (pure-path, no fs touch needed)
# --------------------------------------------------------------------------- #


def test_coord_feature_dir_composes_canonical_shape(tmp_path: Path) -> None:
    result = coord_feature_dir(tmp_path, _SLUG, _MID8)
    expected = (
        CoordinationWorkspace.worktree_path(tmp_path, _SLUG, _MID8)
        / KITTY_SPECS_DIR
        / f"{_SLUG}-{_MID8}"
    )
    assert result == expected
    # The parent.parent of the mission dir is the coord worktree ROOT — the
    # contract probe_coord_state relies on.
    assert result.parent.parent == CoordinationWorkspace.worktree_path(
        tmp_path, _SLUG, _MID8
    )


# --------------------------------------------------------------------------- #
# probe_coord_state — the four states + NONE
# --------------------------------------------------------------------------- #


def test_probe_none_for_empty_mid8(tmp_path: Path) -> None:
    assert probe_coord_state(tmp_path, _SLUG, "") is CoordState.NONE


def test_probe_unmaterialized_when_coord_absent_no_branch(tmp_path: Path) -> None:
    """No coord root and no branch supplied → UNMATERIALIZED (never DELETED)."""
    assert probe_coord_state(tmp_path, _SLUG, _MID8) is CoordState.UNMATERIALIZED


def test_probe_unmaterialized_when_branch_still_present(real_git_repo: Path) -> None:
    """Coord absent but the declared branch still exists in git → UNMATERIALIZED."""
    _git(real_git_repo, "branch", _COORD_BRANCH)
    assert (
        probe_coord_state(
            real_git_repo, _SLUG, _MID8, coordination_branch=_COORD_BRANCH
        )
        is CoordState.UNMATERIALIZED
    )


def test_probe_empty_when_coord_root_without_mission_dir(real_git_repo: Path) -> None:
    """Coord worktree ROOT materialized but its mission dir absent → EMPTY."""
    _materialize_coord_root(real_git_repo)
    assert probe_coord_state(real_git_repo, _SLUG, _MID8) is CoordState.EMPTY


def test_probe_materialized_when_mission_dir_present(real_git_repo: Path) -> None:
    """Coord root AND its mission dir both exist → MATERIALIZED."""
    coord_feature_dir(real_git_repo, _SLUG, _MID8).mkdir(parents=True)
    assert probe_coord_state(real_git_repo, _SLUG, _MID8) is CoordState.MATERIALIZED


def test_probe_deleted_when_coord_absent_and_branch_gone(real_git_repo: Path) -> None:
    """Coord absent AND the declared branch deleted from git → DELETED.

    Real ``git branch -D``: create then delete the coord branch so the single
    ``_coord_branch_exists`` rev-parse arm returns False (no mocks).
    """
    _git(real_git_repo, "branch", _COORD_BRANCH)
    _git(real_git_repo, "branch", "-D", _COORD_BRANCH)
    assert (
        probe_coord_state(
            real_git_repo, _SLUG, _MID8, coordination_branch=_COORD_BRANCH
        )
        is CoordState.DELETED
    )


def test_probe_materialized_ignores_deleted_branch(real_git_repo: Path) -> None:
    """A materialized coord wins even if its branch is gone (DELETED arm skipped).

    The git rev-parse only runs on the absent-coord path; once the worktree is
    on disk the topology is MATERIALIZED regardless of branch state.
    """
    coord_feature_dir(real_git_repo, _SLUG, _MID8).mkdir(parents=True)
    assert (
        probe_coord_state(
            real_git_repo, _SLUG, _MID8, coordination_branch=_COORD_BRANCH
        )
        is CoordState.MATERIALIZED
    )
