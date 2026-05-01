"""SaaS read-model projection policy.

Single source of truth for per-(mode, event) projection behaviour.
See ADR-003-projection-policy.md and docs/trail-model.md (SaaS Read-Model Policy).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from specify_cli.invocation.modes import ModeOfWork

__all__ = [
    "ModeOfWork",
    "EventKind",
    "ProjectionRule",
    "POLICY_TABLE",
    "resolve_projection",
]


class EventKind(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    ARTIFACT_LINK = "artifact_link"
    COMMIT_LINK = "commit_link"


@dataclass(frozen=True)
class ProjectionRule:
    project: bool
    include_request_text: bool
    include_evidence_ref: bool


POLICY_TABLE: dict[tuple[ModeOfWork, EventKind], ProjectionRule] = {
    # Advisory — timeline entries with no body.
    (ModeOfWork.ADVISORY, EventKind.STARTED): ProjectionRule(True, False, False),
    (ModeOfWork.ADVISORY, EventKind.COMPLETED): ProjectionRule(True, False, False),
    (ModeOfWork.ADVISORY, EventKind.ARTIFACT_LINK): ProjectionRule(False, False, False),
    (ModeOfWork.ADVISORY, EventKind.COMMIT_LINK): ProjectionRule(False, False, False),
    # Task execution — full bodies projected; correlation events projected without bodies.
    (ModeOfWork.TASK_EXECUTION, EventKind.STARTED): ProjectionRule(True, True, False),
    (ModeOfWork.TASK_EXECUTION, EventKind.COMPLETED): ProjectionRule(True, True, True),
    (ModeOfWork.TASK_EXECUTION, EventKind.ARTIFACT_LINK): ProjectionRule(True, False, False),
    (ModeOfWork.TASK_EXECUTION, EventKind.COMMIT_LINK): ProjectionRule(True, False, False),
    # Mission step — same projection behaviour as task_execution.
    (ModeOfWork.MISSION_STEP, EventKind.STARTED): ProjectionRule(True, True, False),
    (ModeOfWork.MISSION_STEP, EventKind.COMPLETED): ProjectionRule(True, True, True),
    (ModeOfWork.MISSION_STEP, EventKind.ARTIFACT_LINK): ProjectionRule(True, False, False),
    (ModeOfWork.MISSION_STEP, EventKind.COMMIT_LINK): ProjectionRule(True, False, False),
    # Query — no projection; all events silently dropped.
    (ModeOfWork.QUERY, EventKind.STARTED): ProjectionRule(False, False, False),
    (ModeOfWork.QUERY, EventKind.COMPLETED): ProjectionRule(False, False, False),
    (ModeOfWork.QUERY, EventKind.ARTIFACT_LINK): ProjectionRule(False, False, False),
    (ModeOfWork.QUERY, EventKind.COMMIT_LINK): ProjectionRule(False, False, False),
}


_DEFAULT_RULE = ProjectionRule(project=True, include_request_text=True, include_evidence_ref=True)


def resolve_projection(
    mode: ModeOfWork | None,
    event: EventKind,
) -> ProjectionRule:
    """Return the projection rule for (mode, event).

    ``mode is None`` (pre-mission records) → treated as TASK_EXECUTION to preserve
    pre-WP06 unconditional projection behaviour for legacy records.

    Unknown ``(mode, event)`` pair → falls back to ``_DEFAULT_RULE`` (project all).
    The table is exhaustive for the enums as defined; this path is only hit if
    a future EventKind is added before the table is extended.
    """
    effective_mode = mode if mode is not None else ModeOfWork.TASK_EXECUTION
    return POLICY_TABLE.get((effective_mode, event), _DEFAULT_RULE)
