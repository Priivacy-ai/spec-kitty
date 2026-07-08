"""The ``finalize-tasks`` command family, relocated out of ``tasks.py`` (WP08, #2058).

Mission ``tasks-py-degod-wave2-01KWH9EQ`` FR-001/FR-002: ``_do_finalize_tasks``
+ the 4 ``_ft_*`` phase helpers + ``_FinalizeState`` +
``_default_finalize_ports`` live here, moved VERBATIM from ``tasks.py`` — the
squad-recovered FIFTH family, completing the family relocations (after this
move ALL five command families are out of ``tasks.py``). The ``@app.command``
Typer wrapper (``finalize_tasks``) stays in ``tasks.py`` and delegates to
:func:`_do_finalize_tasks` (the byte-frozen ``--help`` surface is the
registration shim's).

**Orchestration shape** (unchanged): the phase helpers run in the SAME order
as the original single body — resolve → validate → apply → output — so the
frontmatter writes still fire only after every validation gate has passed
(NFR-002). ``finalize_tasks`` is CORELESS (FR-007/FR-010): it validates
through the existing ``tasks_finalize_validation`` seam and has ZERO direct
emission sites (research.md D3) — no byte case is owned by this family.

**Seam bridge** (research.md D1/D7): the relocated bodies reach every patched
seam symbol through a lazy in-function import of the ``tasks`` module
(``from specify_cli.cli.commands.agent import tasks as _tasks``) and call
``_tasks.<attr>(...)``, so every historical ``@patch("...agent.tasks.<sym>")``
/ ``monkeypatch.setattr(tasks, ...)`` keeps INTERCEPTING after the move —
including ``bootstrap_canonical_state`` (×7, test_tasks_canonical_cleanup),
the conftest ``console`` rebinding, and the port adapters constructed by
``_default_finalize_ports`` (which builds the plain ``RealCoordCommitRouter``
— finalize commits nothing itself; the router is the bundle's inert WRITE
authority). ``tasks.py`` re-imports the family in the explicit ``as``
re-export form, so ``tasks.<name>`` stays a module attribute. Symbols with
ZERO patch sites and a canonical home outside ``tasks.py`` (the
``tasks_finalize_validation`` gates, the pre30 guard, ``TASKS_MD_FILENAME``)
are imported directly at module scope (cycle-safe: none of those modules
import ``tasks``). read-surface-ssot-closeout WP08 (FR-001/NFR-001): the
former ``resolve_feature_dir_for_mission`` pre30-guard-wiring seam is
RETIRED — ``_ft_apply_writes`` now calls
``mission_runtime.placement_seam(...).read_dir(STATUS_STATE)`` directly
(module-scope import, not the ``_tasks.<attr>`` proxy).

Per-symbol routing/interception evidence:
``kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md`` (Layer 4 of
the parity contract).
"""

from __future__ import annotations

import contextlib
import traceback
from dataclasses import dataclass, field
from pathlib import Path

import typer

from mission_runtime import MissionArtifactKind, placement_seam
from specify_cli.agent_tasks_ports import MissionHandle, TasksPorts
from specify_cli.cli.commands.agent.tasks_finalize_validation import (
    FrontmatterUpdatePlan,
    compute_wp_frontmatter_updates,
    detect_dependency_conflicts,
    detect_dependency_cycles,
    read_existing_frontmatter,
    validate_wp_coverage,
)
from specify_cli.cli.commands.agent.tasks_outline import TASKS_MD_FILENAME
from specify_cli.status import BootstrapResult
from specify_cli.upgrade.pre30_guard import Pre30LayoutError, check_pre30_layout


