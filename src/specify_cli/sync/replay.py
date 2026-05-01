"""Deterministic replay of offline-queue events (FR-028).

This module is the per-event apply path for replaying events that were
captured into ``.kittify/sync/overflow-*.jsonl`` (or the live offline
queue) back into the local sync surface.

Identity model
--------------
Each replayed event carries a ``(tenant_id, project_id)`` identity
pair. The local target — typically the active session's
``(default_team_id, project_uuid)`` — is the authoritative comparison
key. The reducer is intentionally strict (FR-028):

* both match → idempotent apply.
* tenant mismatch → :class:`TenantMismatch` raised, conflict logged,
  event skipped.
* tenant matches, project mismatch → :class:`ProjectMismatch` raised,
  conflict logged, event skipped.

The :func:`replay_events` driver iterates each event, classifies it,
and aggregates a structured :class:`ReplayResult` containing the
per-event outcomes, conflict log entries, and idempotent-write
counters. Idempotent apply is wired through a caller-supplied
``apply_callable`` so this module stays free of any specific persistence
backend.

Conflict logging is deliberately structured (machine-readable JSON
records on a dedicated ``logging`` logger named
``"specify_cli.sync.replay.conflict"``) so SaaS dashboards can
ingest it later.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any
from collections.abc import Callable, Iterable


__all__ = [
    "ReplayConflictRecord",
    "ReplayDecision",
    "ReplayResult",
    "ReplayTarget",
    "TenantMismatch",
    "ProjectMismatch",
    "classify_event",
    "replay_events",
]


_conflict_logger = logging.getLogger("specify_cli.sync.replay.conflict")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class _MismatchBase(RuntimeError):
    """Common base for replay-identity mismatch errors."""

    error_code: str

    def __init__(
        self,
        message: str,
        *,
        tenant_id: str | None,
        project_id: str | None,
        target_tenant_id: str,
        target_project_id: str,
        event_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.target_tenant_id = target_tenant_id
        self.target_project_id = target_project_id
        self.event_id = event_id


class TenantMismatch(_MismatchBase):
    """Raised when the event's ``tenant_id`` differs from the local target."""

    error_code = "tenant_mismatch"


class ProjectMismatch(_MismatchBase):
    """Raised when ``tenant_id`` matches but ``project_id`` differs."""

    error_code = "project_mismatch"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReplayTarget:
    """Local replay target — the source of truth for identity matching."""

    tenant_id: str
    project_id: str


@dataclass(frozen=True)
class ReplayDecision:
    """Per-event classification before the apply step.

    Attributes:
        verdict: One of ``"apply"``, ``"tenant_mismatch"``,
            ``"project_mismatch"``, or ``"missing_identity"``.
        event_id: The replayed event's ID.
        tenant_id: The event's tenant id (or ``None`` if absent).
        project_id: The event's project id (or ``None`` if absent).
    """

    verdict: str
    event_id: str | None
    tenant_id: str | None
    project_id: str | None


@dataclass
class ReplayConflictRecord:
    """Structured conflict-log record (machine-readable)."""

    error_code: str
    event_id: str | None
    tenant_id: str | None
    project_id: str | None
    target_tenant_id: str
    target_project_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "event_id": self.event_id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "target_tenant_id": self.target_tenant_id,
            "target_project_id": self.target_project_id,
        }


