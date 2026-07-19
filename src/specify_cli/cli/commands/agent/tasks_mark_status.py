"""The ``mark-status`` command family, relocated out of ``tasks.py`` (WP08, #2058).

Mission ``tasks-py-degod-wave2-01KWH9EQ`` FR-001/FR-002: ``_do_mark_status`` +
the 9 ``_ms_*`` phase helpers + ``_MarkStatusState`` +
``_default_mark_status_ports`` live here, moved VERBATIM from ``tasks.py``.
The ``@app.command`` Typer wrapper (``mark_status``) stays in ``tasks.py`` and
delegates to :func:`_do_mark_status` (the byte-frozen ``--help`` surface is the
registration shim's).

**Orchestration shape** (unchanged): the phase helpers run in the SAME order as
the original single body — validate → resolve → apply → history → dossier →
output — so the ``tasks.md`` write still precedes the auto-commit and the
feature status lock still spans the read → resolve → write → commit span
(NFR-002). ``mark_status`` is CORELESS (FR-007): it carries NO transition
decision core and does NOT route through ``move_task``'s ``decide_transition``
(the deferred #2300 unification, guarded structurally by the coreless
non-import gate).

**C-001 divergence wiring**: ``mark_status`` sits on the REFUSE arm — when
auto-commit resolves on, ``_ms_resolve_context`` refuses exit-1 through
``_tasks._protected_branch_status_commit_error`` with NO
``_skip_target_branch_commit`` pre-gate (that skip-exit-0 pre-gate is
``move_task``-only). The wiring moved untouched; the coord harness refuse-arm
case (harness label T005) pins it end-to-end. ``mark_status`` also owns the
no-IDs error byte case (research.md D3, routed through Render by WP04) — the
``_ms_report_none_resolved`` emission moved verbatim.

**Seam bridge** (research.md D1/D7): the relocated bodies reach every patched
seam symbol through a lazy in-function import of the ``tasks`` module
(``from specify_cli.cli.commands.agent import tasks as _tasks``) and call
``_tasks.<attr>(...)``, so every historical ``@patch("...agent.tasks.<sym>")``
/ ``monkeypatch.setattr(tasks, ...)`` keeps INTERCEPTING after the move —
including the heavy ``feature_status_lock`` (D7 ×21) and ``emit_history_added``
(×10) seams, the conftest ``console`` rebinding, ``_resolve_inline_subtasks``
(which stays ``tasks.py``-resident per the T007 partition record) and the port
adapters constructed by ``_default_mark_status_ports`` (the coord router built
by ``tasks.seam_coord_router()``, whose ``commit_artifact`` body routes
``commit_for_mission`` back through ``_tasks.<attr>``, WP03 / degod-follow-ups
constructor-DI collapse). ``tasks.py`` re-imports the family in the explicit ``as`` re-export
form, so ``tasks.<name>`` stays a module attribute. Symbols with ZERO patch
sites and a canonical home outside ``tasks.py`` are imported directly at
module scope (cycle-safe: none of those modules import ``tasks``).

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

from mission_runtime import MissionArtifactKind
from specify_cli.agent_tasks_ports import MissionHandle, TasksPorts
from specify_cli.cli.commands.agent.tasks_materialization import (
    _resolve_checkbox,
    _resolve_pipe_table,
)
from specify_cli.cli.commands.agent.tasks_outline import (
    TASKS_MD_FILENAME,
    TaskIdResolutionFormat,
    TaskIdResolutionOutcome,
    TaskIdResult,
    _INLINE_SUBTASKS_RE,
    _normalize_task_id_input,
    _resolve_history_wp_id,
    _resolve_wp_id,
)
from specify_cli.upgrade.pre30_guard import Pre30LayoutError, check_pre30_layout


@dataclass
class _MarkStatusState:
    """Mutable orchestration state threaded through ``mark_status``'s phases.

    The single-body command tracked ~15 loose locals across validate → resolve →
    apply → history → output; the phase helpers exchange this one value object
    instead. Not frozen: each phase fills its own slice in the SAME order the
    original body did, so the ``tasks.md`` write still precedes the auto-commit.
    """

    # --- raw command inputs ---
    task_ids: list[str]
    status: str
    mission: str | None
    auto_commit: bool | None
    json_output: bool
    # --- phase A/B: resolved context ---
    repo_root: Path = field(default_factory=Path)
    main_repo_root: Path = field(default_factory=Path)
    target_branch: str = ""
    mission_slug: str = ""
    resolved_auto_commit: bool = False
    feature_dir: Path = field(default_factory=Path)
    tasks_md: Path = field(default_factory=Path)
    # --- phase C: apply results ---
    results: list[TaskIdResult] = field(default_factory=list)
    updated_tasks: list[str] = field(default_factory=list)
    not_found_tasks: list[str] = field(default_factory=list)
    resolved_tasks: list[str] = field(default_factory=list)
    artifact_mutated: bool = False


def _default_mark_status_ports() -> TasksPorts:
    """Production port bundle for ``mark_status`` (coord router bound to tasks.py)."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    return TasksPorts(
        fs=_tasks.RealFsReader(),
        # mark_status routes only the commit seam through ``tasks`` and commits
        # target-branch-less (byte-parity with the pre-rewire inline call); it
        # inherited the base ``commit_status`` emitter binding.
        coord=_tasks.seam_coord_router(),
        git=_tasks.RealGitOps(),
        render=_tasks.RealRender(),
    )