@dataclass
class _FinalizeState:
    """Mutable orchestration state threaded through ``finalize_tasks``'s phases.

    Not frozen: each phase fills its own slice in the SAME order the original body
    did (resolve → validate → apply → output), so the frontmatter writes still fire
    only after every validation gate has passed.
    """

    # --- raw command inputs ---
    mission: str | None
    json_output: bool
    validate_only: bool
    # --- phase A: resolved context ---
    repo_root: Path = field(default_factory=Path)
    main_repo_root: Path = field(default_factory=Path)
    target_branch: str = ""
    mission_slug: str = ""
    primary_feature_dir: Path = field(default_factory=Path)
    tasks_md: Path = field(default_factory=Path)
    tasks_dir: Path = field(default_factory=Path)
    # --- phase B: parsed/validated reads ---
    dependencies_map: dict[str, list[str]] = field(default_factory=dict)
    # --- phase C: applied writes + bootstrap ---
    update_plan: FrontmatterUpdatePlan | None = None
    would_modify: list[dict[str, object]] = field(default_factory=list)
    feature_dir: Path = field(default_factory=Path)
    bootstrap_result: BootstrapResult | None = None


def _default_finalize_ports() -> TasksPorts:
    """Production port bundle for ``finalize_tasks`` (FsReader read authority)."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    return TasksPorts(
        fs=_tasks.RealFsReader(),
        coord=_tasks.RealCoordCommitRouter(),
        git=_tasks.RealGitOps(),
        render=_tasks.RealRender(),
    )


def _ft_resolve_context(st: _FinalizeState, ports: TasksPorts) -> None:
    """Phase A: repo/branch/read-dir resolution + the pre30 guard + existence checks.

    FR-010 / T035: the pre30-guard read is GUARD-ONLY (the coord-husk var fed ONLY
    ``check_pre30_layout`` before being reassigned to the primary read), so migrate
    it onto the kind-aware WORK_PACKAGE_TASK authority via the ``FsReader`` port.
    ``tasks.md`` and ``tasks/`` are PRIMARY-partition (FR-001 / C-001 per-leg split),
    so this single read feeds BOTH the guard and the parse. The WP02 T013 proof
    establishes the guard outcome is byte-identical across legs on a modern mission
    (SC-002/NFR-001). Only the STATUS artifacts (bootstrap, event log) use the
    coord-aware resolver in phase C.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    repo_root = _tasks.locate_project_root()
    if repo_root is None:
        _tasks._output_error(st.json_output, "Could not locate project root")
        raise typer.Exit(1)
    st.repo_root = repo_root
    # FR-010 / FR-019: one-shot sparse-checkout session warning.
    _tasks._emit_sparse_session_warning(repo_root, command="spec-kitty agent tasks finalize-tasks")
    st.mission_slug = _tasks._find_mission_slug(
        explicit_mission=st.mission, json_output=st.json_output, repo_root=repo_root
    )
    st.main_repo_root, st.target_branch = _tasks._ensure_target_branch_checked_out(
        repo_root, st.mission_slug, st.json_output
    )
    handle = MissionHandle(repo_root=st.main_repo_root, mission_slug=st.mission_slug)
    st.primary_feature_dir = ports.fs.planning_read_dir(
        handle, kind=MissionArtifactKind.WORK_PACKAGE_TASK
    )
    # Boundary guard — hard-reject pre-3.0 layout before any WP mutation (#1057)
    try:
        check_pre30_layout(st.primary_feature_dir)
    except Pre30LayoutError as e:
        _tasks._output_error(st.json_output, str(e))
        raise typer.Exit(1) from None
    st.tasks_md = st.primary_feature_dir / TASKS_MD_FILENAME
    st.tasks_dir = st.primary_feature_dir / "tasks"

    if not st.tasks_md.exists():
        _tasks._output_error(st.json_output, f"tasks.md not found: {st.tasks_md}")
        raise typer.Exit(1)
    if not st.tasks_dir.exists():
        _tasks._output_error(st.json_output, f"Tasks directory not found: {st.tasks_dir}")
        raise typer.Exit(1)


