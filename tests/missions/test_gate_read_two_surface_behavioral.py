"""WP10 / NFR-002 / NFR-004 (#2107/#2085/#2102): the cross-command two-surface net.

The per-WP suites prove each gate command's read surface in isolation (WP02
``setup_plan``, WP03 accept, WP04 ``map_requirements`` + ``record_analysis``,
WP05 the self-bookkeeping allowlist, WP00 the write twin). This module is the
CONSOLIDATED closeout proof: in ONE composed ``<slug>-<mid8>`` coord-topology
fixture it asserts the SAME two-surface contract across ALL of those commands at
once —

* every command with an observable PLANNING read resolves the PRIMARY
  ``target_branch`` dir, AND
* every command that reads STATUS resolves the COORD surface,

so the pair kills both the "always coord" and the "always primary" mutant at the
command layer, not just per-site. This is the cross-command net the spec's IC-11
contract demands; it does NOT re-prove the per-site red-first repros (those live
in the WP suites) — it asserts the BOTH-surface PROPERTY holds simultaneously
across the gate commands on one fixture.

``record_analysis``'s read is a PLANNING cell, not a STATUS one: its
``analysis_report`` kind is a PRIMARY-partition artifact kind
(``is_primary_artifact_kind(ANALYSIS_REPORT) is True`` — an analysis report is
produced by ``/analyze`` and lands on the primary partition alongside
spec/plan/tasks), so its read resolves the PRIMARY ``target_branch`` dir like
every other planning cell. Separately, its self-bookkeeping ALLOWLIST behavior
(G-5) is asserted via ``test_record_analysis_allowlist_and_g5_dirt`` — the write
preflight does NOT block on ``meta.json`` / provenance churn but STILL blocks on
a stale primary ``spec.md`` (G-5 "real dirt").

Identity is production-shaped: a real 26-char Crockford-base32 ULID, the uppercase
8-char mid8, and the on-disk composed ``<slug>-<mid8>`` layout (NFR-002 / NFR-005)
— a bare-slug fixture would false-green by masking the coord/primary divergence
behind handle canonicalization.

Anti-mutant (NFR-004): each planning assertion drives the production read seam
(:func:`resolve_planning_read_dir`) or the real command entry point. Reverting any
PRIMARY-partition read to the topology-aware candidate resolver
(:func:`candidate_feature_dir_for_mission`) lands it on the materialized ``-coord``
husk, turning its assertion RED. The ``test_planning_seam_red_when_routed_to_coord``
case proves that mutation directly (a clean monkeypatch of the seam's primary leg).
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Iterable
from pathlib import Path

import pytest
import typer

from mission_runtime import (
    MissionArtifactKind,
    is_primary_artifact_kind,
    resolve_placement_only,
)
from specify_cli.acceptance import collect_feature_summary
from specify_cli.cli.commands.agent.mission import (
    _enforce_analysis_report_write_preflight,
)
from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.core.git_ops import resolve_target_branch
from specify_cli.core.paths import get_feature_target_branch
from specify_cli.missions._read_path_resolver import (
    candidate_feature_dir_for_mission,
    primary_feature_dir_for_mission,
    resolve_planning_read_dir,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# Production-shaped identity (real 26-char ULID, uppercase 8-char mid8, composed
# on-disk ``<slug>-<mid8>`` layout). NFR-002 / NFR-005.
_MISSION_ID = "01KVW9B0XFXPKTBE77QT3KRSW8"  # 26 chars
_MID8 = _MISSION_ID[:8]  # "01KVW9B0"
_SLUG = "gate-read-surface-completion"
_HANDLE = f"{_SLUG}-{_MID8}"  # composed on-disk dir name
_COORD_BRANCH = f"kitty/mission-{_SLUG}-{_MID8}"
_TARGET = "feat/gate-read-surface-completion"

_PLANNING_FILES = ("spec.md", "plan.md", "tasks.md", "research.md", "data-model.md")

# The gate-command PLANNING reads, keyed by the artifact kind each command resolves.
# Every one is a PRIMARY-partition kind (asserted in
# ``test_command_planning_kinds_are_primary_partition``), so each MUST resolve the
# PRIMARY ``target_branch`` dir for the coord-topology mission.
_COMMAND_PLANNING_KINDS: dict[str, MissionArtifactKind] = {
    "setup_plan(spec)": MissionArtifactKind.SPEC,
    "accept(tasks)": MissionArtifactKind.TASKS_INDEX,
    "map_requirements(wp_task)": MissionArtifactKind.WORK_PACKAGE_TASK,
    "finalize_tasks(lane_state)": MissionArtifactKind.LANE_STATE,
    # coord-trust-2841: analysis-report is a primary planning artifact
    # (`is_primary_artifact_kind(ANALYSIS_REPORT) is True`); the prior
    # status-group placement below was stale.
    "record_analysis(analysis_report)": MissionArtifactKind.ANALYSIS_REPORT,
}

# The gate-command STATUS reads — every one is a STATUS/placement-partition kind
# and MUST resolve the COORD surface under coord topology (C-001 / C-002 leniency).
_COMMAND_STATUS_KINDS: dict[str, MissionArtifactKind] = {
    "accept(status_state)": MissionArtifactKind.STATUS_STATE,
    "accept(acceptance_matrix)": MissionArtifactKind.ACCEPTANCE_MATRIX,
}

_STATUS_EVENT = {
    "actor": "claude",
    "at": "2026-06-24T12:00:00+00:00",
    "event_id": "01KVW9B0XFXPKTBE77QT3KRSWZ",
    "evidence": None,
    "execution_mode": "worktree",
    "feature_slug": _HANDLE,
    "force": False,
    "from_lane": "genesis",
    "reason": None,
    "review_ref": None,
    "to_lane": "planned",
    "wp_id": "WP01",
}


# ---------------------------------------------------------------------------
# Fixture: ONE composed coord-topology mission with split surfaces.
#   * PRIMARY  (kitty-specs/<slug>-<mid8>): meta.json (target_branch) + planning docs
#   * COORD    (.worktrees/<slug>-<mid8>-coord/...): status events + acceptance matrix
# ---------------------------------------------------------------------------


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True)


def _write_meta(feature_dir: Path, *, with_target: bool) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {
        "mission_id": _MISSION_ID,
        "mid8": _MID8,
        "mission_slug": _HANDLE,
        "mission_type": "software-dev",
        "coordination_branch": _COORD_BRANCH,
    }
    if with_target:
        meta["target_branch"] = _TARGET
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _plant_planning(feature_dir: Path) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    for name in _PLANNING_FILES:
        (feature_dir / name).write_text(f"# {name}\n\nContent.\n", encoding="utf-8")
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / "WP01-sample.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Sample\n"
        "agent: claude\n"
        "assignee: claude\n"
        "shell_pid: '1'\n"
        "---\n\n# WP01\n",
        encoding="utf-8",
    )


def _plant_status_events(feature_dir: Path) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "status.events.jsonl").write_text(
        json.dumps(_STATUS_EVENT) + "\n", encoding="utf-8"
    )


@pytest.fixture
def coord_mission(tmp_path: Path) -> tuple[Path, Path, Path]:
    """A composed ``<slug>-<mid8>`` coord-topology mission with split surfaces.

    Returns ``(repo_root, primary_feature_dir, coord_feature_dir)``. Planning docs
    live on PRIMARY (the post-mission home, INV-5); the status event log + WP tasks
    live on the materialized COORD worktree. The coord branch is materialized so the
    topology classifies as COORD (not a stale husk).
    """
    repo_root = tmp_path
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "t@example.invalid")
    _git(repo_root, "config", "user.name", "Test")
    _git(repo_root, "config", "commit.gpgsign", "false")

    primary_feature_dir = repo_root / "kitty-specs" / _HANDLE
    _write_meta(primary_feature_dir, with_target=True)
    _plant_planning(primary_feature_dir)
    # WORK_PACKAGE_TASK is a PRIMARY-partition kind: a real coord mission carries
    # WP tasks ONLY on primary (INV-5 write/read symmetry). Plant them on PRIMARY
    # so the accept gate's WP-task iteration genuinely exercises the primary read.
    # (Pre-closeout this fixture duplicated the WP task onto COORD too, masking the
    # real gate's "no tasks directory" break — closeout N+1 de-mask, debbie §3.)
    (primary_feature_dir / "tasks").mkdir(parents=True, exist_ok=True)
    (primary_feature_dir / "tasks" / "WP01-sample.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Sample\nagent: claude\n"
        "assignee: claude\nshell_pid: '1'\n---\n\n# WP01\n",
        encoding="utf-8",
    )

    coord_root = CoordinationWorkspace.worktree_path(repo_root, _SLUG, _MID8)
    coord_feature_dir = coord_root / "kitty-specs" / _HANDLE
    _write_meta(coord_feature_dir, with_target=False)
    _plant_status_events(coord_feature_dir)

    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "seed composed coord mission")
    _git(repo_root, "branch", _COORD_BRANCH)
    return repo_root, primary_feature_dir, coord_feature_dir


# ---------------------------------------------------------------------------
# T031 — the cross-command two-surface net.
# ---------------------------------------------------------------------------


def _assert_all_primary(
    repo_root: Path, primary_dir: Path, coord_dir: Path, kinds: Iterable[tuple[str, MissionArtifactKind]]
) -> None:
    for label, kind in kinds:
        resolved = resolve_planning_read_dir(repo_root, _HANDLE, kind=kind).resolve()
        assert resolved == primary_dir.resolve(), (
            f"{label}: PLANNING read resolved {resolved} — expected the PRIMARY "
            f"target_branch dir {primary_dir}. Reverting this read to the topology "
            f"candidate resolver lands it on the coord husk {coord_dir} (RED)."
        )
        assert resolved != coord_dir.resolve(), (
            f"{label}: PLANNING read leaked onto the coord surface {coord_dir}."
        )


def _assert_all_coord(
    repo_root: Path, primary_dir: Path, coord_dir: Path, kinds: Iterable[tuple[str, MissionArtifactKind]]
) -> None:
    for label, kind in kinds:
        resolved = resolve_planning_read_dir(repo_root, _HANDLE, kind=kind).resolve()
        assert resolved == coord_dir.resolve(), (
            f"{label}: STATUS read resolved {resolved} — expected the COORD surface "
            f"{coord_dir} (C-001/C-002). Redirecting the status read to primary "
            f"{primary_dir} turns this RED."
        )
        assert resolved != primary_dir.resolve(), (
            f"{label}: STATUS read leaked onto the primary surface {primary_dir}."
        )


def test_two_surface_seam_across_commands(
    coord_mission: tuple[Path, Path, Path],
) -> None:
    """NFR-004: every command's PLANNING read → primary AND STATUS read → coord.

    Both partitions are asserted on the SAME composed coord fixture, so the pair
    kills both the "always coord" and "always primary" mutant at once.
    """
    repo_root, primary_dir, coord_dir = coord_mission

    _assert_all_primary(
        repo_root, primary_dir, coord_dir, _COMMAND_PLANNING_KINDS.items()
    )
    _assert_all_coord(
        repo_root, primary_dir, coord_dir, _COMMAND_STATUS_KINDS.items()
    )


def test_command_planning_kinds_are_primary_partition() -> None:
    """Invariant: every gate command's planning-read kind is a PRIMARY kind.

    Pins the precondition under which the two-surface net is meaningful — a future
    cross-partition reclassification in ``mission_runtime.artifacts`` is caught
    HERE, not by a silent stale read.
    """
    assert all(
        is_primary_artifact_kind(kind) for kind in _COMMAND_PLANNING_KINDS.values()
    )
    assert all(
        not is_primary_artifact_kind(kind) for kind in _COMMAND_STATUS_KINDS.values()
    )


def test_planning_seam_red_when_routed_to_coord(
    coord_mission: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Anti-mutant: routing the PRIMARY leg to the coord candidate turns it RED.

    The seam routes a PRIMARY-partition kind to the topology-blind primary dir; a
    STATUS-partition kind takes the topology-aware candidate (→ coord husk).
    Forcing ``is_primary_artifact_kind`` to False for the spec kind reverts the
    read to the pre-mission shape (the kind-blind candidate resolver), landing it
    on the coord husk — exactly the regression the two-surface net exists to catch.
    """
    import mission_runtime

    repo_root, primary_dir, coord_dir = coord_mission

    # Sanity: unmutated, the planning kinds resolve PRIMARY.
    resolved_ok = resolve_planning_read_dir(
        repo_root, _HANDLE, kind=MissionArtifactKind.SPEC
    ).resolve()
    assert resolved_ok == primary_dir.resolve()

    # Control: the topology-aware candidate (the pre-mission, kind-blind path)
    # resolves the materialized coord husk under coord topology.
    assert (
        candidate_feature_dir_for_mission(repo_root, _HANDLE).resolve()
        == coord_dir.resolve()
    ), (
        "The topology candidate did not land on the coord husk — the fixture is "
        "not exercising the coord/primary divergence (NFR-002 false-green guard)."
    )

    # Mutate: make the PRIMARY-partition branch fall through to the coord candidate.
    monkeypatch.setattr(mission_runtime, "is_primary_artifact_kind", lambda _kind: False)
    resolved_mutant = resolve_planning_read_dir(
        repo_root, _HANDLE, kind=MissionArtifactKind.SPEC
    ).resolve()
    assert resolved_mutant == coord_dir.resolve(), (
        "Reverting the planning read to the kind-blind candidate did NOT land on "
        "the coord husk — the seam's primary-partition routing is not load-bearing."
    )
    assert resolved_mutant != primary_dir.resolve()


