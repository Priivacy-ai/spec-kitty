"""WP05 / T027 — mission.py routes the 2 decision sites through ``routes_through_coordination`` (FR-005 / FR-001b).

The two coord-routing decision sites in ``mission.py`` read the WP01
``routes_through_coordination(resolve_topology(...))`` predicate over the STORED
topology — never a per-ref ``CommitTarget.kind`` (the retired arm, FR-001b):

* ``_planning_commit_worktree`` — decides whether the commit runs in the coord
  worktree vs the main checkout.
* ``_enforce_analysis_report_write_preflight`` — decides whether to drop
  coord-artifact residue from the dirty set.

Behaviour must be byte-equivalent for already-correct topologies (NFR-003): a
coord-less topology keeps the main checkout / does not drop residue; a coord
topology routes through coordination. An AST gate pins that zero
``.kind is COORDINATION`` *decision* reads remain.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from mission_runtime import CommitTarget, MissionTopology
from specify_cli.cli.commands.agent import mission as mission_mod

pytestmark = pytest.mark.unit

_MISSION_PY = Path(mission_mod.__file__)


def _patch_topology(monkeypatch: pytest.MonkeyPatch, *, coord: bool) -> None:
    """Stub the mission module's stored-topology read (routing reads the topology)."""
    topology = MissionTopology.COORD if coord else MissionTopology.SINGLE_BRANCH
    monkeypatch.setattr(mission_mod, "resolve_topology", lambda _root, _slug: topology)


def test_planning_commit_worktree_flattened_keeps_main_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A coord-less (flattened) topology returns the main checkout + paths unchanged."""
    _patch_topology(monkeypatch, coord=False)
    artifact = tmp_path / "kitty-specs" / "001-demo" / "spec.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# Spec\n", encoding="utf-8")

    worktree, paths = mission_mod._planning_commit_worktree(
        tmp_path, "001-demo", (artifact,)
    )
    assert worktree == tmp_path
    assert paths == (artifact,)


def test_planning_commit_worktree_primary_keeps_main_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A primary (coord-less) topology returns the main checkout."""
    _patch_topology(monkeypatch, coord=False)
    artifact = tmp_path / "kitty-specs" / "001-demo" / "spec.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# Spec\n", encoding="utf-8")

    worktree, paths = mission_mod._planning_commit_worktree(
        tmp_path, "001-demo", (artifact,)
    )
    assert worktree == tmp_path
    assert paths == (artifact,)


def test_planning_commit_worktree_coord_kind_attempts_coord_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A COORD-partition kind under coord topology routes through the coord-worktree branch.

    write-surface-coherence WP03 / T014: the helper is partition-aware. A
    coordination-partition kind (e.g. ``ANALYSIS_REPORT``) under coord topology
    falls past the kind short-circuit and reaches the
    ``routes_through_coordination`` branch. With no resolvable mid8 the helper
    degrades to the main checkout (C-004 safety), but the coord branch MUST be
    taken — proven by spying that ``_safe_load_meta`` (only reached past the
    predicate) is consulted.
    """
    from mission_runtime import MissionArtifactKind

    _patch_topology(monkeypatch, coord=True)
    artifact = tmp_path / "kitty-specs" / "001-demo" / "analysis-report.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# Analysis\n", encoding="utf-8")

    consulted: list[str] = []
    monkeypatch.setattr(
        mission_mod,
        "_safe_load_meta",
        lambda _root, slug: consulted.append(slug) or None,
    )

    worktree, paths = mission_mod._planning_commit_worktree(
        tmp_path, "001-demo", (artifact,), kind=MissionArtifactKind.ANALYSIS_REPORT
    )
    # mid8 unresolvable → degrades to main checkout, but the coord branch WAS taken.
    assert consulted == ["001-demo"], (
        "the COORDINATION branch of routes_through_coordination was not taken — "
        "_safe_load_meta (past the predicate) was never consulted"
    )
    assert worktree == tmp_path  # degraded fallback (no mid8)


def test_planning_commit_worktree_primary_kind_short_circuits_under_coord(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A PRIMARY kind under coord topology NEVER transits coord (T014 convergence).

    The kind partition is the single routing authority for planning artifacts: a
    primary kind returns the main checkout BEFORE the
    ``routes_through_coordination`` decision, so ``_safe_load_meta`` (only reached
    on the coord branch) is never consulted even under coord topology. This kills
    the retired independent coord decision for planning.
    """
    from mission_runtime import MissionArtifactKind

    _patch_topology(monkeypatch, coord=True)
    artifact = tmp_path / "kitty-specs" / "001-demo" / "tasks.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# Tasks\n", encoding="utf-8")

    consulted: list[str] = []
    monkeypatch.setattr(
        mission_mod,
        "_safe_load_meta",
        lambda _root, slug: consulted.append(slug) or None,
    )

    worktree, paths = mission_mod._planning_commit_worktree(
        tmp_path, "001-demo", (artifact,), kind=MissionArtifactKind.TASKS_INDEX
    )
    assert consulted == [], (
        "a PRIMARY kind reached the coord branch (_safe_load_meta consulted) under "
        "coord topology — the kind partition must short-circuit to primary first "
        "(T014); planning must NOT transit coord."
    )
    assert worktree == tmp_path
    assert paths == (artifact,)


