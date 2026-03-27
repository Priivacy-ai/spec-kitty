"""Ownership manifest models for spec-kitty work packages.

Defines ExecutionMode (StrEnum) and OwnershipManifest (frozen dataclass)
representing the ownership profile of a single work package.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ExecutionMode(StrEnum):
    """Execution mode of a work package.

    Exactly two values:
    - code_change: The WP produces source-code or test changes.
    - planning_artifact: The WP produces planning/documentation artifacts only.
    """

    CODE_CHANGE = "code_change"
    PLANNING_ARTIFACT = "planning_artifact"


@dataclass(frozen=True)
class OwnershipManifest:
    """Ownership profile embedded in a work package's frontmatter.

    Attributes:
        execution_mode: Whether this WP changes code or produces planning artifacts.
        owned_files: Tuple of glob patterns describing files owned by this WP.
        authoritative_surface: Path prefix that is the primary surface owned by
            this WP (e.g. ``src/specify_cli/ownership/``).
    """

    execution_mode: ExecutionMode
    owned_files: tuple[str, ...]  # Glob patterns
    authoritative_surface: str  # Path prefix

    @classmethod
    def from_frontmatter(cls, data: dict[str, Any]) -> OwnershipManifest:
        """Construct an OwnershipManifest from parsed frontmatter data.

        Args:
            data: Dictionary with keys ``execution_mode``, ``owned_files``,
                and ``authoritative_surface``.

        Returns:
            A new OwnershipManifest instance.

        Raises:
            KeyError: If a required key is missing.
            ValueError: If ``execution_mode`` is not a valid ExecutionMode value.
        """
        raw_mode = data["execution_mode"]
        execution_mode = ExecutionMode(raw_mode)

        raw_files = data.get("owned_files") or []
        if isinstance(raw_files, str):
            raw_files = [raw_files]
        owned_files = tuple(raw_files)

        authoritative_surface = data.get("authoritative_surface", "")

        return cls(
            execution_mode=execution_mode,
            owned_files=owned_files,
            authoritative_surface=authoritative_surface,
        )

    def to_frontmatter(self) -> dict[str, Any]:
        """Serialize to a frontmatter-compatible dictionary.

        Returns:
            Dictionary suitable for writing into YAML frontmatter.
        """
        return {
            "execution_mode": str(self.execution_mode),
            "owned_files": list(self.owned_files),
            "authoritative_surface": self.authoritative_surface,
        }
