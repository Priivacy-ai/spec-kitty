"""M6 error-contract regression + WP04 coord-empty Option B boundary split.

Two coord-empty handle forms now travel DIFFERENT resolution legs, and WP04's
Option B (loud primary fallback at the canonical surface, #1716/FR-003) makes
them diverge by design:

* **canonical ``<slug>-<mid8>`` dirname** → the mid8-aware read-path leg
  (``resolve_handle_to_read_path``, ``require_exists=True``) STILL fails closed
  with the structured ``StatusReadPathNotFound`` refusal (#1589/#1821; the
  #1718 stale-surface guard, WP01-owned and intentionally preserved). That
  refusal is a ``specify_cli`` exception type; :mod:`mission_runtime` documents
  :class:`ActionContextError` as **the single error type consumers catch**, so
  it must be translated at the boundary and never escape raw (PR #1850 item M6).
* **backfilled bare dirname** → status-surface resolution, where WP04's Option B
  returns the PRIMARY checkout + a loud ``logging.WARNING`` instead of raising.
  So the boundary surfaces a resolved context (no ``ActionContextError``), and
  the fallback is observable via the surface logger.

(The slug-mid8 read-path leg closes onto primary in WP05's read-path fold; until
then this file pins the WP04 boundary split: canonical → translated refusal,
backfilled → primary + warning.)
"""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

import pytest

from mission_runtime import (
    ActionContextError,
    resolve_action_context,
    resolve_placement_only,
)

_SURFACE_LOGGER = "specify_cli.coordination.surface_resolver"

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

    The canonical ``<slug>-<mid8>`` handle travels the mid8-aware read-path leg
    (``require_exists=True``), which still fails closed for coord-empty (the
    #1718 stale-surface guard). The boundary translates that
    ``StatusReadPathNotFound`` (code ``STATUS_READ_PATH_NOT_FOUND``) to
    ``ActionContextError`` preserving the code and the generic read-path-not-found
    message — never silently falling back to the primary checkout.
    """
    assert excinfo.value.code == "STATUS_READ_PATH_NOT_FOUND"
    message = str(excinfo.value)
    assert "Status read path not found" in message, message


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


def test_action_context_backfilled_dirname_resolves_primary_with_warning(
    repo: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """WP04 Option B: bare-dir coord-empty resolves PRIMARY + loud warning.

    The backfilled bare dirname travels status-surface resolution, where Option B
    (#1716/FR-003) returns the primary checkout and emits a loud warning rather
    than raising. The boundary therefore surfaces a resolved context (no
    ``ActionContextError``), and the fallback is observable on the surface logger.
    """
    _build_mission(repo, dirname=_BACKFILLED_DIRNAME)
    _materialize_coord_root_without_mission_dir(repo, _BACKFILLED_DIRNAME)

    with caplog.at_level(logging.WARNING, logger=_SURFACE_LOGGER):
        context = resolve_action_context(
            repo, action="status", feature=_BACKFILLED_DIRNAME
        )

    assert context.feature_dir == str(repo / "kitty-specs" / _BACKFILLED_DIRNAME)
    assert any(
        r.name == _SURFACE_LOGGER and r.levelno == logging.WARNING
        for r in caplog.records
    ), "coord-empty Option B must emit a logging.WARNING (no silent fallback)"


def test_placement_only_canonical_dirname_surfaces_action_context_error(
    repo: Path,
) -> None:
    """``<slug>-<mid8>`` handle: the refusal fires in entry canonicalization."""
    _build_mission(repo, dirname=_CANONICAL_DIRNAME)
    _materialize_coord_root_without_mission_dir(repo, _CANONICAL_DIRNAME)

    with pytest.raises(ActionContextError) as excinfo:
        resolve_placement_only(repo, _CANONICAL_DIRNAME)

    _assert_fail_closed_refusal(excinfo)


def test_placement_only_backfilled_dirname_resolves_with_warning(
    repo: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """WP04 Option B: bare-dir coord-empty placement resolves (no refusal) + warns.

    The shared placement fragment builder travels the same status-surface
    resolution; under Option B it no longer raises for the bare-dir coord-empty
    handle — it returns a placement and the surface emits the loud warning.
    """
    _build_mission(repo, dirname=_BACKFILLED_DIRNAME)
    _materialize_coord_root_without_mission_dir(repo, _BACKFILLED_DIRNAME)

    with caplog.at_level(logging.WARNING, logger=_SURFACE_LOGGER):
        placement = resolve_placement_only(repo, _BACKFILLED_DIRNAME)

    assert placement is not None
    assert any(
        r.name == _SURFACE_LOGGER and r.levelno == logging.WARNING
        for r in caplog.records
    ), "coord-empty Option B must emit a logging.WARNING (no silent fallback)"
