"""Migration 3.2.2: Safe removal of per-project spec-kitty command files.

This migration supersedes the safety behavior of 3.1.2_globalize_commands.
It removes per-project spec-kitty.* command files ONLY when:
  1. The global runtime (~/.kittify/missions/) is present
  2. The global agent command directory has spec-kitty.* files for that agent
  3. The local file has a <!-- spec-kitty-command-version: ... --> header

If any invariant fails for an agent, that agent is skipped entirely and a
warning is added to the changes list. No exceptions are raised.

Non-spec-kitty files (no version header) are never touched.

Idempotency
-----------
A project with no spec-kitty.* command files returns detect() == False
and is skipped without filesystem changes.
"""

from __future__ import annotations

from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult
from .m_0_9_1_complete_lane_migration import get_agent_dirs_for_project
from specify_cli.runtime.home import get_kittify_home

_VERSION_MARKER_PREFIX = "<!-- spec-kitty-command-version:"


@MigrationRegistry.register
class SafeGlobalizeCommandsMigration(BaseMigration):
    """Safe per-project command removal with global-presence verification."""

    migration_id = "3.2.2_safe_globalize_commands"
    description = "Safely remove per-project spec-kitty command files (with global checks)"
    target_version = "3.2.2"

    def detect(self, project_path: Path) -> bool:
        """Return True if any spec-kitty.* command file exists in any agent command dir."""
        for agent_root, subdir in get_agent_dirs_for_project(project_path):
            agent_dir = project_path / agent_root / subdir
            if not agent_dir.is_dir():
                continue
            for f in agent_dir.iterdir():
                if f.name.startswith("spec-kitty."):
                    return True
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        return True, ""

    @staticmethod
    def _global_runtime_present() -> bool:
        """Check if the global runtime missions/ dir exists and has at least one subdir.

        Uses get_kittify_home() so SPEC_KITTY_HOME overrides are respected in
        tests, CI, and custom installation layouts — exactly as init/ensure_runtime do.
        """
        try:
            missions_dir = get_kittify_home() / "missions"
        except Exception:
            return False
        if not missions_dir.is_dir():
            return False
        return any(p.is_dir() for p in missions_dir.iterdir())

    @staticmethod
    def _global_command_file_present(agent_root: str, subdir: str, filename: str) -> bool:
        """Check that a specific command file exists in the global agent command dir.

        Verifies per-filename presence rather than 'at least one file exists',
        because ensure_global_agent_commands() tolerates per-command render failures.
        A partial global install must not cause local-only commands to be deleted.
        """
        try:
            global_agent_dir = Path.home() / agent_root / subdir
        except Exception:
            return False
        return (global_agent_dir / filename).is_file()

    @staticmethod
    def _is_generated_file(path: Path) -> bool:
        """Return True if the file's first line is a spec-kitty version marker."""
        try:
            first_line = path.read_text(encoding="utf-8").split("\n", 1)[0]
            return first_line.strip().startswith(_VERSION_MARKER_PREFIX)
        except (OSError, UnicodeDecodeError):
            return False

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        changes: list[str] = []

        # Invariant 1: global runtime must be present
        if not self._global_runtime_present():
            changes.append(
                "Skipped all agents: global runtime (~/.kittify/missions/) not found. "
                "Run 'spec-kitty init' first."
            )
            return MigrationResult(success=True, changes_made=changes)

        for agent_root, subdir in get_agent_dirs_for_project(project_path):
            agent_dir = project_path / agent_root / subdir
            if not agent_dir.is_dir():
                continue

            # Find spec-kitty.* files in the local agent dir
            targets = sorted(f for f in agent_dir.iterdir() if f.name.startswith("spec-kitty."))

            for target in targets:
                rel = target.relative_to(project_path)

                # Invariant 2: global equivalent of this specific file must exist.
                # A partial global install (ensure_global_agent_commands tolerates
                # per-command failures) must not cause local-only commands to be lost.
                if not self._global_command_file_present(agent_root, subdir, target.name):
                    changes.append(
                        f"Skipped {rel}: no global equivalent at "
                        f"~/{agent_root}/{subdir}/{target.name}"
                    )
                    continue

                # Invariant 3: file must be spec-kitty-generated
                if not self._is_generated_file(target):
                    changes.append(f"Skipped {rel}: no version marker (user-authored file)")
                    continue

                if dry_run:
                    changes.append(f"Would remove: {rel}")
                else:
                    try:
                        target.chmod(target.stat().st_mode | 0o222)
                        target.unlink()
                        changes.append(f"Removed: {rel}")
                    except OSError as exc:
                        changes.append(f"Could not remove {rel}: {exc}")

        return MigrationResult(success=True, changes_made=changes)
