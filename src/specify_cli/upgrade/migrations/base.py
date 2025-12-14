"""Base migration class for Spec Kitty upgrade system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class MigrationResult:
    """Result of a migration operation."""

    success: bool
    changes_made: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class BaseMigration(ABC):
    """Base class for all migrations.

    Migrations should:
    1. Be idempotent (safe to run multiple times)
    2. Check preconditions before applying
    3. Report what changes were made
    4. Handle dry-run mode
    """

    # Migration identifier (e.g., "0.6.5_commands_rename")
    # Format: {version}_{short_description}
    migration_id: str = ""

    # Human-readable description
    description: str = ""

    # Target version this migration brings project to
    target_version: str = ""

    # Minimum version this migration can be applied from (optional)
    # If None, detection is used
    min_version: Optional[str] = None

    @abstractmethod
    def detect(self, project_path: Path) -> bool:
        """Detect if this migration is needed based on project state.

        Returns True if the project has the OLD state that needs migration.
        This is used for heuristic detection when metadata is missing.

        Args:
            project_path: Root of the project (.kittify parent)

        Returns:
            True if migration is needed
        """

    @abstractmethod
    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if migration can be safely applied.

        Args:
            project_path: Root of the project

        Returns:
            (can_apply, reason) - True if safe, False with explanation if not
        """

    @abstractmethod
    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Apply the migration.

        Args:
            project_path: Root of the project (.kittify parent)
            dry_run: If True, only simulate changes

        Returns:
            MigrationResult with details of what was changed
        """
