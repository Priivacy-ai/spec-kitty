"""Bootstrap user-global canonical slash commands for all configured agents.

On every CLI startup, ``ensure_global_agent_commands()`` installs all 16
consumer-facing command files (9 prompt-driven + 7 CLI-driven shims) into the
user-global agent command roots:

    ~/.claude/commands/
    ~/.gemini/commands/
    ~/.github/prompts/
    ... (one directory per configured agent)

This mirrors ``ensure_global_agent_skills()`` exactly — same version-lock
mechanism, same exclusive-lock concurrency guard, same read-only output files.

See ADR ``architecture/2.x/adr/2026-04-07-1-global-slash-command-installation.md``
for the design rationale.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from specify_cli.runtime.bootstrap import _get_cli_version, _lock_exclusive
from specify_cli.runtime.home import get_kittify_home, get_package_asset_root

logger = logging.getLogger(__name__)

_VERSION_FILENAME = "agent-commands.lock"
_LOCK_FILENAME = ".agent-commands.lock"
_MISSION_NAME = "software-dev"


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def get_global_command_dir(agent_key: str) -> Path:
    """Return the user-global command directory for *agent_key*.

    Mirrors the project-local ``AGENT_COMMAND_CONFIG[agent_key]["dir"]`` path
    beneath the user's home directory unless the agent has a documented
    user-global config root.  For example::

        "claude" → ~/.claude/commands/
        "gemini" → ~/.gemini/commands/
        "copilot" → ~/.github/prompts/
        "opencode" → ~/.config/opencode/commands/
    """
    from specify_cli.core.config import AGENT_COMMAND_CONFIG

    if agent_key == "opencode":
        custom_config_dir = os.environ.get("OPENCODE_CONFIG_DIR")
        if custom_config_dir:
            return Path(custom_config_dir).expanduser() / "commands"

        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            return Path(xdg_config_home).expanduser() / "opencode" / "commands"

        return Path.home() / ".config" / "opencode" / "commands"

    config = AGENT_COMMAND_CONFIG[agent_key]
    return Path.home() / config["dir"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_command_templates_dir() -> Path | None:
    """Return the command-templates directory for the current CLI version.

    Resolution order:
    1. Package-bundled assets (highest priority, always matches CLI version).
    2. Global runtime (``~/.kittify/missions/software-dev/command-templates/``).
    """
    try:
        pkg_root = get_package_asset_root()
        pkg_templates = pkg_root / _MISSION_NAME / "command-templates"
        if pkg_templates.is_dir():
            return pkg_templates
    except FileNotFoundError:
        pass

    runtime_templates = get_kittify_home() / "missions" / _MISSION_NAME / "command-templates"
    if runtime_templates.is_dir():
        return runtime_templates

    return None


def _resolve_script_type() -> str:
    """Return the platform-appropriate script type string."""
    return "ps" if os.name == "nt" else "sh"


def _compute_output_filename(command: str, agent_key: str) -> str:
    """Return the on-disk filename for *command* rendered for *agent_key*."""
    from specify_cli.core.config import AGENT_COMMAND_CONFIG

    config = AGENT_COMMAND_CONFIG.get(agent_key)
    if config is None:
        return f"spec-kitty.{command}.md"

    ext: str = config["ext"]
    stem = command
    if agent_key == "codex":
        stem = stem.replace("-", "_")
    if ext:
        return f"spec-kitty.{stem}.{ext}"
    return f"spec-kitty.{stem}"


def _sync_agent_commands(agent_key: str, templates_dir: Path, script_type: str) -> None:
    """Install all 16 command files for *agent_key* into its global root.

    * Prompt-driven commands (9): rendered from full template files via
      ``render_command_template()``.
    * CLI-driven commands (7): thin shims via ``generate_shim_content()``.
    * Stale ``spec-kitty.*`` files no longer in the canonical set are removed.
    * All written files are set read-only (``chmod mode & ~0o222``).

    ``codex`` and ``vibe`` are not handled here. Their command installation
    is driven by ``init`` and ``spec-kitty agent config add`` through
    :mod:`specify_cli.skills.command_installer`, which writes project-local
    skill packages under ``.agents/skills/``.
    """
    from specify_cli.core.config import AGENT_COMMAND_CONFIG
    from specify_cli.shims.generator import generate_shim_content_for_agent
    from specify_cli.shims.registry import CLI_DRIVEN_COMMANDS, PROMPT_DRIVEN_COMMANDS
    from specify_cli.template.asset_generator import render_command_template

    config = AGENT_COMMAND_CONFIG.get(agent_key)
    if config is None:
        logger.debug("No command config for agent %r; skipping", agent_key)
        return

    output_dir = get_global_command_dir(agent_key)
    output_dir.mkdir(parents=True, exist_ok=True)

    canonical_filenames: set[str] = set()

    # --- Prompt-driven commands ---
    for template_path in sorted(templates_dir.glob("*.md")):
        command = template_path.stem
        if command not in PROMPT_DRIVEN_COMMANDS:
            continue
        filename = _compute_output_filename(command, agent_key)
        canonical_filenames.add(filename)
        try:
            content = render_command_template(
                template_path=template_path,
                script_type=script_type,
                agent_key=agent_key,
                arg_format=config["arg_format"],
                extension=config["ext"],
            )
        except Exception:
            logger.warning(
                "Failed to render prompt command %r for agent %r",
                command,
                agent_key,
                exc_info=True,
            )
            continue
        out_path = output_dir / filename
        if out_path.exists():
            out_path.chmod(out_path.stat().st_mode | 0o222)
        out_path.write_text(content, encoding="utf-8")
        out_path.chmod(out_path.stat().st_mode & ~0o222)

    # --- CLI-driven shims ---
    for command in sorted(CLI_DRIVEN_COMMANDS):
        filename = _compute_output_filename(command, agent_key)
        canonical_filenames.add(filename)
        try:
            content = generate_shim_content_for_agent(command, agent_key)
        except Exception:
            logger.warning(
                "Failed to generate shim %r for agent %r",
                command,
                agent_key,
                exc_info=True,
            )
            continue
        out_path = output_dir / filename
        if out_path.exists():
            out_path.chmod(out_path.stat().st_mode | 0o222)
        out_path.write_text(content, encoding="utf-8")
        out_path.chmod(out_path.stat().st_mode & ~0o222)

    # --- Remove stale spec-kitty.* files no longer in canonical set ---
    for existing in output_dir.iterdir():
        if existing.name.startswith("spec-kitty.") and existing.name not in canonical_filenames:
            try:
                existing.chmod(existing.stat().st_mode | 0o222)
                existing.unlink()
            except OSError:
                logger.debug("Could not remove stale command file %s", existing)


# ---------------------------------------------------------------------------
# Public bootstrap entry point
# ---------------------------------------------------------------------------


def ensure_global_agent_commands() -> None:
    """Ensure user-global command files are installed for the current CLI version.

    Called unconditionally at every CLI startup (in ``main_callback()``).
    Uses a version-lock fast path so the cost of a no-op call is a single
    file read.  An exclusive file lock guards the slow path against concurrent
    CLI invocations.
    """
    templates_dir = _get_command_templates_dir()
    if templates_dir is None:
        logger.debug("Command templates not found; skipping global command installation")
        return

    kittify_home = get_kittify_home()
    kittify_home.mkdir(parents=True, exist_ok=True)
    cache_dir = kittify_home / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    version_file = cache_dir / _VERSION_FILENAME
    cli_version = _get_cli_version()
    if version_file.exists() and version_file.read_text().strip() == cli_version:
        return

    lock_path = cache_dir / _LOCK_FILENAME
    lock_fd = open(lock_path, "w")  # noqa: SIM115
    try:
        _lock_exclusive(lock_fd)
        # Re-check after acquiring lock (another process may have finished).
        if version_file.exists() and version_file.read_text().strip() == cli_version:
            return

        from specify_cli.core.config import AGENT_COMMAND_CONFIG

        script_type = _resolve_script_type()
        for agent_key in AGENT_COMMAND_CONFIG:
            try:
                _sync_agent_commands(agent_key, templates_dir, script_type)
            except Exception:
                logger.warning(
                    "Failed to install global commands for agent %r",
                    agent_key,
                    exc_info=True,
                )

        # Write version last — an incomplete run leaves no version file,
        # so the next invocation will retry the full sync.
        version_file.write_text(cli_version)
    finally:
        lock_fd.close()