# ---------------------------------------------------------------------------
# T031 — the real command entry points (observable behavior, not just the seam).
# ---------------------------------------------------------------------------


def test_accept_gate_reads_primary_planning_and_coord_status(
    coord_mission: tuple[Path, Path, Path],
) -> None:
    """Accept gate: planning docs found on PRIMARY (no mis-block) AND status on COORD.

    Drives the PRE-EXISTING entry point ``collect_feature_summary``. Planning docs
    live ONLY on primary and the status event log ONLY on coord, so a single run
    proves BOTH partitions resolved correctly (#2085 / #2107 accept facet).
    """
    repo_root, _primary_dir, _coord_dir = coord_mission

    summary = collect_feature_summary(
        repo_root, _HANDLE, strict_metadata=False, mutate_matrix=False
    )

    # PLANNING → primary: the docs (primary-only) are found, not mis-reported missing.
    assert summary.missing_artifacts == [], (
        "Accept gate mis-blocked planning artifacts — it read the coord surface "
        "instead of primary (planning-read split regressed)."
    )
    # STATUS → coord: the event log (coord-only) is consulted, no "no canonical state".
    assert not [
        issue for issue in summary.activity_issues if "No canonical state found" in issue
    ], (
        "Accept gate lost the status event log — it read primary instead of coord "
        "(C-002 status leniency regressed)."
    )