def _ft_validate_occurrence_map_ready(st: _FinalizeState) -> None:
    """Bulk-edit occurrence-map gate (mirrors ``mission_finalize._validate_occurrence_map_ready``).

    ``spec-kitty agent tasks finalize-tasks`` (this legacy command family) and
    ``spec-kitty agent mission finalize-tasks`` are two independently-dispatched
    commands that both advance a mission past the tasks-finalize boundary.
    Gating only the ``mission`` variant left this one able to complete
    finalize-tasks for a bulk-edit mission with a missing / schema-invalid /
    inadmissible ``occurrence_map.yaml`` with zero gate friction — the exact
    late-failure timing the occurrence-map gate exists to eliminate (found by
    the pre-hand-off adversarial squad, architect-alphonso lens, during
    landing). Reuses ``ensure_occurrence_classification_ready`` unchanged (no
    new validation logic) and self-conditions on stored ``change_mode``, so
    non-bulk-edit missions are unaffected — same contract as the other
    enforcement points.
    """
    from specify_cli.bulk_edit.gate import (
        FINALIZE_TASKS_GATE_BLOCKED_MESSAGE,
        ensure_occurrence_classification_ready,
        finalize_tasks_gate_error_payload,
        render_gate_failure,
    )
    from specify_cli.cli.commands.agent import tasks as _tasks

    result = ensure_occurrence_classification_ready(st.primary_feature_dir)
    if result.passed:
        return
    if st.json_output:
        _tasks._output_error(
            st.json_output,
            FINALIZE_TASKS_GATE_BLOCKED_MESSAGE,
            finalize_tasks_gate_error_payload(result),
        )
    else:
        render_gate_failure(result, _tasks.console)
    raise typer.Exit(1)


def _ft_validate(st: _FinalizeState) -> None:
    """Phase B: occurrence-map gate + parse deps + WP04 coverage/cycle/disagree-loud conflict gates.

    Each gate is a PRE-write refusal — the frontmatter writes in phase C fire only
    after every gate below passes. The occurrence-map gate runs FIRST (fail-fast,
    before the more expensive dependency-graph validators), mirroring the
    placement in ``mission_finalize.finalize_tasks``.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    from specify_cli.core.dependency_parser import (
        parse_dependencies_from_tasks_md as _shared_parse_deps,
    )

    _ft_validate_occurrence_map_ready(st)

    tasks_content = st.tasks_md.read_text(encoding="utf-8")
    st.dependencies_map = _shared_parse_deps(tasks_content)

    coverage = validate_wp_coverage(st.dependencies_map, st.tasks_dir)
    if not coverage.ok:
        _tasks._output_error(
            st.json_output,
            (
                "tasks.md work package coverage is incomplete. finalize-tasks could not match "
                "all WP files to parsed sections, so dependency lanes would be unreliable."
            ),
        )
        raise typer.Exit(1)

    cycles = detect_dependency_cycles(st.dependencies_map)
    if cycles:
        _tasks._output_error(st.json_output, f"Circular dependencies detected: {cycles}")
        raise typer.Exit(1)

    # --- Dependency conflict detection (T004: disagree-loud) ---
    existing_frontmatter = read_existing_frontmatter(st.tasks_dir)
    dep_conflict_errors = detect_dependency_conflicts(st.dependencies_map, existing_frontmatter)
    if dep_conflict_errors:
        error_msg = "Dependency disagreement detected:\n" + "\n".join(dep_conflict_errors)
        _tasks._output_error(st.json_output, error_msg)
        raise typer.Exit(1)


def _ft_apply_writes(st: _FinalizeState) -> None:
    """Phase C: apply the computed frontmatter writes (validate-only-gated) + bootstrap.

    The frontmatter updates are computed side-effect-free, then applied gating ALL
    writes on ``validate_only`` (T005/T006). Bootstrap reads the event log/meta.json
    via the topology-aware (STATUS-partition) resolver — it MUST stay coord-aware.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    from specify_cli.frontmatter import write_frontmatter as _write_fm

    update_plan = compute_wp_frontmatter_updates(st.dependencies_map, st.tasks_dir)
    st.update_plan = update_plan
    for warning in update_plan.warnings:
        _tasks.console.print(f"[yellow]Warning:[/yellow] {warning}")

    would_modify: list[dict[str, object]] = []
    for write in update_plan.writes:
        if not st.validate_only:
            _write_fm(write.wp_file, write.updated_meta.model_dump(exclude_none=True), write.body)
        else:
            would_modify.append({"wp_id": write.wp_id, "changes": {"dependencies": write.dependencies}})
    st.would_modify = would_modify

    # Bootstrap canonical status state for all WPs — STATUS-partition: reads the
    # event log and meta.json via the topology-aware resolver (C-001, coord-husk).
    # read-surface-ssot-closeout WP08 / FR-001 / NFR-001: routed through the
    # kind-aware placement seam directly (no longer proxied through
    # ``_tasks.resolve_feature_dir_for_mission`` — the kind-blind resolver's
    # module re-export was retired in the same WP; ``STATUS_STATE`` resolves
    # the SAME coord-aware dir the kind-blind resolver produced for this read).
    st.feature_dir = placement_seam(st.main_repo_root, st.mission_slug).read_dir(
        MissionArtifactKind.STATUS_STATE
    )
    st.bootstrap_result = _tasks.bootstrap_canonical_state(
        st.feature_dir, st.mission_slug, dry_run=st.validate_only
    )


