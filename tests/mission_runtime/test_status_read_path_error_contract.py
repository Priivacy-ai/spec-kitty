"""M6 error-contract regression: the fail-closed surface refusal must not leak.

When the coordination worktree root is materialized on disk but its mission dir
is absent, the read resolvers raise the structured fail-closed refusal
(``StatusReadPathNotFound``, #1589/#1821/FR-005). That refusal is a
``specify_cli`` exception type; :mod:`mission_runtime` documents
:class:`ActionContextError` as **the single error type consumers catch**
(``resolution.py``), so the refusal must be translated at the boundary —
preserving the fail-closed message — and never escape as a raw traceback
through ``resolve_action_context`` / ``resolve_placement_only`` (PR #1850
review item M6).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from mission_runtime import (
    ActionContextError,
    resolve_action_context,
    resolve_placement_only,
)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

_MID8 = "01KTM6EC"
_MISSION_ID = f"{_MID8}000000000000000000"  # 26-char ULID-shaped
# Canonical post-WP03 shape: the directory name carries the mid8 suffix.
_CANONICAL_DIRNAME = f"m6-error-contract-{_MID8}"
# Backfilled/legacy shape: bare directory name; mid8 lives only in meta.json.
_BACKFILLED_DIRNAME = "m6-backfilled-mission"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.invalid")
    _git(r, "config", "user.name", "Test")
    _git(r, "config", "commit.gpgsign", "false")
    (r / ".kittify").mkdir()
    (r / ".kittify" / "config.yaml").write_text(
        "agents:\n  available:\n    - claude\n", encoding="utf-8"
    )
    return r


def _build_mission(repo: Path, *, dirname: str) -> Path:
    """Coord-topology mission in the primary checkout + commit."""
    feature_dir = repo / "kitty-specs" / dirname
    feature_dir.mkdir(parents=True)
    meta = {
        "mission_id": _MISSION_ID,
        "mid8": _MID8,
        "mission_slug": dirname,
        "mission_type": "software-dev",
        "target_branch": "main",
        "coordination_branch": f"kitty/mission-{dirname}",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (feature_dir / "tasks").mkdir()
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "fixture")
    return feature_dir


def _materialize_coord_root_without_mission_dir(repo: Path, dirname: str) -> Path:
    """The fail-closed window: coord worktree root exists, mission dir absent."""
    composed = dirname if dirname.endswith(f"-{_MID8}") else f"{dirname}-{_MID8}"
    coord_root = repo / ".worktrees" / f"{composed}-coord"
    coord_root.mkdir(parents=True)
    return coord_root


def _assert_fail_closed_refusal(excinfo: pytest.ExceptionInfo[ActionContextError]) -> None:
    """The translation must keep the stable code AND a fail-closed refusal message.

    The refusal surfaces in one of two forms, both carrying the stable
    ``STATUS_READ_PATH_NOT_FOUND`` code and neither silently falling back to the
    primary checkout:
    - the generic read-path-not-found message (canonical-dirname slug resolution), or
    - the specific FR-006 coord-empty hard-fail (``CoordinationWorktreeEmpty``, a
      ``StatusReadPathNotFound`` subclass introduced by mission 01KVGCE8) when the
      coordination worktree is materialized but empty (the backfilled-dirname path).
    """
    assert excinfo.value.code == "STATUS_READ_PATH_NOT_FOUND"
    message = str(excinfo.value)
    assert (
        "Status read path not found" in message
        or "materialized but empty" in message
    ), message


def test_action_context_canonical_dirname_surfaces_action_context_error(
    repo: Path,
) -> None:
    """``<slug>-<mid8>`` handle: the refusal fires in mission-slug resolution."""
    _build_mission(repo, dirname=_CANONICAL_DIRNAME)
    _materialize_coord_root_without_mission_dir(repo, _CANONICAL_DIRNAME)

    with pytest.raises(ActionContextError) as excinfo:
        resolve_action_context(repo, action="status", feature=_CANONICAL_DIRNAME)

    _assert_fail_closed_refusal(excinfo)
    assert _CANONICAL_DIRNAME in str(excinfo.value)


def test_action_context_backfilled_dirname_surfaces_action_context_error(
    repo: Path,
) -> None:
    """Bare-dir mission: the refusal fires in status-surface resolution."""
    _build_mission(repo, dirname=_BACKFILLED_DIRNAME)
    _materialize_coord_root_without_mission_dir(repo, _BACKFILLED_DIRNAME)

    with pytest.raises(ActionContextError) as excinfo:
        resolve_action_context(repo, action="status", feature=_BACKFILLED_DIRNAME)

    _assert_fail_closed_refusal(excinfo)
    assert _BACKFILLED_DIRNAME in str(excinfo.value)


def test_placement_only_canonical_dirname_surfaces_action_context_error(
    repo: Path,
) -> None:
    """``<slug>-<mid8>`` handle: the refusal fires in entry canonicalization."""
    _build_mission(repo, dirname=_CANONICAL_DIRNAME)
    _materialize_coord_root_without_mission_dir(repo, _CANONICAL_DIRNAME)

    with pytest.raises(ActionContextError) as excinfo:
        resolve_placement_only(repo, _CANONICAL_DIRNAME)

    _assert_fail_closed_refusal(excinfo)


def test_placement_only_backfilled_dirname_surfaces_action_context_error(
    repo: Path,
) -> None:
    """Bare-dir mission: the refusal fires in the shared fragment builder."""
    _build_mission(repo, dirname=_BACKFILLED_DIRNAME)
    _materialize_coord_root_without_mission_dir(repo, _BACKFILLED_DIRNAME)

    with pytest.raises(ActionContextError) as excinfo:
        resolve_placement_only(repo, _BACKFILLED_DIRNAME)

    _assert_fail_closed_refusal(excinfo)