def test_analysis_preflight_coordination_drops_residue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A COORDINATION placement drops coord-artifact residue from the dirty set."""
    monkeypatch.setattr(mission_mod, "is_git_repo", lambda _root: True)
    monkeypatch.setattr(
        mission_mod, "_git_dirty_paths", lambda _root: ["kitty-specs/001-demo/spec.md"]
    )
    # Treat the residue path as coord-owned residue so it is dropped → no dirty set.
    monkeypatch.setattr(
        mission_mod, "is_coordination_artifact_residue_path", lambda _p, *, mission_slug=None: True
    )
    _patch_topology(monkeypatch, coord=True)

    placement = CommitTarget(ref="kitty/mission-001-demo-AAAA1111")
    # Should NOT raise (residue dropped → empty dirty set).
    mission_mod._enforce_analysis_report_write_preflight(
        tmp_path, json_output=True, placement_ref=placement, mission_slug="001-demo"
    )


def test_analysis_preflight_primary_keeps_residue_and_gates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-coord placement does NOT drop residue → a dirty tree still gates (NFR-003)."""
    monkeypatch.setattr(mission_mod, "is_git_repo", lambda _root: True)
    monkeypatch.setattr(
        mission_mod, "_git_dirty_paths", lambda _root: ["kitty-specs/001-demo/spec.md"]
    )
    # Even if the path WOULD qualify as residue, a non-coord placement skips the drop.
    monkeypatch.setattr(
        mission_mod, "is_coordination_artifact_residue_path", lambda _p, *, mission_slug=None: True
    )
    _patch_topology(monkeypatch, coord=False)

    placement = CommitTarget(ref="main")
    import typer

    with pytest.raises(typer.Exit):
        mission_mod._enforce_analysis_report_write_preflight(
            tmp_path, json_output=True, placement_ref=placement, mission_slug="001-demo"
        )


def test_no_direct_kind_is_coordination_decision_reads_remain() -> None:
    """FR-005 gate: zero ``placement.kind is COORDINATION`` decision reads in mission.py.

    AST-scoped (not a docstring grep): flags any ``X.kind is ....COORDINATION``
    comparison node in the module body. Both decision sites must read
    ``routes_through_coordination`` over the stored topology instead.
    """
    tree = ast.parse(_MISSION_PY.read_text(encoding="utf-8"))
    offenders: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        left = node.left
        if isinstance(left, ast.Attribute) and left.attr == "kind":
            for comparator in node.comparators:
                if (
                    isinstance(comparator, ast.Attribute)
                    and comparator.attr == "COORDINATION"
                ):
                    offenders.append(node.lineno)
    assert not offenders, (
        f"direct `.kind is COORDINATION` decision read(s) remain in mission.py at "
        f"lines {offenders} — route them through routes_through_coordination (FR-005)."
    )


# ---------------------------------------------------------------------------
# write-surface-coherence WP05 / T022+T023 — the residue-filter ripple
# ---------------------------------------------------------------------------
#
# WP01 moved SPEC/DATA_MODEL/RESEARCH/CHECKLIST into _PRIMARY_ARTIFACT_KINDS, so
# ``is_coordination_artifact_residue_path`` now returns False for a primary
# ``spec.md`` — those files LIVE on primary, so a stale primary copy is the REAL
# artifact, not droppable coordination residue. The preflight dirty-filter (which
# uses the REAL residue predicate, not a stub) must therefore NO LONGER silently
# drop a dirty primary ``spec.md`` from the dirty set — it is a genuine dirty-tree
# blocker. This pins that correctness win (the intended behavior change of WP01).
#
# On the PRE-WP01 partition (SPEC a placement kind) the residue predicate returned
# True for ``spec.md`` and the preflight would drop it → NO exception. So the
# ``pytest.raises`` below goes RED on pre-fix code — proven by revert+restore.


def test_analysis_preflight_real_residue_filter_keeps_stale_primary_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The REAL residue filter no longer drops a stale primary ``spec.md`` (T022 ripple).

    Uses the genuine ``is_coordination_artifact_residue_path`` (NOT a stub) under a
    coord topology. Post-WP01 SPEC is a PRIMARY kind, so the predicate returns False
    for ``kitty-specs/<slug>/spec.md`` and the preflight keeps it in the dirty set →
    the record-analysis preflight gates (raises ``typer.Exit``). This is the
    corrected behavior: a primary planning copy is a real dirty file, not residue.
    """
    import typer

    monkeypatch.setattr(mission_mod, "is_git_repo", lambda _root: True)
    monkeypatch.setattr(
        mission_mod,
        "_git_dirty_paths",
        lambda _root: ["kitty-specs/001-demo/spec.md"],
    )
    # NOTE: deliberately NOT patching ``is_coordination_artifact_residue_path`` —
    # the real predicate (post-WP01) must return False for a primary spec.md.
    _patch_topology(monkeypatch, coord=True)

    placement = CommitTarget(ref="kitty/mission-001-demo-AAAA1111")
    with pytest.raises(typer.Exit):
        mission_mod._enforce_analysis_report_write_preflight(
            tmp_path, json_output=True, placement_ref=placement, mission_slug="001-demo"
        )


def test_analysis_preflight_real_residue_filter_still_drops_coord_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The REAL residue filter STILL drops a genuine COORD-owned residue (status log).

    The complement: a status-event-log copy on the primary checkout under coord
    topology IS coordination residue (STATUS_STATE stays a placement kind), so the
    real predicate returns True and the preflight drops it → no gate. This proves
    the ripple narrowed the filter to genuinely coord-owned kinds, not disabled it.
    """
    monkeypatch.setattr(mission_mod, "is_git_repo", lambda _root: True)
    monkeypatch.setattr(
        mission_mod,
        "_git_dirty_paths",
        lambda _root: ["kitty-specs/001-demo/status.events.jsonl"],
    )
    _patch_topology(monkeypatch, coord=True)

    placement = CommitTarget(ref="kitty/mission-001-demo-AAAA1111")
    # Should NOT raise: the coord-owned status residue is dropped → empty dirty set.
    mission_mod._enforce_analysis_report_write_preflight(
        tmp_path, json_output=True, placement_ref=placement, mission_slug="001-demo"
    )