def _ft_output(st: _FinalizeState) -> None:
    """Phase D: build the validate-only / success envelope and emit it."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    assert st.update_plan is not None and st.bootstrap_result is not None
    update_plan = st.update_plan
    bootstrap_result = st.bootstrap_result
    bootstrap_payload = {
        "total_wps": bootstrap_result.total_wps,
        "already_initialized": bootstrap_result.already_initialized,
        "newly_seeded": bootstrap_result.newly_seeded,
        "skipped": bootstrap_result.skipped,
        "wp_details": bootstrap_result.wp_details,
    }
    if st.validate_only:
        result: dict[str, object] = {
            "result": "validation_passed",
            "validate_only": True,
            "would_modify": st.would_modify,
            "would_preserve": update_plan.preserved_wps,
            "unchanged": update_plan.unchanged_wps,
            "updated_wp_count": update_plan.updated_count,
            "dependencies": st.dependencies_map,
            **_tasks._mission_identity_payload(st.feature_dir),
            "bootstrap": bootstrap_payload,
        }
    else:
        result = {
            "result": "success",
            "updated_wp_count": update_plan.updated_count,
            "modified_wps": update_plan.modified_wps,
            "unchanged_wps": update_plan.unchanged_wps,
            "preserved_wps": update_plan.preserved_wps,
            "dependencies": st.dependencies_map,
            **_tasks._mission_identity_payload(st.feature_dir),
            "bootstrap": bootstrap_payload,
        }

    _tasks._output_result(
        st.json_output,
        result,
        f"[green]✓[/green] Updated {update_plan.updated_count} WP files with dependencies"
        f" (bootstrap: {bootstrap_result.newly_seeded} seeded,"
        f" {bootstrap_result.already_initialized} existing)",
    )


def _do_finalize_tasks(
    mission: str | None,
    json_output: bool,
    validate_only: bool,
    *,
    ports: TasksPorts | None = None,
) -> None:
    """Orchestrate ``finalize-tasks`` over the WP02 ``FsReader`` port, CORELESS.

    ``finalize_tasks`` carries NO decision core (FR-007): it parses/validates deps
    through the existing ``tasks_finalize_validation`` seam and applies the computed
    writes. It does NOT route through any transition core (deferred #2300; guarded by
    the T036 non-import gate). ``ports=None`` builds the production bundle. The phase
    helpers run in the SAME order as the original single body: resolve → validate →
    apply → output.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    ports = ports or _default_finalize_ports()
    st = _FinalizeState(mission=mission, json_output=json_output, validate_only=validate_only)
    try:
        _ft_resolve_context(st, ports)
        _ft_validate(st)
        _ft_apply_writes(st)
        _ft_output(st)
    except typer.Exit:
        raise
    except Exception as e:
        # Emit ErrorLogged event (T016).
        with contextlib.suppress(Exception):
            _tasks.emit_error_logged(
                error_type="runtime",
                error_message=str(e),
                stack_trace=traceback.format_exc(),
            )
        _tasks._output_error(json_output, str(e))
        raise typer.Exit(1) from None
