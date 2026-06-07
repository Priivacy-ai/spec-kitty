"""Migration: install session presence orientation for all non-Claude harnesses.

Phase 2 counterpart to ``m_3_3_0_session_presence_claude_code.py`` (Phase 1).

Iterates over configured agents from ``.kittify/config.yaml`` (via
``load_agent_config``), excluding ``"claude"`` (handled by Phase 1).  For
each configured harness:

1. ``writer.can_write(project_path)`` — harness root exists in this project.
2. ``writer.has_presence(project_path)`` — orientation already written.

If ``can_write`` is True and ``has_presence`` is False, the orientation block
is written.  The migration is idempotent: re-running it after all blocks have
been written is a no-op.

Only agents listed in ``.kittify/config.yaml`` are processed (C-005).
Harness directories present on disk but not in config are ignored.

``detect()`` returns ``True`` when *any* configured non-Claude harness needs its
orientation written, allowing ``spec-kitty upgrade`` to surface the migration
only for projects where work remains.
"""

from __future__ import annotations

from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

# Harnesses fully covered by the Phase 1 migration — skip here to avoid
# double-applying and to preserve a clean separation of concerns.
_PHASE1_KEYS = frozenset({"claude"})


def _configured_non_phase1_keys(project_path: Path) -> list[str]:
    """Return agent keys from config.yaml that are not handled by Phase 1."""
    from specify_cli.core.agent_config import load_agent_config

    config = load_agent_config(project_path)
    return [k for k in (config.available if config else []) if k not in _PHASE1_KEYS]


@MigrationRegistry.register
class SessionPresenceAllHarnessesMigration(BaseMigration):
    """Backfill session presence orientation for all non-Claude configured harnesses."""

    migration_id = "3_3_0_session_presence_all_harnesses"
    description = (
        "Write session presence orientation to each configured non-Claude harness "
        "(only agents listed in .kittify/config.yaml are processed)"
    )
    target_version = "3.3.0"
    runs_on_worktrees = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _iter_pending(project_path: Path) -> list[str]:
        """Return configured harness keys that need orientation written.

        Only keys present in ``.kittify/config.yaml`` are considered (C-005).
        A harness is pending when ``can_write()`` is True and
        ``has_presence()`` is False.
        """
        from specify_cli.session_presence.writers.registry import get_writer

        pending: list[str] = []
        for key in _configured_non_phase1_keys(project_path):
            writer = get_writer(key)
            if writer.can_write(project_path) and not writer.has_presence(project_path):
                pending.append(key)
        return pending

    # ------------------------------------------------------------------
    # BaseMigration interface
    # ------------------------------------------------------------------

    def detect(self, project_path: Path) -> bool:
        """Return ``True`` when any configured non-Claude harness needs orientation written."""
        if not (project_path / ".kittify").is_dir():
            return False
        return bool(self._iter_pending(project_path))

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check that the project is initialized before applying."""
        if not (project_path / ".kittify").is_dir():
            return False, ".kittify/ directory does not exist (not initialized)"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Write orientation for every configured harness that needs it.

        Iterates configured agents from ``.kittify/config.yaml``, skips
        ``"claude"`` (Phase 1), skips any harness whose presence is already
        written, and writes the rest.  Idempotent — safe to call multiple times.
        """
        pending = self._iter_pending(project_path)

        if dry_run:
            dry_changes = [
                f"Would write session presence orientation for harness: {key}"
                for key in pending
            ]
            return MigrationResult(success=True, changes_made=dry_changes)

        if not pending:
            return MigrationResult(success=True, changes_made=[])

        from specify_cli.core.agent_config import load_agent_config
        from specify_cli.session_presence.manager import SessionPresenceManager
        from specify_cli.session_presence.writers.registry import get_writer

        agent_config = load_agent_config(project_path)
        manager = SessionPresenceManager(project_path, agent_config)
        content = manager._build_content()

        applied: list[str] = []
        for key in pending:
            writer = get_writer(key)
            # Re-check idempotency inside the write loop in case a concurrent
            # call already wrote during this run.
            if writer.has_presence(project_path):
                continue
            writer.write(project_path, content)
            applied.append(f"Wrote session presence orientation for harness: {key}")

        return MigrationResult(success=True, changes_made=applied)
