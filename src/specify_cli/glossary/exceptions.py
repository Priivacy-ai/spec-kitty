"""Exception hierarchy for glossary semantic integrity."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

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
        conflicts: list[SemanticConflict],
        strictness: Strictness | None = None,
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


@dataclass(frozen=True)
class SeedValidationError:
    """A single validation error with location context."""

    file_path: Path
    term_index: int | None
    term_surface: str | None
    field: str | None
    message: str


class SeedFileValidationError(GlossaryError):
    """Aggregated validation failure for a glossary seed file."""

    def __init__(self, file_path: Path, errors: list[SeedValidationError]):
        self.file_path = file_path
        self.errors = errors
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        lines = [f"{len(self.errors)} validation error(s) in {self.file_path}:"]
        for err in self.errors:
            loc_parts: list[str] = []
            if err.term_index is not None:
                surface_label = f" '{err.term_surface}'" if err.term_surface else ""
                loc_parts.append(f"term[{err.term_index}]{surface_label}")
            if err.field:
                loc_parts.append(err.field)
            loc = " → ".join(loc_parts) if loc_parts else "file"
            lines.append(f"  - {loc}: {err.message}")
        return "\n".join(lines)
