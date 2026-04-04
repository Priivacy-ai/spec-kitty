"""Generate thin 3-line shim markdown files for all configured agents.

Each generated file contains exactly:
  1. A version marker comment.
  2. An invariant instruction line.
  3. A prohibition line.
  4. A CLI call that passes all arguments through.

No workflow logic is embedded in shim files.  All resolution and
dispatch logic lives in the CLI (see :mod:`specify_cli.shims.entrypoints`
and :mod:`specify_cli.cli.commands.shim`).
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.agent_utils.directories import (
    AGENT_DIR_TO_KEY,
    get_command_agent_dirs_for_project,
    get_agent_dirs_for_project,
)
from specify_cli.shims.registry import CLI_DRIVEN_COMMANDS


def _get_cli_version() -> str:
    """Return the current CLI version string."""
    try:
        from importlib.metadata import version

        return version("spec-kitty-cli")
    except Exception:
        from specify_cli import __version__

        return __version__

# Agent-specific argument placeholders.
# Claude Code passes slash-command arguments as $ARGUMENTS.
# Codex passes the prompt text as $PROMPT.
# All other agents default to $ARGUMENTS.
AGENT_ARG_PLACEHOLDERS: dict[str, str] = {
    "claude": "$ARGUMENTS",
    "codex": "$PROMPT",
}

_DEFAULT_ARG_PLACEHOLDER = "$ARGUMENTS"


def _get_arg_placeholder(agent_key: str) -> str:
    """Return the arg placeholder for *agent_key*."""
    return AGENT_ARG_PLACEHOLDERS.get(agent_key, _DEFAULT_ARG_PLACEHOLDER)


def generate_shim_content(command: str, agent_name: str, arg_placeholder: str) -> str:
    """Return the shim markdown body with version marker.

    The format is invariant across all skills and agents except for the
    ``arg_placeholder`` substitution.  The first line is always a
    ``<!-- spec-kitty-command-version: X.Y.Z -->`` marker so migrations
    and doctor checks can detect stale files.

    Args:
        command:         Skill verb, e.g. ``"implement"``.
        agent_name:      Agent key, e.g. ``"claude"``.
        arg_placeholder: Runtime variable name, e.g. ``"$ARGUMENTS"``.

    Returns:
        A multi-line string ready to write as a ``.md`` file.
    """
    version = _get_cli_version()
    return (
        f"<!-- spec-kitty-command-version: {version} -->\n"
        "Run this exact command and treat its output as authoritative.\n"
        "Do not rediscover context from branches, files, or prompt contents.\n"
        "\n"
        f'`spec-kitty agent shim {command} --agent {agent_name} --raw-args "{arg_placeholder}"`\n'
    )


def generate_all_shims(repo_root: Path) -> list[Path]:
    """Generate shim files for all configured agents and CLI-driven skills.

    Uses :func:`~specify_cli.agent_utils.directories.get_agent_dirs_for_project`
    to honour the project's agent configuration.  Only skills in
    :data:`~specify_cli.shims.registry.CLI_DRIVEN_COMMANDS` are written —
    prompt-driven commands are intentionally skipped because their full
    prompt template files handle the workflow directly.

    Existing shim files are overwritten; directories that do not exist are
    created.

    Args:
        repo_root: Absolute path to the project root.

    Returns:
        Sorted list of paths written.
    """
    cli_skills = sorted(CLI_DRIVEN_COMMANDS)
    agent_dirs = get_command_agent_dirs_for_project(repo_root)
    written: list[Path] = []

    for agent_root, command_subdir in agent_dirs:
        agent_key = AGENT_DIR_TO_KEY.get(agent_root, agent_root.lstrip("."))
        target_dir = repo_root / agent_root / command_subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        written.extend(generate_shims_for_agent_dir(target_dir, agent_key, cli_skills))

    return sorted(written)


def generate_shims_for_agent_dir(
    target_dir: Path,
    agent_key: str,
    cli_skills: list[str] | None = None,
) -> list[Path]:
    """Generate CLI-driven shim files for one agent directory."""
    skills = sorted(cli_skills or CLI_DRIVEN_COMMANDS)
    arg_placeholder = _get_arg_placeholder(agent_key)
    written: list[Path] = []

    for skill in skills:
        filename = f"spec-kitty.{skill}.md"
        content = generate_shim_content(skill, agent_key, arg_placeholder)
        out_path = target_dir / filename
        out_path.write_text(content, encoding="utf-8")
        written.append(out_path)

    return written
