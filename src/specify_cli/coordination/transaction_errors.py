"""Error hierarchy for :mod:`specify_cli.coordination.transaction`.

Extracted VERBATIM from ``transaction.py`` (WP08 campsite split, NFR-007):
behaviour-free. Every subclass carries a stable ``error_code`` class attribute
so callers can route on the code without string parsing. ``transaction.py``
re-exports these names, so ``from specify_cli.coordination.transaction import
BookkeepingError`` (and the rest) keeps resolving to the same class objects.
"""

from __future__ import annotations

from typing import ClassVar

from specify_cli.coordination.types import Refused


class BookkeepingError(Exception):
    """Base for all BookkeepingTransaction failures.

    Subclasses carry a stable ``error_code`` class attribute so callers
    can route on the code without string parsing (NFR-007).
    """

    error_code: ClassVar[str] = "BOOKKEEPING_ERROR"


class BookkeepingPolicyRefused(BookkeepingError):
    """The pre-flight policy gate refused the would-be commit.

    Carries the underlying :class:`Refused` verdict so callers can
    surface the structured diagnostic.
    """

    error_code: ClassVar[str] = "BOOKKEEPING_POLICY_REFUSED"

    def __init__(self, verdict: Refused) -> None:
        self.verdict = verdict
        super().__init__(
            f"Bookkeeping refused: {verdict.error_code}: {verdict.message}"
        )


class BookkeepingLockTimeout(BookkeepingError):
    """The feature status lock could not be acquired within the timeout."""

    error_code: ClassVar[str] = "BOOKKEEPING_LOCK_TIMEOUT"


class BookkeepingWorktreeMissing(BookkeepingError):
    """Worktree resolution found neither a coord nor a valid lane worktree."""

    error_code: ClassVar[str] = "BOOKKEEPING_WORKTREE_MISSING"


class BookkeepingCommitFailed(BookkeepingError):
    """``safe_commit()`` raised; rollback ran; the original error is chained."""

    error_code: ClassVar[str] = "BOOKKEEPING_COMMIT_FAILED"


class BookkeepingDoubleEventId(BookkeepingError):
    """The same event_id was appended twice in one transaction."""

    error_code: ClassVar[str] = "BOOKKEEPING_DOUBLE_EVENT_ID"


class BookkeepingLegacyResolutionFailed(BookkeepingError):
    """Legacy mission detected but the lane worktree could not be resolved.

    Stable error code ``BOOKKEEPING_LEGACY_RESOLUTION_FAILED``.  Raised
    when ``meta.json`` lacks ``coordination_branch`` (legacy mission)
    but the operator's current working directory does not sit inside a
    recognisable lane worktree, so we cannot determine which branch is
    the legitimate write target for this mission's bookkeeping.
    """

    error_code: ClassVar[str] = "BOOKKEEPING_LEGACY_RESOLUTION_FAILED"
