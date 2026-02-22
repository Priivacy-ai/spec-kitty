"""Migration: Remove stale WP status ignore rules from repo .gitignore.

Historical context:
- `kitty-specs/**/tasks/*.md` was temporarily added to tracked `.gitignore`
  to reduce merge conflicts.
- Worktree-specific ignores now belong in `.git/info/exclude` (Bug #120).
- Keeping the rule in tracked `.gitignore` causes new WP files to be ignored
  in the planning repository and forces manual `git add -f`.

The fix:
- Remove WP status ignore patterns from tracked `.gitignore`
- Keep worktree-local excludes in `.git/info/exclude` only
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

MIGRATION_ID = "0.16.2_remove_wp_status_gitignore_rule"
MIGRATION_VERSION = "0.16.2"
MIGRATION_DESCRIPTION = (
    "Remove stale WP status ignore rules from tracked .gitignore"
)

# Patterns to remove from tracked .gitignore.
PATTERNS_TO_REMOVE = [
    r"^kitty-specs/\*\*/tasks/\*\.md$",
    r"^kitty-specs/\*/tasks/\*\.md$",
    r"^# Block WP status files.*$",
    r"^# Research artifacts in kitty-specs/\*\*/research/ are allowed$",
]


def is_wp_status_ignore_pattern(line: str) -> bool:
    """Return True when a line matches stale WP status ignore entries."""
    stripped = line.strip()
    if not stripped:
        return False

    for pattern in PATTERNS_TO_REMOVE:
        if re.match(pattern, stripped):
            return True
    return False


def find_wp_status_entries(gitignore_path: Path) -> List[Tuple[int, str]]:
    """Find stale WP status ignore entries in .gitignore.

    Returns:
        List of (1-based line number, stripped line content).
    """
    if not gitignore_path.exists():
        return []

    content = gitignore_path.read_text(encoding="utf-8-sig", errors="ignore")
    matches: List[Tuple[int, str]] = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        if is_wp_status_ignore_pattern(line):
            matches.append((line_no, line.strip()))
    return matches


def remove_wp_status_entries(
    gitignore_path: Path, dry_run: bool = False
) -> Tuple[List[str], List[str]]:
    """Remove stale WP status ignore entries from .gitignore.

    Returns:
        Tuple of (changes, errors).
    """
    changes: List[str] = []
    errors: List[str] = []

    if not gitignore_path.exists():
        changes.append("No .gitignore file found")
        return changes, errors

    try:
        content = gitignore_path.read_text(encoding="utf-8-sig", errors="ignore")
    except OSError as exc:
        errors.append(f"Failed to read .gitignore: {exc}")
        return changes, errors

    lines = content.splitlines(keepends=True)
    new_lines: List[str] = []
    removed_count = 0

    for index, line in enumerate(lines, start=1):
        if is_wp_status_ignore_pattern(line):
            changes.append(f"Line {index}: Removed '{line.strip()}'")
            removed_count += 1
            continue
        new_lines.append(line)

    if removed_count == 0:
        changes.append("No stale WP status ignore entries found in .gitignore")
        return changes, errors

    if dry_run:
        changes.insert(
            0, f"Would remove {removed_count} stale WP status ignore entries from .gitignore"
        )
        return changes, errors

    try:
        new_content = "".join(new_lines)
        new_content = re.sub(r"\n{3,}", "\n\n", new_content)
        gitignore_path.write_text(new_content, encoding="utf-8")
        changes.insert(
            0, f"Removed {removed_count} stale WP status ignore entries from .gitignore"
        )
    except OSError as exc:
        errors.append(f"Failed to write .gitignore: {exc}")

    return changes, errors


@MigrationRegistry.register
class RemoveWpStatusGitignoreRuleMigration(BaseMigration):
    """Remove stale WP status ignore rules from tracked .gitignore."""

    migration_id = MIGRATION_ID
    description = MIGRATION_DESCRIPTION
    target_version = MIGRATION_VERSION

    def detect(self, project_path: Path) -> bool:
        """Return True when stale WP status entries exist."""
        gitignore_path = project_path / ".gitignore"
        return len(find_wp_status_entries(gitignore_path)) > 0

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check readability/writability preconditions for .gitignore."""
        gitignore_path = project_path / ".gitignore"
        if not gitignore_path.exists():
            return True, ""

        try:
            gitignore_path.read_text(encoding="utf-8-sig", errors="ignore")
            return True, ""
        except OSError as exc:
            return False, f".gitignore is not readable: {exc}"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Apply migration by removing stale WP status ignore entries."""
        gitignore_path = project_path / ".gitignore"
        changes, errors = remove_wp_status_entries(gitignore_path, dry_run=dry_run)
        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
            warnings=[],
        )
