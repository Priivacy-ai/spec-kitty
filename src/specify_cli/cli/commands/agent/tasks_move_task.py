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
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer

from mission_runtime import MissionArtifactKind
from specify_cli.agent_tasks_ports import (
    CommitArtifactResult,
    MissionHandle,
    TasksPorts,
)
from specify_cli.cli.commands.agent.tasks_finalize_validation import (
    _read_transactional_wp_lane,
)
from specify_cli.cli.commands.agent.tasks_materialization import (
    _collect_status_artifacts,
    _persist_review_artifact_override,
    _persist_review_artifact_override_in_coord,
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
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.core.paths import is_worktree_context
from specify_cli.core.utils import write_text_within_directory
from specify_cli.git import SafeCommitPathPolicyError
from specify_cli.missions._read_path_resolver import (
    _canonicalize_primary_read_handle,
)
from specify_cli.review import pre_review_gate
from specify_cli.review.baseline import BaselineTestResult
from specify_cli.status import (
    EVENTS_FILENAME,
    EventPersistenceError,
    Lane,
    ReviewResult,
    StatusEvent,
    TransitionRequest,
    resolve_lane_alias,
)
from specify_cli.task_utils import (
    WorkPackage,
    append_activity_log,
    build_document,
    ensure_lane,
    extract_scalar,
    set_scalar,
    split_frontmatter,
)
from specify_cli.upgrade.pre30_guard import Pre30LayoutError, check_pre30_layout

# coord-primary-partition-lock WP05 (T026 campsite, S1192): the WP-file write
# encoding recurs 3x across the split write/commit-recovery paths inside
# ``_mt_write_and_commit_wp_file`` / ``_mt_commit_wp_file`` (functions this WP
# edits) — hoisted per the standing Sonar directive rather than left
# duplicated across the write + both exception-recovery call sites.
_WP_FILE_WRITE_ENCODING = "utf-8"


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
    # --- phase E/F: emit + persist ---
    event: StatusEvent | None = None
    final_hop_actor: str | None = None


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
    st.current_agent = extract_scalar(st.wp.frontmatter, "agent")
    # Event-store write leg — the SAME coord husk as ``mt_feature_dir``.
    st.feature_dir = st.mt_feature_dir


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
    filtered = _tasks._filter_runtime_state_paths(status.stdout.strip())
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
        # #2335: on the implement→review handoff, recover a killed implementer's
        # uncommitted deliverables by committing them via the tool (auto-commit
        # policy) BEFORE the readiness guard runs — so recovery never dead-ends
        # demanding a manual worktree commit. Scoped to for_review ONLY:
        # approved/done deliverables are already committed (they passed review),
        # so a dirty tree there is a real signal the guard should still surface.
        # --force still bypasses; auto-commit-off defers to the guard.
        if st.target_lane == Lane.FOR_REVIEW and st.resolved_auto_commit and not st.force:
            _mt_commit_lane_deliverables(st)
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
    _persist_review_artifact_override(
        st.verdict_artifact_path,
        repo_root=st.main_repo_root,
        wp_id=st.task_id,
        actor=st.agent or "operator",
        reason=override_reason,
    )
    _persist_review_artifact_override_in_coord(
        st.verdict_artifact_path,
        coord_feature_dir=st.mt_feature_dir,
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
# ``derive_test_scope`` + ``run_scoped_tests_at_head`` + reused
# ``review/baseline.py`` JUnit parser/``diff_baseline``) into the
# ``for_review`` transition. Warn by default (NFR-001); opt-in block via
# config ``review.fail_on_pre_review_regression``; ``--force`` bypasses the
# block and is recorded on the transition's ``policy_metadata`` (FR-004).
#
# The two small composition helpers below (``_mt_pre_review_gate_verdict`` /
# ``_mt_pre_review_gate_with_override_scope``) call ONLY WP01's already-public
# primitives (``derive_test_scope``/``evaluate_pre_review_gate``,
# ``run_scoped_tests_at_head``, ``diff_baseline``, the ``GateVerdict``/
# ``ScopeResult`` dataclasses) — they live here, not in
# ``review/pre_review_gate.py``, because that module is WP01's owned surface
# (outside this WP's ``owned_files``): the override-scope tier needs a
# manually-built ``ScopeResult`` that ``derive_test_scope`` has no seam for,
# so its tail (head-run -> ``diff_baseline``) is mirrored rather than
# threaded through a WP01 signature change.

_PRE_REVIEW_CONFIG_KEY_BLOCK = "fail_on_pre_review_regression"
_PRE_REVIEW_CONFIG_KEY_TEST_COMMAND = "pre_review_test_command"
_PRE_REVIEW_FRONTMATTER_KEY = "pre_review_test_scope"


def _pre_review_gate_filter_groups() -> Mapping[str, tuple[str, ...]] | None:
    """Test seam: production always returns ``None``.

    ``None`` lets ``pre_review_gate.evaluate_pre_review_gate`` derive filter
    groups from the LIVE ``tests/architectural/_gate_coverage.py`` authority
    under the gate's own ``repo_root`` (WP01's FR-006 single-source
    invariant). Integration tests monkeypatch this (and its composite-routing
    sibling below) to inject a hermetic fixture map — the SAME override seam
    ``derive_test_scope`` already exposes for WP01's own unit tests — rather
    than building a throwaway ``tests/architectural/_gate_coverage.py`` in a
    fixture repo, which would silently resolve to the REAL repo's cached
    ``sys.modules`` entry instead (the exact staleness
    ``GateAuthoritiesUnavailable`` guards against).
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

    Mirrors ``tasks_shared._list_wp_branch_mission_specs_changes``'s
    merge-base pattern (``git merge-base HEAD <base>`` then
    ``git diff --name-only``), generalized to every changed file rather than
    a ``kitty-specs/`` subset — the gate scopes tests off the WP's FULL
    changed-file set, not just spec docs. Any git failure degrades to an
    empty tuple (folds into a cheap ``no_coverage`` warn), never a crash.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    merge_base_result = _tasks.subprocess.run(
        ["git", "merge-base", "HEAD", base_branch],
        cwd=str(worktree_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if merge_base_result.returncode != 0:
        return ()
    merge_base = merge_base_result.stdout.strip()
    if not merge_base:
        return ()
    diff_result = _tasks.subprocess.run(
        ["git", "diff", "--name-only", f"{merge_base}..HEAD"],
        cwd=str(worktree_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if diff_result.returncode != 0:
        return ()
    return tuple(line.strip() for line in diff_result.stdout.splitlines() if line.strip())


def _mt_pre_review_gate_with_override_scope(
    test_targets: tuple[str, ...],
    *,
    repo_root: Path,
    baseline: BaselineTestResult | None,
) -> pre_review_gate.GateVerdict:
    """Compose a verdict for an EXPLICIT override scope (FR-004).

    An override IS the test scope, by definition — WP01's census-derived
    ``derive_test_scope`` never runs for this precedence tier. The non-empty
    tail (head-run -> ``diff_baseline`` -> verdict) is NOT hand-mirrored here
    (pre-merge finding, #572/#1979/#2283: the mirrored copy left its
    ``NEW_FAILURES``/block/force + ``UNVERIFIED_BASELINE`` branches with zero
    coverage) — it REUSES ``pre_review_gate.evaluate_with_scope``, the exact
    same tested body ``evaluate_pre_review_gate`` itself drives. Only the
    empty-scope branch stays local: an override's empty list isn't a census
    exclusion, so ``ScopeResult.describe_empty_reason()``'s catch-all/
    composite-dir wording would be misleading — this keeps its own literal
    "override test scope is empty" reason instead.
    """
    scope = pre_review_gate.ScopeResult(
        test_targets=test_targets,
        matched_shard_groups=(),
        matched_composite_dirs=(),
        empty_cone_composite_dirs=(),
        excluded_scope_files=(),
    )
    if scope.is_empty:
        return pre_review_gate.GateVerdict(
            outcome=pre_review_gate.GateOutcome.NO_COVERAGE,
            scope=scope,
            reason="override test scope is empty",
        )
    return pre_review_gate.evaluate_with_scope(scope, repo_root=repo_root, baseline=baseline)


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


def _mt_pre_review_gate_verdict(
    *,
    changed_files: tuple[str, ...],
    override_targets: tuple[str, ...] | None,
    gate_repo_root: Path,
    baseline: BaselineTestResult | None,
) -> pre_review_gate.GateVerdict:
    """Resolve the FR-004 precedence tier, then evaluate the gate.

    An empty ``changed_files`` set with no override short-circuits BEFORE
    even attempting to load the live gate-coverage authorities — keeping the
    hook cheap for the common "nothing changed / no lane workspace"
    case (WP02 spec explicit requirement), distinct from
    :class:`pre_review_gate.GateAuthoritiesUnavailable` (a real authority-load
    failure, folded into the SAME ``no_coverage`` shape once a non-empty
    changed-file set actually attempts derivation).
    """
    if override_targets is not None:
        return _mt_pre_review_gate_with_override_scope(
            override_targets, repo_root=gate_repo_root, baseline=baseline,
        )
    if not changed_files:
        return _mt_empty_scope_verdict("no changed files detected for this WP — skipping the gate cheaply")
    try:
        return pre_review_gate.evaluate_pre_review_gate(
            changed_files,
            repo_root=gate_repo_root,
            baseline=baseline,
            filter_groups=_pre_review_gate_filter_groups(),
            composite_routing=_pre_review_gate_composite_routing(),
        )
    except pre_review_gate.GateAuthoritiesUnavailable as exc:
        return _mt_empty_scope_verdict(
            f"gate authorities unavailable — unverified: {exc}",
            excluded_scope_files=tuple(changed_files),
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
    return "[dim]Pre-review regression gate: no new failures[/dim]"


def _mt_pre_review_gate_block_message(verdict: pre_review_gate.GateVerdict) -> str:
    """The refusal message when the opt-in block engages (FR-001)."""
    nodeids = ", ".join(failure.test for failure in verdict.new_failures[:5])
    more = f" (+{len(verdict.new_failures) - 5} more)" if len(verdict.new_failures) > 5 else ""
    return (
        "Pre-review regression gate BLOCKED this for_review move: "
        f"{len(verdict.new_failures)} new failure(s) introduced — {nodeids}{more}. "
        "Fix the regression, or re-run with --force to override (recorded in the transition evidence)."
    )


def _mt_run_pre_review_gate(st: _MoveTaskState) -> None:
    """T004 (FR-001/NFR-001): warn-default/opt-in-block pre-review regression gate.

    Runs ONLY for ``for_review`` moves, called right after ``_mt_run_decision``
    in ``_do_move_task`` — i.e. AFTER every pre-existing guard has cleared and
    BEFORE the transition is emitted/committed (``_mt_finalize_plan`` /
    ``_mt_execute``). A block raises ``typer.Exit(1)`` here, before any state
    is committed, so existing move-task guard behavior and ordering are
    entirely untouched — this hook is purely additive after the established
    guard sequence.

    Never crashes the transition: an unresolvable workspace, unavailable
    gate-coverage authorities, or any other internal failure all degrade to
    a ``no_coverage`` warn (never a hard block) — the ONLY non-local exit
    this function can take is the deliberate opt-in block below.
    """
    if st.target_lane != Lane.FOR_REVIEW:
        return
    from specify_cli.cli.commands.agent import tasks as _tasks

    assert st.wp is not None
    try:
        worktree_path = _mt_resolve_pre_review_workspace(st)
        changed_files = (
            _mt_pre_review_changed_files(worktree_path, st.target_branch)
            if worktree_path is not None
            else ()
        )
        gate_repo_root = worktree_path or st.main_repo_root
        override_targets = _mt_pre_review_scope_override(st.wp.frontmatter, st.main_repo_root)
        wp_slug = _resolve_wp_slug(st.main_repo_root, st.mission_slug, st.task_id)
        baseline_path = st.feature_dir / "tasks" / wp_slug / "baseline-tests.json"
        baseline = BaselineTestResult.load(baseline_path)
        verdict = _mt_pre_review_gate_verdict(
            changed_files=changed_files,
            override_targets=override_targets,
            gate_repo_root=gate_repo_root,
            baseline=baseline,
        )
    except Exception as exc:  # An internal gate failure must never break move-task (FR-003 spirit).
        verdict = _mt_empty_scope_verdict(f"pre-review gate evaluation failed — unverified: {exc}")

    block_enabled = _mt_pre_review_block_enabled(st.main_repo_root)
    would_block = block_enabled and verdict.outcome is pre_review_gate.GateOutcome.NEW_FAILURES
    force_bypassed = would_block and st.force
    blocked = would_block and not force_bypassed
    st.pre_review_gate_metadata = _mt_pre_review_gate_metadata(
        verdict, block_enabled=block_enabled, blocked=blocked, force_bypassed=force_bypassed,
    )

    if not st.json_output:
        _tasks.console.print(_mt_pre_review_gate_console_warning(verdict, block_enabled=block_enabled))

    if blocked:
        _tasks._output_error(st.json_output, _mt_pre_review_gate_block_message(verdict))
        raise typer.Exit(1)


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
    if decision.planned_rollback or decision.arbiter_forward:
        st.emit_plan = build_transition_plan(
            old_lane=str(st.old_lane),
            target_lane=str(st.target_lane),
            force=st.force,
            review_feedback_pointer=st.review_feedback_pointer,
            arb_review_ref=st.arb_review_ref,
            note_text=st.note_text,
        )


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
        event = ports.coord.commit_status(
            TransitionRequest(
                feature_dir=st.feature_dir,
                mission_slug=st.mission_slug,
                wp_id=st.task_id,
                to_lane=target,
                actor=hop_actor,
                force=emit_force,
                reason=emit_reason,
                evidence=st.evidence_dict if target in (Lane.APPROVED, Lane.DONE) else None,
                policy_metadata=(
                    {"pre_review_gate": st.pre_review_gate_metadata}
                    if target == Lane.FOR_REVIEW and st.pre_review_gate_metadata is not None
                    else None
                ),
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
            ),
            capability=GuardCapability.STANDARD,
        ).event
        final_hop_actor = hop_actor
        # review_ref only applies to the (first) rollback hop, never forward hops.
        emit_review_ref = None
    st.event = event
    st.final_hop_actor = final_hop_actor


# --- phase F: persist the WP file + primary commit via commit_artifact --------


def _mt_resolve_status_placement_ref(st: _MoveTaskState) -> str | None:
    """Best-effort STATUS_STATE placement lookup via the ONE seam authority.

    coord-primary-partition-lock WP05 (T024, FR-004/FR-005, C-001): the
    bookkeeping write-cluster's placement question is answered by
    ``placement_seam(...).write_target(MissionArtifactKind.STATUS_STATE)`` —
    the single kind-aware authority (contracts/seam-api.md H-1) — rather than
    assembled from ``st.target_branch``. ``st.target_branch`` is the
    CURRENT-CHECKOUT branch ``_ensure_target_branch_checked_out`` resolves
    (its own docstring: "respects user's current branch"), NOT necessarily
    the mission's coord-routed STATUS_STATE ref — under coordination topology
    the two genuinely diverge.

    Degrades to ``None`` on any resolution failure (a pre-meta bootstrap
    window, an ad-hoc fixture, or an unresolvable mission handle) — this is
    observability, never a gate (mirrors ``_mt_run_pre_review_gate``'s
    degrade-never-crash discipline, #2438); the primary WP-file commit is
    unaffected either way.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    try:
        target = _tasks.placement_seam(st.main_repo_root, st.mission_slug).write_target(
            MissionArtifactKind.STATUS_STATE
        )
    except Exception:
        return None
    return target.ref


def _mt_wp_commit_success_message(st: _MoveTaskState, status_placement_ref: str | None) -> str:
    """The 'committed' console line, enriched when STATUS_STATE diverges from
    the primary ``target_branch`` (coord-topology missions).

    Purely additive: a ``None`` (unresolvable) or matching ref reproduces the
    ORIGINAL message verbatim — non-regression for the plain/flat-topology
    path (test_patched_protection_policy_intercepts_commit_wp_file sibling).
    """
    message = f"[cyan]→ Committed status change to {st.target_branch} branch[/cyan]"
    if status_placement_ref and status_placement_ref != st.target_branch:
        message += f" [dim](status bookkeeping: {status_placement_ref})[/dim]"
    return message


def _mt_write_and_commit_wp_file(
    st: _MoveTaskState,
    ports: TasksPorts,
    updated_doc: str,
    commit_msg: str,
    skip_target_commit: bool,
) -> tuple[bool, bool, CommitArtifactResult | None, str | None]:
    """Resolve STATUS_STATE placement, then write the WP file + route the primary commit.

    coord-primary-partition-lock WP05 (T023/T024): extracted out of
    ``_mt_commit_wp_file`` for complexity headroom (C901 was 13) BEFORE adding
    seam routing — placement resolution (:func:`_mt_resolve_status_placement_ref`)
    runs FIRST and unconditionally (composes with, never races, the
    ``skip_target_commit`` pre-gate below), then the skip/write/commit branch
    that was previously inline here runs unchanged.

    #2155 (FR-002 / T010): bundle ONLY primary-partition artifacts into the
    ``WORK_PACKAGE_TASK`` commit; the coord-owned status files are already
    committed to the coordination branch by the transactional emitter.

    Returns:
        ``(file_written, commit_success, router_result, status_placement_ref)``.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    assert st.wp is not None
    wp = st.wp
    status_placement_ref = _mt_resolve_status_placement_ref(st)

    if skip_target_commit:
        if not st.json_output:
            _tasks.console.print(
                f"[dim]Note: WP file update not committed to '{st.target_branch}' "
                "(protected branch, coord topology active). "
                "The status transition is committed to the coordination branch "
                "and is authoritative.[/dim]"
            )
        return False, False, None, status_placement_ref

    write_text_within_directory(
        wp.path, updated_doc, root=st.main_repo_root, encoding=_WP_FILE_WRITE_ENCODING
    )
    status_artifacts = _tasks._primary_bundle_status_artifacts(
        st.main_repo_root,
        st.mission_slug,
        _collect_status_artifacts(st.feature_dir),
    )
    # The WP file is WORK_PACKAGE_TASK (primary): route the commit through
    # the coord WRITE ``commit_artifact`` capability (over the ONE canonical
    # ``commit_for_mission`` entry point). The router owns placement
    # resolution AND the protected-primary refusal.
    router_result = ports.coord.commit_artifact(
        MissionHandle(repo_root=st.main_repo_root, mission_slug=st.mission_slug),
        (wp.path.resolve(), *status_artifacts),
        commit_msg,
        kind=MissionArtifactKind.WORK_PACKAGE_TASK,
        policy=_tasks.ProtectionPolicy.resolve(st.main_repo_root),
    )
    commit_success = router_result.status == "committed"
    return True, commit_success, router_result, status_placement_ref


def _mt_commit_wp_file(
    st: _MoveTaskState,
    ports: TasksPorts,
    updated_doc: str,
    agent_name: str,
    skip_target_commit: bool,
) -> None:
    """Auto-commit branch: write the WP file and route the primary commit.

    #2155 (FR-002 / T010): bundle ONLY primary-partition artifacts into the
    ``WORK_PACKAGE_TASK`` commit; the coord-owned status files are already committed
    to the coordination branch by the transactional emitter. A guard refusal folded
    into ``status="error"`` is surfaced, never swallowed.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    assert st.wp is not None
    wp = st.wp
    spec_number = st.mission_slug.split("-")[0] if "-" in st.mission_slug else st.mission_slug
    commit_msg = f"chore: Move {st.task_id} to {st.target_lane} on spec {spec_number}"
    if agent_name != "unknown":
        commit_msg += f" [{agent_name}]"
    file_written = False
    try:
        file_written, commit_success, router_result, status_placement_ref = (
            _mt_write_and_commit_wp_file(st, ports, updated_doc, commit_msg, skip_target_commit)
        )
        if commit_success:
            if not st.json_output:
                _tasks.console.print(_mt_wp_commit_success_message(st, status_placement_ref))
        elif not skip_target_commit and router_result is not None:
            # #2155: do NOT swallow a router error as a soft "Failed to auto-commit".
            diagnostic = router_result.diagnostic
            detail = f": {diagnostic}" if diagnostic else ""
            if not st.json_output:
                _tasks.console.print(
                    f"[yellow]Warning:[/yellow] WP-file auto-commit "
                    f"did not land ({router_result.status}){detail}"
                )
    except SafeCommitPathPolicyError:
        # #2155: a wrong-surface guard refusal is a real defect — re-raise, never hide.
        if not file_written:
            write_text_within_directory(
                wp.path, updated_doc, root=st.main_repo_root, encoding=_WP_FILE_WRITE_ENCODING
            )
        raise
    except Exception as e:
        if not file_written:
            write_text_within_directory(
                wp.path, updated_doc, root=st.main_repo_root, encoding=_WP_FILE_WRITE_ENCODING
            )
        if not st.json_output:
            _tasks.console.print(f"[yellow]Warning:[/yellow] Auto-commit skipped: {e}")


def _mt_persist_tracker_refs(st: _MoveTaskState, skip_target_commit: bool) -> None:
    """T040 / FR-011: persist ``--tracker-ref`` values into the WP frontmatter."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    assert st.wp is not None
    if not (st.tracker_ref_values and not skip_target_commit):
        return
    try:
        from specify_cli.frontmatter import write_frontmatter as _write_fm
        from specify_cli.status import read_wp_frontmatter as _read_wp_fm

        wp_meta, body = _read_wp_fm(st.wp.path)
        existing = list(wp_meta.tracker_refs or [])
        merged = sorted(set(existing) | set(st.tracker_ref_values))
        if merged != existing:
            updated = wp_meta.update(tracker_refs=merged)
            _write_fm(st.wp.path, updated.model_dump(exclude_none=True), body)
    except Exception as _tr_exc:  # pragma: no cover - defensive
        if not st.json_output:
            _tasks.console.print(
                f"[yellow]Warning:[/yellow] Failed to persist --tracker-ref: {_tr_exc}"
            )


def _mt_persist_wp_file(st: _MoveTaskState, ports: TasksPorts) -> None:
    """Apply operational frontmatter + history, then write/commit the WP file."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    assert st.wp is not None and st.decision is not None
    wp = st.wp
    wp_content = wp.path.read_text(encoding="utf-8-sig")
    updated_front, updated_body, updated_padding = split_frontmatter(wp_content)
    if st.assignee:
        updated_front = set_scalar(updated_front, "assignee", st.assignee)
    if st.agent:
        updated_front = set_scalar(updated_front, "agent", st.agent)
    if st.shell_pid:
        updated_front = set_scalar(updated_front, "shell_pid", st.shell_pid)
    timestamp = datetime.now(UTC).strftime(_tasks.UTC_SECOND_TIMESTAMP_FORMAT)
    agent_name = st.final_hop_actor or "unknown"
    shell_pid_val = st.shell_pid or extract_scalar(updated_front, "shell_pid") or ""
    note_text = st.note_text or f"Moved to {st.target_lane}"
    shell_part = f"shell_pid={shell_pid_val} – " if shell_pid_val else ""
    history_entry = f"- {timestamp} – {agent_name} – {shell_part}{note_text}"
    updated_body = append_activity_log(updated_body, history_entry)
    updated_doc = build_document(updated_front, updated_body, updated_padding)
    # WP03: the primary-commit skip is DRIVEN by the core decision, not the raw fact.
    skip_target_commit = st.decision.skip_primary
    if st.resolved_auto_commit:
        _mt_commit_wp_file(st, ports, updated_doc, agent_name, skip_target_commit)
    else:
        write_text_within_directory(
            wp.path, updated_doc, root=st.main_repo_root, encoding="utf-8"
        )
    _mt_persist_tracker_refs(st, skip_target_commit)


# --- phase G/H: review-lock release + result output --------------------------


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


def _do_move_task(
    task_id: str,
    to: str,
    mission: str | None,
    agent: str | None,
    assignee: str | None,
    shell_pid: str | None,
    note: str | None,
    review_feedback_file: Path | None,
    approval_ref: str | None,
    reviewer: str | None,
    self_review_fallback: bool,
    intended_reviewer: str | None,
    reviewer_failure_reason: str | None,
    done_override_reason: str | None,
    force: bool,
    tracker_ref: list[str] | None,
    skip_review_artifact_check: bool,
    auto_commit: bool | None,
    json_output: bool,
    *,
    ports: TasksPorts | None = None,
) -> None:
    """Orchestrate ``move-task`` over the WP03 core + WP02 ports (C-005 seam).

    ``ports=None`` builds the production bundle (coord router bound to this
    module's patchable symbols). Tests inject a Fake bundle to observe the executed
    side-effects (T029). The phase helpers run in the SAME order as the original
    single body: resolve → gather → decide → finalize → execute → output.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    ports = ports or _default_move_task_ports()
    st = _MoveTaskState(
        task_id=task_id,
        to=to,
        mission=mission,
        agent=agent,
        assignee=assignee,
        shell_pid=shell_pid,
        note=note,
        review_feedback_file=review_feedback_file,
        approval_ref=approval_ref,
        reviewer=reviewer,
        self_review_fallback=self_review_fallback,
        intended_reviewer=intended_reviewer,
        reviewer_failure_reason=reviewer_failure_reason,
        done_override_reason=done_override_reason,
        force=force,
        tracker_ref=tracker_ref,
        skip_review_artifact_check=skip_review_artifact_check,
        auto_commit=auto_commit,
        json_output=json_output,
    )
    try:
        _mt_resolve_targets(st, ports)
        _mt_gather_review_facts(st)
        _mt_run_decision(st)
        _mt_run_pre_review_gate(st)
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
                wp_id=task_id,
                stack_trace=traceback.format_exc(),
                agent_id=agent,
            )
        diagnostic = e.to_diagnostic() if isinstance(e, EventPersistenceError) else None
        if diagnostic is not None and st.canonical_lane is not None:
            diagnostic["failed_event_to_lane"] = diagnostic.get("to_lane")
            diagnostic["to_lane"] = st.canonical_lane
            diagnostic["requested_lane"] = st.canonical_lane
        _tasks._output_error(json_output, str(e), diagnostic=diagnostic)
        raise typer.Exit(1) from None



# ===========================================================================
# WP09 (tasks-py-degod-wave2-01KWH9EQ / FR-008, IC-07): the final
# registration-shim sweep relocates the move_task-family stragglers that
# remained ``tasks.py``-resident after WP05 — the arbiter override pair
# (``_detect_arbiter_override`` / ``_run_arbiter_override``), the #2155
# mixed-bundle partition (``_primary_bundle_status_artifacts``), the coord
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


def _primary_bundle_status_artifacts(
    main_repo_root: Path, mission_slug: str, status_artifacts: list[Path]
) -> list[Path]:
    """Drop coord-owned status files from a PRIMARY-surface auto-commit bundle.

    #2155 (FR-002 / T010): the ``move_task`` auto-commit routes the WP file (a
    ``WORK_PACKAGE_TASK`` / primary-partition artifact) through
    ``commit_for_mission(kind=WORK_PACKAGE_TASK)``, which commits on the PRIMARY
    repo root. Under coordination topology the coord-owned status files
    (``status.events.jsonl`` / ``status.json``) resolved by
    :func:`_collect_status_artifacts` live UNDER ``.worktrees/`` (the coord
    worktree) and are ALREADY committed to the coordination branch by the
    transactional emitter (``emit_status_transition_transactional``). Staging
    those ``.worktrees/`` paths from the primary root trips the
    ``SafeCommitPathPolicyError`` guard (#1887), which ``commit_for_mission``
    folds into a ``status="error"`` result — leaving the working tree dirty and
    the WP file uncommitted (the surviving #2155 residual).

    The single canonical partition (``COORD_OWNED_STATUS_FILES``, the same set
    ``implement.py:_exclude_coord_owned`` keys on) excludes coord-owned status
    under coord topology only. On a flat/legacy mission the status files ARE
    canonical on PRIMARY, so they stay in the bundle (the never-divergent
    flat-topology behaviour the WP02 stored topology resolves transparently).
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    if not _tasks.routes_through_coordination(_tasks.resolve_topology(main_repo_root, mission_slug)):
        return status_artifacts
    from specify_cli.status import COORD_OWNED_STATUS_FILES

    return [p for p in status_artifacts if p.name not in COORD_OWNED_STATUS_FILES]


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
