"""orchestrator-api read-path resolution on an EMPTY coord topology.

REMEDIATED for the single-authority topology cleanup (#2070, FR-004 / WP04
Option B). These tests live on the **external automation** surface
(``specify_cli.orchestrator_api.commands``) and exercise the
``_resolve_mission_dir`` read-path seam for a coord-declared mission whose
coordination worktree is materialized-but-empty.

Earlier (pre-mission) these tests pinned a ``topology is None`` fail-closed
band-aid: the seam was expected to raise ``StatusReadPathNotFound`` for this
fixture. The single-authority cleanup **absorbs** ``topology`` at the read-path
boundary (``classify_from_meta``) — a readable coord-declared meta classifies to
a CONCRETE ``MissionTopology``, and the EMPTY coord state then resolves to the
authoritative PRIMARY checkout (the loud warning lives at the surface) rather
than failing closed. The genuine fail-closed guarantees survive elsewhere
(corrupt/unreadable meta, a genuine absence under ``require_exists=True``, and
the #1848 ``CoordinationBranchDeleted`` data-loss carve-out) — they are simply
no longer reached for this readable EMPTY-coord case.

The fixtures stay **topology-true** (NFR-002): a real 26-char ULID
``mission_id``, a primary checkout declaring ``coordination_branch``, and a
materialized ``-coord`` worktree whose mission dir is empty.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.coordination.workspace import CoordinationWorkspace
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


def test_resolve_seam_resolves_primary_on_empty_coord_topology(tmp_path: Path) -> None:
    """Single-authority topology cleanup (FR-004 / WP04 Option B): an EMPTY coord
    worktree resolves PRIMARY, not a fail-closed raise.

    REMEDIATED from the retired ``topology is None`` husk-arm contract. This
    fixture declares ``coordination_branch`` with a real ULID ``mission_id`` but
    its ``topology`` field is absent, so the read-path BOUNDARY now classifies it
    on-read (``classify_from_meta``) into a CONCRETE ``MissionTopology`` (FR-004).
    The coord worktree root exists but its mission dir does not — the EMPTY
    transient state (C-005). Under the single-authority model the PRIMARY checkout
    is authoritative for the EMPTY state (WP04 Option B; the loud warning lives at
    the surface), so the resolver returns the primary mission dir instead of the
    pre-mission ``topology is None`` band-aid raise. The genuine fail-closed
    guarantees are preserved elsewhere — corrupt/unreadable meta
    (``topology is None``), a genuine absence under ``require_exists=True``, and
    the #1848 ``CoordinationBranchDeleted`` data-loss carve-out — they are simply
    no longer triggered for a readable, classified coord-declared mission whose
    coord surface is merely empty.
    """
    repo_root, primary = _seed_coord_topology(tmp_path)

    resolved = orch._resolve_mission_dir(repo_root, _MISSION_SLUG)

    # Single-authority: the PRIMARY checkout is the authoritative surface for the
    # EMPTY coord state — no fail-closed raise, no stale-coord husk.
    assert resolved == primary, (
        "EMPTY coord topology must resolve to the PRIMARY checkout under the "
        f"single-authority model (FR-004 / WP04 Option B); got {resolved}"
    )
    assert ".worktrees" not in str(resolved), (
        "must not route into the empty coord worktree"
    )
    assert primary.exists()


def test_mission_state_endpoint_reads_primary_on_empty_coord_topology(
    tmp_path: Path,
) -> None:
    """Single-authority topology cleanup (FR-004 / WP04 Option B): the endpoint
    reads PRIMARY status for an EMPTY coord topology rather than failing closed.

    REMEDIATED from the retired pre-mission contract (which expected the endpoint
    to surface ``STATUS_READ_PATH_NOT_FOUND`` for this fixture). Under the
    single-authority model a readable coord-declared mission is classified on-read
    into a CONCRETE topology and the EMPTY coord state resolves to the PRIMARY
    checkout (the authoritative surface). The endpoint therefore succeeds, reading
    the primary status surface (here: the seeded WP01 in ``planned``), instead of
    consulting the now-dead ``topology is None`` fail-closed husk-arm.

    The M2 typed-error pass-through machinery (``StatusReadPathNotFound`` →
    ``error_code`` + candidates, never flattened to ``MISSION_NOT_FOUND``) remains
    in ``_resolve_mission_dir_or_fail`` and is still load-bearing for the paths
    that DO raise (corrupt/unreadable meta, ``CoordinationBranchDeleted``); it is
    simply not triggered by a readable EMPTY-coord fixture anymore.
    """
    repo_root, _ = _seed_coord_topology(tmp_path)

    with patch.object(orch, "_get_main_repo_root", return_value=repo_root):
        result = runner.invoke(
            app,
            ["mission-state", "--mission", _MISSION_SLUG],
            catch_exceptions=False,
        )

    envelope = json.loads(result.output.strip().split("\n")[0])
    assert envelope["success"] is True, (
        "single-authority: EMPTY coord topology reads PRIMARY and succeeds; "
        f"envelope={envelope}"
    )
    assert envelope["error_code"] is None
    # The status came from the PRIMARY surface (the seeded WP01).
    data = envelope["data"]
    assert data["mission_slug"] == _MISSION_SLUG
    wp_ids = {wp["wp_id"] for wp in data["work_packages"]}
    assert "WP01" in wp_ids


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
