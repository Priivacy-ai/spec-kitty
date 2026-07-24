"""The ``move-task`` command family, relocated out of ``tasks.py`` (WP05, #2305).

Mission ``tasks-py-degod-wave2-01KWH9EQ`` FR-001/FR-002: the LARGEST family —
``_do_move_task`` + the 23 ``_mt_*`` phase helpers + ``_MoveTaskState`` +
``_default_move_task_ports`` — lives here, moved VERBATIM from ``tasks.py``.
The ``@app.command`` Typer wrapper (``move_task``) stays in ``tasks.py`` and
delegates to :func:`_do_move_task` (the byte-frozen ``--help`` surface is the
registration shim's).

**Orchestration shape** (unchanged): the Typer command declares the CLI
surface; ``_do_move_task`` gathers facts (I/O), runs the pure
``decide_transition`` core (``tasks_transition_core``), and executes the
resulting ``Emit`` through the two coord WRITE capabilities
(``commit_status`` for each lane hop, ``commit_artifact`` for the primary
WP-file commit) and the coord READ authority (``feature_write_dir`` resolves
the FR-010 coord husk — NEVER a primary kind). The
partial-write-on-refusal timing (override/arbiter persists at their OLD guard
positions) and the coord skip-exit-0 arm are preserved verbatim.

**C-001 divergence wiring**: ``move_task`` is the ONLY command with the
``_skip_target_branch_commit`` pre-gate (skip-exit-0 on coord topology +
protected branch). The pre-gate call sits at its original position in
``_mt_resolve_targets`` — before the protected-branch refusal and the
authoritative event-log read — reaching the shared helper via
``_tasks._skip_target_branch_commit``; the coord harness T004 (skip arm +
wrong-leg detector) pins it.

**Seam bridge** (research.md D1/D7): the relocated bodies reach every patched
seam symbol through a lazy in-function import of the ``tasks`` module
(``from specify_cli.cli.commands.agent import tasks as _tasks``) and call
``_tasks.<attr>(...)``, so every historical ``@patch("...agent.tasks.<sym>")``
/ ``monkeypatch.setattr(tasks, ...)`` keeps INTERCEPTING after the move.
``tasks.py`` re-imports the family in the explicit ``as`` re-export form, so
``tasks.<name>`` stays a module attribute. Symbols with ZERO patch sites and a
canonical home outside ``tasks.py`` are imported directly at module scope
(cycle-safe: none of those modules import ``tasks``).

Per-symbol routing/interception evidence:
``kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md`` (Layer 4 of
the parity contract).
"""

from __future__ import annotations

import contextlib
import logging
import traceback
import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import typer

if TYPE_CHECKING:
    from collections.abc import Sequence

    from doctrine.missions.step_contracts import GateBinding

from mission_runtime import MissionArtifactKind
from specify_cli.agent_tasks_ports import (
    MissionHandle,
    TasksPorts,
)
from specify_cli.cli.commands.agent.tasks_finalize_validation import (
    _read_transactional_wp_lane,
)
from specify_cli.cli.commands.agent.tasks_materialization import (
    _persist_review_artifact_override,
    _resolve_wp_slug,
)
from specify_cli.cli.commands.agent.tasks_parsing_validation import (
    _get_latest_review_cycle_verdict,
    _issue_matrix_approval_blocker,
    _self_review_fallback_option_error,
)
from specify_cli.cli.commands.agent.tasks_transition_core import (
    Emit,
    MoveTaskRequest,
    RefuseExit1,
    TransitionPlan,
    _effective_note_text,
    arbiter_persist_signal,
    build_transition_plan,
    override_persist_signal,
)
from specify_cli.coordination.atomic_write import (
    enroll_subprocess_byproducts,
    restore_generated_artifact_snapshots,
    subprocess_created_paths,
)
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.core.env import first_set_sync_disable_env
from specify_cli.core.paths import is_worktree_context
from specify_cli.core.vcs.git import merge_base_changed_files
from specify_cli.missions._read_path_resolver import (
    _canonicalize_primary_read_handle,
    primary_feature_dir_for_mission,
)
from specify_cli.mission_metadata import resolve_mission_identity
from specify_cli.review import pre_review_gate
from specify_cli.review.baseline import BaselineTestResult
from specify_cli.review.gate_bindings import (
    GateBindingResolution,
    resolve_gate_bindings_for_transition,
    resolve_mission_type,
)
from specify_cli.review.gate_registry import (
    GateHandler,
    TransitionGateContext,
    get_gate_handler,
)
from specify_cli.review.scope_source import ScopeSource, resolve_scope_source
from specify_cli.review.verdict_aggregation import (
    AggregateDecision,
    aggregate_verdicts,
)
from specify_cli.status import (
    EVENTS_FILENAME,
    EventPersistenceError,
    Lane,
    ReviewResult,
    ResolvedBinding,
    StatusEvent,
    TransitionRequest,
    WPInnerStateDelta,
    resolve_lane_alias,
)
from specify_cli.task_utils import (
    WorkPackage,
    ensure_lane,
    extract_scalar,
)
from specify_cli.upgrade.pre30_guard import Pre30LayoutError, check_pre30_layout



def _default_move_task_ports() -> TasksPorts:
    """Production port bundle for ``move_task`` (coord router bound to tasks.py)."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    return TasksPorts(
        fs=_tasks.RealFsReader(),
        # move_task routes BOTH seams through the ``tasks`` namespace (it was the
        # only family to override ``commit_status``); no ``target_branch``.
        coord=_tasks.seam_coord_router(route_emit=True),
        git=_tasks.RealGitOps(),
        render=_tasks.RealRender(),
    )


@dataclass
class _MoveTaskState:
    """Mutable orchestration state threaded through ``move_task``'s phases.

    The single-body command tracked ~30 loose locals across gather → decide →
    execute; the phase helpers exchange this one value object instead. Not frozen:
    each phase fills its own slice in the same order the original body did.
    """

    # --- raw command inputs ---
    task_id: str
    to: str
    mission: str | None
    agent: str | None
    assignee: str | None
    shell_pid: str | None
    note: str | None
    review_feedback_file: Path | None
    approval_ref: str | None
    reviewer: str | None
    self_review_fallback: bool
    intended_reviewer: str | None
    reviewer_failure_reason: str | None
    done_override_reason: str | None
    force: bool
    tracker_ref: list[str] | None
    skip_review_artifact_check: bool
    auto_commit: bool | None
    json_output: bool
    skip_pre_review_gate: bool = False
    model: str | None = None
    profile: str | None = None
    invocation_id: str | None = None
    # --- phase A: resolved targets ---
    target_lane: Lane = Lane.PLANNED
    repo_root: Path = field(default_factory=Path)
    main_repo_root: Path = field(default_factory=Path)
    target_branch: str = ""
    mission_slug: str = ""
    tracker_ref_values: tuple[str, ...] = ()
    skip_target_branch_commit: bool = False
    resolved_auto_commit: bool = False
    feature_dir: Path = field(default_factory=Path)
    mt_feature_dir: Path = field(default_factory=Path)
    wp: WorkPackage | None = None
    old_lane: Lane = Lane.PLANNED
    current_agent: str | None = None
    resolved_binding: ResolvedBinding | None = None
    # --- phase B: decision facts ---
    verdict_artifact_path: Path | None = None
    resolved_feedback_source: Path | None = None
    request: MoveTaskRequest | None = None
    # --- phase C: decision ---
    decision: Emit | None = None
    arb_review_ref: str | None = None
    # --- phase C.5: pre-review regression gate (WP02 T004/T005) ---
    pre_review_gate_metadata: dict[str, Any] | None = None
    # --- phase D: emit plan ---
    emit_plan: TransitionPlan | None = None
    evidence_dict: dict[str, Any] | None = None
    note_text: str | None = None
    actor: str = "user"
    canonical_lane: str | None = None
    review_feedback_pointer: str | None = None
    rejected_review_result: ReviewResult | None = None
    # SC-007: the structured review outcome (reviewer + verdict + reference) WP06
    # threads into ``build_transition_plan`` (WP02's optional ``review_result``
    # seam) so the two ``in_review -> *`` edges it owns are force-free instead of
    # ``force=True``. ``None`` off the in_review-exit edges (WP02 owns the rest).
    plan_review_result: ReviewResult | None = None
    # --- phase E/F: emit + persist ---
    event: StatusEvent | None = None
    final_hop_actor: str | None = None
    # True once the claim triple (``shell_pid``/``shell_pid_created_at``/``agent``)
    # rode a real ``planned -> claimed`` transition's ``policy_metadata`` sidecar
    # (FR-004), so :func:`_mt_emit_runtime_state` does NOT re-emit it as an
    # off-axis ``InnerStateChanged`` delta.
    claim_emitted: bool = False


# --- phase A: resolve targets (I/O) -----------------------------------------


def _mt_warn_worktree_kitty_specs(st: _MoveTaskState) -> None:
    """Informational note when a worktree carries a stale ``kitty-specs/`` copy."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    cwd = Path.cwd().resolve()
    if not (is_worktree_context(cwd) and not st.json_output and cwd != st.main_repo_root):
        return
    worktree_kitty = None
    current = cwd
    while current != current.parent and ".worktrees" in str(current):
        if (current / KITTY_SPECS_DIR).exists():
            worktree_kitty = current / KITTY_SPECS_DIR
            break
        current = current.parent
    if worktree_kitty and (worktree_kitty / st.mission_slug / "tasks").exists():
        _tasks.console.print(
            f"[dim]Note: Using planning repo's kitty-specs/ on {st.target_branch} "
            "(worktree copy ignored)[/dim]"
        )


def _mt_resolve_current_agent(st: _MoveTaskState) -> str | None:
    """Resolve the prior-owner agent from the reduced snapshot (FR-007, IC-04).

    The WP file no longer carries the ``agent`` runtime field post-cutover, so the
    ownership read routes onto the ungated snapshot accessor instead of
    ``extract_scalar(frontmatter, "agent")``. Extracted (not inlined) so the
    snapshot read is a unit-testable seam and the cx-15 ``_mt_emit_runtime_state``
    off-axis emit path is left untouched (D-14). Returns ``None`` for an unclaimed
    WP (no snapshot ``agent`` slot) — matching the pre-reroute "no agent in
    frontmatter" result.
    """
    from specify_cli.status import wp_snapshot_state

    snapshot = wp_snapshot_state(st.feature_dir, st.task_id)
    if snapshot is None:
        return None
    agent = snapshot.get("agent")
    return str(agent) if agent else None


