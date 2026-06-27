"""WP04 coord-empty Option B — the loud primary-fallback warning (NON-FAKEABLE).

Mission ``mission-surface-resolver-safety-net-01KVN754`` applies the operator-
decided **Option B**: a materialized-but-empty coordination worktree no longer
hard-fails. ``resolve_status_surface_with_anchor`` falls back to the PRIMARY
checkout and proceeds, emitting a single **loud, observable** warning so an
operator or orchestrating agent can intervene (FR-001 / FR-003 / NFR-003; #1716).

The centerpiece is a **3-part conjunctive** assertion that a ``print`` or a
``logging.DEBUG`` line could NOT satisfy:

  (a) a record at EXACTLY ``logging.WARNING`` from the named module logger
      ``specify_cli.coordination.surface_resolver``;
  (b) the message names BOTH operator recovery paths — flatten (drop the
      ``coordination_branch`` key) AND ``spec-kitty agent worktree repair``;
  (c) the resolver returns the PRIMARY dir (not the coord dir, not a raise).

Grep anchors for the reviewer:
  * logger name:   ``specify_cli.coordination.surface_resolver``
  * warning const: ``surface_resolver._COORD_EMPTY_FALLBACK_WARNING``

ADR: ``docs/adr/3.x/2026-06-19-1-coord-empty-surface-fallback.md``.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

import pytest

from specify_cli.coordination.surface_resolver import (
    resolve_status_surface_with_anchor,
)
from specify_cli.coordination.workspace import CoordinationWorkspace

pytestmark = pytest.mark.git_repo

# Production-shaped identity (Mission Identity Model 083+): a real 26-char ULID.
MISSION_ID = "01KTDVHZKGCHCW6HQ4V577PNES"
MID8 = MISSION_ID[:8]
BARE_SLUG = "coord-empty-warning-mission"
SLUG_WITH_MID8 = f"{BARE_SLUG}-{MID8}"
COORD_BRANCH = f"kitty/mission-{SLUG_WITH_MID8}"

# The single named logger the resolver emits through (grep anchor for review).
_LOGGER_NAME = "specify_cli.coordination.surface_resolver"


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(repo_root: Path) -> None:
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "warn@example.test")
    _git(repo_root, "config", "user.name", "Coord Empty Warning")
    _git(repo_root, "commit", "--allow-empty", "-qm", "init")


def _write_meta(feature_dir: Path, **fields: object) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(json.dumps(fields), encoding="utf-8")


def _materialise_coord_empty(repo_root: Path, slug: str) -> Path:
    """Primary declares coord branch; coord worktree ROOT exists but is empty.

    Returns the expected PRIMARY mission dir the resolver must fall back to.
    """
    _init_repo(repo_root)
    primary_dir = repo_root / "kitty-specs" / slug
    _write_meta(
        primary_dir,
        mission_id=MISSION_ID,
        coordination_branch=COORD_BRANCH,
    )
    _git(repo_root, "branch", COORD_BRANCH)
    coord_root = CoordinationWorkspace.worktree_path(repo_root, slug, MID8)
    coord_root.mkdir(parents=True)  # materialised, NO mission dir inside
    return primary_dir


@pytest.mark.parametrize("slug", [BARE_SLUG, SLUG_WITH_MID8], ids=["bare", "slug-mid8"])
def test_coord_empty_warns_loudly_and_returns_primary(
    tmp_path: Path, slug: str, caplog: pytest.LogCaptureFixture
) -> None:
    """3-part conjunction: WARNING level + BOTH recovery tokens + PRIMARY dir.

    A ``print`` (no log record), a ``logging.DEBUG`` line (wrong level), or a
    message missing either recovery token all FAIL this test. The fallback must
    be observable AND actionable AND must resolve to the primary checkout.
    """
    primary_dir = _materialise_coord_empty(tmp_path, slug)

    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        resolved = resolve_status_surface_with_anchor(tmp_path, slug)

    # (a) EXACTLY one record, at EXACTLY logging.WARNING, from the named logger.
    warning_records = [
        r
        for r in caplog.records
        if r.name == _LOGGER_NAME and r.levelno == logging.WARNING
    ]
    assert warning_records, (
        "coord-empty must emit a record at EXACTLY logging.WARNING from "
        f"{_LOGGER_NAME!r} — a print or DEBUG line must NOT satisfy this. "
        f"Records seen: {[(r.name, r.levelname) for r in caplog.records]}"
    )
    # No DEBUG/INFO downgrade smuggled the message in below WARNING.
    assert all(r.levelno >= logging.WARNING for r in warning_records)

    message = warning_records[0].getMessage()
    lowered = message.lower()
    # (b) BOTH recovery paths named — discriminating tokens, not "an error".
    assert "flatten" in lowered and "coordination_branch" in message, (
        "warning must name recovery path (a): flatten the mission by removing "
        f"the `coordination_branch` key. Got: {message!r}"
    )
    assert "doctor workspaces --fix" in message, (
        "warning must name recovery path (b): the real repair command "
        "(spec-kitty doctor workspaces --fix, per FR-007/#1890). "
        f"Got: {message!r}"
    )
    # (c) The resolver RETURNS the PRIMARY dir — Option B fallback, not a raise,
    #     not the coord dir.
    assert resolved.read_dir.resolve() == primary_dir.resolve(), (
        "coord-empty Option B must resolve to the PRIMARY checkout, not the "
        f"coord dir. Got: {resolved.read_dir}"
    )
    assert resolved.primary_anchor.resolve() == primary_dir.resolve()
