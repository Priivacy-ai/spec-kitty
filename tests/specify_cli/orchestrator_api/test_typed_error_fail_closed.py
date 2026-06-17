"""WP09 (M2 + M3): orchestrator-api typed-error pass-through + fail-closed identity.

These two defects live on the **external automation** surface
(``specify_cli.orchestrator_api.commands``), both rooted in the
``_resolve_mission_dir`` read-path seam:

* **M2 (FR-001, typed-error fidelity).** The seam used to catch
  :class:`StatusReadPathNotFound` and return ``None``; the 8 endpoints then
  emitted the unconditional ``MISSION_NOT_FOUND`` envelope — dropping the real
  ``error_code`` + ``coord_candidate`` / ``primary_candidate``. The fix surfaces
  the resolver's typed read-path code while preserving the external envelope
  *shape*.
* **M3 (FR-011, read-path SAFETY).** The seam seeded
  ``resolve_mid8(slug, mission_id=None)`` → empty ``mid8`` (``''``), which
  **suppresses** the coord-aware fail-closed branch
  (``_read_path_resolver.py`` gates the guard on ``bool(mid8)``). External
  automation could therefore read **stale primary** status on a coord topology.
  The fix reads the **real** ``mission_id`` from meta and passes it to
  ``resolve_mid8`` so the ``bool(mid8)`` guard fires.

Both fixtures are **topology-true** (NFR-002): a real 26-char ULID
``mission_id``, a primary checkout declaring ``coordination_branch``, and a
materialized ``-coord`` worktree whose mission dir is empty (the stale-primary
window). A single-repo / fabricated-short-id fixture cannot exercise the
coord-vs-primary defect.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.missions._read_path_resolver import (
    STATUS_READ_PATH_NOT_FOUND_CODE,
    StatusReadPathNotFound,
)
from specify_cli.orchestrator_api import commands as orch
from specify_cli.orchestrator_api.commands import app

pytestmark = [pytest.mark.fast]

runner = CliRunner()

# Full 26-char ULID — realistic mission identity (NFR-002: no fabricated short ids).
_MISSION_ID = "01KV8NPCQ9ZX3R7W2M5T8H4FBD"
_MID8 = _MISSION_ID[:8]  # "01KV8NPC"
_HUMAN_SLUG = "read-path-error-fidelity-adoption"
_MISSION_SLUG = f"{_HUMAN_SLUG}-{_MID8}"
_COORD_BRANCH = f"kitty/mission-{_MISSION_SLUG}"


def _seed_coord_topology(tmp_path: Path) -> tuple[Path, Path]:
    """Build a real coord topology with a stale primary surface.

    The primary checkout carries the mission dir + ``meta.json`` declaring
    ``coordination_branch`` and the real ULID ``mission_id``; the ``-coord``
    worktree is materialized but its mission dir is empty. Reading the primary
    in this window exposes stale status — the exact hazard the ``bool(mid8)``
    fail-closed guard exists to refuse.

    Returns ``(repo_root, primary_mission_dir)``.
    """
    repo_root = tmp_path / "repo"
    primary = repo_root / "kitty-specs" / _MISSION_SLUG
    primary.mkdir(parents=True)
    meta = {
        "mission_id": _MISSION_ID,
        "mission_slug": _MISSION_SLUG,
        "slug": _MISSION_SLUG,
        "mission_number": None,
        "mission_type": "software-dev",
        "coordination_branch": _COORD_BRANCH,
        "status_phase": 2,
    }
    (primary / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    # Stale primary status surface (would be read if the guard were suppressed).
    (primary / "status.events.jsonl").write_text("", encoding="utf-8")
    tasks_dir = primary / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Stale\ndependencies: []\n---\n",
        encoding="utf-8",
    )

    # Materialize the coord worktree (declared topology) but DO NOT create the
    # mission dir inside it — that is the stale/empty hazard window.
    coord_root = CoordinationWorkspace.worktree_path(repo_root, _MISSION_SLUG, _MID8)
    coord_root.mkdir(parents=True)

    return repo_root, primary


def test_resolve_seam_fails_closed_on_coord_topology(tmp_path: Path) -> None:
    """T041 (M3) — the coord-aware fail-closed guard fires through the seam.

    Captured-red (pinned to the GATE, not merely "stale read succeeds"):
    on HEAD ``_resolve_mission_dir`` seeds ``resolve_mid8(slug, mission_id=None)``
    → ``mid8 == ''`` → ``fail_closed`` evaluates ``False`` → the resolver returns
    the **stale primary** mission dir and ``_resolve_mission_dir`` hands it back
    (no raise). HEAD red therefore looks like::

        assert _resolve_mission_dir(repo_root, slug) is primary   # PASSES on HEAD
        # i.e. the guard NEVER fired; stale primary was returned.

    After the fix the real ``mission_id`` is read from meta, ``mid8`` is
    non-empty, the ``bool(mid8)`` guard fires, and the seam raises
    :class:`StatusReadPathNotFound` rather than returning the stale primary.
    """
    repo_root, primary = _seed_coord_topology(tmp_path)

    with pytest.raises(StatusReadPathNotFound) as excinfo:
        orch._resolve_mission_dir(repo_root, _MISSION_SLUG)

    exc = excinfo.value
    # The guard must have evaluated against the REAL identity (non-empty mid8),
    # not the suppressed empty seed.
    assert exc.mid8 == _MID8, (
        "fail-closed must fire on the REAL mid8 derived from meta mission_id; "
        "an empty mid8 here means the guard was suppressed (M3 unfixed)"
    )
    # It must NOT have silently returned the stale primary.
    assert primary.exists()


def test_mission_state_endpoint_emits_typed_code_not_mission_not_found(
    tmp_path: Path,
) -> None:
    """T039 (M2) — endpoint surfaces the typed read-path code, not MISSION_NOT_FOUND.

    On HEAD the seam flattens ``StatusReadPathNotFound`` → ``None`` and the
    endpoint emits ``MISSION_NOT_FOUND`` (dropping the typed code + candidates).
    After the fix the endpoint surfaces ``STATUS_READ_PATH_NOT_FOUND`` with the
    coord / primary candidate paths, preserving the external envelope *shape*.
    """
    repo_root, _ = _seed_coord_topology(tmp_path)

    with patch.object(orch, "_get_main_repo_root", return_value=repo_root):
        result = runner.invoke(
            app,
            ["mission-state", "--mission", _MISSION_SLUG],
            catch_exceptions=False,
        )

    envelope = json.loads(result.output.strip().split("\n")[0])
    assert envelope["success"] is False
    assert envelope["error_code"] == STATUS_READ_PATH_NOT_FOUND_CODE, (
        "endpoint must surface the resolver's typed read-path code, not the "
        "flattened MISSION_NOT_FOUND"
    )
    assert envelope["error_code"] != "MISSION_NOT_FOUND"
    # Envelope SHAPE preserved + candidate fidelity surfaced.
    data = envelope["data"]
    assert "coord_candidate" in data
    assert "primary_candidate" in data


def test_genuine_not_found_still_emits_mission_not_found(tmp_path: Path) -> None:
    """Regression guard: a mission that genuinely does not exist (no coord
    topology, no fail-closed window) still emits ``MISSION_NOT_FOUND`` — the fix
    raises fidelity for the fail-closed path WITHOUT reclassifying ordinary
    not-found into the typed code.
    """
    repo_root = tmp_path / "repo"
    (repo_root / "kitty-specs").mkdir(parents=True)

    with patch.object(orch, "_get_main_repo_root", return_value=repo_root):
        result = runner.invoke(
            app,
            ["mission-state", "--mission", "999-does-not-exist"],
            catch_exceptions=False,
        )

    envelope = json.loads(result.output.strip().split("\n")[0])
    assert envelope["success"] is False
    assert envelope["error_code"] == "MISSION_NOT_FOUND"
