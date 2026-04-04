"""Rebuild managed agent command surfaces from the canonical runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RewriteResult:
    """Summary of a managed command rewrite pass."""

    agents_processed: int = 0
    files_written: list[Path] = field(default_factory=list)
    files_deleted: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def rewrite_agent_shims(repo_root: Path) -> RewriteResult:
    """Reinstall managed command files for every configured agent.

    This now delegates to the canonical command installer so each configured
    agent receives the same treatment as `spec-kitty init` and current-version
    upgrades:

    - command-capable agents project their managed files from the global
      canonical pack (or render project-local overrides when present)
    - Codex retires legacy `.codex/prompts/spec-kitty.*` files and relies on
      skills instead
    """
    from specify_cli.core.agent_config import AgentConfigError, load_agent_config
    from specify_cli.runtime.agent_commands import install_project_commands_for_agent

    result = RewriteResult()
    try:
        agents = list(load_agent_config(repo_root).available)
    except AgentConfigError:
        return result

    for agent_key in agents:
        install_result = install_project_commands_for_agent(repo_root, agent_key)
        result.agents_processed += 1
        result.files_written.extend(install_result.files_written)
        result.files_deleted.extend(install_result.files_removed)

    result.files_written = sorted(result.files_written)
    result.files_deleted = sorted(result.files_deleted)
    return result
