"""Bootstrap user-global canonical slash commands for all configured agents.

On every CLI startup, ``ensure_global_agent_commands()`` installs all 15
consumer-facing command files (8 prompt-driven + 7 CLI-driven shims) into the
user-global agent command roots:

    ~/.claude/commands/
    ~/.gemini/commands/
    ~/.github/prompts/
    ... (one directory per configured agent)

This mirrors ``ensure_global_agent_skills()`` exactly — same version-lock
mechanism, same exclusive-lock concurrency guard, same read-only output files.

See ADR ``docs/adr/3.x/2026-04-07-1-global-slash-command-installation.md``
for the design rationale.
"""

from __future__ import annotations

import logging
import os
import sys
from importlib.util import find_spec
from pathlib import Path

from specify_cli.core.config import DEFAULT_MISSION_KEY
from specify_cli.runtime.bootstrap import _get_cli_version, _lock_exclusive
from specify_cli.runtime.home import get_kittify_home

logger = logging.getLogger(__name__)

_VERSION_FILENAME = "agent-commands.lock"
_LOCK_FILENAME = ".agent-commands.lock"
_VERSION_MARKER_PREFIX = "<!-- spec-kitty-command-version:"
_VERSION_MARKER_HEAD_LINES = 20


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
    return Path.home() / str(config["dir"])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_command_templates_dir() -> Path:
    """Return the command-templates directory from the doctrine package.

    Uses import metadata rather than ``import doctrine`` so CLI startup does
    not execute doctrine's heavy validation imports before command dispatch.

    Raises ``FileNotFoundError`` if the doctrine package is absent, which
    indicates a corrupted install.
    """
    if os.environ.get("SPEC_KITTY_TEMPLATE_ROOT"):
        from specify_cli.runtime.home import get_package_asset_root

        package_asset_root = get_package_asset_root()
        legacy_command_templates = package_asset_root / DEFAULT_MISSION_KEY / "command-templates"
        if legacy_command_templates.exists():
            return legacy_command_templates

    loaded_doctrine = sys.modules.get("doctrine")
    loaded_file = getattr(loaded_doctrine, "__file__", None)
    if isinstance(loaded_file, str) and loaded_file:
        return Path(loaded_file).parent / "missions" / "mission-steps" / DEFAULT_MISSION_KEY

    try:
        spec = find_spec("doctrine")
    except (ModuleNotFoundError, ValueError):
        spec = None
    locations = list(spec.submodule_search_locations or ()) if spec is not None else []
    if not locations:
        raise FileNotFoundError("doctrine package has no search location; installation may be corrupted")
    doctrine_path = Path(locations[0])
    return doctrine_path / "missions" / "mission-steps" / DEFAULT_MISSION_KEY


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
    if ext:
        return f"spec-kitty.{stem}.{ext}"
    return f"spec-kitty.{stem}"


def _expected_command_filenames(agent_key: str, templates_dir: Path) -> set[str]:
    """Return the complete managed command filename set for *agent_key*.

    The prompt-driven half is only valid when its backing template is present.
    Missing templates therefore make the health check fail instead of allowing a
    partial command install to be stamped as current.
    """
    from specify_cli.shims.registry import CLI_DRIVEN_COMMANDS, PROMPT_DRIVEN_COMMANDS

    # Templates now live under per-step subdirectories: {step}/prompt.md
    template_commands = {
        step_dir.name
        for step_dir in templates_dir.iterdir()
        if step_dir.is_dir() and (step_dir / "prompt.md").is_file()
    }
    if not template_commands >= PROMPT_DRIVEN_COMMANDS:
        return set()

    return {
        _compute_output_filename(command, agent_key)
        for command in sorted(PROMPT_DRIVEN_COMMANDS | CLI_DRIVEN_COMMANDS)
    }


def _file_has_current_version_marker(path: Path, cli_version: str) -> bool:
    """Return True when *path* has this CLI version's managed marker."""
    expected = f"{_VERSION_MARKER_PREFIX} {cli_version} -->"
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    return any(
        line.strip() == expected
        for line in content.splitlines()[:_VERSION_MARKER_HEAD_LINES]
    )