def _ms_validate_inputs(st: _MarkStatusState) -> None:
    """Phase A: validate ``--status`` + non-empty task IDs, then normalize IDs."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    if st.status not in ("done", "pending"):
        _tasks._output_error(st.json_output, f"Invalid status '{st.status}'. Must be 'done' or 'pending'.")
        raise typer.Exit(1)
    if not st.task_ids:
        _tasks._output_error(st.json_output, "At least one task ID is required")
        raise typer.Exit(1)
    # WP04/T022 (FR-017): accept both bare and mission-qualified task IDs
    # (``T001`` or ``<mission_slug>/T001`` / ``<mission_slug>:T001``). Normalize to
    # bare task IDs before validation. A garbage ID surfaces as "no task IDs found
    # in tasks.md" downstream — preserving the structured-error contract.
    st.task_ids = [_normalize_task_id_input(tid) for tid in st.task_ids]


def _ms_resolve_context(st: _MarkStatusState) -> None:
    """Phase B(i): repo/branch/auto-commit + the protected-branch refuse-exit-1 gate.

    The protected-branch guard fires unconditionally under ``auto_commit`` — it does
    NOT consult ``_skip_target_branch_commit``, so on a coord + protected-primary
    tree ``mark_status`` REFUSES (exit 1) where ``move_task`` SKIPS (exit 0). That
    divergence is deliberate (T005 / deferred #2300) and preserved here.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    repo_root = _tasks.locate_project_root()
    if repo_root is None:
        _tasks._output_error(st.json_output, "Could not locate project root")
        raise typer.Exit(1)
    st.repo_root = repo_root
    # FR-010 / FR-019: one-shot sparse-checkout session warning.
    _tasks._emit_sparse_session_warning(repo_root, command="spec-kitty agent tasks mark-status")
    st.resolved_auto_commit = (
        _tasks.get_auto_commit_default(repo_root) if st.auto_commit is None else st.auto_commit
    )
    st.mission_slug = _tasks._find_mission_slug(
        explicit_mission=st.mission, json_output=st.json_output, repo_root=repo_root
    )
    st.main_repo_root, st.target_branch = _tasks._ensure_target_branch_checked_out(
        repo_root, st.mission_slug, st.json_output
    )
    if st.resolved_auto_commit:
        protected_error = _tasks._protected_branch_status_commit_error(
            st.target_branch,
            st.main_repo_root,
            "spec-kitty agent tasks mark-status",
        )
        if protected_error is not None:
            _tasks._output_error(st.json_output, protected_error)
            raise typer.Exit(1)


def _ms_resolve_read_dir(st: _MarkStatusState, ports: TasksPorts) -> None:
    """Phase B(ii): resolve the TASKS_INDEX write surface (#2154) + pre30 guard.

    #2154 (FR-001 / T008): ``tasks.md`` is a TASKS_INDEX (primary-partition)
    artifact — resolve the WRITE leg through the SAME kind-aware authority the
    validation read and the commit leg use (now the ``FsReader`` port), so the
    subtask write lands on the PRIMARY surface a coord-topology mission reads back
    from. The kind-blind ``resolve_feature_dir_for_mission`` returns the ``-coord``
    husk under coord topology, so the write and the validation read would diverge.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    handle = MissionHandle(repo_root=st.main_repo_root, mission_slug=st.mission_slug)
    st.feature_dir = ports.fs.planning_read_dir(handle, kind=MissionArtifactKind.TASKS_INDEX)
    # Boundary guard — hard-reject pre-3.0 layout before any WP mutation
    try:
        check_pre30_layout(st.feature_dir)
    except Pre30LayoutError as e:
        _tasks._output_error(st.json_output, str(e))
        raise typer.Exit(1) from None
    st.tasks_md = st.feature_dir / TASKS_MD_FILENAME


def _ms_report_none_resolved(st: _MarkStatusState) -> None:
    """Emit the contracted 'no task IDs resolved' error and exit 1."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    if st.json_output:
        render = _tasks.RealRender()
        print(render.json_envelope(_tasks._mark_status_json_payload(st.results)))
    elif any(result.format == TaskIdResolutionFormat.WP_ID for result in st.results):
        detail = "; ".join(result.message for result in st.results if result.message)
        _tasks._output_error(st.json_output, detail)
    else:
        _tasks._output_error(st.json_output, f"No task IDs found in tasks.md: {', '.join(st.not_found_tasks)}")
    raise typer.Exit(1)


def _ms_commit(st: _MarkStatusState, ports: TasksPorts) -> None:
    """Auto-commit the ``tasks.md`` mutation through the coord ``commit_artifact`` port.

    ``tasks.md`` is TASKS_INDEX (primary): route the commit through the coord WRITE
    ``commit_artifact`` capability (over the canonical ``commit_for_mission`` entry
    point). The router owns placement resolution AND the protected-primary refusal.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    # Extract spec number from mission_slug (e.g., "014" from "014-feature-name").
    spec_number = st.mission_slug.split("-")[0] if "-" in st.mission_slug else st.mission_slug
    if len(st.updated_tasks) == 1:
        commit_msg = f"chore: Mark {st.updated_tasks[0]} as {st.status} on spec {spec_number}"
    else:
        commit_msg = f"chore: Mark {len(st.updated_tasks)} subtasks as {st.status} on spec {spec_number}"
    try:
        actual_tasks_path = st.tasks_md.resolve()
        router_result = ports.coord.commit_artifact(
            MissionHandle(repo_root=st.main_repo_root, mission_slug=st.mission_slug),
            (actual_tasks_path,),
            commit_msg,
            kind=MissionArtifactKind.TASKS_INDEX,
            policy=_tasks.ProtectionPolicy.resolve(st.main_repo_root),
        )
        if router_result.status == "committed":
            if not st.json_output:
                _tasks.console.print(f"[cyan]→ Committed subtask changes to {st.target_branch} branch[/cyan]")
        elif not st.json_output:
            _tasks.console.print("[yellow]Warning:[/yellow] Failed to auto-commit subtask changes")
    except Exception as e:
        if not st.json_output:
            _tasks.console.print(f"[yellow]Warning:[/yellow] Auto-commit exception: {e}")


def _ms_apply_updates(st: _MarkStatusState, ports: TasksPorts) -> None:
    """Phase C: resolve each task ID to a durable row, write tasks.md, auto-commit.

    Holds the feature status lock across the read → resolve → write → commit span,
    exactly as the pre-rewire single body did.

    WP04/T015 (FR-003/FR-008/C-001): the canonical subtask-completion surface
    (``CHECKBOX`` / ``INLINE_SUBTASKS``) is re-sourced from an
    ``InnerStateChanged`` emit (``_ms_emit_subtask_state``, called by
    ``_do_mark_status`` after this phase) once the phase-1 snapshot authority is
    active. #2684 flag-OFF dual-write: while that authority is INACTIVE (the
    pre-cutover default), ``emit._infer_subtasks_complete`` still reads the
    ``CHECKBOX`` byte off ``tasks.md``, so the checkbox flip is persisted at flag
    OFF (legacy authority = dual-write). At flag ON the ``CHECKBOX`` resolver runs
    against a throwaway copy of ``lines`` so its in-place mutation never leaks
    into the file that gets written (event-sourced only). ``PIPE_TABLE`` is a
    distinct, non-canonical surface (the review gate's
    ``iter_wp_section_subtask_rows`` never reads it) and keeps its existing
    durable write regardless of flag.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    from specify_cli.status import phase1_snapshot_authority_active
    with _tasks.feature_status_lock(st.main_repo_root, st.mission_slug):
        if not st.tasks_md.exists():
            _tasks._output_error(st.json_output, f"tasks.md not found: {st.tasks_md}")
            raise typer.Exit(1)

        content = st.tasks_md.read_text(encoding="utf-8")
        lines = content.split("\n")
        results: list[TaskIdResult] = []
        artifact_mutated = False

        # #2684 flag-OFF dual-write: at flag OFF the CHECKBOX byte in ``tasks.md``
        # is still the completion authority the review gate re-sources from
        # (``emit._infer_subtasks_complete`` reads ``count_wp_section_subtask_rows``
        # off ``tasks.md`` when the phase-1 snapshot authority is inactive). So the
        # checkbox flip MUST be persisted at flag OFF (legacy authority = dual-write),
        # exactly as before the eviction. At flag ON the reduced snapshot is the
        # sole authority, so the checkbox stays event-sourced-only (probe copy).
        legacy_checkbox_write = not phase1_snapshot_authority_active(st.feature_dir)

        # Update all requested tasks in a single pass.
        for task_id in st.task_ids:
            before_content = "\n".join(lines)
            # WP04/T015: at flag ON, probe the checkbox resolver against a throwaway
            # copy — its in-place row mutation must never reach the persisted
            # ``lines`` since the canonical subtask surface is not durably written.
            # At flag OFF, mutate ``lines`` directly so the legacy checkbox byte is
            # persisted (dual-write, see ``legacy_checkbox_write`` above).
            checkbox_lines = lines if legacy_checkbox_write else list(lines)
            result = (
                _resolve_checkbox(task_id, checkbox_lines, st.status)
                or _resolve_pipe_table(task_id, lines, st.status)
                or _tasks._resolve_inline_subtasks(task_id, before_content, st.status, st.feature_dir)
                or _resolve_wp_id(task_id, st.status, st.mission_slug, st.feature_dir)
                or TaskIdResult(
                    id=task_id,
                    outcome=TaskIdResolutionOutcome.NOT_FOUND,
                    format=None,
                    message=f"{task_id} was not found in any supported task format.",
                )
            )
            results.append(result)
            if result.outcome == TaskIdResolutionOutcome.UPDATED and (
                result.format == TaskIdResolutionFormat.PIPE_TABLE
                or (
                    legacy_checkbox_write
                    and result.format == TaskIdResolutionFormat.CHECKBOX
                )
            ):
                artifact_mutated = True

        st.results = results
        st.updated_tasks = [r.id for r in results if r.outcome == TaskIdResolutionOutcome.UPDATED]
        st.not_found_tasks = [r.id for r in results if r.outcome == TaskIdResolutionOutcome.NOT_FOUND]
        st.resolved_tasks = [r.id for r in results if r.outcome != TaskIdResolutionOutcome.NOT_FOUND]
        st.artifact_mutated = artifact_mutated

        # Fail if no tasks were resolved.
        if not st.resolved_tasks:
            _ms_report_none_resolved(st)

        # Write updated content (single write for all changes) — PIPE_TABLE only;
        # CHECKBOX/INLINE_SUBTASKS completion is event-sourced (see docstring).
        if artifact_mutated:
            st.tasks_md.write_text("\n".join(lines), encoding="utf-8")

        # Auto-commit to TARGET branch (detects from feature meta.json).
        if st.resolved_auto_commit and artifact_mutated:
            _ms_commit(st, ports)


