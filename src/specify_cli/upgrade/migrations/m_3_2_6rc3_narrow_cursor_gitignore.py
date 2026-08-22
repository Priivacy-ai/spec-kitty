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
``spec-kitty upgrade``: it removes the exact legacy ``.cursor/`` row only
when the Spec Kitty auto-managed marker proves ownership, then backfills the
three narrow entries. Unattributed blanket rules are operator policy: they are
preserved with a warning instead of being deleted by name alone.
"""

from __future__ import annotations

import re
from pathlib import Path

from specify_cli.gitignore_manager import (
    AGENT_DIRECTORIES,
    RUNTIME_PROTECTED_ENTRIES,
    SPEC_KITTY_GITIGNORE_MARKER,
    GitignorePathError,
    read_gitignore_text,
    write_gitignore_text,
)

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

# The old manager emitted exactly ``.cursor/`` among these registry-backed
# rows. A blanket variant or a row outside this marker-labelled block has no
# trustworthy Spec Kitty provenance and must remain operator-owned.
_LEGACY_MANAGED_CURSOR_ENTRY = ".cursor/"
_LEGACY_CURSOR_PREDECESSOR = ".gemini/"
_LEGACY_CURSOR_SUCCESSOR = ".qwen/"
_KNOWN_MANAGED_ENTRIES = frozenset(
    [
        *(entry.directory for entry in AGENT_DIRECTORIES),
        *RUNTIME_PROTECTED_ENTRIES,
        _LEGACY_MANAGED_CURSOR_ENTRY,
    ]
)


def _is_blanket_cursor_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    return bool(_BLANKET_PATTERN.match(stripped))


def _is_historical_managed_cursor_position(lines: list[str], index: int) -> bool:
    """Prove the legacy row by its exact deterministic manager neighbours."""
    return (
        0 < index < len(lines) - 1
        and lines[index].strip() == _LEGACY_MANAGED_CURSOR_ENTRY
        and lines[index - 1].strip() == _LEGACY_CURSOR_PREDECESSOR
        and lines[index + 1].strip() == _LEGACY_CURSOR_SUCCESSOR
    )


def _classify_blanket_lines(content: str) -> tuple[list[int], list[str]]:
    """Return owned line indexes and preserved, unattributed blanket rows."""
    owned_indexes: list[int] = []
    unowned_lines: list[str] = []
    in_managed_block = False
    lines = content.splitlines(keepends=True)

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == SPEC_KITTY_GITIGNORE_MARKER:
            in_managed_block = True
            continue
        if not stripped:
            continue
        if stripped.startswith("#"):
            in_managed_block = False
            continue
        if _is_blanket_cursor_line(line):
            if in_managed_block and _is_historical_managed_cursor_position(lines, index):
                owned_indexes.append(index)
            else:
                unowned_lines.append(line)
            continue
        if in_managed_block and stripped not in _KNOWN_MANAGED_ENTRIES:
            # An operator-authored entry ends the provable manager-owned run.
            in_managed_block = False

    return owned_indexes, unowned_lines


def _read_gitignore(gitignore_path: Path) -> str:
    return read_gitignore_text(gitignore_path) or ""


def _strip_owned_blanket_lines(lines: list[str], owned_indexes: set[int]) -> tuple[list[str], int]:
    """Drop blanket lines, closing only the hole each removal leaves behind.

    When a removed line sat between two blank lines, the trailing blank is
    dropped so the removal does not create a new double-blank run at that
    spot. Blank-line runs elsewhere in the operator's file are untouched.
    """
    kept: list[str] = []
    removed = 0
    just_removed = False
    for index, line in enumerate(lines):
        if index in owned_indexes:
            removed += 1
            just_removed = True
            continue
        if just_removed and not line.strip() and kept and not kept[-1].strip():
            continue
        just_removed = False
        kept.append(line)
    return kept, removed


def _append_missing_entries(content: str, entries: list[str]) -> str:
    """Append manager rows in memory, preserving the existing newline style."""
    if not entries:
        return content

    newline = "\r\n" if "\r\n" in content else "\n"
    updated = content
    lines = content.splitlines()
    if SPEC_KITTY_GITIGNORE_MARKER not in lines:
        if updated and not updated.endswith(("\n", "\r")):
            updated += newline
        if updated and lines and lines[-1].strip():
            updated += newline
        updated += SPEC_KITTY_GITIGNORE_MARKER + newline
    elif updated and not updated.endswith(("\n", "\r")):
        updated += newline

    return updated + "".join(f"{entry}{newline}" for entry in entries)


def _build_updated_content(
    content: str,
    owned_indexes: list[int],
    missing_entries: list[str],
) -> tuple[str, int]:
    kept, removed = _strip_owned_blanket_lines(
        content.splitlines(keepends=True),
        set(owned_indexes),
    )
    return _append_missing_entries("".join(kept), missing_entries), removed


def _missing_narrow_entries(gitignore_path: Path) -> list[str]:
    content = read_gitignore_text(gitignore_path)
    if content is None:
        return list(_NARROW_ENTRIES)
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
        try:
            content = _read_gitignore(gitignore_path)
            owned_indexes, unowned_lines = _classify_blanket_lines(content)
            if owned_indexes or unowned_lines:
                return True
            return bool(_missing_narrow_entries(gitignore_path))
        except (GitignorePathError, OSError):
            # Route unsafe/unreadable files through can_apply() so upgrade
            # records a loud failure rather than silently skipping it.
            return True

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if not project_path.exists():
            return False, f"Project path does not exist: {project_path}"

        gitignore_path = project_path / ".gitignore"
        try:
            _read_gitignore(gitignore_path)
            return True, ""
        except (GitignorePathError, OSError) as e:
            return False, f".gitignore is not readable: {e}"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        gitignore_path = project_path / ".gitignore"
        try:
            content = _read_gitignore(gitignore_path)
            content_lines = content.splitlines(keepends=True)
            owned_indexes, unowned_lines = _classify_blanket_lines(content)
            owned_lines = [content_lines[index] for index in owned_indexes]
            missing = _missing_narrow_entries(gitignore_path)
        except (GitignorePathError, OSError) as exc:
            return MigrationResult(success=False, errors=[str(exc)])

        warnings = [
            f"Preserved operator-owned blanket .cursor rule '{line.strip()}'; remove it manually to make other .cursor files stageable." for line in unowned_lines
        ]

        if dry_run:
            changes = [f"Would remove managed blanket line: '{line.strip()}'" for line in owned_lines]
            changes.extend(f"Would add gitignore entry: {entry}" for entry in missing)
            if not changes:
                changes.append("No managed blanket .cursor/ entry and narrow entries already present")
            return MigrationResult(
                success=True,
                changes_made=changes,
                warnings=warnings,
                manual_review_required=bool(warnings),
                preserved_paths=[str(gitignore_path)] if warnings else [],
            )

        updated_content, removed = _build_updated_content(content, owned_indexes, missing)
        try:
            if updated_content != content:
                write_gitignore_text(gitignore_path, updated_content)
        except (GitignorePathError, OSError) as exc:
            return MigrationResult(success=False, errors=[str(exc)])

        applied_changes: list[str] = []
        if removed:
            applied_changes.extend(f"Removed managed blanket line: '{line.strip()}'" for line in owned_lines)

        if missing:
            applied_changes.extend(f"Added gitignore entry: {entry}" for entry in missing)

        if not applied_changes:
            applied_changes.append("No managed blanket .cursor/ entry and narrow entries already present")

        return MigrationResult(
            success=True,
            changes_made=applied_changes,
            warnings=warnings,
            manual_review_required=bool(warnings),
            preserved_paths=[str(gitignore_path)] if warnings else [],
        )