def test_accept_gate_iterates_wp_tasks_from_primary(
    coord_mission: tuple[Path, Path, Path],
) -> None:
    """Closeout N+1: WP-task iteration resolves PRIMARY, not the coord husk.

    ``WORK_PACKAGE_TASK`` is a PRIMARY-partition kind; the ``coord_mission``
    fixture carries the WP task ONLY on primary (a real coord mission does). The
    REAL accept gate (``collect_feature_summary`` → ``_iter_work_packages``) must
    iterate that primary WP task and NOT raise ``AcceptanceError: ... has no tasks
    directory`` against the materialized ``-coord`` worktree (whose ``tasks/`` dir
    is absent). Pre-fix, ``_iter_work_packages`` resolved the coord-aware seam and
    raised — see debbie §3. This test fails RED on the pre-fix product.
    """
    repo_root, _primary_dir, _coord_dir = coord_mission

    # No raise: the WP-task read landed on PRIMARY (where the task lives), not the
    # coord husk. Pre-fix this raised AcceptanceError("has no tasks directory").
    summary = collect_feature_summary(
        repo_root, _HANDLE, strict_metadata=False, mutate_matrix=False
    )

    # The primary-only WP task was actually iterated (the gate SAW it).
    assert [wp.work_package_id for wp in summary.work_packages] == ["WP01"], (
        "Accept gate did not iterate the primary WP task — it read the coord "
        "surface (WORK_PACKAGE_TASK is a PRIMARY-partition kind; closeout N+1)."
    )


