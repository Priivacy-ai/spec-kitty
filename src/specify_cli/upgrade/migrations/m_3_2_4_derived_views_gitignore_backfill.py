"""Migration: backfill ``.kittify/derived/`` gitignore coverage (#2369, Defect B).

``spec-kitty materialize`` writes regenerable machine-facing views (lifecycle /
board-summary / progress JSON) under ``.kittify/derived/<slug>/``. That surface
is registered as an ``IGNORED`` state surface (``derived_mission_views`` in
``state/contract.py``), so a fresh ``spec-kitty init`` emits ``.kittify/derived/``
into ``.gitignore`` via the full runtime entry set.

Existing projects, however, only receive gitignore repairs through the
per-entry runtime-hygiene migrations, none of which knew about
``.kittify/derived/``. So an already-initialised project that runs
``materialize`` (e.g. an orchestrator-completed mission) had the derived views
show up as untracked, dirtying the tree and failing ``spec-kitty accept``'s
``git_dirty`` check.

This backfill repairs that: it adds ``.kittify/derived/`` to ``.gitignore`` for
projects that lack it. Following the ``3.2.3_encoding_provenance`` precedent,
the entry is **hardcoded here** rather than sourced from the live contract so
the migration's behaviour is frozen and deterministic regardless of future
contract changes.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.gitignore_manager import GitignoreManager

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

_DERIVED_VIEWS_ENTRY = ".kittify/derived/"


def _read_gitignore_entries(project_path: Path) -> set[str]:
    gitignore_path = project_path / ".gitignore"
    if not gitignore_path.exists():
        return set()
    return {
        line.strip()
        for line in gitignore_path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


@MigrationRegistry.register
class DerivedViewsGitignoreBackfillMigration(BaseMigration):  # type: ignore[misc]
    """Ensure the regenerable ``.kittify/derived/`` views dir is gitignored."""

    migration_id = "3.2.4_derived_mission_views_gitignore_backfill"
    description = "Backfill .kittify/derived/ gitignore coverage"
    target_version = "3.2.4"

    def detect(self, project_path: Path) -> bool:
        return _DERIVED_VIEWS_ENTRY not in _read_gitignore_entries(project_path)

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if not project_path.exists():
            return False, f"Project path does not exist: {project_path}"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        already_present = _DERIVED_VIEWS_ENTRY in _read_gitignore_entries(project_path)

        if dry_run:
            changes = (
                []
                if already_present
                else [f"Would add {_DERIVED_VIEWS_ENTRY} to .gitignore"]
            )
            return MigrationResult(success=True, changes_made=changes)

        modified = GitignoreManager(project_path).ensure_entries([_DERIVED_VIEWS_ENTRY])
        changes = (
            [f"Added gitignore entry: {_DERIVED_VIEWS_ENTRY}"]
            if modified
            else ["gitignore entry already present"]
        )
        return MigrationResult(success=True, changes_made=changes)