def _ms_emit_subtask_state(st: _MarkStatusState) -> None:
    """Emit the ``InnerStateChanged`` subtask-completion delta (T015, FR-003).

    This is the durable completion record the review gate re-sources from
    (``tasks_shared._check_unchecked_subtasks``, T016) — it replaces the
    ``tasks.md`` checkbox byte as the canonical subtask-completion authority.
    Grouped by owning WP (reusing the ``resolved_tasks_by_wp`` pattern
    ``_ms_emit_history`` already uses) so a batch mark of several task ids
    emits ONE delta per WP, never one event per task id (FR-003 "single or
    batch"). Unresolved task ids (no owning WP) are silently skipped here —
    ``_ms_emit_history`` already surfaces that warning; duplicating it would
    double-print. The emit target is ``st.feature_dir``, resolved from stored
    topology during ``_ms_resolve_read_dir`` — never ``Path.cwd()`` (C-003/#2647).
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    from specify_cli.status import emit_inner_state_changed
    from specify_cli.status import Lane, Status, WPInnerStateDelta

    if not st.updated_tasks:
        return

    target_status: Status = Lane.DONE if st.status == "done" else Lane.PLANNED
    try:
        tasks_content = st.tasks_md.read_text(encoding="utf-8")
        resolved_tasks_by_wp: dict[str, list[str]] = {}
        for task_id in st.updated_tasks:
            history_wp_id = _resolve_history_wp_id(tasks_content, task_id)
            if history_wp_id is not None:
                resolved_tasks_by_wp.setdefault(history_wp_id, []).append(task_id)

        for wp_id, task_ids_for_wp in resolved_tasks_by_wp.items():
            emit_inner_state_changed(
                st.feature_dir,
                wp_id,
                WPInnerStateDelta(
                    subtasks=dict.fromkeys(task_ids_for_wp, target_status)
                ),
                actor="user",
                mission_slug=st.mission_slug,
                repo_root=st.main_repo_root,
            )
    except Exception as e:
        if not st.json_output:
            _tasks.console.print(f"[yellow]Warning:[/yellow] Subtask state emission failed: {e}")


def _ms_emit_history(st: _MarkStatusState) -> None:
    """Emit HistoryAdded events for the updated subtasks (T014)."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    try:
        if st.updated_tasks:
            resolved_tasks_by_wp: dict[str, list[str]] = {}
            unresolved_tasks: list[str] = []
            tasks_content = st.tasks_md.read_text(encoding="utf-8")
            for task_id in st.updated_tasks:
                history_wp_id = _resolve_history_wp_id(tasks_content, task_id)
                if history_wp_id is None:
                    unresolved_tasks.append(task_id)
                else:
                    resolved_tasks_by_wp.setdefault(history_wp_id, []).append(task_id)

            for history_wp_id, task_ids_for_wp in resolved_tasks_by_wp.items():
                task_list_str = ", ".join(task_ids_for_wp)
                _tasks.emit_history_added(
                    wp_id=history_wp_id,
                    entry_type="note",
                    entry_content=f"Subtask(s) {task_list_str} marked as {st.status}",
                    author="user",
                )
            if unresolved_tasks and not st.json_output:
                _tasks.console.print(
                    "[yellow]Warning:[/yellow] Could not resolve owning WP for HistoryAdded event: "
                    + ", ".join(unresolved_tasks)
                )
    except Exception as e:
        if not st.json_output:
            _tasks.console.print(f"[yellow]Warning:[/yellow] Event emission failed: {e}")