def test_record_analysis_allowlist_and_g5_dirt(
    coord_mission: tuple[Path, Path, Path],
) -> None:
    """record_analysis STATUS/allowlist behavior (NOT a vacuous planning cell).

    Per the WP10 remediation: after WP04's double-resolution collapse,
    ``record_analysis`` has no observable planning-read delta. Its observable
    behavior is the dirty-tree preflight — it does NOT block on self-bookkeeping
    churn (meta.json / provenance) but STILL blocks on a stale primary ``spec.md``
    (the G-5 "real dirt" invariant). Over-allowlisting ``spec.md`` turns the second
    arm RED.
    """
    repo_root, primary_dir, _coord_dir = coord_mission

    # Self-bookkeeping churn (meta.json + provenance) — allowlisted, must NOT block.
    (primary_dir / "meta.json").write_text(
        (primary_dir / "meta.json").read_text(encoding="utf-8").replace(
            "software-dev", "software-dev "
        ),
        encoding="utf-8",
    )
    provenance = repo_root / ".kittify" / "encoding-provenance"
    provenance.mkdir(parents=True, exist_ok=True)
    (provenance / "global.jsonl").write_text(
        '{"path": "kitty-specs/x/spec.md", "encoding": "utf-8"}\n', encoding="utf-8"
    )
    _git(repo_root, "add", ".kittify")
    _git(repo_root, "commit", "-q", "-m", "seed provenance")
    (provenance / "global.jsonl").write_text(
        '{"path": "kitty-specs/x/spec.md", "encoding": "utf-8"}\n'
        '{"path": "kitty-specs/y/plan.md", "encoding": "utf-8"}\n',
        encoding="utf-8",
    )

    # Allowlist arm: self-bookkeeping churn does NOT block the preflight.
    _enforce_analysis_report_write_preflight(
        repo_root,
        json_output=True,
        placement_ref=None,
        mission_slug=_HANDLE,
    )

    # G-5 arm: a stale primary spec.md is real dirt and STILL blocks. Over-allowlisting
    # spec.md (folding it into the self-bookkeeping set) turns this RED.
    (primary_dir / "spec.md").write_text("# spec.md\n\nEDITED.\n", encoding="utf-8")
    with pytest.raises(typer.Exit):
        _enforce_analysis_report_write_preflight(
            repo_root,
            json_output=True,
            placement_ref=None,
            mission_slug=_HANDLE,
        )


