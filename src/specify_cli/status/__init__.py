"""Canonical status engine for spec-kitty work package lifecycle.

Public API surface — all consumers import from this package.
"""

from .models import (
    DoneEvidence,
    Lane,
    RepoEvidence,
    ReviewApproval,
    StatusEvent,
    StatusSnapshot,
    ULID_PATTERN,
    VerificationResult,
)
from .transitions import (
    ALLOWED_TRANSITIONS,
    CANONICAL_LANES,
    LANE_ALIASES,
    TERMINAL_LANES,
    is_terminal,
    resolve_lane_alias,
    validate_transition,
)
from .phase import (
    DEFAULT_PHASE,
    VALID_PHASES,
    is_01x_branch,
    resolve_phase,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "CANONICAL_LANES",
    "DEFAULT_PHASE",
    "DoneEvidence",
    "Lane",
    "LANE_ALIASES",
    "RepoEvidence",
    "ReviewApproval",
    "StatusEvent",
    "StatusSnapshot",
    "TERMINAL_LANES",
    "ULID_PATTERN",
    "VALID_PHASES",
    "VerificationResult",
    "is_01x_branch",
    "is_terminal",
    "resolve_lane_alias",
    "resolve_phase",
    "validate_transition",
]
