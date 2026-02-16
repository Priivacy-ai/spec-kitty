"""Exception hierarchy for glossary semantic integrity."""

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import SemanticConflict


class GlossaryError(Exception):
    """Base exception for glossary errors."""
    pass


class BlockedByConflict(GlossaryError):
    """Generation blocked by unresolved high-severity conflict."""

    def __init__(self, conflicts: List["SemanticConflict"]):
        self.conflicts = conflicts
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
