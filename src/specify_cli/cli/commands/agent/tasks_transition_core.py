"""Pure transition-decision core for ``agent tasks move-task`` (WP03).

This module lifts ``move_task``'s **transition decision** out of the interleaved
command body into ONE pure function, :func:`decide_transition`, plus the pure
lane-hop shaper :func:`build_transition_plan` it delegates to. It is a
behaviour-preserving (pure-parity) extraction: it **reproduces move_task's exact
current behaviour** (research D4 / FR-004 / NFR-001) — including the pre-existing
skip-vs-refuse divergence that ``#2300`` defers, and the OLD
partial-write-on-refusal *timing* of the two proceed-side-effect persists
(review-artifact override and arbiter decision). The pure core owns the
decision; the imperative SHELL still executes those two persists at their
ORIGINAL guard positions — the override persist inside the rejected-verdict
proceed arm (before feedback/subtasks/review-currency/done-ancestry/issue-matrix)
and the arbiter persist before the issue-matrix guard — so a later guard's
refusal (exit 1) still leaves the OLD partial write on disk, exactly as the
un-refactored command did. Those two positions are surfaced to the shell as pure
early signals (:func:`override_persist_signal`, :func:`arbiter_persist_signal`)
computed from early facts alone. This module does not reconcile or unify
behaviour.

Design (functional core / imperative shell):

* The orchestrator (``move_task``) performs all filesystem / git / clock reads
  and passes the resulting FACTS in a frozen :class:`MoveTaskRequest`.
* :func:`decide_transition` is **pure** — no filesystem, git, status-emission,
  rendering, or clock access — and returns a :data:`TransitionOutcome`:
  - :class:`RefuseExit1` — a guard failed; the shell prints the error (plus any
    ``console_warning`` lines) and exits 1.
  - :class:`Emit` — the transition proceeds; ``skip_primary`` encodes the coord
    skip-exit-0 arm (the WP-file commit to the protected primary is skipped, the
    coord emission still happens), and the proceed-authorisation flags tell the
    shell which side effects (review-artifact override, planned-rollback review
    cycle, arbiter decision) to execute before the emit loop.
* The two DURABLE proceed persists (override + arbiter) are additionally gated by
  the pure :func:`override_persist_signal` / :func:`arbiter_persist_signal`
  helpers, which the shell consults to fire each persist at its OLD guard
  position — before the later guards that could still refuse — preserving the
  original partial-write-on-refusal behaviour.

The coord skip arm is encoded as ``Emit(skip_primary=True)`` — **not** a no-emit
terminal — because ``move_task`` still emits the transition to the coordination
branch and exits 0 in that arm (spec §Behavior-parity guard). ``move_task`` has
no exit-0-without-emit path, so no separate ``SkipExit0`` terminal is minted here.

The guard sequence mirrors the live command exactly (order is load-bearing — the
first failing guard wins). Each guard is a small pure helper so the aggregate
complexity stays within the ≤15 ceiling (NFR-003) and every branch is directly
unit-testable (NFR-002).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from specify_cli.cli.commands.agent.tasks_finalize_validation import (
    _is_backward_transition,
    _lane_targets_for_emit,
)
from specify_cli.cli.commands.agent.tasks_parsing_validation import (
    _self_review_fallback_option_error,
)
from specify_cli.status import Lane, resolve_lane_alias

# Terminal lanes that build approval evidence + run the rejected-verdict guard.
_APPROVAL_LANES: tuple[str, ...] = (Lane.APPROVED, Lane.DONE)
# Lanes whose forward move validates subtasks + review currency.
_REVIEW_GATE_LANES: tuple[str, ...] = (Lane.FOR_REVIEW, Lane.APPROVED, Lane.DONE)


# ---------------------------------------------------------------------------
# Request (pre-read facts) + outcome value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MoveTaskRequest:
    """Every fact ``decide_transition`` needs — all resolved by the shell.

    The shell (``move_task``) performs the I/O (dir resolution, event reads,
    review-artifact reads, git ancestry, protection-policy checks, reviewer
    auto-detection) and freezes the results here so the decision is pure.
    """

    task_id: str
    target_lane: str
    old_lane: str
    force: bool
    agent: str | None
    current_agent: str | None
    note: str | None
    auto_commit: bool
    target_branch: str
    skip_target_branch_commit: bool
    tracker_ref_values: tuple[str, ...]
    assignee: str | None
    shell_pid: str | None
    self_review_fallback: bool
    intended_reviewer: str | None
    reviewer_failure_reason: str | None
    # Pre-computed protected-branch refusal string (None when not applicable).
    protected_error: str | None
    # Latest review-cycle verdict + artifact name (APPROVAL_LANES only).
    review_verdict: str | None
    review_artifact_name: str | None
    skip_review_artifact_check: bool
    # Review-feedback file facts (resolved absolute path shown in messages).
    feedback_provided: bool
    feedback_source: str | None
    feedback_exists: bool
    feedback_is_file: bool
    feedback_content: str | None
    # Review-gate facts (REVIEW_GATE_LANES).
    unchecked_subtasks: tuple[str, ...]
    review_ready: bool
    review_guidance: tuple[str, ...]
    # done-ancestry facts (DONE only).
    done_execution_mode: str | None
    done_merged: bool
    done_merge_msg: str
    done_override_reason: str | None
    # issue-matrix approval blocker (APPROVAL_LANES only; None when clear).
    issue_matrix_blocker: str | None
    # Arbiter-override detection (I/O in the shell).
    is_arbiter_override: bool
    # Approval evidence inputs (reviewer auto-detected / approval-ref defaulted).
    effective_reviewer: str | None
    effective_approval_ref: str | None


@dataclass(frozen=True)
class TransitionPlan:
    """The pure lane-hop shape the emit loop executes."""

    canonical_lane: str
    transition_targets: list[str]
    emit_force: bool
    emit_reason: str | None
    emit_review_ref: str | None


@dataclass(frozen=True)
class RefuseExit1:
    """A guard failed: the shell prints ``error`` (+ warning) and exits 1."""

    error: str
    diagnostic: dict[str, Any] | None = None
    console_warning: tuple[str, ...] = ()


@dataclass(frozen=True)
class Emit:
    """The transition proceeds; the shell executes the plan + authorised effects."""

    plan: TransitionPlan
    skip_primary: bool
    evidence_dict: dict[str, Any] | None
    note_text: str | None
    authorize_review_override: bool = False
    planned_rollback: bool = False
    arbiter_forward: bool = False
    done_override_note: bool = False


TransitionOutcome = Emit | RefuseExit1


# ---------------------------------------------------------------------------
# Pure lane-hop shaper (arbiter / force / backward / coord skip inputs)
# ---------------------------------------------------------------------------


def build_transition_plan(
    *,
    old_lane: str,
    target_lane: str,
    force: bool,
    review_feedback_pointer: str | None,
    arb_review_ref: str | None,
    note_text: str | None,
) -> TransitionPlan:
    """Compute the canonical lane, hop list, force flag, reason, and review_ref.

    Reproduces ``move_task`` lines building ``emit_review_ref`` / ``canonical_lane``
    / ``emit_reason`` / ``emit_force`` / the backward-rewind auto-promotion /
    ``transition_targets`` — verbatim (FR-004). ``review_feedback_pointer`` and
    ``arb_review_ref`` are threaded in by the shell after it runs the
    planned-rollback / arbiter side effects (they are ``None`` on the happy path).
    """
    canonical_lane = resolve_lane_alias(target_lane)

    emit_review_ref: str | None = None
    if target_lane == Lane.PLANNED and review_feedback_pointer:
        emit_review_ref = review_feedback_pointer
    elif (
        old_lane == Lane.FOR_REVIEW
        and resolve_lane_alias(target_lane) in (Lane.IN_PROGRESS, Lane.PLANNED)
        and force
    ):
        emit_review_ref = "force-override"

    # Arbiter override reuses the rejection's review_ref when no base ref applies.
    if arb_review_ref and emit_review_ref is None:
        emit_review_ref = arb_review_ref

    emit_reason: str | None = note_text if note_text else None
    if force and not emit_reason:
        emit_reason = f"Force move to {target_lane}"

    emit_force = force
    if not emit_reason:
        emit_reason = (
            f"Force move to {target_lane}"
            if force
            else f"move-task: {old_lane} -> {target_lane}"
        )

    if not force and _is_backward_transition(old_lane, canonical_lane):
        emit_force = True
        original_reason = (
            None
            if emit_reason is None or emit_reason.startswith("move-task: ")
            else emit_reason
        )
        reason_parts = [f"backward rewind: {old_lane} -> {canonical_lane}"]
        if review_feedback_pointer and review_feedback_pointer != "force-override":
            reason_parts.append(review_feedback_pointer)
        if original_reason:
            reason_parts.append(original_reason)
        emit_reason = ": ".join(reason_parts)

    transition_targets = [canonical_lane]
    if not emit_force:
        transition_targets = _lane_targets_for_emit(old_lane, canonical_lane)

    return TransitionPlan(
        canonical_lane=canonical_lane,
        transition_targets=transition_targets,
        emit_force=emit_force,
        emit_reason=emit_reason,
        emit_review_ref=emit_review_ref,
    )


# ---------------------------------------------------------------------------
# Guard helpers (pure; each returns a RefuseExit1 or None). Order matters.
# ---------------------------------------------------------------------------


def _guard_self_review(req: MoveTaskRequest) -> RefuseExit1 | None:
    error = _self_review_fallback_option_error(
        enabled=req.self_review_fallback,
        target_lane=req.target_lane,
        force=req.force,
        intended_reviewer=req.intended_reviewer,
        failure_reason=req.reviewer_failure_reason,
    )
    return RefuseExit1(error) if error else None


def _guard_unsupported_skip_metadata(req: MoveTaskRequest) -> RefuseExit1 | None:
    if not req.skip_target_branch_commit:
        return None
    unsupported: list[str] = []
    if req.tracker_ref_values:
        unsupported.append("tracker_refs")
    if req.assignee:
        unsupported.append("assignee")
    if req.shell_pid:
        unsupported.append("shell_pid")
    if req.note:
        unsupported.append("activity_log")
    if not unsupported:
        return None
    return RefuseExit1(
        "Cannot persist WP frontmatter/activity metadata on protected "
        f"branch '{req.target_branch}' while coordination topology is active: "
        f"{', '.join(unsupported)}. Rerun from an allowed "
        "branch, omit those metadata flags, or use --no-auto-commit.",
        diagnostic={
            "error": "WP_METADATA_UNSUPPORTED_ON_PROTECTED_COORD_BRANCH",
            "target_branch": req.target_branch,
            "fields": unsupported,
        },
    )


def _guard_protected_branch(req: MoveTaskRequest) -> RefuseExit1 | None:
    if req.auto_commit and not req.skip_target_branch_commit and req.protected_error:
        return RefuseExit1(req.protected_error)
    return None


def _guard_agent_ownership(req: MoveTaskRequest) -> RefuseExit1 | None:
    if not (
        req.current_agent
        and req.agent
        and req.current_agent != req.agent
        and not req.force
    ):
        return None
    warning = (
        "",
        "[bold red]⚠️  AGENT OWNERSHIP WARNING[/bold red]",
        f"   {req.task_id} is currently assigned to: [cyan]{req.current_agent}[/cyan]",
        f"   You are trying to move it as: [yellow]{req.agent}[/yellow]",
        "",
        "   If you are the correct agent, use --force to override.",
        "   If not, you may be modifying the wrong WP!",
        "",
    )
    return RefuseExit1(
        f"Agent mismatch: {req.task_id} is assigned to '{req.current_agent}', "
        f"not '{req.agent}'. Use --force to override.",
        console_warning=warning,
    )


def _guard_rejected_verdict(req: MoveTaskRequest) -> RefuseExit1 | None:
    """Refuse arms of the rejected-verdict guard (APPROVAL_LANES only).

    The PROCEED-with-override arm is not a refusal — it is signalled by
    :func:`_authorize_review_override`.
    """
    if req.target_lane not in _APPROVAL_LANES or req.review_artifact_name is None:
        return None
    if req.review_verdict is None:
        return RefuseExit1(
            f"{req.task_id} {req.review_artifact_name} has no parseable review verdict.\n"
            "Repair the review artifact before approving or marking done."
        )
    if req.review_verdict == "rejected":
        if not req.skip_review_artifact_check:
            return RefuseExit1(
                f"{req.task_id} has a rejected review artifact ({req.review_artifact_name}). "
                "Re-run with --skip-review-artifact-check --note <reason> "
                "to record an arbiter override."
            )
        if not (req.note.strip() if isinstance(req.note, str) else ""):
            return RefuseExit1(
                "--skip-review-artifact-check requires --note so override evidence is durable."
            )
    return None


def _authorize_review_override(req: MoveTaskRequest) -> bool:
    """True when the rejected-verdict override arm proceeds (persist evidence)."""
    return (
        req.target_lane in _APPROVAL_LANES
        and req.review_artifact_name is not None
        and req.review_verdict == "rejected"
        and req.skip_review_artifact_check
        and bool(req.note.strip() if isinstance(req.note, str) else "")
    )


def _guard_feedback_file(req: MoveTaskRequest) -> RefuseExit1 | None:
    if not req.feedback_provided:
        return None
    if not req.feedback_exists:
        return RefuseExit1(f"Review feedback file not found: {req.feedback_source}")
    if not req.feedback_is_file:
        return RefuseExit1(f"Review feedback path is not a file: {req.feedback_source}")
    return None


def _guard_planned_rollback(req: MoveTaskRequest) -> RefuseExit1 | None:
    if req.target_lane != Lane.PLANNED:
        return None
    if not (req.feedback_provided and req.feedback_exists and req.feedback_is_file):
        return RefuseExit1(
            f"❌ Moving {req.task_id} to 'planned' requires review feedback.\n\n"
            "Please provide feedback:\n"
            "  1. Create feedback file: echo '**Issue**: Description' > feedback.md\n"
            f"  2. Run: spec-kitty agent tasks move-task {req.task_id} "
            "--to planned --review-feedback-file feedback.md\n\n"
            "This requirement cannot be bypassed with --force."
        )
    if not (req.feedback_content or "").strip():
        return RefuseExit1(f"Review feedback file is empty: {req.feedback_source}")
    return None


def _guard_subtasks(req: MoveTaskRequest) -> RefuseExit1 | None:
    if req.target_lane not in _REVIEW_GATE_LANES or req.force:
        return None
    if not req.unchecked_subtasks:
        return None
    error = f"Cannot move {req.task_id} to {req.target_lane} - unchecked subtasks:\n"
    for task in req.unchecked_subtasks:
        error += f"  - [ ] {task}\n"
    error += "\nMark these complete first:\n"
    for task in req.unchecked_subtasks[:3]:
        error += f"  spec-kitty agent tasks mark-status {task} --status done\n"
    error += "\nOr use --force to override (not recommended)"
    return RefuseExit1(error)


def _guard_review_currency(req: MoveTaskRequest) -> RefuseExit1 | None:
    if req.target_lane not in _REVIEW_GATE_LANES or req.review_ready:
        return None
    error = f"Cannot move {req.task_id} to {req.target_lane}\n\n"
    error += "\n".join(req.review_guidance)
    if not req.force:
        error += "\n\nOr use --force to override (not recommended)"
    return RefuseExit1(error)


def _guard_done_ancestry(req: MoveTaskRequest) -> RefuseExit1 | None:
    if req.target_lane != Lane.DONE or req.done_execution_mode != "code_change":
        return None
    if req.done_merged:
        return None
    if _done_override_reason(req):
        return None
    return RefuseExit1(
        f"Cannot move {req.task_id} to done without verified merge ancestry.\n"
        f"{req.done_merge_msg}\n"
        f"If review just passed, move it to approved first:\n"
        f'  spec-kitty agent tasks move-task {req.task_id} --to approved --note "Review passed"\n'
        f'To proceed anyway, provide --done-override-reason "<why this is acceptable>".'
    )


def _guard_issue_matrix(req: MoveTaskRequest) -> RefuseExit1 | None:
    if req.target_lane in _APPROVAL_LANES and req.issue_matrix_blocker:
        return RefuseExit1(req.issue_matrix_blocker)
    return None


_GUARDS = (
    _guard_self_review,
    _guard_unsupported_skip_metadata,
    _guard_protected_branch,
    _guard_agent_ownership,
    _guard_rejected_verdict,
    _guard_feedback_file,
    _guard_planned_rollback,
    _guard_subtasks,
    _guard_review_currency,
    _guard_done_ancestry,
    _guard_issue_matrix,
)

# The two DURABLE proceed persists fire at fixed positions in the OLD guard
# sequence. Deriving the slice bounds from guard identity (not literals) keeps the
# OLD-timing signals correct if the guard order is ever reshuffled.
_REJECTED_VERDICT_GUARD_INDEX = _GUARDS.index(_guard_rejected_verdict)
_ISSUE_MATRIX_GUARD_INDEX = _GUARDS.index(_guard_issue_matrix)


def _guards_clear(req: MoveTaskRequest, guards: tuple[Any, ...]) -> bool:
    """True when none of ``guards`` refuses ``req`` (pure prefix evaluation)."""
    return all(guard(req) is None for guard in guards)


def override_persist_signal(req: MoveTaskRequest) -> bool:
    """OLD-timing gate for the review-artifact override persist (FR-004).

    In the un-refactored ``move_task`` the override evidence is written INSIDE the
    rejected-verdict guard's proceed arm (guard position 5), BEFORE the
    feedback-file, subtasks, review-currency, done-ancestry and issue-matrix
    guards run. The shell fires the persist when this returns ``True``, so a LATER
    guard's refusal (exit 1) still leaves the OLD partial write on disk.

    Returns ``True`` only when every guard that PRECEDES the rejected-verdict arm
    (self-review, unsupported-skip, protected-branch, agent-ownership) clears AND
    the rejected-verdict proceed arm authorises the override — mirroring the
    original short-circuit where an earlier guard refusal never reached the
    persist. Pure: consumes early facts only.
    """
    preceding = _GUARDS[:_REJECTED_VERDICT_GUARD_INDEX]
    return _guards_clear(req, preceding) and _authorize_review_override(req)


def arbiter_persist_signal(req: MoveTaskRequest) -> bool:
    """OLD-timing gate for the arbiter-override decision persist (FR-004).

    In the un-refactored ``move_task`` the arbiter decision JSON is written just
    BEFORE the issue-matrix guard. The shell fires the persist when this returns
    ``True``, so an issue-matrix refusal (exit 1) still leaves the OLD partial
    write on disk.

    Returns ``True`` only when every guard up to and including done-ancestry
    clears AND the move is an arbiter override — mirroring the original ordering
    where any earlier guard refusal never reached the persist. Pure: the arbiter
    fact (``is_arbiter_override``) is resolved by the shell and frozen on ``req``.
    """
    preceding = _GUARDS[:_ISSUE_MATRIX_GUARD_INDEX]
    return _guards_clear(req, preceding) and req.is_arbiter_override


# ---------------------------------------------------------------------------
# Reason / evidence / done-override helpers (pure)
# ---------------------------------------------------------------------------


def _done_override_reason(req: MoveTaskRequest) -> str | None:
    reason = req.done_override_reason
    return reason.strip() if isinstance(reason, str) else reason


def _effective_note_text(req: MoveTaskRequest) -> tuple[str | None, bool]:
    """Return ``(note_text, done_override_applied)`` folding the done-override note.

    Reproduces ``move_task``: the user note is stripped, and on a code-change
    ``done`` move with no merge ancestry but an override reason, the override note
    is appended (and a console warning is emitted — signalled by the bool).
    """
    user_note = req.note.strip() if isinstance(req.note, str) else req.note
    note_text = user_note
    if (
        req.target_lane == Lane.DONE
        and req.done_execution_mode == "code_change"
        and not req.done_merged
    ):
        override_reason = _done_override_reason(req)
        if override_reason:
            override_note = f"Done override: {override_reason}"
            note_text = f"{note_text} | {override_note}" if note_text else override_note
            return note_text, True
    return note_text, False


def _approval_evidence(req: MoveTaskRequest) -> dict[str, Any] | None:
    if req.target_lane not in _APPROVAL_LANES:
        return None
    return {
        "review": {
            "reviewer": req.effective_reviewer,
            "verdict": Lane.APPROVED,
            "reference": req.effective_approval_ref or "force-override",
        },
    }


# ---------------------------------------------------------------------------
# The single pure decision entry point
# ---------------------------------------------------------------------------


def decide_transition(req: MoveTaskRequest) -> TransitionOutcome:
    """Decide the move_task transition purely (FR-004 / NFR-001).

    Runs the guard sequence in the live command's order and returns the first
    :class:`RefuseExit1`; if every guard clears, returns an :class:`Emit` carrying
    the lane-hop plan, the coord ``skip_primary`` flag, approval evidence, and the
    proceed-authorisation flags the shell executes side effects from.
    """
    for guard in _GUARDS:
        refusal = guard(req)
        if refusal is not None:
            return refusal

    note_text, done_override_note = _effective_note_text(req)
    plan = build_transition_plan(
        old_lane=req.old_lane,
        target_lane=req.target_lane,
        force=req.force,
        review_feedback_pointer=None,
        arb_review_ref=None,
        note_text=note_text,
    )
    return Emit(
        plan=plan,
        skip_primary=req.skip_target_branch_commit,
        evidence_dict=_approval_evidence(req),
        note_text=note_text,
        authorize_review_override=_authorize_review_override(req),
        planned_rollback=req.target_lane == Lane.PLANNED,
        arbiter_forward=req.is_arbiter_override,
        done_override_note=done_override_note,
    )
