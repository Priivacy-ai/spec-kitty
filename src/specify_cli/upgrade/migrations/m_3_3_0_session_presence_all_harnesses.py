"""Migration: install session presence orientation for all non-Claude harnesses.

Phase 2 counterpart to ``m_3_3_0_session_presence_claude_code.py`` (Phase 1).

Iterates over every entry in ``WRITER_REGISTRY`` except ``"claude"`` (which is
handled by Phase 1).  For each registered harness:

1. ``writer.can_write(project_path)`` — harness root exists in this project.
2. ``writer.has_presence(project_path)`` — orientation already written.

If ``can_write`` is True and ``has_presence`` is False, the orientation block
is written.  The migration is idempotent: re-running it after all blocks have
been written is a no-op.

``detect()`` returns ``True`` when *any* registered non-Claude harness needs its
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


@MigrationRegistry.register
class SessionPresenceAllHarnessesMigration(BaseMigration):
    """Backfill session presence orientation for all non-Claude harnesses."""

    migration_id = "3_3_0_session_presence_all_harnesses"
    description = (
        "Write session presence orientation to each configured harness "
        "(cursor, windsurf, copilot, roo, kiro, gemini, codex, opencode, "
        "antigravity, pi, vibe, letta, qwen, kilocode, auggie, q)"
    )
    target_version = "3.3.0"
    runs_on_worktrees = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _iter_pending(project_path: Path) -> list[str]:
        """Return harness keys that need orientation written.

        A harness is pending when ``can_write()`` is True and
        ``has_presence()`` is False.
        """
        from specify_cli.session_presence.writers.registry import WRITER_REGISTRY

        pending: list[str] = []
        for key, writer in WRITER_REGISTRY.items():
            if key in _PHASE1_KEYS:
                continue
            if writer.can_write(project_path) and not writer.has_presence(project_path):
                pending.append(key)
        return pending

    # ------------------------------------------------------------------
    # BaseMigration interface
    # ------------------------------------------------------------------

    def detect(self, project_path: Path) -> bool:
        """Return ``True`` when any non-Claude harness needs orientation written."""
        if not (project_path / ".kittify").is_dir():
            return False
        return bool(self._iter_pending(project_path))

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check that the project is initialized before applying."""
        if not (project_path / ".kittify").is_dir():
            return False, ".kittify/ directory does not exist (not initialized)"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Write orientation for every harness that needs it.

        Iterates ``WRITER_REGISTRY``, skips ``"claude"`` (Phase 1), skips any
        harness whose presence is already written, and writes the rest.
        Idempotent — safe to call multiple times.
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
        from specify_cli.session_presence.writers.registry import WRITER_REGISTRY

        agent_config = load_agent_config(project_path)
        manager = SessionPresenceManager(project_path, agent_config)
        content = manager._build_content()

        applied: list[str] = []
        for key in pending:
            writer = WRITER_REGISTRY[key]
            # Re-check idempotency inside the write loop in case a concurrent
            # call already wrote during this run.
            if writer.has_presence(project_path):
                continue
            writer.write(project_path, content)
            applied.append(f"Wrote session presence orientation for harness: {key}")

        return MigrationResult(success=True, changes_made=applied)
