"""Migration: normalize managed command files around the global command pack."""

from __future__ import annotations

from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


def _configured_agents(project_path: Path) -> list[str]:
    from specify_cli.core.agent_config import load_agent_config

    try:
        return list(load_agent_config(project_path).available)
    except Exception:
        return []


@MigrationRegistry.register
class GlobalizeCommandPackMigration(BaseMigration):
    """Project managed command files from the global canonical pack."""

    migration_id = "3.0.3_globalize_command_pack"
    description = "Project managed command files from the global canonical pack and retire legacy Codex prompts"
    target_version = "3.0.3"

    def detect(self, project_path: Path) -> bool:
        if not (project_path / ".kittify").is_dir():
            return False
        from specify_cli.runtime.agent_commands import project_command_install_needed

        agents = _configured_agents(project_path)
        if not agents:
            return False

        return any(project_command_install_needed(project_path, agent_key) for agent_key in agents)

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if not (project_path / ".kittify").is_dir():
            return False, ".kittify/ directory does not exist (not initialized)"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        from specify_cli.runtime.agent_commands import (
            ensure_global_agent_commands,
            install_project_commands_for_agent,
        )

        agents = _configured_agents(project_path)
        changes: list[str] = []
        warnings: list[str] = []

        if not agents:
            warnings.append("No configured agents found; skipping managed command normalization")
            return MigrationResult(success=True, changes_made=changes, warnings=warnings)

        if dry_run:
            changes.append(f"Would normalize managed command files for {len(agents)} configured agent(s)")
            return MigrationResult(success=True, changes_made=changes, warnings=warnings)

        ensure_global_agent_commands()

        for agent_key in agents:
            result = install_project_commands_for_agent(project_path, agent_key)
            written = len(result.files_written)
            removed = len(result.files_removed)
            changes.append(
                f"{agent_key}: mode={result.mode}, linked={written}, retired={removed}"
            )

        return MigrationResult(success=True, changes_made=changes, warnings=warnings)
