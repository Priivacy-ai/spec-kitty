"""Migration: backfill ``.worktrees/`` gitignore coverage (#3689).

Every mission worktree is a full checkout under ``.worktrees/<slug>-<mid8>``
(``core/constants.py::WORKTREES_DIR``), but the only code that ever excluded
that root from git was migration ``0.13.1_exclude_worktrees`` -- which writes
the local-only ``.git/info/exclude`` and, by ``target_version``, never runs
for a project stamped >= 0.13.1. Every project initialised since then has an
unignored ``.worktrees/``: the first worktree makes the main checkout's
``git status`` show ``?? .worktrees/`` forever, and a stray ``git add -A``
stages an entire nested checkout. Parts of the codebase already assume the
root is ignored (``agent/workflow.py`` FR-002(b), ``workflow_executor.py``).

Fresh ``init`` now emits the entry via the ``worktrees_root`` state-contract
surface (``get_runtime_gitignore_entries()``); this migration heals
already-initialised projects. A pre-0.13.1 project whose ``.git/info/exclude``
already covers the root gets a redundant-but-harmless ``.gitignore`` entry --
an improvement, since ``.gitignore`` travels with clones and ``info/exclude``
does not.

Sibling to ``3.2.6rc3_lint_report_gitignore_backfill`` (#3435) and the
``3.2.4``/``3.2.5`` backfills. Following the same precedent, the entry is
**hardcoded here** rather than sourced from the live contract so the
migration's behaviour is frozen and deterministic regardless of future
contract changes.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.gitignore_manager import (
    GitignoreManager,
    GitignorePathError,
    is_gitignore_root_effectively_ignored,
)

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

_WORKTREES_ENTRY = ".worktrees/"
_WORKTREES_PROBE = ".worktrees/.spec-kitty-ignore-probe"
# Any of these forms is a whole-root rule. Coverage also requires that no
# later negation can re-include a narrower descendant.
_EQUIVALENT_ENTRIES: frozenset[str] = frozenset({".worktrees", ".worktrees/", "/.worktrees/", "/.worktrees"})


def _needs_backfill(project_path: Path) -> bool:
    return not is_gitignore_root_effectively_ignored(
        project_path,
        root_path=".worktrees",
        equivalent_entries=_EQUIVALENT_ENTRIES,
        probe_path=_WORKTREES_PROBE,
    )


@MigrationRegistry.register
class WorktreesGitignoreBackfillMigration(BaseMigration):
    """Ensure the ``.worktrees/`` execution-worktrees root is gitignored."""

    migration_id = "3.2.6rc3_worktrees_gitignore_backfill"
    description = "Backfill .worktrees/ gitignore coverage (#3689)"
    target_version = "3.2.6rc3"

    def detect(self, project_path: Path) -> bool:
        try:
            return _needs_backfill(project_path)
        except (GitignorePathError, OSError):
            # Route unsafe/unreadable files through can_apply() so the runner
            # records a loud migration failure instead of silently skipping it.
            return True

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if not project_path.exists():
            return False, f"Project path does not exist: {project_path}"
        try:
            _needs_backfill(project_path)
        except (GitignorePathError, OSError) as exc:
            return False, str(exc)
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        try:
            missing = _needs_backfill(project_path)
        except (GitignorePathError, OSError) as exc:
            return MigrationResult(success=False, errors=[str(exc)])

        if dry_run:
            if missing:
                return MigrationResult(
                    success=True,
                    changes_made=[f"Would add {_WORKTREES_ENTRY} to .gitignore"],
                )
            return MigrationResult(success=True, changes_made=[])

        if not missing:
            return MigrationResult(success=True, changes_made=["gitignore entry already present"])

        try:
            # Force-append is required when an earlier canonical rule is
            # neutralized by a later negation. Reasserting at EOF preserves
            # user-authored rules while making the managed protection effective.
            GitignoreManager(project_path).ensure_entries([_WORKTREES_ENTRY], force_append=True)
        except (GitignorePathError, OSError) as exc:
            return MigrationResult(success=False, errors=[str(exc)])

        try:
            if _needs_backfill(project_path):
                return MigrationResult(
                    success=False,
                    errors=[".worktrees/ is still not effectively gitignored after backfill"],
                )
        except (GitignorePathError, OSError) as exc:
            return MigrationResult(success=False, errors=[str(exc)])
        return MigrationResult(
            success=True,
            changes_made=[f"Added gitignore entry: {_WORKTREES_ENTRY}"],
        )
