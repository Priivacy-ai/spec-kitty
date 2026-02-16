"""Exception hierarchy for glossary semantic integrity."""

from __future__ import annotations

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import SemanticConflict
    from .strictness import Strictness


class GlossaryError(Exception):
    """Base exception for glossary errors."""
    pass


class BlockedByConflict(GlossaryError):
    """Generation blocked by unresolved semantic conflicts.

    This exception is raised by the generation gate middleware when
    the effective strictness policy requires blocking generation.
    """

    def __init__(
        self,
        conflicts: List["SemanticConflict"],
        strictness: "Strictness | None" = None,
        message: str | None = None,
    ):
        """Initialize BlockedByConflict exception.

        Args:
            conflicts: List of conflicts that triggered the block
            strictness: The effective strictness mode (for context)
            message: Optional custom message (defaults to generic message)
        """
        self.conflicts = conflicts
        self.strictness = strictness

        # Use custom message if provided, otherwise generate default
        if message:
            super().__init__(message)
        else:
            conflict_count = len(conflicts)
            super().__init__(
                f"Generation blocked by {conflict_count} semantic conflict(s). "
                f"Resolve conflicts or use --strictness off to bypass."
            )


class DeferredToAsync(GlossaryError):
    """User deferred conflict resolution to async mode."""

    def __init__(self, conflict_id: str):
        self.conflict_id = conflict_id
        super().__init__(
            f"Conflict {conflict_id} deferred to async resolution. "
            f"Generation remains blocked. Resolve via CLI or SaaS decision inbox."
        )


class AbortResume(GlossaryError):
    """User aborted resume (context changed)."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Resume aborted: {reason}")
