"""Migration: narrow the blanket ``.cursor/`` gitignore entry (#2498).

``GitignoreManager`` used to protect Cursor with a single blanket
``.cursor/`` entry, added unconditionally by ``protect_all_agents()`` at
init regardless of which agents were selected. That conflicts with teams
that version-control their own rules under ``.cursor/rules/`` (e.g.
``.cursor/rules/contributing.mdc``): once ``.cursor/`` is gitignored, those
tracked files become unstageable.

The registry (``gitignore_manager.AGENT_DIRECTORIES``) now lists only the
narrow paths Spec Kitty itself generates under ``.cursor/`` --
``.cursor/rules/spec-kitty.mdc``, ``.cursor/commands/`` and
``.cursor/skills/`` -- so a fresh ``spec-kitty init`` no longer writes the
blanket line. This migration repairs already-initialised projects on
``spec-kitty upgrade``: it removes a pre-existing blanket-blocking
``.cursor`` line (mirroring the ``0.12.1_remove_kitty_specs_from_gitignore``
precedent) and backfills the three narrow entries (mirroring the
``3.2.5_agents_skills_gitignore_backfill`` precedent), so projects keep
ignoring what Spec Kitty actually generates without re-blocking everything
else under ``.cursor/``.
"""

from __future__ import annotations

import re
from pathlib import Path

from specify_cli.gitignore_manager import GitignoreManager

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

MIGRATION_ID = "3.2.6rc3_narrow_cursor_gitignore"
MIGRATION_VERSION = "3.2.6rc3"

# Narrow entries Spec Kitty itself generates under .cursor/ -- kept in sync
# with the cursor rows in gitignore_manager.AGENT_DIRECTORIES.
_NARROW_ENTRIES = [
    ".cursor/rules/spec-kitty.mdc",
    ".cursor/commands/",
    ".cursor/skills/",
]

# Matches a line that blocks the entire .cursor directory in any of the
# forms git treats as equivalent: `.cursor`, `.cursor/`, `.cursor/*`,
# `.cursor/**`, optionally anchored with a leading `/` or prefixed with
# `**/`. Does not match narrower subpath patterns like `.cursor/rules/` or
# `.cursor/plans`, nor negations (`!.cursor/...`) or comments.
_BLANKET_PATTERN = re.compile(r"^(/|\*\*/)?\.cursor(/|/\*{1,2})?$")


def _is_blanket_cursor_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    return bool(_BLANKET_PATTERN.match(stripped))


def _find_blanket_lines(gitignore_path: Path) -> list[str]:
    if not gitignore_path.exists():
        return []
    content = gitignore_path.read_text(encoding="utf-8-sig", errors="ignore")
    return [line for line in content.splitlines() if _is_blanket_cursor_line(line)]


def _strip_blanket_lines(lines: list[str]) -> tuple[list[str], int]:
    """Drop blanket lines, closing only the hole each removal leaves behind.

    When a removed line sat between two blank lines, the trailing blank is
    dropped so the removal does not create a new double-blank run at that
    spot. Blank-line runs elsewhere in the operator's file are untouched.
    """
    kept: list[str] = []
    removed = 0
    just_removed = False
    for line in lines:
        if _is_blanket_cursor_line(line):
            removed += 1
            just_removed = True
            continue
        if just_removed and not line.strip() and kept and not kept[-1].strip():
            continue
        just_removed = False
        kept.append(line)
    return kept, removed


def _remove_blanket_lines(gitignore_path: Path) -> int:
    if not gitignore_path.exists():
        return 0
    content = gitignore_path.read_text(encoding="utf-8-sig", errors="ignore")
    kept, removed = _strip_blanket_lines(content.splitlines(keepends=True))
    if removed:
        gitignore_path.write_text("".join(kept), encoding="utf-8")
    return removed


def _missing_narrow_entries(gitignore_path: Path) -> list[str]:
    if not gitignore_path.exists():
        return list(_NARROW_ENTRIES)
    content = gitignore_path.read_text(encoding="utf-8-sig", errors="ignore")
    present = {line.strip() for line in content.splitlines()}
    return [entry for entry in _NARROW_ENTRIES if entry not in present]


@MigrationRegistry.register
class NarrowCursorGitignoreMigration(BaseMigration):
    """Replace the blanket ``.cursor/`` gitignore entry with narrow ones."""

    migration_id = MIGRATION_ID
    description = "Narrow blanket .cursor/ gitignore entry to Spec Kitty-generated paths only (#2498)"
    target_version = MIGRATION_VERSION

    def detect(self, project_path: Path) -> bool:
        gitignore_path = project_path / ".gitignore"
        if _find_blanket_lines(gitignore_path):
            return True
        return bool(_missing_narrow_entries(gitignore_path))

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if not project_path.exists():
            return False, f"Project path does not exist: {project_path}"

        gitignore_path = project_path / ".gitignore"
        if not gitignore_path.exists():
            return True, ""
        try:
            gitignore_path.read_text(encoding="utf-8-sig", errors="ignore")
            return True, ""
        except OSError as e:
            return False, f".gitignore is not readable: {e}"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        gitignore_path = project_path / ".gitignore"
        blanket_lines = _find_blanket_lines(gitignore_path)
        missing = _missing_narrow_entries(gitignore_path)

        if dry_run:
            changes = [f"Would remove blanket line: '{line.strip()}'" for line in blanket_lines]
            changes.extend(f"Would add gitignore entry: {entry}" for entry in missing)
            if not changes:
                changes.append("No blanket .cursor/ entries and narrow entries already present")
            return MigrationResult(success=True, changes_made=changes)

        applied_changes: list[str] = []
        removed = _remove_blanket_lines(gitignore_path)
        if removed:
            applied_changes.extend(f"Removed blanket line: '{line.strip()}'" for line in blanket_lines)

        if missing:
            GitignoreManager(project_path).ensure_entries(missing)
            applied_changes.extend(f"Added gitignore entry: {entry}" for entry in missing)

        if not applied_changes:
            applied_changes.append("No blanket .cursor/ entries and narrow entries already present")

        return MigrationResult(success=True, changes_made=applied_changes)
