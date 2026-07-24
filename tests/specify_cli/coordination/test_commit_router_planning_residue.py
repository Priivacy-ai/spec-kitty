"""Tests for the planning-commit residue relocated into commit_router (#2056 WP08).

WP08 relocated ``_planning_commit_worktree`` / ``_resolve_planning_placement``
(and reconciled the former mission.py ``_stage_finalize_artifacts_in_coord_worktree``
into the canonical ``_stage_artifacts_in_coord_worktree``) out of the ``mission``
god module into ``coordination/commit_router``. These were LIVE on this base
(``tasks.py``'s map-requirements + planning auto-commit paths call them), so the
relocation must be behavior-preserving:

* the symbols are DEFINED in commit_router,
* ``tasks.py`` imports them FROM commit_router,
* ``mission`` re-exports them so historical patch targets keep resolving,
* a PRIMARY artifact kind never transits the coordination worktree,
* the reconciled staging helper still skips the status-log/snapshot files
  (``MissionArtifactKind.STATUS_STATE``, formerly ``COORD_OWNED_STATUS_FILES``,
  retired onto the owner in WP13) (#1589)
  and is the single source (no forked second copy).

INV-8: commit_router carries no ``from specify_cli.cli`` import (covered directly
here + by ``tests/coordination/test_commit_router_layering.py``).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from mission_runtime import CommitTarget, MissionArtifactKind
from specify_cli.coordination import commit_router

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Relocation shape: symbols defined here + re-exported from mission
# ---------------------------------------------------------------------------


def test_symbols_defined_in_commit_router() -> None:
    assert callable(commit_router._planning_commit_worktree)
    assert callable(commit_router._resolve_planning_placement)
    # The reconciled staging alias points at the single canonical helper.
    assert (
        commit_router._stage_finalize_artifacts_in_coord_worktree
        is commit_router._stage_artifacts_in_coord_worktree
    )


def test_mission_re_exports_relocated_symbols() -> None:
    from specify_cli.cli.commands.agent import mission as mission_mod

    # FR-007: the relocated planning-commit primitives are DEFINED in
    # ``commit_router`` and the ``mission`` shim merely re-exports them. Assert
    # by ``__module__`` rather than object identity: another test in the suite
    # (``tests/coordination/test_commit_router.py``) ``importlib.reload``s
    # commit_router, which rebinds its module-level functions to fresh objects
    # while the shim retains its original import binding — an ``is`` check is
    # order-dependent and flakes under that reload, but the relocation invariant
    # (symbol owned by commit_router, re-exported by the shim) still holds.
    #
    # Presence on ``mission_mod`` is NOT re-asserted here (#2076, WP03 dedupe):
    # all three names are members of ``_COMMIT_RESIDUE`` in
    # ``test_mission_shim_reexports.py`` and already covered by the
    # parametrized ``test_mission_reexports_required_symbol`` shim guard;
    # ``getattr`` below still raises loudly if a re-export is ever dropped.
    for name in (
        "_planning_commit_worktree",
        "_resolve_planning_placement",
        "_stage_finalize_artifacts_in_coord_worktree",
    ):
        shim_obj = getattr(mission_mod, name)
        # ``_stage_finalize_artifacts_in_coord_worktree`` is the reconciled alias
        # of ``_stage_artifacts_in_coord_worktree`` (same defining module).
        assert shim_obj.__module__ == commit_router.__name__, (
            f"mission.{name} must be re-exported from commit_router, "
            f"got it from {shim_obj.__module__}"
        )


def test_tasks_py_imports_from_commit_router() -> None:
    """``tasks.py`` must import the relocated primitives from commit_router.

    Post-merge reality (WP08 residue check): ``tasks.py``'s map-requirements
    body routes through ``commit_for_mission`` (the canonical entry point), so
    the now-dead direct ``_planning_commit_worktree`` import was correctly
    dropped — only ``_resolve_planning_placement`` is imported live. The
    relocation invariant for ``_planning_commit_worktree`` (DEFINED in
    commit_router) is asserted separately below; the residue rule remains that
    whatever tasks.py imports, it imports from commit_router and NOT from the
    ``mission`` god module.
    """
    import specify_cli.cli.commands.agent.tasks as tasks_mod

    # Wave 2 degod (#2305) relocated the map-requirements body (the consumer of
    # ``_resolve_planning_placement``) into a sibling family module with a lazy
    # in-function import. The residue invariant is about the SOURCE, not the
    # location: whatever module on the tasks command surface consumes the
    # planning primitives must import them from commit_router and NOT from the
    # ``mission`` god module — so the scan covers the whole surface (shim +
    # ``tasks_*`` siblings); ``ast.walk`` sees in-function ImportFrom nodes.
    surface_dir = Path(tasks_mod.__file__).parent
    surface_files = [Path(tasks_mod.__file__), *sorted(surface_dir.glob("tasks_*.py"))]
    imported_from_router: set[str] = set()
    imported_from_mission: set[str] = set()
    candidates = {"_planning_commit_worktree", "_resolve_planning_placement"}
    for src_file in surface_files:
        tree = ast.parse(src_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module is None:
                continue
            names = {alias.name for alias in node.names} & candidates
            if not names:
                continue
            if node.module == "specify_cli.coordination.commit_router":
                imported_from_router |= names
            elif node.module == "specify_cli.cli.commands.agent.mission":
                imported_from_mission |= names
    # ``_planning_commit_worktree`` is no longer imported anywhere on the tasks
    # surface (the map-requirements path routes through ``commit_for_mission``);
    # the live import is exactly ``_resolve_planning_placement``.
    assert imported_from_router == {"_resolve_planning_placement"}
    assert not imported_from_mission, (
        "the tasks command surface must NOT import these from mission after WP08"
    )
    # The relocated ``_planning_commit_worktree`` still LIVES in commit_router
    # even though tasks.py no longer imports it directly.
    assert hasattr(commit_router, "_planning_commit_worktree")
    assert commit_router._planning_commit_worktree.__module__ == commit_router.__name__


def test_commit_router_has_no_cli_imports() -> None:
    """INV-8: commit_router never reaches into specify_cli.cli (any depth)."""
    src = Path(commit_router.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("specify_cli.cli"), f"forbidden cli import: {node.module}"
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("specify_cli.cli"), f"forbidden cli import: {alias.name}"


# ---------------------------------------------------------------------------
# _resolve_planning_placement — delegation to the WP-less projection
# ---------------------------------------------------------------------------


def test_resolve_planning_placement_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_resolve(repo_root: Path, mission_slug: str, *, kind: MissionArtifactKind) -> CommitTarget:
        captured["args"] = (repo_root, mission_slug, kind)
        return CommitTarget(ref="prog/x")

    monkeypatch.setattr(commit_router, "resolve_placement_only", fake_resolve)
    result = commit_router._resolve_planning_placement(
        Path("/repo"), "001-m", kind=MissionArtifactKind.TASKS_INDEX
    )
    assert result.ref == "prog/x"
    assert captured["args"] == (Path("/repo"), "001-m", MissionArtifactKind.TASKS_INDEX)


# ---------------------------------------------------------------------------
# _planning_commit_worktree — partition routing
# ---------------------------------------------------------------------------


def test_planning_commit_worktree_primary_kind_keeps_main_checkout() -> None:
    """A PRIMARY kind never transits coordination — returns the primary checkout."""
    repo = Path("/repo")
    paths = (repo / "kitty-specs" / "001-m" / "tasks.md",)
    worktree, returned = commit_router._planning_commit_worktree(
        repo, "001-m", paths, kind=MissionArtifactKind.WORK_PACKAGE_TASK
    )
    assert worktree == repo
    assert returned == paths


def test_planning_commit_worktree_default_kind_is_primary() -> None:
    """The default kind (TASKS_INDEX) is primary → no coord transit."""
    repo = Path("/repo")
    paths = (repo / "kitty-specs" / "001-m" / "tasks.md",)
    worktree, returned = commit_router._planning_commit_worktree(repo, "001-m", paths)
    assert worktree == repo
    assert returned == paths


def test_planning_commit_worktree_coord_kind_no_coord_topology(monkeypatch: pytest.MonkeyPatch) -> None:
    """A coordination kind on a non-coord topology stays on the main checkout."""
    monkeypatch.setattr(commit_router, "is_primary_artifact_kind", lambda _kind: False)
    monkeypatch.setattr(commit_router, "resolve_topology", lambda _r, _s: "flattened")
    monkeypatch.setattr(commit_router, "routes_through_coordination", lambda _t: False)
    repo = Path("/repo")
    paths = (repo / "x",)
    worktree, returned = commit_router._planning_commit_worktree(
        repo, "001-m", paths, kind=MissionArtifactKind.STATUS_STATE
    )
    assert worktree == repo
    assert returned == paths


def test_planning_commit_worktree_coord_kind_no_mid8(monkeypatch: pytest.MonkeyPatch) -> None:
    """When mid8 cannot be resolved the coord transit falls back to the primary."""
    monkeypatch.setattr(commit_router, "is_primary_artifact_kind", lambda _kind: False)
    monkeypatch.setattr(commit_router, "resolve_topology", lambda _r, _s: "coordination")
    monkeypatch.setattr(commit_router, "routes_through_coordination", lambda _t: True)
    monkeypatch.setattr(commit_router, "_resolve_mid8", lambda _r, _s: None)
    repo = Path("/repo")
    paths = (repo / "x",)
    worktree, returned = commit_router._planning_commit_worktree(
        repo, "001-m", paths, kind=MissionArtifactKind.STATUS_STATE
    )
    assert worktree == repo
    assert returned == paths


# ---------------------------------------------------------------------------
# Reconciled staging helper — skips coord-owned status files (#1589)
# ---------------------------------------------------------------------------


def test_staging_skips_coord_owned_status_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    coord = tmp_path / "coord"
    feature = repo / "kitty-specs" / "001-m"
    feature.mkdir(parents=True)
    coord.mkdir()

    status_file = feature / "status.events.jsonl"
    status_file.write_text("events", encoding="utf-8")
    plain = feature / "tasks.md"
    plain.write_text("tasks", encoding="utf-8")

    staged = commit_router._stage_finalize_artifacts_in_coord_worktree(
        [status_file, plain], coord, repo
    )

    # The coord-owned status file is skipped; tasks.md is copied across.
    assert all(p.name not in {"status.events.jsonl", "status.json"} for p in staged)
    assert (coord / "kitty-specs" / "001-m" / "tasks.md") in staged
    assert (coord / "kitty-specs" / "001-m" / "tasks.md").exists()


def test_staging_cleans_primary_residue_created_this_invocation(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    coord = tmp_path / "coord"
    feature = repo / "kitty-specs" / "001-m"
    feature.mkdir(parents=True)
    coord.mkdir()

    created = feature / "lanes.json"
    created.write_text("{}", encoding="utf-8")

    staged = commit_router._stage_finalize_artifacts_in_coord_worktree(
        [created], coord, repo, primary_paths_created_this_invocation=frozenset({created})
    )

    # R6: a path created this invocation is removed from the primary checkout
    # after staging (it only ever lives on the coordination branch).
    assert (coord / "kitty-specs" / "001-m" / "lanes.json") in staged
    assert not created.exists()
