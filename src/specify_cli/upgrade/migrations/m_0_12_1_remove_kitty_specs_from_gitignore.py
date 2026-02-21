"""Migration: Remove kitty-specs/ from main repo .gitignore.

Historical context:
- Earlier spec-kitty versions or user templates may have added `kitty-specs/` to .gitignore
- This prevents git from tracking feature specifications, causing failures in:
  - `spec-kitty agent feature create-feature`
  - `/spec-kitty.specify` (commit step)
  - Other commands that commit to kitty-specs/

The fix:
- Remove `kitty-specs/` entries from main repo .gitignore
- Keep worktree-specific patterns like `kitty-specs/**/tasks/*.md` (those prevent merge conflicts)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

MIGRATION_ID = "0.12.1_remove_kitty_specs_from_gitignore"
MIGRATION_VERSION = "0.12.1"
MIGRATION_DESCRIPTION = "Remove kitty-specs/ from main repo .gitignore to allow tracking feature specs"

# Patterns to REMOVE (block entire kitty-specs directory)
PATTERNS_TO_REMOVE = [
    r"^kitty-specs/?$",  # kitty-specs or kitty-specs/
    r"^/kitty-specs/?$",  # /kitty-specs or /kitty-specs/
]

# Patterns to KEEP (worktree-specific, prevent merge conflicts)
PATTERNS_TO_KEEP = [
    r"kitty-specs/\*\*/tasks/",  # kitty-specs/**/tasks/*.md
    r"kitty-specs/.*/tasks/",  # kitty-specs/*/tasks/*.md
]


def is_blocking_pattern(line: str) -> bool:
    """Check if a line blocks the entire kitty-specs directory.

    Returns True for patterns like:
    - kitty-specs
    - kitty-specs/
    - /kitty-specs
    - /kitty-specs/

    Returns False for specific subpath patterns like:
    - kitty-specs/**/tasks/*.md (this is fine, used in worktrees)
    """
    stripped = line.strip()

    # Skip comments and empty lines
    if not stripped or stripped.startswith("#"):
        return False

    # Check if it's a specific subpath pattern (KEEP these)
    for keep_pattern in PATTERNS_TO_KEEP:
        if re.search(keep_pattern, stripped):
            return False

    # Check if it blocks the entire directory (REMOVE these)
    for remove_pattern in PATTERNS_TO_REMOVE:
        if re.match(remove_pattern, stripped):
            return True

    return False


def find_blocking_entries(gitignore_path: Path) -> List[Tuple[int, str]]:
    """Find all lines that block kitty-specs/ entirely.

    Returns list of (line_number, line_content) tuples.
    Line numbers are 1-indexed for user display.
    """
    if not gitignore_path.exists():
        return []

    blocking_entries = []
    content = gitignore_path.read_text(encoding="utf-8-sig", errors="ignore")

    for i, line in enumerate(content.splitlines(), start=1):
        if is_blocking_pattern(line):
            blocking_entries.append((i, line.strip()))

    return blocking_entries


def remove_blocking_entries(gitignore_path: Path, dry_run: bool = False) -> Tuple[List[str], List[str]]:
    """Remove entries that block kitty-specs/ from .gitignore.

    Returns (changes, errors) tuple.
    """
    changes: List[str] = []
    errors: List[str] = []

    if not gitignore_path.exists():
        changes.append("No .gitignore file found")
        return changes, errors

    try:
        content = gitignore_path.read_text(encoding="utf-8-sig", errors="ignore")
    except OSError as e:
        errors.append(f"Failed to read .gitignore: {e}")
        return changes, errors

    lines = content.splitlines(keepends=True)
    new_lines = []
    removed_count = 0

    for i, line in enumerate(lines, start=1):
        if is_blocking_pattern(line):
            changes.append(f"Line {i}: Removed '{line.strip()}'")
            removed_count += 1
            # Skip this line (don't add to new_lines)
        else:
            new_lines.append(line)

    if removed_count == 0:
        changes.append("No blocking kitty-specs/ entries found in .gitignore")
        return changes, errors

    if dry_run:
        changes.insert(0, f"Would remove {removed_count} blocking entries from .gitignore")
        return changes, errors

    # Write updated content
    try:
        new_content = "".join(new_lines)
        # Clean up any resulting double blank lines
        new_content = re.sub(r"\n{3,}", "\n\n", new_content)
        gitignore_path.write_text(new_content, encoding="utf-8")
        changes.insert(0, f"Removed {removed_count} blocking entries from .gitignore")
    except OSError as e:
        errors.append(f"Failed to write .gitignore: {e}")

    return changes, errors


@MigrationRegistry.register
class RemoveKittySpecsFromGitignoreMigration(BaseMigration):
    """Remove kitty-specs/ from main repo .gitignore.

    Feature specifications must be tracked in git. If kitty-specs/ is in
    .gitignore, git add operations fail during feature creation.
    """

    migration_id = MIGRATION_ID
    description = MIGRATION_DESCRIPTION
    target_version = MIGRATION_VERSION

    def detect(self, project_path: Path) -> bool:
        """Check if .gitignore contains blocking kitty-specs/ entries."""
        gitignore_path = project_path / ".gitignore"
        blocking_entries = find_blocking_entries(gitignore_path)
        return len(blocking_entries) > 0

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if we can modify .gitignore."""
        gitignore_path = project_path / ".gitignore"

        if not gitignore_path.exists():
            return True, ""

        try:
            gitignore_path.read_text(encoding="utf-8-sig", errors="ignore")
            return True, ""
        except OSError as e:
            return False, f".gitignore is not readable: {e}"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Remove blocking kitty-specs/ entries from .gitignore."""
        gitignore_path = project_path / ".gitignore"
        changes, errors = remove_blocking_entries(gitignore_path, dry_run=dry_run)

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
            warnings=[],
        )
