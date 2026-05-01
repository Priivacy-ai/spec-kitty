"""Decision Moment service layer — open/resolve/defer/cancel orchestration.

Public API:
    open_decision(repo_root, mission_slug, *, ...)  -> DecisionOpenResponse
    resolve_decision(repo_root, mission_slug, decision_id, *, ...) -> DecisionTerminalResponse
    defer_decision(repo_root, mission_slug, decision_id, *, ...)   -> DecisionTerminalResponse
    cancel_decision(repo_root, mission_slug, decision_id, *, ...)  -> DecisionTerminalResponse

Also exports:
    DecisionError(Exception) — structured error with ``code`` and ``details``.

mission_id resolution:
    Reads ``<repo_root>/kitty-specs/<mission_slug>/meta.json`` → ``mission_id`` field.
    Raises ``DecisionError(MISSION_NOT_FOUND)`` if meta.json is missing or has no
    ``mission_id``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import ulid as _ulid_mod

from specify_cli.decisions import emit as _emit
from specify_cli.decisions import store as _store
from specify_cli.decisions.models import (
    DecisionErrorCode,
    DecisionOpenResponse,
    DecisionStatus,
    DecisionTerminalResponse,
    IndexEntry,
    OriginFlow,
)

__all__ = [
    "DecisionError",
    "open_decision",
    "resolve_decision",
    "defer_decision",
    "cancel_decision",
]


# ---------------------------------------------------------------------------
# Error class
# ---------------------------------------------------------------------------


class DecisionError(Exception):
    """Structured error raised by the decisions service.

    Attributes:
        code: Machine-readable DecisionErrorCode.
        details: Optional dict with context (decision_id, status, etc.).
    """

    def __init__(
        self,
        code: DecisionErrorCode,
        details: dict | None = None,  # type: ignore[type-arg]
        message: str | None = None,
    ) -> None:
        self.code = code
        self.details = details or {}
        msg = message or f"Decision error: {code.value}"
        super().__init__(msg)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _mint_decision_id() -> str:
    """Mint a new ULID-based decision_id."""
    return str(_ulid_mod.ULID())


def _now_utc() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(UTC)


_TERMINAL_STATUSES = {
    DecisionStatus.RESOLVED,
    DecisionStatus.DEFERRED,
    DecisionStatus.CANCELED,
}


def _is_terminal(status: DecisionStatus) -> bool:
    return status in _TERMINAL_STATUSES


def _resolve_mission_id(repo_root: Path, mission_slug: str) -> str:
    """Read mission_id from kitty-specs/<slug>/meta.json.

    Raises:
        DecisionError(MISSION_NOT_FOUND): if meta.json is missing or has no mission_id.
    """
    meta_path = repo_root / "kitty-specs" / mission_slug / "meta.json"
    if not meta_path.exists():
        raise DecisionError(
            code=DecisionErrorCode.MISSION_NOT_FOUND,
            details={"mission_slug": mission_slug},
            message=f"meta.json not found for mission {mission_slug!r}",
        )
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise DecisionError(
            code=DecisionErrorCode.MISSION_NOT_FOUND,
            details={"mission_slug": mission_slug},
            message=f"Failed to read meta.json for mission {mission_slug!r}: {exc}",
        ) from exc
    mission_id = meta.get("mission_id")
    if not mission_id:
        raise DecisionError(
            code=DecisionErrorCode.MISSION_NOT_FOUND,
            details={"mission_slug": mission_slug},
            message=f"meta.json for {mission_slug!r} has no mission_id field",
        )
    return str(mission_id)


def _mission_dir(repo_root: Path, mission_slug: str) -> Path:
    """Return kitty-specs/<mission_slug>/."""
    return repo_root / "kitty-specs" / mission_slug


# ---------------------------------------------------------------------------
# open_decision
# ---------------------------------------------------------------------------


def open_decision(
    repo_root: Path,
    mission_slug: str,
    *,
    origin_flow: OriginFlow,
    input_key: str,
    question: str,
    options: tuple[str, ...] = (),
    step_id: str | None = None,
    slot_key: str | None = None,
    actor: str,
    dry_run: bool = False,
    decision_id: str | None = None,
) -> DecisionOpenResponse:
    """Open a new decision or return idempotently if already open.

    Args:
        repo_root:    Repository root (parent of kitty-specs/).
        mission_slug: The mission slug.
        origin_flow:  Which CLI flow is creating this decision.
        input_key:    The specific input this decision governs.
        question:     Human-readable question text.
        options:      Ordered tuple of candidate answers.
        step_id:      Interview step identifier (supply step_id OR slot_key).
        slot_key:     Slot key (used when step_id is not available).
        actor:        Identity of the opening actor.
        dry_run:      If True, validate and look up without writing.
        decision_id:  Pre-minted ULID to use as the decision_id.  If None, a
                      new ULID is minted inside this function.  Callers that
                      need to emit the id to stdout *before* any write should
                      mint the ULID themselves and pass it here (FR-003).

    Returns:
        DecisionOpenResponse

    Raises:
        DecisionError(MISSING_STEP_OR_SLOT): if both step_id and slot_key are None.
        DecisionError(ALREADY_CLOSED): if a matching entry exists in terminal state.
        DecisionError(MISSION_NOT_FOUND): if meta.json is missing or invalid.
    """
    if step_id is None and slot_key is None:
        raise DecisionError(
            code=DecisionErrorCode.MISSING_STEP_OR_SLOT,
            message="Either step_id or slot_key must be provided",
        )

    mission_id = _resolve_mission_id(repo_root, mission_slug)
    mission_dir = _mission_dir(repo_root, mission_slug)

    if dry_run:
        return DecisionOpenResponse(
            decision_id="DRY_RUN",
            idempotent=False,
            mission_id=mission_id,
            artifact_path="",
            event_lamport=None,
        )

    # Look up existing entry by logical key
    index = _store.load_index(mission_dir)
    existing = _store.find_by_logical_key(
        index,
        origin_flow,
        step_id,
        slot_key,
        input_key,
    )

    if existing is not None:
        if not _is_terminal(existing.status):
            # Idempotent return — already open
            return DecisionOpenResponse(
                decision_id=existing.decision_id,
                idempotent=True,
                mission_id=mission_id,
                artifact_path=str(_store.artifact_path(mission_dir, existing.decision_id)),
                event_lamport=None,
            )
        else:
            # Already closed — reject
            raise DecisionError(
                code=DecisionErrorCode.ALREADY_CLOSED,
                details={
                    "decision_id": existing.decision_id,
                    "status": existing.status.value,
                },
                message=(f"Decision {existing.decision_id!r} is already in terminal state {existing.status.value!r}"),
            )

    # Mint new decision (use caller-supplied id if provided, else mint fresh)
    decision_id = decision_id if decision_id is not None else _mint_decision_id()
    created_at = _now_utc()
    entry = IndexEntry(
        decision_id=decision_id,
        origin_flow=origin_flow,
        step_id=step_id,
        slot_key=slot_key,
        input_key=input_key,
        question=question,
        options=tuple(options),
        status=DecisionStatus.OPEN,
        created_at=created_at,
        mission_id=mission_id,
        mission_slug=mission_slug,
    )

    _store.append_entry(mission_dir, entry)
    artifact = _store.write_artifact(mission_dir, entry)
    lamport = _emit.emit_decision_opened(
        repo_root,
        mission_slug,
        decision_id=decision_id,
        entry=entry,
        actor=actor,
    )

    return DecisionOpenResponse(
        decision_id=decision_id,
        idempotent=False,
        mission_id=mission_id,
        artifact_path=str(artifact),
        event_lamport=lamport,
    )


# ---------------------------------------------------------------------------
# _terminal_command — shared logic for resolve/defer/cancel
# ---------------------------------------------------------------------------


def _terminal_command(
    repo_root: Path,
    mission_slug: str,
    decision_id: str,
    *,
    target_status: DecisionStatus,
    terminal_outcome: str,
    final_answer: str | None = None,
    other_answer: bool = False,
    rationale: str | None = None,
    summary_json: dict[str, str] | None = None,
    resolved_by: str | None = None,
    actor: str,
    dry_run: bool = False,
) -> DecisionTerminalResponse:
    """Shared implementation for resolve, defer, and cancel.

    Raises:
        DecisionError(NOT_FOUND): if decision_id is not in the index.
        DecisionError(TERMINAL_CONFLICT): if already terminal with different payload.
    """
    if dry_run:
        return DecisionTerminalResponse(
            decision_id=decision_id,
            status=target_status,
            terminal_outcome=terminal_outcome,
            idempotent=False,
            event_lamport=None,
        )

    mission_dir = _mission_dir(repo_root, mission_slug)
    index = _store.load_index(mission_dir)
    entry = next(
        (e for e in index.entries if e.decision_id == decision_id),
        None,
    )
    if entry is None:
        raise DecisionError(
            code=DecisionErrorCode.NOT_FOUND,
            details={"decision_id": decision_id},
            message=f"Decision {decision_id!r} not found in index",
        )

    if _is_terminal(entry.status):
        # Already terminal — check for idempotency or conflict
        if entry.status == target_status:
            # Same outcome — check payload identity
            payload_matches = entry.final_answer == final_answer and entry.other_answer == other_answer and entry.rationale == rationale
            if payload_matches:
                return DecisionTerminalResponse(
                    decision_id=decision_id,
                    status=target_status,
                    terminal_outcome=terminal_outcome,
                    idempotent=True,
                    event_lamport=None,
                )
        # Different outcome or different payload — conflict
        raise DecisionError(
            code=DecisionErrorCode.TERMINAL_CONFLICT,
            details={
                "decision_id": decision_id,
                "existing_status": entry.status.value,
                "requested_status": target_status.value,
            },
            message=(f"Decision {decision_id!r} is already in terminal state {entry.status.value!r}; cannot transition to {target_status.value!r}"),
        )

    # Apply the terminal transition
    resolved_at = _now_utc()
    updated_index = _store.update_entry(
        mission_dir,
        decision_id,
        status=target_status,
        final_answer=final_answer,
        other_answer=other_answer,
        rationale=rationale,
        summary_json=summary_json,
        resolved_by=resolved_by,
        resolved_at=resolved_at,
    )

    # Get the updated entry for artifact + event
    updated_entry = next(e for e in updated_index.entries if e.decision_id == decision_id)
    _store.write_artifact(mission_dir, updated_entry)
    lamport = _emit.emit_decision_resolved(
        repo_root,
        mission_slug,
        decision_id=decision_id,
        entry=updated_entry,
        actor=actor,
    )

    return DecisionTerminalResponse(
        decision_id=decision_id,
        status=target_status,
        terminal_outcome=terminal_outcome,
        idempotent=False,
        event_lamport=lamport,
    )


# ---------------------------------------------------------------------------
# resolve_decision / defer_decision / cancel_decision
# ---------------------------------------------------------------------------


def resolve_decision(
    repo_root: Path,
    mission_slug: str,
    decision_id: str,
    *,
    final_answer: str,
    other_answer: bool = False,
    rationale: str | None = None,
    summary_json: dict[str, str] | None = None,
    resolved_by: str | None = None,
    actor: str,
    dry_run: bool = False,
) -> DecisionTerminalResponse:
    """Resolve a decision with a concrete answer.

    Args:
        repo_root:    Repository root (parent of kitty-specs/).
        mission_slug: The mission slug.
        decision_id:  The ULID identifier of the decision to resolve.
        final_answer: The chosen answer text (required, non-empty).
        other_answer: True if the answer is "other" (write-in).
        rationale:    Optional explanation of the choice.
        summary_json: Optional provenance payload; persisted as C-005 requires.
                      Expected shape: ``{"text": <str>, "source": <SummarySource.value>}``.
        resolved_by:  Identity of the resolver (falls back to actor).
        actor:        Identity of the acting agent.
        dry_run:      If True, validate without writing.

    Returns:
        DecisionTerminalResponse
    """
    return _terminal_command(
        repo_root,
        mission_slug,
        decision_id,
        target_status=DecisionStatus.RESOLVED,
        terminal_outcome="resolved",
        final_answer=final_answer,
        other_answer=other_answer,
        rationale=rationale,
        summary_json=summary_json,
        resolved_by=resolved_by,
        actor=actor,
        dry_run=dry_run,
    )


def defer_decision(
    repo_root: Path,
    mission_slug: str,
    decision_id: str,
    *,
    rationale: str,
    resolved_by: str | None = None,
    actor: str,
    dry_run: bool = False,
) -> DecisionTerminalResponse:
    """Defer a decision for later resolution.

    Args:
        repo_root:    Repository root (parent of kitty-specs/).
        mission_slug: The mission slug.
        decision_id:  The ULID identifier of the decision to defer.
        rationale:    Explanation of why it's being deferred (required).
        resolved_by:  Identity of the deferring party (falls back to actor).
        actor:        Identity of the acting agent.
        dry_run:      If True, validate without writing.

    Returns:
        DecisionTerminalResponse
    """
    return _terminal_command(
        repo_root,
        mission_slug,
        decision_id,
        target_status=DecisionStatus.DEFERRED,
        terminal_outcome="deferred",
        rationale=rationale,
        resolved_by=resolved_by,
        actor=actor,
        dry_run=dry_run,
    )


def cancel_decision(
    repo_root: Path,
    mission_slug: str,
    decision_id: str,
    *,
    rationale: str,
    resolved_by: str | None = None,
    actor: str,
    dry_run: bool = False,
) -> DecisionTerminalResponse:
    """Cancel a decision (deemed no longer relevant).

    Args:
        repo_root:    Repository root (parent of kitty-specs/).
        mission_slug: The mission slug.
        decision_id:  The ULID identifier of the decision to cancel.
        rationale:    Explanation of why it's being canceled (required).
        resolved_by:  Identity of the canceling party (falls back to actor).
        actor:        Identity of the acting agent.
        dry_run:      If True, validate without writing.

    Returns:
        DecisionTerminalResponse
    """
    return _terminal_command(
        repo_root,
        mission_slug,
        decision_id,
        target_status=DecisionStatus.CANCELED,
        terminal_outcome="canceled",
        rationale=rationale,
        resolved_by=resolved_by,
        actor=actor,
        dry_run=dry_run,
    )