def _mt_resolve_targets(st: _MoveTaskState, ports: TasksPorts) -> None:
    """Resolve roots/branch/feature-dir and load the WP + its canonical lane."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    st.target_lane = Lane(ensure_lane(st.to))
    repo_root = _tasks.locate_project_root()
    if repo_root is None:
        _tasks._output_error(st.json_output, "Could not locate project root")
        raise typer.Exit(1)
    st.repo_root = repo_root
    # FR-010 / FR-019: one-shot sparse-checkout warning before any read/mutate.
    _tasks._emit_sparse_session_warning(repo_root, command="spec-kitty agent tasks move-task")
    st.resolved_auto_commit = (
        _tasks.get_auto_commit_default(repo_root) if st.auto_commit is None else st.auto_commit
    )
    st.mission_slug = _tasks._find_mission_slug(
        explicit_mission=st.mission, json_output=st.json_output, repo_root=repo_root
    )
    st.main_repo_root, st.target_branch = _tasks._ensure_target_branch_checked_out(
        repo_root, st.mission_slug, st.json_output
    )
    from specify_cli.cli.commands.agent.workflow import _resolve_dispatch_binding

    claim_mission_id: str | None = None
    if st.invocation_id is not None:
        primary_feature_dir = primary_feature_dir_for_mission(
            st.main_repo_root,
            _canonicalize_primary_read_handle(st.main_repo_root, st.mission_slug),
        )
        claim_mission_id = resolve_mission_identity(primary_feature_dir).mission_id
    st.resolved_binding = _resolve_dispatch_binding(
        model=st.model,
        profile=st.profile,
        invocation_id=st.invocation_id,
        repo_root=st.main_repo_root,
        mission_id=claim_mission_id,
        wp_id=st.task_id,
        action="review" if st.target_lane == Lane.IN_REVIEW else "implement",
    )
    st.skip_target_branch_commit = (
        _tasks._skip_target_branch_commit(st.main_repo_root, st.mission_slug, st.target_branch)
        if st.resolved_auto_commit
        else False
    )
    # Protected-branch status-commit refusal — a hard early exit that MUST fire
    # before the authoritative event-log read below (``_read_transactional_wp_lane``),
    # matching the pre-rewire order. Deferring it into the decision core (pass 1)
    # let an un-bootstrapped event log raise "Canonical status not found" first,
    # masking the protected-branch refusal (issue #1386 regression).
    if st.resolved_auto_commit and not st.skip_target_branch_commit:
        protected_error = _tasks._protected_branch_status_commit_error(
            st.target_branch, st.main_repo_root, "spec-kitty agent tasks move-task"
        )
        if protected_error is not None:
            self_review_error = _self_review_fallback_option_error(
                enabled=st.self_review_fallback,
                target_lane=str(st.target_lane),
                force=st.force,
                intended_reviewer=st.intended_reviewer,
                failure_reason=st.reviewer_failure_reason,
            )
            if self_review_error is not None:
                _tasks._output_error(st.json_output, self_review_error)
                raise typer.Exit(1)
            _tasks._output_error(st.json_output, protected_error)
            raise typer.Exit(1)
    st.tracker_ref_values = tuple(
        t.strip() for t in (st.tracker_ref or []) if t and t.strip()
    )
    _mt_warn_worktree_kitty_specs(st)
    # Boundary guard — hard-reject pre-3.0 layout before any WP mutation.
    # WP06 FR-010 (T027): the shared coord-status dir STAYS on the coord husk.
    # ``feature_write_dir`` wraps ``resolve_feature_dir_for_mission`` (the kind-blind
    # coord-husk leg) — the SAME on-disk dir the pre-rewire body read; it feeds the
    # pre30 guard, the authoritative event-log lane read (``_read_transactional_wp_lane``),
    # and the coord override persist. It is NEVER repointed to a primary kind — that
    # would move the event-log read off the coord husk and reintroduce the split-brain
    # FR-010 closes.
    handle = MissionHandle(repo_root=st.main_repo_root, mission_slug=st.mission_slug)
    st.mt_feature_dir = ports.coord.feature_write_dir(handle)
    try:
        check_pre30_layout(st.mt_feature_dir)
    except Pre30LayoutError as e:
        _tasks._output_error(st.json_output, str(e))
        raise typer.Exit(1) from None
    st.wp = _tasks.locate_work_package(repo_root, st.mission_slug, st.task_id)
    # Lane is event-log-only; read from the canonical coord-husk event log.
    st.old_lane = _read_transactional_wp_lane(
        feature_dir=st.mt_feature_dir,
        mission_slug=st.mission_slug,
        wp_id=st.task_id,
        repo_root=st.main_repo_root,
    )
    # Event-store write leg — the SAME coord husk as ``mt_feature_dir``.
    st.feature_dir = st.mt_feature_dir
    # FR-007 / IC-04: prior-owner attribution is snapshot-sourced (the WP file no
    # longer carries the ``agent`` runtime field post-cutover) — read via the
    # ungated snapshot accessor in an extracted helper, not
    # ``extract_scalar(frontmatter, "agent")``.
    st.current_agent = _mt_resolve_current_agent(st)


# --- phase B: gather decision facts (I/O) -----------------------------------


def _mt_resolve_feedback(st: _MoveTaskState) -> tuple[str | None, bool, bool, str | None]:
    """Resolve the ``--review-feedback-file`` facts (+ planned-rollback content)."""
    if st.review_feedback_file is None:
        return None, False, False, None
    candidate = st.review_feedback_file.expanduser()
    candidate = (
        candidate.resolve()
        if candidate.is_absolute()
        else (Path.cwd() / candidate).resolve()
    )
    source_str = str(candidate)
    exists = candidate.exists()
    is_file = candidate.is_file()
    content: str | None = None
    if exists and is_file:
        st.resolved_feedback_source = candidate
        if st.target_lane == Lane.PLANNED:
            content = candidate.read_text(encoding="utf-8").strip()
    return source_str, exists, is_file, content


def _mt_build_request(
    st: _MoveTaskState,
    *,
    protected_error: str | None,
    review_verdict: str | None,
    review_artifact_name: str | None,
    feedback: tuple[str | None, bool, bool, str | None],
    unchecked_subtasks: tuple[str, ...],
    review_ready: bool,
    review_guidance: tuple[str, ...],
) -> MoveTaskRequest:
    """Assemble the pass-1 ``MoveTaskRequest`` (late facts default to skip-safe)."""
    feedback_source_str, feedback_exists, feedback_is_file, feedback_content = feedback
    return MoveTaskRequest(
        task_id=st.task_id,
        target_lane=str(st.target_lane),
        old_lane=str(st.old_lane),
        force=st.force,
        agent=st.agent,
        current_agent=st.current_agent,
        note=st.note,
        auto_commit=bool(st.resolved_auto_commit),
        target_branch=st.target_branch,
        skip_target_branch_commit=st.skip_target_branch_commit,
        tracker_ref_values=tuple(st.tracker_ref_values),
        assignee=st.assignee,
        shell_pid=st.shell_pid,
        self_review_fallback=st.self_review_fallback,
        intended_reviewer=st.intended_reviewer,
        reviewer_failure_reason=st.reviewer_failure_reason,
        protected_error=protected_error,
        review_verdict=review_verdict,
        review_artifact_name=review_artifact_name,
        skip_review_artifact_check=st.skip_review_artifact_check,
        feedback_provided=st.review_feedback_file is not None,
        feedback_source=feedback_source_str,
        feedback_exists=feedback_exists,
        feedback_is_file=feedback_is_file,
        feedback_content=feedback_content,
        unchecked_subtasks=unchecked_subtasks,
        review_ready=review_ready,
        review_guidance=review_guidance,
        done_execution_mode=None,
        done_merged=False,
        done_merge_msg="",
        done_override_reason=st.done_override_reason,
        issue_matrix_blocker=None,
        is_arbiter_override=False,
        effective_reviewer=None,
        effective_approval_ref=None,
    )


def _lane_deliverable_paths(worktree_path: Path, porcelain: str) -> tuple[Path, ...]:
    """Parse ``git status --porcelain`` lines into absolute deliverable paths."""
    paths: list[Path] = []
    for line in porcelain.splitlines():
        if len(line) < 4:
            continue
        entry = line[3:]
        if " -> " in entry:  # rename/copy — the destination is the live path
            entry = entry.split(" -> ", 1)[1]
        entry = entry.strip().strip('"')
        if entry:
            paths.append(worktree_path / entry)
    return tuple(paths)


def _mt_commit_lane_deliverables(st: _MoveTaskState) -> None:
    """Commit finished lane deliverables before a review transition (#2335).

    A killed implementer can leave its deliverables uncommitted in the lane
    worktree; without this, ``move-task --to for_review`` dead-ends demanding a
    manual in-worktree ``git commit`` — violating the tool-drives-commits rule.
    When auto-commit is enabled, stage + commit the finished deliverables via the
    tool (``safe_commit`` on the lane branch) so the readiness guard sees a clean
    tree. Best-effort: any failure leaves the tree untouched and the existing
    ``_validate_ready_for_review`` guard explains the situation.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    from specify_cli.lanes.persistence import CorruptLanesError, MissingLanesError

    try:
        workspace = _tasks.resolve_workspace_for_wp(
            st.main_repo_root, st.mission_slug, st.task_id
        )
    except (ValueError, FileNotFoundError, MissingLanesError, CorruptLanesError):
        # No resolvable lane workspace (missions without lanes.json included) —
        # nothing to recover; the readiness guard stays authoritative.
        return
    # Only a real lane worktree carries deliverables to commit; a planning-artifact
    # / repo-root WP has no lane branch (branch_name is None) — nothing to do.
    if workspace.resolution_kind != "lane_workspace" or workspace.branch_name is None:
        return
    worktree_path = workspace.worktree_path
    if not worktree_path.exists():
        return

    status = _tasks.subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(worktree_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if status.returncode != 0:
        return
    # Reuse the guard's runtime-state filter so we only commit genuine deliverables
    # (never spec-kitty's own review-lock / .kittify bookkeeping).
    filtered = _tasks._filter_runtime_state_paths(status.stdout)
    if not filtered:
        return
    paths = _lane_deliverable_paths(worktree_path, filtered)
    if not paths:
        return

    try:
        from mission_runtime import CommitTarget

        from specify_cli.git import safe_commit

        safe_commit(
            repo_root=st.main_repo_root,
            worktree_root=worktree_path,
            target=CommitTarget(ref=workspace.branch_name),
            message=f"chore({st.task_id}): commit lane deliverables for review",
            paths=paths,
        )
        if not st.json_output:
            _tasks.console.print(
                f"[cyan]Committed lane deliverables for {st.task_id} on "
                f"{workspace.branch_name} before review.[/cyan]"
            )
    except Exception as exc:  # noqa: BLE001 — best-effort; the guard explains on failure
        if not st.json_output:
            _tasks.console.print(
                f"[yellow]Warning:[/yellow] could not auto-commit lane deliverables "
                f"for {st.task_id}: {exc}"
            )


def _mt_gather_review_facts(st: _MoveTaskState) -> None:
    """Gather the early (guard-gating) facts and build the pass-1 request."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    assert st.wp is not None
    # Protected-branch refusal already fired as a hard early exit in
    # ``_mt_resolve_targets`` (before the event-log read) — if the branch were
    # protected we would never reach here, so this is always None by construction.
    protected_error: str | None = None
    review_verdict: str | None = None
    review_artifact_name: str | None = None
    if st.target_lane in (Lane.APPROVED, Lane.DONE):
        _verdict_wp_dir = st.wp.path.parent / st.wp.path.stem
        review_verdict, st.verdict_artifact_path = _get_latest_review_cycle_verdict(
            _verdict_wp_dir
        )
        review_artifact_name = (
            st.verdict_artifact_path.name if st.verdict_artifact_path is not None else None
        )
    feedback = _mt_resolve_feedback(st)
    unchecked_subtasks: tuple[str, ...] = ()
    if st.target_lane in (Lane.FOR_REVIEW, Lane.APPROVED, Lane.DONE) and not st.force:
        unchecked_subtasks = tuple(
            _tasks._check_unchecked_subtasks(st.repo_root, st.mission_slug, st.task_id, st.force)
        )
    review_ready = True
    review_guidance: tuple[str, ...] = ()
    if st.target_lane in (Lane.FOR_REVIEW, Lane.APPROVED, Lane.DONE):
        # A for_review auto-commit is deliberately deferred until the real
        # pre-review gate permits progress. The initial decision still runs
        # every other read-only guard before that gate; readiness is refreshed
        # immediately after the deferred commit. Other lanes and explicit
        # no-auto-commit moves retain their original validation order.
        defer_readiness = (
            st.target_lane == Lane.FOR_REVIEW
            and st.resolved_auto_commit
            and not st.force
        )
        if not defer_readiness:
            is_valid, guidance = _tasks._validate_ready_for_review(
                st.repo_root,
                st.mission_slug,
                st.task_id,
                st.force,
                target_lane=str(st.target_lane),
            )
            review_ready = is_valid
            review_guidance = tuple(guidance)
    st.request = _mt_build_request(
        st,
        protected_error=protected_error,
        review_verdict=review_verdict,
        review_artifact_name=review_artifact_name,
        feedback=feedback,
        unchecked_subtasks=unchecked_subtasks,
        review_ready=review_ready,
        review_guidance=review_guidance,
    )


def _mt_complete_deferred_for_review_readiness(st: _MoveTaskState) -> None:
    """Commit deliverables and refresh readiness only after the gate permits."""
    from specify_cli.cli.commands.agent import tasks as _tasks

    if not (
        st.target_lane == Lane.FOR_REVIEW
        and st.resolved_auto_commit
        and not st.force
    ):
        return
    assert st.request is not None
    _mt_commit_lane_deliverables(st)
    is_valid, guidance = _tasks._validate_ready_for_review(
        st.repo_root,
        st.mission_slug,
        st.task_id,
        st.force,
        target_lane=str(st.target_lane),
    )
    st.request = replace(
        st.request,
        review_ready=is_valid,
        review_guidance=tuple(guidance),
    )
    _mt_run_decision(st)


# --- phase C: two-pass decision + partial-write persists ---------------------


def _mt_fire_override_persist(st: _MoveTaskState) -> None:
    """OLD-timing review-artifact override (FR-004 partial-write-on-refusal).

    Fires before the guard sequence so a LATER guard's exit-1 refusal still leaves
    the override on disk — reproducing the un-refactored command's timing.
    """
    assert st.request is not None
    if not (override_persist_signal(st.request) and st.verdict_artifact_path is not None):
        return
    override_reason = st.note.strip() if isinstance(st.note, str) else ""
    # FR-009 (WP09): a single topology-resolved ``InnerStateChanged`` ``review``
    # emit is authoritative for both the primary and coord worktrees, so the
    # former ``_persist_review_artifact_override_in_coord`` mirror is collapsed
    # away — one emit, no coord frontmatter stamp.
    _persist_review_artifact_override(
        st.verdict_artifact_path,
        repo_root=st.main_repo_root,
        wp_id=st.task_id,
        actor=st.agent or "operator",
        reason=override_reason,
    )


def _mt_done_ancestry_facts(st: _MoveTaskState) -> tuple[str | None, bool, str]:
    """Late fact: done-transition execution mode + branch-merge ancestry."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    if st.target_lane != Lane.DONE:
        return None, False, ""
    try:
        done_workspace = _tasks.resolve_workspace_for_wp(
            st.main_repo_root, st.mission_slug, st.task_id
        )
        done_execution_mode: str | None = done_workspace.execution_mode
    except (ValueError, FileNotFoundError):
        done_execution_mode = "code_change"
    done_merged = False
    done_merge_msg = ""
    if done_execution_mode == "code_change":
        done_merged, done_merge_msg = _tasks._wp_branch_merged_into_target(
            repo_root=st.main_repo_root,
            mission_slug=st.mission_slug,
            wp_id=st.task_id,
            target_branch=st.target_branch,
        )
    return done_execution_mode, done_merged, done_merge_msg


def _mt_issue_matrix_facts(st: _MoveTaskState) -> str | None:
    """Late fact: issue-matrix approval blocker.

    C-002: the canonicalizer fold + the blind primitive
    ``primary_feature_dir_for_mission`` stay co-located in the command module —
    NEVER routed through a port. The blind primitive is reached via
    ``_tasks.<attr>``: its ``tasks`` binding is a live patch seam
    (``@patch("...agent.tasks.primary_feature_dir_for_mission")``,
    test_pre30_guard_wiring).
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    if st.target_lane not in (Lane.APPROVED, Lane.DONE):
        return None
    canonical_handle = _canonicalize_primary_read_handle(st.main_repo_root, st.mission_slug)
    blocker: str | None = _issue_matrix_approval_blocker(
        st.feature_dir,
        target_lane=st.target_lane,
        primary_feature_dir=_tasks.primary_feature_dir_for_mission(
            st.main_repo_root, canonical_handle
        ),
    )
    return blocker


def _mt_approval_facts(st: _MoveTaskState) -> tuple[str | None, str | None]:
    """Late fact: auto-detected reviewer + defaulted approval reference."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    if st.target_lane not in (Lane.APPROVED, Lane.DONE):
        return None, None
    effective_reviewer = st.reviewer or _tasks._detect_reviewer_name()
    user_note = st.note.strip() if isinstance(st.note, str) else st.note
    effective_approval_ref = (
        st.approval_ref
        or (user_note if user_note else None)
        or f"auto-approval:{st.task_id}:{datetime.now(UTC).strftime('%Y%m%d')}"
    )
    return effective_reviewer, effective_approval_ref


def _mt_gather_late_facts(st: _MoveTaskState) -> None:
    """Gather pass-2 facts (allowed to raise) and rebuild the request."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    assert st.request is not None
    done_execution_mode, done_merged, done_merge_msg = _mt_done_ancestry_facts(st)
    issue_matrix_blocker = _mt_issue_matrix_facts(st)
    effective_reviewer, effective_approval_ref = _mt_approval_facts(st)
    is_arbiter_override = _tasks._detect_arbiter_override(
        st.feature_dir, st.task_id, st.old_lane, resolve_lane_alias(st.target_lane), st.force
    )
    st.request = replace(
        st.request,
        done_execution_mode=done_execution_mode,
        done_merged=done_merged,
        done_merge_msg=done_merge_msg,
        issue_matrix_blocker=issue_matrix_blocker,
        is_arbiter_override=is_arbiter_override,
        effective_reviewer=effective_reviewer,
        effective_approval_ref=effective_approval_ref,
    )


def _mt_fire_arbiter_persist(st: _MoveTaskState) -> None:
    """OLD-timing arbiter-decision persist (FR-004 partial-write-on-refusal).

    Fires before pass 2 runs the issue-matrix guard, so an issue-matrix refusal
    still leaves the arbiter JSON on disk. ``arb_review_ref`` links the forward
    event to the rejection it overrides.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    assert st.request is not None
    if not arbiter_persist_signal(st.request):
        return
    arb_note_text, _ = _effective_note_text(st.request)
    st.arb_review_ref = _tasks._run_arbiter_override(
        feature_dir=st.feature_dir,
        mission_slug=st.mission_slug,
        main_repo_root=st.main_repo_root,
        task_id=st.task_id,
        note_text=arb_note_text,
        agent=st.agent,
        json_output=st.json_output,
    )


def _mt_run_decision(st: _MoveTaskState) -> None:
    """Two-pass pure decision; RefuseExit1 short-circuits with the guard output."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    assert st.request is not None
    # OLD-timing override persist BEFORE the guard sequence (pass 1).
    _mt_fire_override_persist(st)
    decision = _tasks.decide_transition(st.request)
    if not isinstance(decision, RefuseExit1):
        # Early guards cleared — gather the late (possibly-raising) facts, fire the
        # OLD-timing arbiter persist ahead of the issue-matrix guard, then re-decide.
        _mt_gather_late_facts(st)
        _mt_fire_arbiter_persist(st)
        assert st.request is not None
        decision = _tasks.decide_transition(st.request)
    if isinstance(decision, RefuseExit1):
        if not st.json_output:
            for warn_line in decision.console_warning:
                _tasks.console.print(warn_line)
        _tasks._output_error(st.json_output, decision.error, diagnostic=decision.diagnostic)
        raise typer.Exit(1)
    st.decision = decision


# --- phase C.5: pre-review regression gate (WP02 T004/T005, FR-001/FR-004) ---
#
# Mission review-regression-gate-01KWX6DF WP02: wires WP01's engine
# (``review/pre_review_gate.py`` — ``evaluate_pre_review_gate`` +
# ``run_scoped_tests_at_head`` + reused ``review/baseline.py`` JUnit
# parser/``diff_baseline``) into the ``for_review`` transition. Warn by
# default (NFR-001); opt-in block via config
# ``review.fail_on_pre_review_regression``; ``--force`` bypasses the block
# and is recorded on the transition's ``policy_metadata`` (FR-004).
#
# The composition helper below (``_mt_pre_review_gate_with_override_scope``)
# calls ONLY WP01's already-public primitives (``evaluate_with_scope``, the
# ``GateVerdict``/``ScopeResult`` dataclasses) — it lives here, not in
# ``review/pre_review_gate.py``, because that module is WP01's owned surface
# (outside this WP's ``owned_files``): the override-scope tier needs a
# manually-built ``ScopeResult`` that the engine has no seam for, so its tail
# (head-run -> ``diff_baseline``) is mirrored rather than threaded through a
# WP01 signature change. (The sibling census-derived composition helper,
# ``_mt_pre_review_gate_verdict``, was dead code with no production call site
# — retired by mission scopesource-gate-followup-01KY6S9P WP04, FR-002.)

_PRE_REVIEW_CONFIG_KEY_BLOCK = "fail_on_pre_review_regression"
_PRE_REVIEW_CONFIG_KEY_TEST_COMMAND = "pre_review_test_command"
_PRE_REVIEW_CONFIG_KEY_TEST_COMMAND_REPLACEMENT = "test_command"
_PRE_REVIEW_FRONTMATTER_KEY = "pre_review_test_scope"

#: T043 (FR-011): the legacy ``review.pre_review_test_command`` key is aliased to
#: the ``ScopeSource`` single test-command authority (``review.test_command``).
#: Its name always lied about its axis (squad C-C3) — it fed scope *targets*, not
#: a command. Under the inverted, doctrine-resolved gate the ``ScopeSource`` is
#: the single authority, so a config that still sets the old key keeps working
#: but earns a ONE-TIME deprecation warning (guarded by the module flag below) —
#: never a silent break for existing consumer configs.
_PRE_REVIEW_TEST_COMMAND_DEPRECATION = (
    "review.pre_review_test_command is deprecated; the inverted pre-review gate "
    "resolves its test command from the ScopeSource single authority "
    "(review.test_command). The old key is still honored — move the value to "
    "review.test_command to silence this notice."
)
#: One-shot latch so the deprecation warning fires at most once per process, not
#: on every ``for_review`` transition (T043).
_pre_review_test_command_deprecation_emitted = False


def _pre_review_gate_filter_groups() -> Mapping[str, tuple[str, ...]] | None:
    """Test seam: production always returns ``None``.

    ``None`` is threaded through ``_mt_resolve_scope_source`` into
    ``resolve_scope_source(..., filter_groups_override=None)``, so
    ``GateCoverageScopeSource`` derives filter groups from the LIVE
    ``tests/architectural/_gate_coverage.py`` authority under the gate's own
    ``repo_root`` (WP01's FR-006 single-source invariant). Integration tests
    monkeypatch this (and its composite-routing sibling below) to inject a
    hermetic fixture map — the SAME override seam ``GateCoverageScopeSource``'s
    census derivation consumes — rather than building a throwaway
    ``tests/architectural/_gate_coverage.py`` in a fixture repo, which would
    silently resolve to the REAL repo's cached ``sys.modules`` entry instead
    (the exact staleness ``GateAuthoritiesUnavailable`` guards against).
    """
    return None


def _pre_review_gate_composite_routing() -> Mapping[str, pre_review_gate._CompositeRoute] | None:
    """Test seam sibling to :func:`_pre_review_gate_filter_groups` (see there)."""
    return None


def _mt_review_config_section(main_repo_root: Path) -> Mapping[str, Any]:
    """Best-effort read of the ``review:`` section of ``.kittify/config.yaml``.

    Mirrors ``review/baseline.py``'s ``_get_test_command`` read pattern
    exactly: a missing file, malformed YAML, or absent section all degrade to
    an empty mapping rather than raising — config lookup must never crash a
    transition.
    """
    config_path = main_repo_root / ".kittify" / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        from ruamel.yaml import YAML

        yaml = YAML()
        config = yaml.load(config_path)
    except Exception:
        return {}
    if not config:
        return {}
    review_section = config.get("review") if hasattr(config, "get") else None
    return dict(review_section) if review_section else {}


def _mt_pre_review_block_enabled(main_repo_root: Path) -> bool:
    """FR-001/NFR-001: opt-in block toggle — ``review.fail_on_pre_review_regression``."""
    return bool(_mt_review_config_section(main_repo_root).get(_PRE_REVIEW_CONFIG_KEY_BLOCK, False))


def _mt_pre_review_gate_env_disable_reason() -> str | None:
    """#2573 FR-002: the first honored disable env var, or ``None`` if none set.

    The gate honors the SAME sync-disable vocabulary as the daemon (``core.env.
    SYNC_DISABLE_ENV_VARS``) rather than inventing a third env var.
    """
    env_var = first_set_sync_disable_env()
    return f"{env_var} is set" if env_var else None


def _mt_pre_review_gate_skip_reason(st: _MoveTaskState) -> str | None:
    """#2573 FR-002: why the gate should be skipped this move, or ``None`` to run it.

    The ``--skip-pre-review-gate`` flag is checked first (an explicit, per-
    invocation opt-out); the disable env vars are checked second (a
    process-wide opt-out already used by the sync layer). Either one skips
    the gate WITHOUT ever resolving a workspace or spawning the scoped
    pytest subprocess — the default (neither set) still runs/enforces the
    gate exactly as before this fix.
    """
    if st.skip_pre_review_gate:
        return "--skip-pre-review-gate flag"
    return _mt_pre_review_gate_env_disable_reason()


def _mt_pre_review_scope_override(wp_frontmatter: str, main_repo_root: Path) -> tuple[str, ...] | None:
    """FR-004 override precedence: frontmatter > config > ``None`` (auto-scope).

    Precedence is frontmatter ``pre_review_test_scope`` > config
    ``review.pre_review_test_command`` > ``None`` (WP01's census-derived
    auto-scope). Both override surfaces hold a whitespace-separated list of
    pytest target arguments — the SAME shape
    ``pre_review_gate.run_scoped_tests_at_head`` already consumes — so only
    WHICH targets run is overridable; the runner mechanics (head-side pytest
    + ``diff_baseline``) stay WP01's regardless of precedence tier.
    """
    frontmatter_value = extract_scalar(wp_frontmatter, _PRE_REVIEW_FRONTMATTER_KEY)
    if frontmatter_value:
        return tuple(frontmatter_value.split())
    config_value = _mt_review_config_section(main_repo_root).get(_PRE_REVIEW_CONFIG_KEY_TEST_COMMAND)
    if config_value:
        return tuple(str(config_value).split())
    return None


def _mt_resolve_pre_review_workspace(st: _MoveTaskState) -> Path | None:
    """Resolve the on-disk worktree the WP's code changes live in.

    Returns ``None`` when no genuine workspace is resolvable (planning-lane
    WP, missing ``lanes.json``, a worktree husk, ...) — the gate then
    degrades cheaply to a ``no_coverage`` warn without ever diffing or
    running tests. Mirrors ``_mt_commit_lane_deliverables``'s own resolution
    + exception handling.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    from specify_cli.lanes.persistence import CorruptLanesError, MissingLanesError

    try:
        workspace = _tasks.resolve_workspace_for_wp(st.main_repo_root, st.mission_slug, st.task_id)
    except (ValueError, FileNotFoundError, MissingLanesError, CorruptLanesError):
        return None
    if not workspace.exists:
        return None
    # Annotated local: mypy runs with ``follow_imports = "skip"`` on this
    # quarantined module, so ``workspace`` (and ``ResolvedWorkspace`` itself)
    # surface as ``Any`` here; pinning the FIELD access to the stdlib ``Path``
    # type re-establishes the known concrete return type without a
    # suppression (mirrors ``RealFsReader``'s own idiom in
    # ``agent_tasks_ports.py``, which pins against a non-quarantined type).
    resolved_worktree_path: Path = workspace.worktree_path
    return resolved_worktree_path


def _mt_pre_review_changed_files(worktree_path: Path, base_branch: str) -> tuple[str, ...]:
    """Merge-base diff of the WP's worktree HEAD vs. its target branch.

    Routes through the canonical merge-base/diff surface
    (``core.vcs.git.merge_base_changed_files``, mission
    merge-base-diff-ssot-01KX44SD) rather than an inline ``git merge-base`` /
    ``git diff --name-only`` pair, generalized to every changed file rather
    than a ``kitty-specs/`` subset — the gate scopes tests off the WP's FULL
    changed-file set, not just spec docs. Any git failure degrades to an
    empty tuple (folds into a cheap ``no_coverage`` warn), never a crash.
    """
    changed = set(merge_base_changed_files(worktree_path, base_branch))
    changed.update(_mt_pre_review_dirty_paths(worktree_path))
    return tuple(sorted(changed))


def _mt_pre_review_dirty_paths(worktree_path: Path) -> tuple[str, ...]:
    """Return relevant staged, unstaged, and untracked deliverable paths."""
    from specify_cli.cli.commands.agent import tasks as _tasks

    status = _tasks.subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(worktree_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if status.returncode != 0:
        return ()
    filtered = _tasks._filter_runtime_state_paths(status.stdout)
    paths = _lane_deliverable_paths(worktree_path, filtered)
    return tuple(
        sorted(
            str(path.relative_to(worktree_path))
            for path in paths
            if path.is_relative_to(worktree_path)
        )
    )


def _mt_pre_review_gate_with_override_scope(
    test_targets: tuple[str, ...],
    *,
    repo_root: Path,
    baseline: BaselineTestResult | None,
    progress_callback: Callable[[float], None] | None = None,
) -> pre_review_gate.GateVerdict:
    """Compose a verdict for an EXPLICIT override scope (FR-004).

    An override IS the test scope, by definition — the census-derived scope
    (``GateCoverageScopeSource``) never runs for this precedence tier. The non-empty
    tail (head-run -> ``diff_baseline`` -> verdict) is NOT hand-mirrored here
    (pre-merge finding, #572/#1979/#2283: the mirrored copy left its
    ``NEW_FAILURES``/block/force + ``UNVERIFIED_BASELINE`` branches with zero
    coverage) — it REUSES ``pre_review_gate.evaluate_with_scope``, the exact
    same tested body ``evaluate_pre_review_gate`` itself drives. Only the
    empty-scope branch stays local: an override's empty list isn't a census
    exclusion, so ``ScopeResult.describe_empty_reason()``'s catch-all/
    composite-dir wording would be misleading — this keeps its own literal
    "override test scope is empty" reason instead.

    No ``SOURCE_MISMATCH`` here by design (#2894): this tier calls
    ``evaluate_with_scope`` with ``scope_source=None``, so it runs the legacy
    hardcoded pytest/JUnit path and never computes a ``source_identity`` to
    compare against the baseline's. That is intentional — an operator-pinned
    override IS the authoritative scope, so a baseline captured under a
    different source is not a reason to distrust it; the tier fails toward
    ``NEW_FAILURES``/``UNVERIFIED_BASELINE``, never a hard block.
    """
    scope = pre_review_gate.ScopeResult.from_override(test_targets)
    if scope.is_empty:
        return pre_review_gate.GateVerdict(
            outcome=pre_review_gate.GateOutcome.NO_COVERAGE,
            scope=scope,
            reason="override test scope is empty",
        )
    return pre_review_gate.evaluate_with_scope(
        scope,
        repo_root=repo_root,
        baseline=baseline,
        progress_callback=progress_callback,
    )


def _mt_empty_scope_verdict(reason: str, *, excluded_scope_files: tuple[str, ...] = ()) -> pre_review_gate.GateVerdict:
    """A ``no_coverage`` verdict built without deriving/running anything."""
    return pre_review_gate.GateVerdict(
        outcome=pre_review_gate.GateOutcome.NO_COVERAGE,
        scope=pre_review_gate.ScopeResult(
            test_targets=(),
            matched_shard_groups=(),
            matched_composite_dirs=(),
            empty_cone_composite_dirs=(),
            excluded_scope_files=excluded_scope_files,
        ),
        reason=reason,
    )


def _mt_cancelled_verdict() -> pre_review_gate.GateVerdict:
    """The terminal ``CANCELLED`` verdict a ``KeyboardInterrupt`` degrades to (T041/C-003).

    Single construction shared by every fail-open envelope (gate execution AND
    the pre-dispatch resolution phase) so a ``Ctrl-C`` anywhere in the hook lands
    on the sanctioned terminal-``CANCELLED`` hard-stop, never an unhandled
    ``BaseException`` that escapes ``move-task`` as exit 130 (FR-013 invariant).
    """
    return pre_review_gate.GateVerdict(
        outcome=pre_review_gate.GateOutcome.CANCELLED,
        scope=pre_review_gate.ScopeResult.from_override(()),
        reason="scoped test run cancelled",
        run_state=pre_review_gate.HeadRunState.CANCELLED,
    )


def _mt_pre_review_gate_metadata(
    verdict: pre_review_gate.GateVerdict,
    *,
    block_enabled: bool,
    blocked: bool,
    force_bypassed: bool,
) -> dict[str, Any]:
    """The FR-004 transition-evidence payload recorded via ``policy_metadata``."""
    scope = verdict.scope
    return {
        "outcome": verdict.outcome.value,
        "reason": verdict.reason,
        "new_failure_count": len(verdict.new_failures),
        "new_failure_nodeids": [failure.test for failure in verdict.new_failures],
        "pre_existing_failure_count": len(verdict.pre_existing_failures),
        "affected_shard_count": len(scope.matched_shard_groups) + len(scope.matched_composite_dirs),
        "matched_shard_groups": list(scope.matched_shard_groups),
        "matched_composite_dirs": list(scope.matched_composite_dirs),
        "test_targets": list(scope.test_targets),
        "block_enabled": block_enabled,
        "blocked": blocked,
        "force_bypassed": force_bypassed,
        "run_state": verdict.run_state.value,
    }


#: Pre-merge finding (#572/#1979/#2283): the opt-in block
#: (``review.fail_on_pre_review_regression``) can ONLY ever fire on a
#: ``NEW_FAILURES`` verdict (see ``_mt_run_pre_review_gate``'s ``would_block``
#: below), which itself needs a computed baseline. ``baseline.py``'s
#: ``capture_baseline`` returns ``None`` (no artifact ever written) when
#: ``review.test_command`` is unset — so an operator who opts in to the block
#: WITHOUT also configuring ``review.test_command`` gets a block that can
#: NEVER engage: every for_review move degrades to ``NO_COVERAGE`` or
#: ``UNVERIFIED_BASELINE`` (never ``NEW_FAILURES``), silently. That silence is
#: itself a defect, so this hint is surfaced as an EXPLICIT, non-dim warning
#: rather than folded into the routine dim advisory line below.
_PRE_REVIEW_BLOCK_UNENFORCEABLE_HINT = (
    "block requested via review.fail_on_pre_review_regression but COULD NOT be enforced — "
    "no verified new-failure verdict exists to block on. A baseline must be captured at "
    "implement time (configure review.test_command in .kittify/config.yaml) before this "
    "block can ever take effect."
)


def _mt_pre_review_gate_console_warning(verdict: pre_review_gate.GateVerdict, *, block_enabled: bool) -> str:
    """Human-readable (non-JSON) console line surfacing the verdict.

    ``block_enabled`` does not change the warn-vs-block semantics here (the
    transition still proceeds — you cannot block on data that doesn't
    exist) — it only decides whether the ``NO_COVERAGE``/``UNVERIFIED_BASELINE``
    line escalates from a routine dim advisory to an explicit block-inert
    warning naming the ``review.test_command`` prerequisite.
    """
    outcome = verdict.outcome
    if outcome is pre_review_gate.GateOutcome.NEW_FAILURES:
        shard_count = len(verdict.scope.matched_shard_groups) + len(verdict.scope.matched_composite_dirs)
        nodeids = ", ".join(failure.test for failure in verdict.new_failures[:5])
        more = f" (+{len(verdict.new_failures) - 5} more)" if len(verdict.new_failures) > 5 else ""
        return (
            f"[yellow]Pre-review regression gate:[/yellow] {len(verdict.new_failures)} new failure(s) "
            f"across {shard_count} affected shard(s) — {nodeids}{more}"
        )
    if outcome in (pre_review_gate.GateOutcome.NO_COVERAGE, pre_review_gate.GateOutcome.UNVERIFIED_BASELINE):
        if block_enabled:
            return (
                "[yellow]Pre-review regression gate:[/yellow] "
                f"{_PRE_REVIEW_BLOCK_UNENFORCEABLE_HINT} "
                f"(outcome={outcome.value}: {verdict.reason or 'unverified'})"
            )
        return f"[dim]Pre-review regression gate: {outcome.value} — {verdict.reason or 'unverified'}[/dim]"
    if outcome is pre_review_gate.GateOutcome.SOURCE_MISMATCH:
        # FR-009/FR-011 (mission scopesource-gate-followup-01KY6S9P WP04):
        # warn-shaped, fail-open by construction (absent from
        # ``verdict_aggregation``'s terminal/block member allowlists) — names
        # both identities so an operator can see WHY the diff is untrustworthy.
        return f"[yellow]Pre-review regression gate: {outcome.value} — {verdict.reason or 'unverified'}[/yellow]"
    if outcome in (pre_review_gate.GateOutcome.TIMED_OUT, pre_review_gate.GateOutcome.CANCELLED):
        return f"[red]Pre-review regression gate: {outcome.value} — {verdict.reason or 'interrupted'}[/red]"
    if outcome is pre_review_gate.GateOutcome.NO_NEW_FAILURES:
        return "[dim]Pre-review regression gate: no new failures[/dim]"
    # Defensive: a future ``GateOutcome`` member must never silently render as
    # a clean pass (mission scopesource-gate-followup-01KY6S9P WP04, T023) —
    # this branch is unreachable for today's exhaustive member set but closes
    # the silent-clean-pass class for whatever comes next.
    return f"[dim]Pre-review regression gate: {outcome.value}[/dim]"


def _mt_pre_review_gate_block_message(verdict: pre_review_gate.GateVerdict) -> str:
    """The refusal message when the opt-in block engages (FR-001)."""
    nodeids = ", ".join(failure.test for failure in verdict.new_failures[:5])
    more = f" (+{len(verdict.new_failures) - 5} more)" if len(verdict.new_failures) > 5 else ""
    return (
        "Pre-review regression gate BLOCKED this for_review move: "
        f"{len(verdict.new_failures)} new failure(s) introduced — {nodeids}{more}. "
        "Fix the regression, or re-run with --force to override (recorded in the transition evidence)."
    )


@dataclass(frozen=True)
class _TransitionGateInputs:
    """The shared, per-transition I/O the gate resolves once before dispatch.

    The changed-files SSOT (``_mt_pre_review_changed_files`` → ``:927``) is
    resolved here, then handed to the doctrine-resolved dispatch and the
    aggregation. Reused, never re-derived (contract "What the hook does NOT
    change"). The dirty-path baseline used to enrol subprocess byproducts
    (:func:`_mt_resolve_transition_gate_verdicts`) is resolved alongside these
    inputs but returned separately — it is transient bookkeeping, not part of
    the shared per-transition surface.
    """

    worktree_path: Path | None
    changed_files: tuple[str, ...]
    gate_repo_root: Path


@dataclass(frozen=True)
class _TransitionGateEffect:
    """The observable surface the aggregate decision maps onto (hook performs it).

    ``metadata`` is the ``policy_metadata`` payload; ``console_lines`` are the
    per-handler warn lines (≤1 per handler, NFR-002); ``representative`` is the
    single verdict the metadata/block message render from; ``blocked`` /
    ``terminal`` / ``should_exit`` drive the two hard-stops (T041).
    """

    metadata: dict[str, Any]
    console_lines: tuple[str, ...]
    representative: pre_review_gate.GateVerdict
    blocked: bool
    terminal: bool
    should_exit: bool


def _mt_warn_pre_review_test_command_deprecated(main_repo_root: Path) -> None:
    """T043 (FR-011): one-time deprecation warning for ``review.pre_review_test_command``.

    The legacy key is aliased to the ``ScopeSource`` single authority
    (``review.test_command``) and STILL honored — never a silent break — but a
    config that sets it earns exactly one process-wide deprecation warning
    (guarded by the module latch), routed through the standard ``warnings``
    surface so it never pollutes ``--json`` output.
    """
    global _pre_review_test_command_deprecation_emitted
    if _pre_review_test_command_deprecation_emitted:
        return
    if _mt_review_config_section(main_repo_root).get(_PRE_REVIEW_CONFIG_KEY_TEST_COMMAND) is None:
        return
    _pre_review_test_command_deprecation_emitted = True
    warnings.warn(_PRE_REVIEW_TEST_COMMAND_DEPRECATION, DeprecationWarning, stacklevel=2)


def _mt_resolve_scope_source(gate_repo_root: Path) -> ScopeSource:
    """Build the activation-selected ``ScopeSource`` for the pre-review handler.

    FR-014 (mission scopesource-gate-followup-01KY6S9P WP04, post-plan squad
    finding priti-M1 — load-bearing): delegates to WP02's
    ``resolve_scope_source`` factory — the SAME selection authority
    ``baseline.py``'s write-side capture already uses — instead of
    hard-constructing ``GateCoverageScopeSource`` directly. Without this
    the head path would stay pinned to ``GateCoverageScopeSource`` while
    the baseline uses whichever source ``review.test_command`` selects,
    producing a guaranteed ``SOURCE_MISMATCH`` on every non-pytest review —
    the exact false-positive this rewire closes.

    The two census test seams (:func:`_pre_review_gate_filter_groups` /
    :func:`_pre_review_gate_composite_routing`) are threaded through as
    ``resolve_scope_source``'s ``*_override`` parameters so production still
    leaves them ``None`` (live authority) and hermetic tests can inject a
    fixture map — the SAME seam the incumbent used. ``resolve_scope_source``
    lives in ``scope_source.py`` and never imports back into this module, so
    no import cycle forms.
    """
    return resolve_scope_source(
        gate_repo_root,
        filter_groups_override=_pre_review_gate_filter_groups(),
        composite_routing_override=_pre_review_gate_composite_routing(),
    )


def _mt_resolve_active_gate_bindings(st: _MoveTaskState) -> GateBindingResolution:
    """Resolve which doctrine-bound handlers gate this lane edge (FR-007/008).

    The impure orchestration seam: resolves the mission type from identity
    (never hardcoded) and delegates to
    :func:`resolve_gate_bindings_for_transition` (one graph load + one filter +
    one contract-bindings load, NFR-005). Kept a named module function so the
    escape-hatch / observability tests can inject a canned resolution without a
    full activated-doctrine repo fixture.
    """
    edge_key = f"{st.old_lane.value}->{st.target_lane.value}"
    mission = resolve_mission_type(st, feature_dir=st.feature_dir)
    return resolve_gate_bindings_for_transition(st.main_repo_root, mission, edge_key)


def _mt_resolve_gate_baseline(st: _MoveTaskState) -> BaselineTestResult | None:
    """Load the WP's captured baseline (``None`` when never captured).

    Shared by the doctrine-bound handler context and the FR-004 override tier so
    both diff against the SAME baseline artifact.
    """
    wp_slug = _resolve_wp_slug(st.main_repo_root, st.mission_slug, st.task_id)
    # C-008 (coord-commit-integrity-01KY5JS8): baseline-tests.json is a
    # WORK_PACKAGE_TASK-kind (PRIMARY-partition) artifact authored by
    # implement_capture_baseline. Under coord topology ``st.feature_dir`` is the
    # kind-blind coord husk where the PRIMARY-authored baseline does NOT exist —
    # reading it there silently loses pre-existing-failure suppression. Route the
    # READ through the SAME kind-aware seam the review gate uses (workflow.py
    # ``_resolve_workflow_read_dir(kind=WORK_PACKAGE_TASK)``), not the husk.
    from specify_cli.cli.commands.agent.workflow import _resolve_workflow_read_dir

    baseline_read_dir = _resolve_workflow_read_dir(
        repo_root=st.main_repo_root,
        mission_slug=st.mission_slug,
        kind=MissionArtifactKind.WORK_PACKAGE_TASK,
    )
    return BaselineTestResult.load(baseline_read_dir / "tasks" / wp_slug / "baseline-tests.json")


def _mt_build_transition_gate_context(st: _MoveTaskState, inputs: _TransitionGateInputs) -> TransitionGateContext:
    """Assemble the ``TransitionGateContext`` handed to every handler (data-model §8)."""
    return TransitionGateContext(
        changed_files=inputs.changed_files,
        scope_source=_mt_resolve_scope_source(inputs.gate_repo_root),
        baseline=_mt_resolve_gate_baseline(st),
        repo_root=inputs.gate_repo_root,
        force=st.force,
        from_lane=st.old_lane,
        to_lane=st.target_lane,
    )


def _mt_fail_open_gate(
    run: Callable[[], pre_review_gate.GateVerdict],
    *,
    changed_files: tuple[str, ...] = (),
) -> pre_review_gate.GateVerdict:
    """Run a gate-execution callable under the incumbent three-catch fail-open (T041/FR-013).

    Mirrors the incumbent's three-catch verbatim:
    ``KeyboardInterrupt`` → terminal ``CANCELLED``; ``GateAuthoritiesUnavailable``
    → unverified ``NO_COVERAGE`` warn (the erroneous-activation degrade, #2534);
    any other ``Exception`` → unverified ``NO_COVERAGE`` warn. Guarantees a gate
    fault yields exactly ONE verdict and never escapes move-task — whichever
    precedence tier produced the callable (a bound handler OR the FR-004 explicit
    override scope). The override tier is just another gate-execution path, so it
    MUST fail open here too; a bare ``KeyboardInterrupt`` in the override runner
    escaping to exit 130 would breach the terminal-CANCELLED hard-stop invariant.
    """
    try:
        return run()
    except KeyboardInterrupt:
        return _mt_cancelled_verdict()
    except pre_review_gate.GateAuthoritiesUnavailable as exc:
        return _mt_empty_scope_verdict(
            f"gate authorities unavailable — unverified: {exc}",
            excluded_scope_files=changed_files,
        )
    except Exception as exc:  # noqa: BLE001 — FR-013 per-handler fail-open (never break move-task)
        return _mt_empty_scope_verdict(f"pre-review gate evaluation failed — unverified: {exc}")


def _mt_dispatch_one_gate(
    binding: GateBinding,
    ctx: TransitionGateContext,
    handler_lookup: Callable[[str], GateHandler],
) -> pre_review_gate.GateVerdict:
    """Dispatch ONE bound handler under the shared three-catch fail-open (T041).

    Each fault yields exactly ONE verdict and never crosses into another handler.
    """
    return _mt_fail_open_gate(
        lambda: handler_lookup(binding.handler).run(ctx),
        changed_files=ctx.changed_files,
    )


def _mt_dispatch_transition_gates(
    bindings: Sequence[GateBinding],
    ctx: TransitionGateContext,
    *,
    handler_lookup: Callable[[str], GateHandler] = get_gate_handler,
) -> list[pre_review_gate.GateVerdict]:
    """Dispatch each active binding in the resolver's stable order (FR-004/008).

    ``get_gate_handler(b.handler).run(ctx)`` per binding (never a bare
    ``GATE_REGISTRY[name]``); order is the stable sort the resolver already
    applied, so aggregation precedence is deterministic (NFR-001).
    """
    return [_mt_dispatch_one_gate(binding, ctx, handler_lookup) for binding in bindings]


_PRE_REVIEW_GATE_RUNNING_NOTICE = (
    "[cyan]Pre-review regression gate: running scoped tests at head "
    "(may take a few minutes)...[/cyan]"
)


def _mt_collect_transition_gate_verdicts(
    st: _MoveTaskState,
    inputs: _TransitionGateInputs,
    _tasks: Any,
) -> list[pre_review_gate.GateVerdict]:
    """Resolve the FR-004 precedence tier, then the bindings, and return the verdict list.

    Precedence, mirroring the incumbent (NFR-001): an explicit operator override
    (frontmatter ``pre_review_test_scope`` > config ``pre_review_test_command``)
    IS the test scope — it bypasses BOTH the changed-file census AND doctrine
    binding resolution, evaluated through the shared
    :func:`_mt_pre_review_gate_with_override_scope` tier. WP09's first inversion
    dropped this tier (it never consulted the override), silently ignoring every
    operator-pinned scope; restoring it is part of full incumbent fidelity.

    Absent an override: a cheap short-circuit first — an empty changed-file set
    means there is nothing to gate, so it degrades to a single ``NO_COVERAGE``
    warn WITHOUT loading the activation graph (bounded cost, NFR-005). A
    resolution with no active binding (no contract / no binding / not activated)
    returns the resolver's **distinguishable** ``NO_COVERAGE`` reason
    (FR-008/012), never a silent vanish.
    """
    wp = getattr(st, "wp", None)
    override_targets = (
        _mt_pre_review_scope_override(wp.frontmatter, st.main_repo_root) if wp is not None else None
    )
    if override_targets is not None:
        if not st.json_output:
            _tasks.console.print(_PRE_REVIEW_GATE_RUNNING_NOTICE)
        return [
            _mt_fail_open_gate(
                lambda: _mt_pre_review_gate_with_override_scope(
                    override_targets,
                    repo_root=inputs.gate_repo_root,
                    baseline=_mt_resolve_gate_baseline(st),
                ),
                changed_files=inputs.changed_files,
            )
        ]
    if not inputs.changed_files:
        return [_mt_empty_scope_verdict("no changed files detected for this WP — skipping the gate cheaply")]
    resolution = _mt_resolve_active_gate_bindings(st)
    if not resolution.active:
        return [_mt_empty_scope_verdict(resolution.reason)]
    if not st.json_output:
        _tasks.console.print(_PRE_REVIEW_GATE_RUNNING_NOTICE)
    ctx = _mt_build_transition_gate_context(st, inputs)
    return _mt_dispatch_transition_gates(list(resolution.active), ctx)


def _mt_resolve_transition_gate_inputs(
    st: _MoveTaskState,
) -> tuple[_TransitionGateInputs, tuple[str, ...]]:
    """Resolve the workspace, dirty-path baseline, and changed-files SSOT (unchanged).

    Returns ``(inputs, dirty_before)``: ``dirty_before`` is the transient
    pre-dispatch dirty-path snapshot used later to enrol whatever a gate's
    subprocess creates (:func:`_mt_run_transition_gates`) — it is not part of
    the shared :class:`_TransitionGateInputs` surface.
    """
    worktree_path = _mt_resolve_pre_review_workspace(st)
    dirty_before = _mt_pre_review_dirty_paths(worktree_path) if worktree_path is not None else ()
    changed_files = (
        _mt_pre_review_changed_files(worktree_path, st.target_branch)
        if worktree_path is not None
        else ()
    )
    inputs = _TransitionGateInputs(
        worktree_path=worktree_path,
        changed_files=changed_files,
        gate_repo_root=worktree_path or st.main_repo_root,
    )
    return inputs, dirty_before


def _mt_resolve_transition_gate_verdicts(
    st: _MoveTaskState, _tasks: Any
) -> tuple[_TransitionGateInputs | None, tuple[str, ...], list[pre_review_gate.GateVerdict]]:
    """Run the pre-dispatch resolution phase under the SAME fail-open as :func:`_mt_fail_open_gate`.

    The incumbent (base ``e4ef6e850``) degraded a *resolution* fault to a
    ``NO_COVERAGE`` warn and PROCEEDED. The inverted hook only wrapped the
    dispatch/override tiers, so a fault in the pre-dispatch resolution phase —
    the deprecation warn, input resolution, or binding resolution + context build
    inside :func:`_mt_collect_transition_gate_verdicts` — escaped unwrapped to
    ``_do_move_task``'s outer ``except Exception`` and REFUSED the ``for_review``
    move (a fail-open→fail-closed regression + an unsanctioned third hard-stop),
    while a ``Ctrl-C`` (a ``BaseException``) slipped past that ``except Exception``
    entirely and exited 130 — the exact breach the terminal-``CANCELLED`` path
    exists to prevent. Routing resolution through the same three-catch restores
    C-003 / FR-013: ``KeyboardInterrupt`` → terminal ``CANCELLED``; any other
    ``Exception`` (malformed step-contract, unset org-pack env var, invalid DRG
    graph, malformed ``meta.json``/``"pending"`` sentinel, or ``warnings.warn``
    under ``-W error``) → exactly one visible ``NO_COVERAGE`` warn and PROCEED.

    Returns ``(inputs, dirty_before, verdicts)``; ``inputs`` is ``None`` when
    resolution raised before the workspace inputs were built (no changed/dirty
    paths to reconcile), in which case ``dirty_before`` is empty.
    """
    try:
        _mt_warn_pre_review_test_command_deprecated(st.main_repo_root)
        inputs, dirty_before = _mt_resolve_transition_gate_inputs(st)
        return inputs, dirty_before, _mt_collect_transition_gate_verdicts(st, inputs, _tasks)
    except KeyboardInterrupt:
        return None, (), [_mt_cancelled_verdict()]
    except pre_review_gate.GateAuthoritiesUnavailable as exc:
        return None, (), [_mt_empty_scope_verdict(f"gate authorities unavailable — unverified: {exc}")]
    except Exception as exc:  # noqa: BLE001 — FR-013 fail-open over resolution (never break move-task)
        return None, (), [_mt_empty_scope_verdict(f"pre-review gate resolution failed — unverified: {exc}")]


def _mt_gate_representative(
    aggregate: Any, verdicts: Sequence[pre_review_gate.GateVerdict]
) -> pre_review_gate.GateVerdict:
    """The single verdict the metadata / block message render from.

    Deterministic and, for the half-A single-handler reality, always the one
    dispatched verdict: the terminal verdict if the decision is terminal, else
    the first blocking (``NEW_FAILURES``) verdict, else the last verdict.
    """
    if aggregate.terminal_verdict is not None:
        return cast(pre_review_gate.GateVerdict, aggregate.terminal_verdict)
    if aggregate.blocking_verdicts:
        return cast(pre_review_gate.GateVerdict, aggregate.blocking_verdicts[0])
    if verdicts:
        return verdicts[-1]
    return _mt_empty_scope_verdict("no active gate bindings for this transition")


def _mt_translate_gate_verdicts(
    verdicts: Sequence[pre_review_gate.GateVerdict],
    *,
    block_enabled: bool,
    force: bool,
) -> _TransitionGateEffect:
    """Aggregate the per-handler verdicts and render the observable effect (FR-014).

    Precedence (terminal > block > warn) lives in WP08's pure
    :func:`aggregate_verdicts`; this helper only maps the aggregate onto the
    metadata / console / block-exit surface the incumbent produced, so the
    single-verdict path reproduces the base-captured parity tuple field-by-field
    (NFR-001).
    """
    aggregate = aggregate_verdicts(verdicts, block_enabled=block_enabled, force=force)
    representative = _mt_gate_representative(aggregate, verdicts)
    blocked = aggregate.decision is AggregateDecision.BLOCK
    terminal = aggregate.decision is AggregateDecision.TERMINAL
    force_bypassed = block_enabled and force and bool(aggregate.blocking_verdicts)
    metadata = _mt_pre_review_gate_metadata(
        representative,
        block_enabled=block_enabled,
        blocked=blocked,
        force_bypassed=force_bypassed,
    )
    if terminal:
        metadata["transition_applied"] = False
    console_lines = tuple(
        _mt_pre_review_gate_console_warning(verdict, block_enabled=block_enabled)
        for verdict in aggregate.warnings
    ) or (_mt_pre_review_gate_console_warning(representative, block_enabled=block_enabled),)
    return _TransitionGateEffect(
        metadata=metadata,
        console_lines=console_lines,
        representative=representative,
        blocked=blocked,
        terminal=terminal,
        should_exit=aggregate.should_exit,
    )


def _mt_emit_skipped_gate(st: _MoveTaskState, _tasks: Any, skip_reason: str) -> None:
    """Record + announce a skipped gate (escape hatch, #2573 FR-002)."""
    verdict = _mt_empty_scope_verdict(f"gate skipped — {skip_reason}")
    st.pre_review_gate_metadata = _mt_pre_review_gate_metadata(
        verdict, block_enabled=False, blocked=False, force_bypassed=False,
    )
    if not st.json_output:
        _tasks.console.print(f"[yellow]Pre-review regression gate: SKIPPED ({skip_reason})[/yellow]")


def _mt_emit_transition_gate_effect(
    st: _MoveTaskState,
    effect: _TransitionGateEffect,
    _tasks: Any,
) -> None:
    """Emit console + perform the two hard-stops (T041) from the aggregate effect."""
    if not st.json_output:
        for line in effect.console_lines:
            _tasks.console.print(line)
    if effect.terminal:
        outcome_value = effect.representative.outcome.value
        _tasks._output_error(
            st.json_output,
            f"Pre-review regression gate {outcome_value}; transition not applied",
            diagnostic={
                "result": "error",
                "error": f"pre-review gate {outcome_value}",
                "transition_applied": False,
                "pre_review_gate": st.pre_review_gate_metadata,
            },
        )
        raise typer.Exit(1)
    if effect.blocked:
        _tasks._output_error(st.json_output, _mt_pre_review_gate_block_message(effect.representative))
        raise typer.Exit(1)


def _mt_run_transition_gates(st: _MoveTaskState) -> None:
    """FR-009/013/014: the inverted, doctrine-resolved transition gate.

    Generalizes the incumbent ``_mt_run_pre_review_gate``: instead of a
    hardcoded call to ``evaluate_pre_review_gate``, it resolves WHICH named
    handlers the repo's active doctrine binds to the current lane edge (WP06's
    ``resolve_gate_bindings_for_transition`` + WP04's ``GATE_REGISTRY``),
    dispatches each with per-handler fail-open (T041), and aggregates via WP08's
    pure ``aggregate_verdicts`` (T040). A thin orchestrator: the join and the
    aggregation are the pure functions it merely calls (NFR-006).

    Runs ONLY for ``for_review`` moves, right after ``_mt_run_decision`` in
    ``_do_move_task`` — AFTER every pre-existing guard clears and BEFORE the
    transition is emitted/committed. Purely additive after the guard sequence:
    the two hard-stops (terminal interruption; opt-in ``NEW_FAILURES`` block) are
    the only non-local exits, and every handler-execution error degrades to one
    visible ``NO_COVERAGE`` warn (C-003).
    """
    if st.target_lane != Lane.FOR_REVIEW:
        return
    from specify_cli.cli.commands.agent import tasks as _tasks

    # #2573 FR-002: the opt-out escape hatch — checked BEFORE touching the
    # workspace or WP frontmatter, so a skip never resolves a lane workspace,
    # diffs changed files, or spawns the scoped pytest subprocess.
    skip_reason = _mt_pre_review_gate_skip_reason(st)
    if skip_reason is not None:
        _mt_emit_skipped_gate(st, _tasks, skip_reason)
        return

    assert st.wp is not None
    inputs, dirty_before, verdicts = _mt_resolve_transition_gate_verdicts(st, _tasks)
    worktree_path = inputs.worktree_path if inputs is not None else None
    byproduct_snapshots = _mt_enrol_gate_byproducts(worktree_path, dirty_before)
    block_enabled = _mt_pre_review_block_enabled(st.main_repo_root)
    effect = _mt_translate_gate_verdicts(verdicts, block_enabled=block_enabled, force=st.force)
    # IC-07f (WP16): the enrolment above is the compensator's snapshot leg
    # (``{path: None}`` for a subprocess-created path — the pre-transaction
    # state the compensator restores to). Committed on success means simply
    # NOT restoring: the created bytes stay put. On the two hard-stops
    # (terminal interruption, opt-in block) the step aborts, so the SAME
    # single restore path the merge executor and the coordination transaction
    # use (:func:`restore_generated_artifact_snapshots`) unlinks them —
    # genuinely reverted, not merely detected-and-abandoned.
    if byproduct_snapshots and effect.should_exit:
        restore_generated_artifact_snapshots(byproduct_snapshots)
    st.pre_review_gate_metadata = effect.metadata
    _mt_emit_transition_gate_effect(st, effect, _tasks)


def _mt_enrol_gate_byproducts(
    worktree_path: Path | None, dirty_before: tuple[str, ...]
) -> dict[Path, bytes | None]:
    """Enrol any path a bound gate's subprocess created into the owner (C3).

    A gate handler may spawn a scoped pytest run that creates cache/coverage
    byproducts inside the WP's own worktree. Diffing the post-dispatch dirty
    set against ``dirty_before`` (captured pre-dispatch) yields exactly the
    paths the subprocess created (:func:`subprocess_created_paths`, the SAME
    owner helper the merge executor and the coordination transaction use).
    Enrolling them (:func:`enroll_subprocess_byproducts`) snapshots their
    absent pre-transaction state and returns it — the caller (
    :func:`_mt_run_transition_gates`) routes that snapshot through the single
    restore compensator on the abort/block path, so the byproduct is
    genuinely committed on success and reverted on abort, never merely
    detected and abandoned.
    """
    if worktree_path is None:
        return {}
    dirty_after = _mt_pre_review_dirty_paths(worktree_path)
    created = subprocess_created_paths(
        (worktree_path / rel for rel in dirty_before),
        (worktree_path / rel for rel in dirty_after),
    )
    if not created:
        return {}
    # Annotated local: mypy runs with ``follow_imports = "skip"`` on this
    # quarantined module, so the cross-module call surfaces as ``Any`` here;
    # pinning it re-establishes the known concrete return type without a
    # suppression (mirrors ``_mt_resolve_pre_review_workspace``'s own idiom).
    snapshots: dict[Path, bytes | None] = enroll_subprocess_byproducts(
        created, trusted_roots=(worktree_path,)
    )
    return snapshots


def _mt_run_pre_review_gate(st: _MoveTaskState) -> None:
    """Thin forwarder onto the inverted hook :func:`_mt_run_transition_gates`.

    Kept as a real, exported symbol (frozen compat surface, squad P-F1) and as
    the ``_do_move_task`` call-site target so the observability monkeypatch that
    binds ``_mt_run_pre_review_gate`` by name keeps intercepting. Do NOT repoint
    the call site at ``_mt_run_transition_gates`` — that would no-op the patch.
    """
    return _mt_run_transition_gates(st)


# --- phase D: finalize emit plan --------------------------------------------


def _mt_finalize_plan(st: _MoveTaskState) -> None:
    """Execute the decision's authorised side-effect *inputs* and finalize the plan.

    The override/arbiter persists already fired at their OLD guard positions — they
    are NOT repeated here. Only the planned-rollback review cycle (which produces
    the feedback pointer) runs, then the plan is rebuilt when a side-effect produced
    a ``review_ref``.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    assert st.decision is not None
    decision = st.decision
    st.emit_plan = decision.plan
    st.evidence_dict = decision.evidence_dict
    st.note_text = decision.note_text
    st.actor = st.agent or "user"
    st.canonical_lane = decision.plan.canonical_lane
    if decision.planned_rollback and st.resolved_feedback_source is not None:
        from specify_cli.review.cycle import create_rejected_review_cycle

        review_cycle = create_rejected_review_cycle(
            main_repo_root=st.main_repo_root,
            mission_slug=st.mission_slug,
            wp_id=st.task_id,
            wp_slug=_resolve_wp_slug(st.main_repo_root, st.mission_slug, st.task_id),
            feedback_source=st.resolved_feedback_source,
            reviewer_agent=st.agent or "unknown",
        )
        st.review_feedback_pointer = review_cycle.pointer
        st.rejected_review_result = review_cycle.review_result
    if decision.done_override_note and not st.json_output:
        _tasks.console.print(
            "[yellow]⚠️  Proceeding with done override; reason recorded in "
            "history/events.[/yellow]"
        )
    # SC-007: WP06 owns the two ``in_review -> *`` edges re-scoped from WP02.
    # Build the structured review outcome BEFORE the plan rebuild so it can be
    # threaded into ``build_transition_plan`` (WP02's optional ``review_result``
    # seam) — the FSM then accepts those backward edges force-free instead of
    # promoting ``emit_force=True``.
    st.plan_review_result = _mt_plan_review_result(st)
    if (
        decision.planned_rollback
        or decision.arbiter_forward
        or (
            st.old_lane == Lane.IN_REVIEW
            and st.target_lane in (Lane.PLANNED, Lane.IN_PROGRESS)
        )
    ):
        st.emit_plan = build_transition_plan(
            old_lane=str(st.old_lane),
            target_lane=str(st.target_lane),
            force=st.force,
            review_feedback_pointer=st.review_feedback_pointer,
            arb_review_ref=st.arb_review_ref,
            note_text=st.note_text,
            review_result=st.plan_review_result,
        )


def _mt_plan_review_result(st: _MoveTaskState) -> ReviewResult | None:
    """Structured review outcome justifying a force-free exit from ``in_review``.

    SC-007: WP06 owns the two ``in_review -> *`` edges re-scoped from WP02
    (``in_review -> planned`` and ``in_review -> in_progress``). It threads this
    ``ReviewResult`` (reviewer + verdict + reference) into
    :func:`build_transition_plan` (WP02's optional ``review_result`` seam) so the
    FSM accepts the backward edge force-free — the review outcome justifies the
    reverse transition instead of a raw ``force`` flag. Returns ``None`` off the
    in_review exit so every other edge is untouched (WP02 owns the other 3 edges
    and the ``build_transition_plan`` signature — WP06 only consumes them).

    A rejection to ``planned`` already minted a structured result via the review
    cycle (:attr:`rejected_review_result`); reuse it so its ``reference`` matches
    the emitted ``review_ref`` (the ``_check_review_result_consistency`` guard).
    """
    if st.old_lane != Lane.IN_REVIEW:
        return None
    if st.rejected_review_result is not None:
        return st.rejected_review_result
    reviewer = (st.reviewer or st.agent or st.actor or "unknown").strip() or "unknown"
    if st.target_lane in (Lane.APPROVED, Lane.DONE):
        verdict = "approved"
        reference = (st.approval_ref or f"approval:{st.task_id}").strip() or (
            f"approval:{st.task_id}"
        )
    else:
        verdict = "changes_requested"
        reference = (
            st.review_feedback_pointer or st.note_text or f"review:{st.task_id}"
        ).strip() or f"review:{st.task_id}"
    return ReviewResult(reviewer=reviewer, verdict=verdict, reference=reference)


# --- phase E: emit the lane transition(s) via commit_status ------------------


def _mt_current_event_lane(st: _MoveTaskState) -> str:
    """The WP's current canonical lane (the emit chain's from-lane seed)."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    current_event_lane: str | None = None
    for existing_event in reversed(
        _tasks.read_events_transactional(
            feature_dir=st.feature_dir,
            mission_slug=st.mission_slug,
            repo_root=st.main_repo_root,
        )
    ):
        if existing_event.wp_id == st.task_id:
            current_event_lane = str(existing_event.to_lane)
            break
    if current_event_lane is None:
        # No canonical state — finalize-tasks must run first (#1589).
        from specify_cli.status import uninitialized_status_error

        raise RuntimeError(
            uninitialized_status_error(st.mission_slug, st.task_id, st.feature_dir)
        )
    return current_event_lane


def _mt_hop_review_result(
    st: _MoveTaskState,
    event: StatusEvent | None,
    current_event_lane: str,
    target: str,
    hop_actor: str,
) -> ReviewResult | None:
    """Auto-construct a ``ReviewResult`` when a hop leaves ``in_review``."""
    rejected = st.rejected_review_result
    in_review = (event is not None and event.to_lane == Lane.IN_REVIEW) or (
        event is None and current_event_lane == Lane.IN_REVIEW
    )
    if in_review and target == Lane.PLANNED and rejected is not None:
        return rejected
    if in_review and st.evidence_dict is not None:
        review_section = st.evidence_dict.get("review", {})
        return ReviewResult(
            reviewer=review_section.get("reviewer", hop_actor),
            verdict=review_section.get("verdict", Lane.APPROVED),
            reference=review_section.get("reference", f"auto-forward:{st.task_id}"),
        )
    # SC-007: a force-free ``in_review -> {planned,in_progress}`` exit carries the
    # same structured review outcome threaded into the plan (WP06) so the
    # commit-time FSM guard accepts it without a ``force`` flag.
    if in_review and st.plan_review_result is not None:
        return st.plan_review_result
    return None


def _mt_hop_actor(
    st: _MoveTaskState, event: StatusEvent | None, current_event_lane: str, target: str
) -> str:
    """Resolve the actor for one emit hop (impl handoff preserves the WP agent)."""
    from_lane_for_hop = (
        event.to_lane if event is not None else resolve_lane_alias(current_event_lane)
    )
    return (
        st.agent
        or (
            st.current_agent
            if from_lane_for_hop == Lane.IN_PROGRESS and target == Lane.FOR_REVIEW
            else None
        )
        or "user"
    )


def _mt_shell_pid_baseline(pid: int) -> str | None:
    """Best-effort PID-reuse identity baseline for a claim (D3b / #2580).

    Mirrors ``frontmatter.write_shell_pid_claim``'s baseline capture WITHOUT
    resurrecting a WP-file write — WP07 owns that symbol; WP06 only records the
    baseline alongside ``shell_pid`` in the event stream (claim ``policy_metadata``
    or an ``InnerStateChanged`` delta). Degrades to ``None`` when uncapturable
    (a claim still succeeds; ``stale_detection`` treats an absent baseline as a
    legacy claim, zero regression).
    """
    from specify_cli.core.process_liveness import capture_creation_time_baseline

    return capture_creation_time_baseline(pid)


def _mt_hop_policy_metadata(
    st: _MoveTaskState, target: str
) -> dict[str, Any] | None:
    """Resolve the ``policy_metadata`` sidecar for one emit hop.

    FR-004: the claim triple (``shell_pid``/``shell_pid_created_at``/``agent``)
    rides the real ``planned -> claimed`` transition's ``policy_metadata`` — the
    reducer's claim fold extracts those exact keys into the snapshot runtime
    slots (``build_claim_policy_metadata`` is the WP01 shape authority). The
    pre-review-gate metadata rides the ``* -> for_review`` hop. ``None``
    otherwise.
    """
    if target == Lane.CLAIMED and st.shell_pid:
        from specify_cli.status import build_claim_policy_metadata

        pid = int(st.shell_pid)
        baseline = _mt_shell_pid_baseline(pid)
        claim_metadata: dict[str, Any] = build_claim_policy_metadata(
            pid, baseline or "", st.agent or st.actor or "unknown"
        )
        return claim_metadata
    if target == Lane.FOR_REVIEW and st.pre_review_gate_metadata is not None:
        return {"pre_review_gate": st.pre_review_gate_metadata}
    return None


def _binding_role_for_lane(lane: Lane | str) -> str | None:
    """Map a target lane to its resolved-binding role.

    Shared by :func:`_mt_emit_transitions` (the live transition-emit path,
    which needs the ``None`` case to skip binding-role annotation for any
    lane that is neither a claim nor a review-claim) and
    :func:`_mt_reassignment_binding_fields` (the off-transition reassignment
    path, which always wants a role and falls back to ``"implementer"`` at
    its own call site — collapses the previously duplicated role map).
    """
    if lane == Lane.CLAIMED:
        return "implementer"
    if lane == Lane.IN_REVIEW:
        return "reviewer"
    return None


def _mt_emit_transitions(st: _MoveTaskState, ports: TasksPorts) -> None:
    """Emit each lane hop through the coord WRITE ``commit_status`` capability."""
    assert st.emit_plan is not None
    emit_plan = st.emit_plan
    emit_force = emit_plan.emit_force
    emit_reason = emit_plan.emit_reason
    emit_review_ref = emit_plan.emit_review_ref
    current_event_lane = _mt_current_event_lane(st)
    event: StatusEvent | None = None
    final_hop_actor = st.actor
    for target in emit_plan.transition_targets:
        hop_actor = _mt_hop_actor(st, event, current_event_lane, target)
        hop_review_result = _mt_hop_review_result(
            st, event, current_event_lane, target, hop_actor
        )
        hop_policy_metadata = _mt_hop_policy_metadata(st, target)
        binding_role = _binding_role_for_lane(target)
        transition_actor: str | dict[str, str | None] = hop_actor
        annotation_delta = None
        if binding_role is not None and st.resolved_binding is not None:
            from specify_cli.status import build_self_asserting_actor

            # FR-005: route the compact ``--agent`` value through the single
            # self-asserting actor seam — only the parsed BARE tool reaches
            # actor.tool, absent segments stay None, and the dispatch binding
            # wins over the self-asserted parse.
            transition_actor = build_self_asserting_actor(
                role=binding_role,
                agent=st.agent,
                fallback_tool=hop_actor,
                binding=st.resolved_binding,
            )
            annotation_delta = st.resolved_binding.to_delta(role=binding_role)
        if target == Lane.CLAIMED and st.shell_pid:
            # FR-004: the claim triple rode this transition's policy_metadata —
            # do NOT re-emit it as an off-axis InnerStateChanged delta.
            st.claim_emitted = True
        event = ports.coord.commit_status(
            TransitionRequest(
                feature_dir=st.feature_dir,
                mission_slug=st.mission_slug,
                wp_id=st.task_id,
                to_lane=target,
                actor=transition_actor,
                force=emit_force,
                reason=emit_reason,
                evidence=st.evidence_dict if target in (Lane.APPROVED, Lane.DONE) else None,
                policy_metadata=hop_policy_metadata,
                review_ref=emit_review_ref,
                workspace_context=f"move-task:{st.main_repo_root}",
                subtasks_complete=(
                    True
                    if target in (Lane.FOR_REVIEW, Lane.APPROVED) and not emit_force
                    else None
                ),
                implementation_evidence_present=(
                    True
                    if target in (Lane.FOR_REVIEW, Lane.APPROVED) and not emit_force
                    else None
                ),
                repo_root=st.main_repo_root,
                review_result=hop_review_result,
                annotation_delta=annotation_delta,
            ),
            capability=GuardCapability.STANDARD,
        ).event
        final_hop_actor = hop_actor
        # review_ref only applies to the (first) rollback hop, never forward hops.
        emit_review_ref = None
    st.event = event
    st.final_hop_actor = final_hop_actor


# --- phase F: persist the WP file + primary commit via commit_artifact --------


def _mt_rollback_subtasks_reset(
    st: _MoveTaskState, ports: TasksPorts
) -> dict[str, Lane]:
    """Subtask-reset delta for a rollback to ``planned`` (#2513, via the log).

    A WP rolled back to ``planned`` must be fully re-implemented — leaving its
    completion state intact would let the review gate pass immediately on the
    next ``for_review`` with no work re-done. With subtask completion
    event-sourced (WP04), the intent is now expressed as an ``InnerStateChanged``
    ``subtasks`` delta resetting every roster row to ``planned`` (the gate
    re-blocks off the snapshot) rather than unchecking the ``tasks.md`` checkbox
    bytes — so ``tasks.md`` stays byte-stable (AC-5).

    The roster (which task ids belong to this WP) is the authored WP-file
    ``subtasks:`` frontmatter list — static design intent — read through the
    TASKS_INDEX (primary) read dir, never ``Path.cwd()`` (SC-008 / #2647).
    Returns an empty mapping only for an explicitly authored empty roster.
    """
    from specify_cli.core.subtask_rows import authored_subtask_roster

    handle = MissionHandle(repo_root=st.main_repo_root, mission_slug=st.mission_slug)
    feature_dir = ports.fs.planning_read_dir(
        handle, kind=MissionArtifactKind.TASKS_INDEX
    )
    roster = authored_subtask_roster(feature_dir, st.task_id)
    return dict.fromkeys(roster, Lane.PLANNED)


def _mt_reassignment_binding_fields(st: _MoveTaskState) -> dict[str, Any]:
    """Resolved actual for an off-transition agent reassignment."""
    if not st.agent or st.resolved_binding is None:
        return {}
    role = _binding_role_for_lane(st.target_lane) or "implementer"
    delta = st.resolved_binding.to_delta(role=role)
    binding_fields: dict[str, Any] = delta.to_dict()
    return binding_fields


def _mt_emit_runtime_state(st: _MoveTaskState, ports: TasksPorts) -> None:
    """Emit the move-task runtime-state deltas as off-axis ``InnerStateChanged``.

    The god-write is cut (FR-006/FR-007/FR-008, AC-5): the WP file stops carrying
    runtime state — the event log carries it.

    - The claim triple (``shell_pid``/``shell_pid_created_at``/``agent``) for a
      real ``planned -> claimed`` transition already rode that transition's
      ``policy_metadata`` sidecar (FR-004; see :func:`_mt_hop_policy_metadata`)
      and is flagged on ``st.claim_emitted`` — it is NOT re-emitted here. A
      reassignment/refresh OUTSIDE the claim transition is an off-axis delta.
    - ``assignee``, the Activity-Log ``note`` (FR-007), and the ``tracker_refs``
      **union** (FR-006) are off-axis deltas.
    - A rollback to ``planned`` carries a ``subtasks`` reset so the review gate
      re-blocks off the snapshot (#2513, via the log — not the checkbox).

    Every emit resolves its write target from ``st.feature_dir`` — resolved from
    stored topology in :func:`_mt_resolve_targets` — never ``Path.cwd()``
    (SC-008 / #2647; ``emit_inner_state_changed`` re-canonicalizes it there too).
    """
    from specify_cli.status import emit_inner_state_changed

    fields: dict[str, Any] = {}
    if not st.claim_emitted:
        if st.agent:
            fields["agent"] = st.agent
            fields.update(_mt_reassignment_binding_fields(st))
        if st.shell_pid:
            pid = int(st.shell_pid)
            fields["shell_pid"] = pid
            baseline = _mt_shell_pid_baseline(pid)
            if baseline is not None:
                fields["shell_pid_created_at"] = baseline
    if st.assignee:
        fields["assignee"] = st.assignee
    # FR-007: a USER-supplied Activity-Log note becomes a ``note`` annotation. The
    # synthetic ``Moved to <lane>`` fallback the old god-write wrote is already
    # captured by the transition's ``reason`` — re-emitting it would only add a
    # redundant trailing annotation, so it is not emitted off-axis (the WP file
    # no longer carries runtime state at all -- the event log is sole authority).
    if st.note_text:
        fields["note"] = st.note_text
    if st.tracker_ref_values:
        fields["tracker_refs"] = list(st.tracker_ref_values)
    if st.target_lane == Lane.PLANNED:
        reset = _mt_rollback_subtasks_reset(st, ports)
        if reset:
            fields["subtasks"] = reset
        # #2512: a rollback to ``planned`` RELEASES the prior claim so the
        # rolled-back WP exposes no live claim marker. Field repro: an agent
        # process was killed (macOS idle-sleep) leaving ``agent``/``shell_pid``
        # behind; the rollback reset the lane but not the claim, so the next
        # resume failed ``LANE_ALLOCATION_FAILED``. With the god-write cut the
        # claim now lives in the reduced snapshot (the claim transition's
        # ``policy_metadata``), and it was released in NEITHER surface — so the
        # release is emitted here off-axis as an ``InnerStateChanged`` clearing
        # both slots (empty ``agent`` / zero ``shell_pid`` fold to a falsy,
        # released snapshot slot). Event-only: the WP file stays byte-stable
        # (AC-5) -- runtime state lives solely in the event log. Skipped when
        # the SAME move re-plants a fresh claim
        # (an explicit ``--agent``/``--shell-pid`` override already set the
        # field above).
        if "agent" not in fields:
            fields["agent"] = ""
        if "shell_pid" not in fields:
            fields["shell_pid"] = 0

    delta = WPInnerStateDelta(**fields)
    if delta.is_empty():
        return
    emit_inner_state_changed(
        st.feature_dir,
        st.task_id,
        delta,
        actor=st.final_hop_actor or st.actor,
        mission_slug=st.mission_slug,
        repo_root=st.main_repo_root,
    )


def _mt_persist_wp_file(st: _MoveTaskState, ports: TasksPorts) -> None:
    """Record the move-task runtime state — event-only (IC-04 flip complete).

    Runtime state is emitted as ``InnerStateChanged`` annotations (plus the claim
    ``policy_metadata`` that rode the transition). Post-cutover the WP file no
    longer carries runtime state — the event log is the sole authority. WP04 (IC-03)
    made the readers unconditional and dropped the retired phase-authority
    predicate + facade export; this WP removes the last consumer of that gate here,
    so the former early-return (once the flag was on) and the ``_mt_dual_write_wp_file``
    god-write it guarded (``agent``/``assignee``/``shell_pid`` + Activity-Log) are
    both deleted (FR-007, D-14). ``_mt_emit_runtime_state`` (the off-axis emit) is unchanged.
    """
    assert st.wp is not None and st.decision is not None
    _mt_emit_runtime_state(st, ports)


# --- phase H: review-lock release + result output ----------------------------


def _mt_release_review_lock(st: _MoveTaskState) -> None:
    """FR-017 / FR-018: release the review lock when review terminates.

    Placed AFTER the lane-transition commit so a failed release never rolls back
    the recorded transition; failures are logged, never fatal.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    release_from = (Lane.FOR_REVIEW, Lane.IN_REVIEW, Lane.IN_PROGRESS)
    release_to = (Lane.APPROVED, Lane.PLANNED)
    if not (st.old_lane in release_from and st.target_lane in release_to):
        return
    try:
        from specify_cli.review.lock import ReviewLock

        lock_workspace = _tasks.resolve_workspace_for_wp(
            st.main_repo_root, st.mission_slug, st.task_id
        )
        ReviewLock.release(Path(lock_workspace.worktree_path))
    except Exception as _release_exc:  # pragma: no cover - defensive
        logging.getLogger(__name__).warning(
            "Review lock release failed for %s in %s: %s",
            st.task_id,
            st.mission_slug,
            _release_exc,
        )


def _mt_execute(st: _MoveTaskState, ports: TasksPorts) -> None:
    """Emit the transition(s) + persist the WP file under the status lock."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    with _tasks.feature_status_lock(st.main_repo_root, st.mission_slug):
        _mt_emit_transitions(st, ports)
        if st.self_review_fallback:
            from specify_cli.status import emit_reviewer_self_approval

            emit_reviewer_self_approval(
                st.feature_dir,
                mission_slug=st.mission_slug,
                wp_id=st.task_id,
                implementing_actor=st.final_hop_actor or "",
                intended_reviewer=(st.intended_reviewer or "").strip(),
                failure_reason=(st.reviewer_failure_reason or "").strip(),
                fallback_approved=True,
            )
        _mt_persist_wp_file(st, ports)
    # The rollback-to-``planned`` reset is now the ``subtasks`` reset delta emitted
    # inside ``_mt_persist_wp_file`` (#2513-via-snapshot) — the out-of-lock uncheck
    # seam is gone. The review-lock release still runs last on the rollback path
    # (D2 ordering preserved).
    _mt_release_review_lock(st)


def _mt_output(st: _MoveTaskState) -> None:
    """Emit the success envelope + dependent-WP warnings (coord skip arm aware)."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    assert st.decision is not None and st.wp is not None
    event_fields = _tasks._status_event_result_fields(st.event)
    # WP03: the coord skip arm's polymorphic ``--json`` envelope is driven by the
    # core decision (``Emit.skip_primary``), not the raw fact.
    status_events_path = (
        _tasks._coord_status_events_path(st.main_repo_root, st.mission_slug)
        if st.decision.skip_primary
        else None
    )
    result: dict[str, object] = {
        "result": "success",
        "task_id": st.task_id,
        "old_lane": st.old_lane,
        "new_lane": st.target_lane,
        "path": str(st.wp.path),
        "event_id": event_fields["event_id"],
        "work_package_id": st.task_id,
        "to_lane": event_fields["to_lane"] or st.canonical_lane,
        "status_events_path": str(status_events_path or (st.feature_dir / EVENTS_FILENAME)),
    }
    if st.decision.skip_primary:
        result["wp_file_update"] = "skipped"
        result["wp_file_update_reason"] = (
            "protected branch with coordination topology; status event "
            "is authoritative on the coordination branch"
        )
        if st.agent:
            result["frontmatter_fields_skipped"] = ["agent"]
    if st.review_feedback_pointer is not None:
        result["review_feedback"] = st.review_feedback_pointer
    if st.pre_review_gate_metadata is not None:
        result["pre_review_gate"] = st.pre_review_gate_metadata
    _tasks._output_result(
        st.json_output,
        result,
        f"[green]✓[/green] Moved {st.task_id} from {st.old_lane} to {st.target_lane}",
    )
    # Check for dependent WP warnings when moving to for_review (T083).
    _tasks._check_dependent_warnings(
        st.repo_root, st.mission_slug, st.task_id, st.target_lane, st.json_output
    )


@dataclass(frozen=True)
class _MoveTaskArgs:
    """Parameter object for ``_do_move_task``'s raw CLI-facing arguments.

    T033 (#2649): the pre-extraction signature carried 21 individual
    parameters (task_id..skip_pre_review_gate, plus the ``ports`` DI seam) —
    over the local ≤13 ceiling. Grouping every raw input into ONE dataclass
    (field set and defaults mirror the pre-extraction signature exactly,
    NFR-002) collapses the call surface to ``(args, *, ports)`` — 2
    parameters — leaving headroom for future flags (e.g. draft PR #2639) to
    join this dataclass instead of re-breaching the ceiling. Module-private
    (C-008/NFR-004): no net-new public symbol.
    """

    task_id: str
    to: str
    mission: str | None
    agent: str | None
    assignee: str | None
    shell_pid: str | None
    note: str | None
    review_feedback_file: Path | None
    approval_ref: str | None
    reviewer: str | None
    self_review_fallback: bool
    intended_reviewer: str | None
    reviewer_failure_reason: str | None
    done_override_reason: str | None
    force: bool
    tracker_ref: list[str] | None
    skip_review_artifact_check: bool
    auto_commit: bool | None
    json_output: bool
    skip_pre_review_gate: bool = False
    model: str | None = None
    profile: str | None = None
    invocation_id: str | None = None


def _do_move_task(args: _MoveTaskArgs, *, ports: TasksPorts | None = None) -> None:
    """Orchestrate ``move-task`` over the WP03 core + WP02 ports (C-005 seam).

    ``ports=None`` builds the production bundle (coord router bound to this
    module's patchable symbols). Tests inject a Fake bundle to observe the executed
    side-effects (T029). The phase helpers run in the SAME order as the original
    single body: resolve → gather → decide → finalize → execute → output.

    T033 (#2649): ``args`` groups the 19 raw CLI-facing inputs the original
    21-parameter signature carried individually — see :class:`_MoveTaskArgs`.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    ports = ports or _default_move_task_ports()
    st = _MoveTaskState(
        task_id=args.task_id,
        to=args.to,
        mission=args.mission,
        agent=args.agent,
        model=args.model,
        profile=args.profile,
        invocation_id=args.invocation_id,
        assignee=args.assignee,
        shell_pid=args.shell_pid,
        note=args.note,
        review_feedback_file=args.review_feedback_file,
        approval_ref=args.approval_ref,
        reviewer=args.reviewer,
        self_review_fallback=args.self_review_fallback,
        intended_reviewer=args.intended_reviewer,
        reviewer_failure_reason=args.reviewer_failure_reason,
        done_override_reason=args.done_override_reason,
        force=args.force,
        tracker_ref=args.tracker_ref,
        skip_review_artifact_check=args.skip_review_artifact_check,
        auto_commit=args.auto_commit,
        json_output=args.json_output,
        skip_pre_review_gate=args.skip_pre_review_gate,
    )
    try:
        _mt_resolve_targets(st, ports)
        # Fail on an unbootstrapped event log before review/workspace gates can
        # mask the actionable root cause (for example, a dependency cycle that
        # prevented finalize-tasks from creating lanes.json; #1589).
        _mt_current_event_lane(st)
        _mt_gather_review_facts(st)
        _mt_run_decision(st)
        _mt_run_pre_review_gate(st)
        _mt_complete_deferred_for_review_readiness(st)
        _mt_finalize_plan(st)
        _mt_execute(st, ports)
        _mt_output(st)
    except typer.Exit:
        raise
    except Exception as e:
        # Emit ErrorLogged event (T016).
        with contextlib.suppress(Exception):
            _tasks.emit_error_logged(
                error_type="runtime",
                error_message=str(e),
                wp_id=args.task_id,
                stack_trace=traceback.format_exc(),
                agent_id=args.agent,
            )
        diagnostic = e.to_diagnostic() if isinstance(e, EventPersistenceError) else None
        if diagnostic is not None and st.canonical_lane is not None:
            diagnostic["failed_event_to_lane"] = diagnostic.get("to_lane")
            diagnostic["to_lane"] = st.canonical_lane
            diagnostic["requested_lane"] = st.canonical_lane
        _tasks._output_error(args.json_output, str(e), diagnostic=diagnostic)
        raise typer.Exit(1) from None



# ===========================================================================
# WP09 (tasks-py-degod-wave2-01KWH9EQ / FR-008, IC-07): the final
# registration-shim sweep relocates the move_task-family stragglers that
# remained ``tasks.py``-resident after WP05 — the arbiter override pair
# (``_detect_arbiter_override`` / ``_run_arbiter_override``), the coord
# event-path probe (``_coord_status_events_path``), the event-field shaper
# (``_status_event_result_fields``) and the reviewer detector
# (``_detect_reviewer_name``). Moved VERBATIM except that patched seam
# symbols (``resolve_topology``, ``subprocess``, ``read_events_transactional``,
# ``console`` — research.md D7 / the ``__all__`` seam-infra names) are now
# routed through ``_tasks.<attr>`` (lazy in-function import) so every
# historical ``@patch("...agent.tasks.<sym>")`` keeps INTERCEPTING.
# ``tasks.py`` re-imports each name in the explicit ``as`` re-export form, so
# ``tasks.<name>`` stays a module attribute (NFR-002).
# ===========================================================================


def _coord_status_events_path(repo_root: Path, mission_slug: str) -> Path | None:
    """Return coord-worktree status event path when coord topology is active."""
    try:
        from specify_cli.coordination.workspace import CoordinationWorkspace
        from specify_cli.lanes.branch_naming import mission_dir_name, resolve_transaction_mid8
        from specify_cli.missions._read_path_resolver import candidate_feature_dir_for_mission
        from specify_cli.status import EVENTS_FILENAME

        # Topology resolver (FR-004): resolve the on-disk mid8 from the embedded
        # ``<slug>-<mid8>`` tail; "" for a legacy/flattened mission (no coord dir).
        mid8 = resolve_transaction_mid8(
            mission_slug, mission_id=None, mid8=None, coordination_branch=None
        )
        if not mid8:
            return None
        # Delegate the idempotent ``<slug>-<mid8>`` compose to the seam so the
        # inline endswith-dedup (the #1949 reinvention WP09 bans) lives only in
        # lanes.branch_naming (FR-010).
        mission_dir = mission_dir_name(mission_slug, mid8=mid8)
        coord_root = CoordinationWorkspace.worktree_path(repo_root, mission_slug, mid8)
        if not coord_root.exists():
            return None
        coord_feature_dir: Path = candidate_feature_dir_for_mission(coord_root, mission_dir)
        events_path: Path = coord_feature_dir / EVENTS_FILENAME
        return events_path
    except Exception:
        return None


def _status_event_result_fields(event: object | None) -> dict[str, str | None]:
    """Return JSON-safe status event fields for command output."""
    if event is None:
        return {"event_id": None, "to_lane": None}

    event_id = getattr(event, "event_id", None)
    if not isinstance(event_id, str):
        event_id = None

    to_lane = getattr(event, "to_lane", None)
    if to_lane is None:
        to_lane_value = None
    else:
        raw_value = getattr(to_lane, "value", to_lane)
        to_lane_value = raw_value if isinstance(raw_value, str) else str(raw_value)

    return {"event_id": event_id, "to_lane": to_lane_value}


def _detect_reviewer_name() -> str:
    """Detect reviewer name from git config, with safe fallback."""
    from specify_cli.cli.commands.agent import tasks as _tasks

    try:
        result = _tasks.subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or "unknown"
    except (_tasks.subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _detect_arbiter_override(
    feature_dir: Path,
    task_id: str,
    old_lane: Lane,
    target_canonical: str,
    force: bool,
) -> bool:
    """Return whether this move is an arbiter override (WP03 I/O for the core).

    A ``--force`` forward move from ``planned`` that follows a rejection event is
    an arbiter override. Detection reads the event log; the pure
    ``decide_transition`` core consumes the boolean result.
    """
    try:
        from specify_cli.review.arbiter import _is_arbiter_override
    except ImportError:
        return False
    return bool(
        _is_arbiter_override(feature_dir, task_id, old_lane, target_canonical, force)
    )


def _run_arbiter_override(
    *,
    feature_dir: Path,
    mission_slug: str,
    main_repo_root: Path,
    task_id: str,
    note_text: str | None,
    agent: str | None,
    json_output: bool,
) -> str | None:
    """Persist the arbiter decision and return the rejection's ``review_ref``.

    Executes the arbiter-override side effect once ``decide_transition`` has
    authorised it (``Emit.arbiter_forward``). Returns the derived ``review_ref``
    so the emit plan can link the forward event to the rejection it overrides.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    try:
        from specify_cli.review.arbiter import (
            create_arbiter_decision,
            parse_category_from_note,
            persist_arbiter_decision,
        )
    except ImportError:
        return None

    _arb_events = _tasks.read_events_transactional(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        repo_root=main_repo_root,
    )
    _arb_wp_events = [e for e in _arb_events if e.wp_id == task_id]
    _arb_latest = _arb_wp_events[-1] if _arb_wp_events else None
    _arb_review_ref = _arb_latest.review_ref if _arb_latest else None

    _arb_category, _arb_explanation = parse_category_from_note(note_text)
    _arb_actor = agent or "operator"
    arbiter_decision = create_arbiter_decision(
        arbiter_name=_arb_actor,
        category=_arb_category,
        explanation=_arb_explanation,
    )
    try:
        _arb_path = persist_arbiter_decision(
            feature_dir=feature_dir,
            wp_id=task_id,
            review_ref=_arb_review_ref,
            decision=arbiter_decision,
        )
        if not json_output:
            _tasks.console.print(f"[yellow]Arbiter override recorded:[/yellow] [bold]{_arb_category}[/bold] — {_arb_explanation}")
            _tasks.console.print(f"[dim]  Decision persisted: {_arb_path}[/dim]")
    except Exception as _arb_err:
        if not json_output:
            _tasks.console.print(f"[dim]Warning: Could not persist arbiter decision: {_arb_err}[/dim]")

    return _arb_review_ref