def _ms_dossier_sync(st: _MarkStatusState) -> None:
    """Fire-and-forget dossier sync (best-effort)."""
    with contextlib.suppress(Exception):
        from specify_cli.sync.dossier_pipeline import (
            trigger_feature_dossier_sync_if_enabled,
        )

        trigger_feature_dossier_sync_if_enabled(
            st.feature_dir,
            st.mission_slug,
            st.repo_root,
        )


def _ms_output(st: _MarkStatusState) -> None:
    """Emit the mark-status success envelope + not-found warnings."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    result = _tasks._mark_status_json_payload(st.results)
    if st.not_found_tasks and not st.json_output:
        _tasks.console.print(f"[yellow]Warning:[/yellow] Not found: {', '.join(st.not_found_tasks)}")
    if len(st.updated_tasks) == 1:
        success_msg = f"[green]✓[/green] Marked {st.updated_tasks[0]} as {st.status}"
    elif not st.updated_tasks:
        success_msg = f"[green]✓[/green] Requested status already satisfied for: {', '.join(st.resolved_tasks)}"
    else:
        success_msg = f"[green]✓[/green] Marked {len(st.updated_tasks)} subtasks as {st.status}: {', '.join(st.updated_tasks)}"
    _tasks._output_result(st.json_output, result, success_msg)


def _do_mark_status(
    task_ids: list[str],
    status: str,
    mission: str | None,
    auto_commit: bool | None,
    json_output: bool,
    *,
    ports: TasksPorts | None = None,
) -> None:
    """Orchestrate ``mark-status`` over the WP02 ports (C-005 seam), CORELESS.

    ``mark_status`` carries NO transition decision core (FR-007): it resolves task
    IDs to durable rows and writes/commits ``tasks.md``. It does NOT route through
    ``move_task``'s ``decide_transition`` core — that is the deferred #2300
    unification, guarded structurally by the T036 non-import gate. ``ports=None``
    builds the production bundle (coord router bound to this module's patchable
    ``commit_for_mission``). The phase helpers run in the SAME order as the original
    single body: validate → resolve → apply → history → dossier → output.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    st = _MarkStatusState(
        task_ids=list(task_ids),
        status=status,
        mission=mission,
        auto_commit=auto_commit,
        json_output=json_output,
    )
    try:
        _ms_validate_inputs(st)
        _ms_resolve_context(st)
        ports = ports or _default_mark_status_ports()
        _ms_resolve_read_dir(st, ports)
        _ms_apply_updates(st, ports)
        _ms_emit_subtask_state(st)
        _ms_emit_history(st)
        _ms_dossier_sync(st)
        _ms_output(st)
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


