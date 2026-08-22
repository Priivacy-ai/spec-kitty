"""Migration: backfill ``.kittify/lint-report.json`` gitignore coverage (#3435).

``spec-kitty charter lint`` writes its decay-scan report to
``.kittify/lint-report.json`` as a side effect of what is otherwise a
read-only diagnostic. That surface is registered ``IGNORED`` in the state
contract (``charter_lint_report``), so a fresh ``spec-kitty init`` gitignores
it -- but already-initialised projects had no backfill for it. Running
``charter lint`` on such a project leaves the report untracked, which then
trips ``record-analysis``'s dirty-tree guard on a file the operator never
knowingly created.

Sibling to ``3.2.4_runtime_dirs_gitignore_backfill`` (#2384) and
``3.2.5_agents_skills_gitignore_backfill`` (#2412). Following the same
precedent, the entry is **hardcoded here** rather than sourced from the live
contract so the migration's behaviour is frozen and deterministic regardless
of future contract changes.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.gitignore_manager import (
    GitignoreManager,
    GitignorePathError,
    read_gitignore_text,
)

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

_LINT_REPORT_ENTRY = ".kittify/lint-report.json"
# Single file; no equivalent forms (unlike the sibling directory backfills,
# where `.foo` / `.foo/` / `/.foo/` all count). The frozenset keeps the same
# any-equivalent-form check shape as the siblings for consistency.
_EQUIVALENT_ENTRIES: frozenset[str] = frozenset({_LINT_REPORT_ENTRY})


def _read_gitignore_entries(project_path: Path) -> set[str]:
    gitignore_path = project_path / ".gitignore"
    content = read_gitignore_text(gitignore_path)
    if content is None:
        return set()
    return {line.strip() for line in content.splitlines() if line.strip() and not line.lstrip().startswith("#")}


def _is_missing(present: set[str]) -> bool:
    return _EQUIVALENT_ENTRIES.isdisjoint(present)


@MigrationRegistry.register
class LintReportGitignoreBackfillMigration(BaseMigration):
    """Ensure ``.kittify/lint-report.json`` is gitignored."""

    migration_id = "3.2.6rc3_lint_report_gitignore_backfill"
    description = "Backfill .kittify/lint-report.json gitignore coverage (#3435)"
    target_version = "3.2.6rc3"

    def detect(self, project_path: Path) -> bool:
        try:
            return _is_missing(_read_gitignore_entries(project_path))
        except (GitignorePathError, OSError):
            # Route unsafe/unreadable files through can_apply() so the runner
            # records a loud migration failure instead of silently skipping it.
            return True

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if not project_path.exists():
            return False, f"Project path does not exist: {project_path}"
        try:
            _read_gitignore_entries(project_path)
        except (GitignorePathError, OSError) as exc:
            return False, str(exc)
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        try:
            missing = _is_missing(_read_gitignore_entries(project_path))
        except (GitignorePathError, OSError) as exc:
            return MigrationResult(success=False, errors=[str(exc)])

        if dry_run:
            if missing:
                return MigrationResult(
                    success=True,
                    changes_made=[f"Would add {_LINT_REPORT_ENTRY} to .gitignore"],
                )
            return MigrationResult(success=True, changes_made=[])

        if not missing:
            return MigrationResult(success=True, changes_made=["gitignore entry already present"])

        try:
            GitignoreManager(project_path).ensure_entries([_LINT_REPORT_ENTRY])
        except (GitignorePathError, OSError) as exc:
            return MigrationResult(success=False, errors=[str(exc)])
        return MigrationResult(
            success=True,
            changes_made=[f"Added gitignore entry: {_LINT_REPORT_ENTRY}"],
        )
