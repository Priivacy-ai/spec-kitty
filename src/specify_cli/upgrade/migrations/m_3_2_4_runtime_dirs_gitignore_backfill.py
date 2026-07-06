"""Migration: backfill ``.kittify/migrations/`` + ``.kittify/logs/`` gitignore (#2384).

Sibling to ``3.2.4_derived_mission_views_gitignore_backfill`` (#2369). Two more
generated ``.kittify/`` subtrees are registered ``IGNORED`` state surfaces — so a
fresh ``spec-kitty init`` gitignores them — but already-initialised projects had
no backfill for them, so they showed up untracked and failed ``spec-kitty
accept``'s ``git_dirty`` check:

- ``.kittify/migrations/`` — mission-state repair manifests + quarantine backups
  (write-only local audit/recovery output).
- ``.kittify/logs/`` — per-WP implementation/review console logs (orchestrator).

This backfill adds both directory entries to ``.gitignore`` for projects that
lack them. Following the ``3.2.3_encoding_provenance`` precedent, the entries are
**hardcoded here** rather than sourced from the live contract so the migration's
behaviour is frozen and deterministic regardless of future contract changes.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.gitignore_manager import GitignoreManager

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

# Canonical (trailing-slash) entries this migration ensures.
_RUNTIME_DIR_ENTRIES: tuple[str, ...] = (
    ".kittify/migrations/",
    ".kittify/logs/",
)
# A hand-added entry without the trailing slash ignores the same directory, so
# treat either form as already-present — the backfill stays idempotent and never
# appends a duplicate beside a user's slash-less variant.
_EQUIVALENT_ENTRIES: dict[str, frozenset[str]] = {
    entry: frozenset({entry, entry.rstrip("/")}) for entry in _RUNTIME_DIR_ENTRIES
}


def _read_gitignore_entries(project_path: Path) -> set[str]:
    gitignore_path = project_path / ".gitignore"
    if not gitignore_path.exists():
        return set()
    return {
        line.strip()
        for line in gitignore_path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def _missing_entries(present: set[str]) -> list[str]:
    return [
        entry
        for entry in _RUNTIME_DIR_ENTRIES
        if _EQUIVALENT_ENTRIES[entry].isdisjoint(present)
    ]


@MigrationRegistry.register
class RuntimeDirsGitignoreBackfillMigration(BaseMigration):
    """Ensure ``.kittify/migrations/`` and ``.kittify/logs/`` are gitignored."""

    migration_id = "3.2.4_runtime_dirs_gitignore_backfill"
    description = "Backfill .kittify/migrations/ and .kittify/logs/ gitignore coverage"
    target_version = "3.2.4"

    def detect(self, project_path: Path) -> bool:
        return bool(_missing_entries(_read_gitignore_entries(project_path)))

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if not project_path.exists():
            return False, f"Project path does not exist: {project_path}"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        missing = _missing_entries(_read_gitignore_entries(project_path))

        if dry_run:
            changes = [f"Would add {entry} to .gitignore" for entry in missing]
            return MigrationResult(success=True, changes_made=changes)

        if not missing:
            return MigrationResult(
                success=True, changes_made=["gitignore entries already present"]
            )

        GitignoreManager(project_path).ensure_entries(missing)
        return MigrationResult(
            success=True,
            changes_made=[f"Added gitignore entries: {', '.join(missing)}"],
        )
