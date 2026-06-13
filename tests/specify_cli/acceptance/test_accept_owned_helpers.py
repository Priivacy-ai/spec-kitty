"""Unit coverage for the WP02 ACCEPT_OWNED exclusion helpers (C-GATE-2 / NFR-003).

The accept gate snapshots ``git status --porcelain`` and refuses to proceed on a
dirty tree. Its *own* derived writes (``acceptance-matrix.json`` + ``status.json``,
scoped to the mission dir) must never trip that check, while every non-accept-owned
dirty path stays fail-closed. These tests pin the pure helpers that implement that
exclusion: :func:`_accept_owned_relpaths`, :func:`_porcelain_path`, and
:func:`_filter_accept_owned_dirty`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.acceptance import (
    ACCEPT_OWNED_BASENAMES,
    _accept_owned_relpaths,  # noqa: PLC2701 — internal helper tested deliberately
    _filter_accept_owned_dirty,  # noqa: PLC2701 — internal helper tested deliberately
    _porcelain_path,  # noqa: PLC2701 — internal helper tested deliberately
)

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# _accept_owned_relpaths
# ---------------------------------------------------------------------------


def test_accept_owned_relpaths_scoped_to_feature_dir(tmp_path: Path) -> None:
    """Returns POSIX-normalized repo-relative paths for each accept-owned basename."""
    feature_dir = tmp_path / "kitty-specs" / "099-feat"
    feature_dir.mkdir(parents=True)
    owned = _accept_owned_relpaths(tmp_path, feature_dir)
    assert owned == frozenset(
        f"kitty-specs/099-feat/{basename}" for basename in ACCEPT_OWNED_BASENAMES
    )


def test_accept_owned_relpaths_dedupes_repeated_feature_dirs(tmp_path: Path) -> None:
    """The same feature dir passed twice (primary == status dir) is visited once."""
    feature_dir = tmp_path / "kitty-specs" / "099-feat"
    feature_dir.mkdir(parents=True)
    owned = _accept_owned_relpaths(tmp_path, feature_dir, feature_dir)
    assert len(owned) == len(ACCEPT_OWNED_BASENAMES)


def test_accept_owned_relpaths_skips_dirs_outside_repo_root(tmp_path: Path) -> None:
    """An accept-owned artifact living outside the repo root cannot collide with
    porcelain output, so it is skipped (the ``relative_to`` ValueError branch)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    outside = tmp_path / "elsewhere" / "coord-feat"
    outside.mkdir(parents=True)
    # Outside dir contributes nothing; inside dir contributes its basenames.
    inside = repo_root / "kitty-specs" / "099-feat"
    inside.mkdir(parents=True)
    owned = _accept_owned_relpaths(repo_root, outside, inside)
    assert owned == frozenset(
        f"kitty-specs/099-feat/{basename}" for basename in ACCEPT_OWNED_BASENAMES
    )


# ---------------------------------------------------------------------------
# _porcelain_path
# ---------------------------------------------------------------------------


def test_porcelain_path_plain_entry() -> None:
    assert _porcelain_path(" M kitty-specs/099-feat/status.json") == (
        "kitty-specs/099-feat/status.json"
    )


def test_porcelain_path_rename_entry_takes_destination() -> None:
    """Rename entries ``old -> new`` resolve to the destination path."""
    line = "R  kitty-specs/old.json -> kitty-specs/new.json"
    assert _porcelain_path(line) == "kitty-specs/new.json"


def test_porcelain_path_short_line_is_empty() -> None:
    """A line shorter than the 3-char status prefix yields an empty path."""
    assert _porcelain_path("M") == ""


# ---------------------------------------------------------------------------
# _filter_accept_owned_dirty
# ---------------------------------------------------------------------------


def test_filter_accept_owned_dirty_drops_only_owned_paths() -> None:
    owned = frozenset({"kitty-specs/099-feat/status.json"})
    git_dirty = [
        " M kitty-specs/099-feat/status.json",  # accept-owned → dropped
        " M src/app.py",  # non-owned → preserved verbatim
    ]
    assert _filter_accept_owned_dirty(git_dirty, owned) == [" M src/app.py"]


def test_filter_accept_owned_dirty_no_owned_returns_input_unchanged() -> None:
    """Empty owned set short-circuits and returns the snapshot untouched."""
    git_dirty = [" M src/app.py", "?? new.txt"]
    assert _filter_accept_owned_dirty(git_dirty, frozenset()) == git_dirty


def test_filter_accept_owned_dirty_preserves_non_owned_when_owned_present() -> None:
    """A non-accept-owned dirty path is never dropped (fail-closed, NFR-003)."""
    owned = frozenset({"kitty-specs/099-feat/acceptance-matrix.json"})
    git_dirty = [" M docs/readme.md"]
    assert _filter_accept_owned_dirty(git_dirty, owned) == [" M docs/readme.md"]