@dataclass
class ReplayResult:
    """Aggregate result of a :func:`replay_events` invocation."""

    target: ReplayTarget
    applied: int = 0
    skipped_tenant: int = 0
    skipped_project: int = 0
    skipped_missing_identity: int = 0
    conflicts: list[ReplayConflictRecord] = field(default_factory=list)
    decisions: list[ReplayDecision] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _extract_identity(event: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    """Return ``(tenant_id, project_id, event_id)`` for *event*.

    The identity may live on the top-level envelope or inside
    ``payload``; the canonical event shape historically uses both.
    """
    payload = event.get("payload") or {}

    def _pick(*keys: str) -> str | None:
        for key in keys:
            value = event.get(key)
            if value is None:
                value = payload.get(key)
            if value is not None and str(value):
                return str(value)
        return None

    tenant_id = _pick("tenant_id", "team_id", "default_team_id")
    project_id = _pick("project_id", "project_uuid")
    event_id = _pick("event_id")
    return tenant_id, project_id, event_id


def classify_event(
    event: dict[str, Any],
    target: ReplayTarget,
) -> ReplayDecision:
    """Classify *event* against *target* without applying it.

    Returns a :class:`ReplayDecision`. The ``verdict`` value is one of:

    * ``"apply"`` — both ``tenant_id`` and ``project_id`` match
      *target*.
    * ``"tenant_mismatch"`` — tenant differs.
    * ``"project_mismatch"`` — tenant matches but project differs.
    * ``"missing_identity"`` — the event lacks a usable identity pair.
    """
    tenant_id, project_id, event_id = _extract_identity(event)

    if tenant_id is None or project_id is None:
        return ReplayDecision(
            verdict="missing_identity",
            event_id=event_id,
            tenant_id=tenant_id,
            project_id=project_id,
        )

    if tenant_id != target.tenant_id:
        return ReplayDecision(
            verdict="tenant_mismatch",
            event_id=event_id,
            tenant_id=tenant_id,
            project_id=project_id,
        )

    if project_id != target.project_id:
        return ReplayDecision(
            verdict="project_mismatch",
            event_id=event_id,
            tenant_id=tenant_id,
            project_id=project_id,
        )

    return ReplayDecision(
        verdict="apply",
        event_id=event_id,
        tenant_id=tenant_id,
        project_id=project_id,
    )


def _log_conflict(record: ReplayConflictRecord) -> None:
    """Emit a structured JSON conflict line on the dedicated logger."""
    _conflict_logger.warning(
        "replay.conflict %s",
        json.dumps(record.to_dict(), sort_keys=True),
    )


# ---------------------------------------------------------------------------
# Public driver
# ---------------------------------------------------------------------------


def replay_events(
    events: Iterable[dict[str, Any]],
    target: ReplayTarget,
    *,
    apply_callable: Callable[[dict[str, Any]], None] | None = None,
    raise_on_mismatch: bool = False,
) -> ReplayResult:
    """Replay *events* against *target*, classifying each event by identity.

    Args:
        events: Iterable of event dicts (e.g. parsed from a JSONL
            overflow drain file).
        target: The :class:`ReplayTarget` representing the local
            tenant/project pair.
        apply_callable: Optional per-event side-effect for matched
            events. Called exactly once per event with the event dict.
            Idempotent apply semantics are the caller's responsibility:
            replaying the same event twice MUST NOT produce duplicate
            local writes.
        raise_on_mismatch: When ``True``, the first mismatch raises
            (:class:`TenantMismatch` or :class:`ProjectMismatch`); the
            partial :class:`ReplayResult` is attached to the exception
            via ``__cause__``. When ``False`` (default), mismatches are
            logged and counted; replay continues with the next event.

    Returns:
        A :class:`ReplayResult` summarising apply / mismatch / skip
        counters.
    """
    result = ReplayResult(target=target)

    for event in events:
        decision = classify_event(event, target)
        result.decisions.append(decision)

        if decision.verdict == "apply":
            if apply_callable is not None:
                apply_callable(event)
            result.applied += 1
            continue

        if decision.verdict == "missing_identity":
            result.skipped_missing_identity += 1
            record = ReplayConflictRecord(
                error_code="missing_identity",
                event_id=decision.event_id,
                tenant_id=decision.tenant_id,
                project_id=decision.project_id,
                target_tenant_id=target.tenant_id,
                target_project_id=target.project_id,
            )
            result.conflicts.append(record)
            _log_conflict(record)
            continue

        if decision.verdict == "tenant_mismatch":
            result.skipped_tenant += 1
            record = ReplayConflictRecord(
                error_code="tenant_mismatch",
                event_id=decision.event_id,
                tenant_id=decision.tenant_id,
                project_id=decision.project_id,
                target_tenant_id=target.tenant_id,
                target_project_id=target.project_id,
            )
            result.conflicts.append(record)
            _log_conflict(record)
            if raise_on_mismatch:
                raise TenantMismatch(
                    f"Replay tenant mismatch: event tenant {decision.tenant_id!r} != target tenant {target.tenant_id!r}",
                    tenant_id=decision.tenant_id,
                    project_id=decision.project_id,
                    target_tenant_id=target.tenant_id,
                    target_project_id=target.project_id,
                    event_id=decision.event_id,
                )
            continue

        if decision.verdict == "project_mismatch":
            result.skipped_project += 1
            record = ReplayConflictRecord(
                error_code="project_mismatch",
                event_id=decision.event_id,
                tenant_id=decision.tenant_id,
                project_id=decision.project_id,
                target_tenant_id=target.tenant_id,
                target_project_id=target.project_id,
            )
            result.conflicts.append(record)
            _log_conflict(record)
            if raise_on_mismatch:
                raise ProjectMismatch(
                    f"Replay project mismatch: event project {decision.project_id!r} != target project {target.project_id!r}",
                    tenant_id=decision.tenant_id,
                    project_id=decision.project_id,
                    target_tenant_id=target.tenant_id,
                    target_project_id=target.project_id,
                    event_id=decision.event_id,
                )
            continue

        # Unknown verdict — fail loudly rather than silently dropping.
        raise RuntimeError(f"Unknown replay verdict: {decision.verdict!r}")

    return result