# ---------------------------------------------------------------------------
# T031 (DoD) — the WP00 write twin on the SAME two-surface fixture.
# ---------------------------------------------------------------------------


def test_write_twin_resolves_target_branch_not_main(
    coord_mission: tuple[Path, Path, Path],
) -> None:
    """WP00 write twin (G-6 / FR-004 / FR-009e): commit resolution → target_branch.

    On the composed coord fixture, ``get_feature_target_branch`` /
    ``resolve_target_branch`` / the finalize-tasks commit placement all resolve the
    mission's ``target_branch`` (read from ``meta.json`` on the PRIMARY surface), NOT
    the protected repo primary ``main`` — and the coord surface is unchanged.
    Reverting the resolver to ``candidate_feature_dir_for_mission`` (coord has no
    ``target_branch`` in this fixture's coord meta) regresses it toward the primary
    fallback (RED).
    """
    repo_root, _primary_dir, coord_dir = coord_mission

    assert get_feature_target_branch(repo_root, _HANDLE) == _TARGET, (
        "get_feature_target_branch must anchor on the PRIMARY meta.json "
        "(target_branch), not the topology candidate."
    )

    resolution = resolve_target_branch(
        _HANDLE,
        repo_root,
        current_branch="feat/some-other-branch",
        respect_current=True,
    )
    assert resolution.target == _TARGET

    placement = resolve_placement_only(
        repo_root, _HANDLE, kind=MissionArtifactKind.TASKS_INDEX
    )
    assert placement.ref == _TARGET, (
        "finalize-tasks TASKS_INDEX commit must resolve target_branch, not the "
        f"protected repo primary (got {placement.ref!r})."
    )

    # The STATUS/coord surface is untouched by the write-twin resolution.
    assert (coord_dir / "status.events.jsonl").exists()


def test_write_twin_anchors_on_primary_not_candidate(
    coord_mission: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Anti-mutant write arm: anchoring on the coord candidate regresses target.

    The coord meta in this fixture carries NO ``target_branch`` (the #2106
    divergence), so anchoring the resolver's meta lookup on the candidate dir drops
    to the fallback — proving the production resolver anchors on PRIMARY.
    """
    repo_root, primary_dir, _coord_dir = coord_mission

    # Control: the production primary anchor points at the primary feature dir,
    # which carries target_branch; the coord meta in this fixture lacks it.
    assert (
        primary_feature_dir_for_mission(repo_root, _HANDLE).resolve()
        == primary_dir.resolve()
    )

    # Sanity: production resolves target_branch off primary.
    assert get_feature_target_branch(repo_root, _HANDLE) == _TARGET

    # Mutate the write-side anchor (lazily imported by get_feature_target_branch from
    # the resolver source) to a dir whose meta.json lacks target_branch — the coord
    # divergence the fix removes. The resolver must drop to the fallback (not _TARGET).
    no_target_dir = repo_root / "kitty-specs" / "no-target"
    no_target_dir.mkdir(parents=True)
    (no_target_dir / "meta.json").write_text(
        json.dumps({"mission_slug": _HANDLE, "mid8": _MID8}), encoding="utf-8"
    )
    monkeypatch.setattr(
        "specify_cli.missions._read_path_resolver.primary_feature_dir_for_mission",
        lambda root, slug: no_target_dir,
    )
    mutated = get_feature_target_branch(repo_root, _HANDLE)
    assert mutated != _TARGET, (
        "Anchoring on a candidate dir without target_branch did NOT regress target "
        "resolution — the write-twin primary anchor is not load-bearing."
    )