def _agent_commands_healthy(agent_key: str, templates_dir: Path, cli_version: str) -> bool:
    """Return True when one agent's global command directory is complete."""
    expected = _expected_command_filenames(agent_key, templates_dir)
    if not expected:
        return False

    output_dir = get_global_command_dir(agent_key)
    if not output_dir.is_dir():
        return False

    existing = {
        path.name
        for path in output_dir.iterdir()
        if path.is_file() and path.name.startswith("spec-kitty.")
    }
    if existing != expected:
        return False

    return all(
        _file_has_current_version_marker(output_dir / filename, cli_version)
        for filename in expected
    )


def _all_global_agent_commands_healthy(
    templates_dir: Path,
    cli_version: str,
    agent_keys: list[str] | None = None,
) -> bool:
    """Return True when every command-layer agent has a complete command set."""
    from specify_cli.core.config import AGENT_COMMAND_CONFIG

    keys = agent_keys if agent_keys is not None else list(AGENT_COMMAND_CONFIG.keys())
    return all(
        _agent_commands_healthy(agent_key, templates_dir, cli_version)
        for agent_key in keys
    )


def _sync_agent_commands(agent_key: str, templates_dir: Path, script_type: str) -> None:
    """Install all 15 command files for *agent_key* into its global root.

    * Prompt-driven commands (8): rendered from per-step ``{step}/prompt.md``
      templates via ``render_command_template()``.
    * CLI-driven commands (7): thin shims via ``generate_shim_content()``.
    * Stale ``spec-kitty.*`` files no longer in the canonical set are removed.
    * All written files are set read-only (``chmod mode & ~0o222``).

    Command-skill agents such as ``codex``, ``vibe``, ``pi``, and ``letta`` are
    not handled here. Their command installation
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

    # --- Prompt-driven commands (per-step subdirectory layout) ---
    for step_dir in sorted(templates_dir.iterdir()):
        if not step_dir.is_dir():
            continue
        command = step_dir.name
        if command not in PROMPT_DRIVEN_COMMANDS:
            continue
        template_path = step_dir / "prompt.md"
        if not template_path.exists():
            logger.warning(
                "Step %r has no prompt.md; skipping command %r",
                str(step_dir),
                command,
            )
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


def ensure_global_agent_commands(*, agent_keys: list[str] | None = None) -> None:
    """Ensure user-global command files are installed for the current CLI version.

    Called unconditionally at every CLI startup (in ``main_callback()``).
    Uses a version-lock fast path so the cost of a no-op call is a single
    file read.  An exclusive file lock guards the slow path against concurrent
    CLI invocations.

    Args:
        agent_keys: Optional list of agent keys to scope the install to.
            Defaults to all agents in ``AGENT_COMMAND_CONFIG``.
            Pass a non-``None`` value to limit repair to specific agents
            (e.g., from ``doctor skills --fix``).
    """
    from specify_cli.core.config import AGENT_COMMAND_CONFIG

    templates_dir = _get_command_templates_dir()

    kittify_home = get_kittify_home()
    kittify_home.mkdir(parents=True, exist_ok=True)
    cache_dir = kittify_home / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    keys_to_process = agent_keys if agent_keys is not None else list(AGENT_COMMAND_CONFIG.keys())

    version_file = cache_dir / _VERSION_FILENAME
    cli_version = _get_cli_version()
    if (
        agent_keys is None  # skip fast path when scoped to specific agents
        and version_file.exists()
        and version_file.read_text().strip() == cli_version
        and _all_global_agent_commands_healthy(templates_dir, cli_version)
    ):
        return

    lock_path = cache_dir / _LOCK_FILENAME
    lock_fd = open(lock_path, "w")  # noqa: SIM115
    try:
        _lock_exclusive(lock_fd)
        # Re-check after acquiring lock (another process may have finished).
        if (
            agent_keys is None
            and version_file.exists()
            and version_file.read_text().strip() == cli_version
            and _all_global_agent_commands_healthy(templates_dir, cli_version)
        ):
            return

        script_type = _resolve_script_type()
        try:
            for agent_key in keys_to_process:
                _sync_agent_commands(agent_key, templates_dir, script_type)
        except Exception:
            logger.warning("Command sync failed; version lock not updated", exc_info=True)
            raise

        # Write version lock only after all agents synced successfully.
        # Scoped calls (agent_keys != None) never update the global lock.
        if agent_keys is None and _all_global_agent_commands_healthy(
            templates_dir, cli_version
        ):
            version_file.write_text(cli_version)
    finally:
        lock_fd.close()