# ===========================================================================
# WP09 (tasks-py-degod-wave2-01KWH9EQ / FR-008, IC-07): the final
# registration-shim sweep relocates the mark_status-family straggler that
# remained ``tasks.py``-resident after WP08 — the inline-Subtasks resolver
# (``_resolve_inline_subtasks``). Moved VERBATIM (``_INLINE_SUBTASKS_RE`` /
# ``_persist_inline_subtask_status`` and the ``TaskIdResult`` vocabulary are
# module-scope imports here; none is a ``tasks``-namespace patch seam). The
# ``_ms_apply_updates`` call site above keeps routing through
# ``_tasks.<attr>``, so the seam-interception contract
# (``@patch("...agent.tasks._resolve_inline_subtasks")``,
# test_tasks_mark_status_seam.py) keeps INTERCEPTING; ``tasks.py`` re-imports
# the name in the explicit ``as`` re-export form (NFR-002).
# ===========================================================================


def _resolve_inline_subtasks(
    task_id: str,
    tasks_content: str,
    status: str,
    feature_dir: Path,
) -> TaskIdResult | None:
    """
    Search tasks_content for 'Subtasks: T001, T002' lines containing task_id.

    WP04/T015 (FR-003/FR-008): inline references are discovery hints used to
    map ``task_id`` to its owning WP context — completion is no longer
    persisted as a materialized ``tasks.md`` checkbox row. The durable record
    is the ``InnerStateChanged`` ``subtasks`` delta ``_ms_emit_subtask_state``
    emits from the ``UPDATED``/``INLINE_SUBTASKS`` result this resolver now
    returns unconditionally on a match. ``feature_dir`` is accepted for call-site
    compatibility but no longer used to persist a row.
    """
    del feature_dir
    normalized_task_id = task_id.upper()
    for match in _INLINE_SUBTASKS_RE.finditer(tasks_content):
        ids = [value.strip().upper() for value in match.group("ids").split(",")]
        if normalized_task_id in ids:
            return TaskIdResult(
                id=task_id,
                outcome=TaskIdResolutionOutcome.UPDATED,
                format=TaskIdResolutionFormat.INLINE_SUBTASKS,
                message=f"Recorded inline Subtasks reference {task_id} as {status} (event-sourced).",
            )
    return None
