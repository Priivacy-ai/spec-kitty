"""SaaS read-model projection policy.

Single source of truth for per-(mode, event) projection behaviour.
See ADR-003-projection-policy.md and docs/trail-model.md (SaaS Read-Model Policy).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from specify_cli.invocation.modes import ModeOfWork

__all__ = [
    "ModeOfWork",
    "EventKind",
    "ProjectionRule",
    "POLICY_TABLE",
    "resolve_projection",
]


class EventKind(str, Enum):
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
    (ModeOfWork.ADVISORY, EventKind.STARTED):       ProjectionRule(True,  False, False),
    (ModeOfWork.ADVISORY, EventKind.COMPLETED):     ProjectionRule(True,  False, False),
    (ModeOfWork.ADVISORY, EventKind.ARTIFACT_LINK): ProjectionRule(False, False, False),
    (ModeOfWork.ADVISORY, EventKind.COMMIT_LINK):   ProjectionRule(False, False, False),

    # Task execution — full bodies projected; correlation events projected without bodies.
    (ModeOfWork.TASK_EXECUTION, EventKind.STARTED):       ProjectionRule(True, True,  False),
    (ModeOfWork.TASK_EXECUTION, EventKind.COMPLETED):     ProjectionRule(True, True,  True),
    (ModeOfWork.TASK_EXECUTION, EventKind.ARTIFACT_LINK): ProjectionRule(True, False, False),
    (ModeOfWork.TASK_EXECUTION, EventKind.COMMIT_LINK):   ProjectionRule(True, False, False),

    # Mission step — same projection behaviour as task_execution.
    (ModeOfWork.MISSION_STEP, EventKind.STARTED):       ProjectionRule(True, True,  False),
    (ModeOfWork.MISSION_STEP, EventKind.COMPLETED):     ProjectionRule(True, True,  True),
    (ModeOfWork.MISSION_STEP, EventKind.ARTIFACT_LINK): ProjectionRule(True, False, False),
    (ModeOfWork.MISSION_STEP, EventKind.COMMIT_LINK):   ProjectionRule(True, False, False),

    # Query — no projection; all events silently dropped.
    (ModeOfWork.QUERY, EventKind.STARTED):       ProjectionRule(False, False, False),
    (ModeOfWork.QUERY, EventKind.COMPLETED):     ProjectionRule(False, False, False),
    (ModeOfWork.QUERY, EventKind.ARTIFACT_LINK): ProjectionRule(False, False, False),
    (ModeOfWork.QUERY, EventKind.COMMIT_LINK):   ProjectionRule(False, False, False),
}


#: The fallback for a ``(mode, event)`` pair with no row. Projects NOTHING.
#:
#: It used to be ``ProjectionRule(True, True, True)`` — the most permissive rule in
#: the table — so a pair the policy had never been asked about disclosed the request
#: body by default. The table is exhaustive for the enums as declared (pinned by
#: ``test_policy_table_covers_all_16_pairs``), which means this arm is reachable only
#: by adding an enum member without a row: a change whose author has, by definition,
#: not decided what may be disclosed for it. The unasked question now answers "not
#: this" (#3030 FR-025 census — a lookup default is a guard too).
_NO_POLICY_RULE = ProjectionRule(project=False, include_request_text=False, include_evidence_ref=False)


def resolve_projection(
    mode: ModeOfWork | None,
    event: EventKind,
) -> ProjectionRule:
    """Return the projection rule for (mode, event).

    ``mode is None`` (pre-mission records, and every completed event) → treated as
    TASK_EXECUTION to preserve pre-WP06 unconditional projection behaviour for
    legacy records. Absence is a known, decided case — not the unknown one below.

    A ``(mode, event)`` pair with no row → :data:`_NO_POLICY_RULE` (project
    nothing). The table is exhaustive for the enums as defined; this path is only
    reachable if a future enum member is added before the table is extended, and an
    undecided disclosure question is not answered "disclose".
    """
    effective_mode = mode if mode is not None else ModeOfWork.TASK_EXECUTION
    return POLICY_TABLE.get((effective_mode, event), _NO_POLICY_RULE)
