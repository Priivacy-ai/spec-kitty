"""Agent configuration management commands."""

from __future__ import annotations

import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from specify_cli.core.config import AGENT_COMMAND_CONFIG
from specify_cli.core.agent_config import (
    load_agent_config,
    save_agent_config,
    AgentConfig,
    AgentConfigError,
)
from specify_cli.runtime.agent_commands import get_global_command_dir
from specify_cli.upgrade.migrations.m_0_9_1_complete_lane_migration import (
    AGENT_DIR_TO_KEY,
    CompleteLaneMigration,
)
from specify_cli.tasks_support import find_repo_root

app = typer.Typer(
    name="config",
    help="Manage project AI agent configuration (add, remove, list agents)",
    no_args_is_help=True,
)
console = Console()

# Reverse mapping: key to (dir, subdir)
KEY_TO_AGENT_DIR = {
    AGENT_DIR_TO_KEY[agent_dir]: (agent_dir, subdir)
    for agent_dir, subdir in CompleteLaneMigration.AGENT_DIRS
    if agent_dir in AGENT_DIR_TO_KEY
}
SKILL_ONLY_AGENTS = {"codex", "vibe"}
GLOBAL_COMMAND_AGENTS = frozenset(AGENT_COMMAND_CONFIG)
VALID_AGENTS = set(AGENT_DIR_TO_KEY.values()) | SKILL_ONLY_AGENTS


def _display_path(path: Path) -> str:
    """Render paths compactly for CLI output."""
    try:
        rel = path.relative_to(Path.home())
        label = f"~/{rel.as_posix()}"
    except ValueError:
        label = path.as_posix()
    return label.rstrip("/") + "/"


def _agent_location(repo_root: Path, agent_key: str) -> tuple[Path | None, str, bool]:
    """Return the managed command/skill location for an agent."""
    if agent_key in GLOBAL_COMMAND_AGENTS:
        path = get_global_command_dir(agent_key)
        return path, f"{_display_path(path)} (global)", path.exists()

    if agent_key in SKILL_ONLY_AGENTS:
        path = repo_root / ".agents" / "skills"
        return path, ".agents/skills/ (project skills)", path.exists()

    agent_dir_info = KEY_TO_AGENT_DIR.get(agent_key)
    if agent_dir_info:
        agent_dir, subdir = agent_dir_info
        path = repo_root / agent_dir / subdir
        return path, f"{agent_dir}/{subdir}/", path.exists()

    return None, "unknown agent", False


def _project_agent_root(repo_root: Path, agent_key: str) -> Path | None:
    """Return the legacy project-local root for command-layer agents."""
    agent_dir_info = KEY_TO_AGENT_DIR.get(agent_key)
    if agent_dir_info is None:
        return None
    agent_root, _ = agent_dir_info
    return repo_root / agent_root


def _project_agent_surface(repo_root: Path, agent_key: str) -> tuple[Path, Path, str] | None:
    """Return root, managed surface, and display label for a project agent."""
    agent_dir_info = KEY_TO_AGENT_DIR.get(agent_key)
    if agent_dir_info is None:
        return None
    agent_root, subdir = agent_dir_info
    root = repo_root / agent_root
    return root, root / subdir, f"{agent_root}/{subdir}/"


def _remove_project_agent_surface(repo_root: Path, agent_key: str) -> tuple[bool, str]:
    """Remove only the managed command surface for an agent."""
    paths = _project_agent_surface(repo_root, agent_key)
    if paths is None:
        return False, f"Unknown agent: {agent_key}"

    root, surface, label = paths
    if not surface.exists():
        return False, f"{label} already removed"

    try:
        if surface.is_dir():
            shutil.rmtree(surface)
        else:
            surface.unlink()

        try:
            root.rmdir()
            return True, f"Removed {root.name}/"
        except OSError:
            return True, f"Removed {label}"
    except OSError as exc:
        return False, f"Failed to remove {label}: {exc}"


def _load_config_or_exit(repo_root: Path) -> AgentConfig:
    try:
        return load_agent_config(repo_root)
    except AgentConfigError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


def _register_skill_agent(repo_root: Path, config: AgentConfig, agent_key: str) -> tuple[bool, str | None]:
    """Install command skills for Codex/Vibe and update config."""
    from specify_cli.skills import command_installer  # noqa: PLC0415
    from specify_cli.skills.vibe_config import ensure_project_skill_path  # noqa: PLC0415

    try:
        report = command_installer.install(repo_root, agent_key)
        if agent_key == "vibe":
            ensure_project_skill_path(repo_root)
        installed = len(report.added) + len(report.reused_shared)
        config.available.append(agent_key)
        console.print(
            f"[green]✓[/green] Registered {agent_key} "
            f"({installed} command skills in .agents/skills/)"
        )
        return True, None
    except Exception as exc:
        return False, f"Failed to install {agent_key} skills: {exc}"


def _register_global_command_agent(config: AgentConfig, agent_key: str) -> None:
    """Register a slash-command agent whose command files are global."""
    global_dir = get_global_command_dir(agent_key)
    config.available.append(agent_key)
    console.print(
        f"[green]✓[/green] Registered {agent_key} "
        f"(global commands at {_display_path(global_dir)})"
    )


def _create_project_agent_dir(repo_root: Path, config: AgentConfig, agent_key: str) -> tuple[bool, str | None]:
    """Fallback for legacy project-local command agents."""
    agent_dir_info = KEY_TO_AGENT_DIR.get(agent_key)
    if not agent_dir_info:
        return False, f"Unknown agent: {agent_key}"

    agent_root, subdir = agent_dir_info
    agent_dir = repo_root / agent_root / subdir

    try:
        agent_dir.mkdir(parents=True, exist_ok=True)
        missions_dir = repo_root / ".kittify" / "missions" / "software-dev" / "command-templates"

        if missions_dir.exists():
            for template_file in missions_dir.glob("*.md"):
                dest_file = agent_dir / f"spec-kitty.{template_file.name}"
                shutil.copy2(template_file, dest_file)

        config.available.append(agent_key)
        console.print(f"[green]✓[/green] Added {agent_root}/{subdir}/")
        return True, None
    except OSError as exc:
        return False, f"Failed to create {agent_root}/{subdir}/: {exc}"


def _remove_orphaned_agent_dirs(repo_root: Path, config: AgentConfig) -> bool:
    """Remove project-local command dirs for agents not in config."""
    console.print("[cyan]Checking for orphaned directories...[/cyan]")
    changes_made = False
    all_agent_keys = set(AGENT_DIR_TO_KEY.values())
    orphaned = [
        key
        for key in all_agent_keys
        if key not in config.available
        and (surface := _project_agent_surface(repo_root, key)) is not None
        and surface[1].exists()
    ]

    for agent_key in orphaned:
        removed, message = _remove_project_agent_surface(repo_root, agent_key)
        if removed:
            removed_label = message.removeprefix("Removed ")
            console.print(f"  [green]✓[/green] Removed orphaned {removed_label}")
            changes_made = True
        else:
            console.print(f"  [red]✗[/red] {message}")

    return changes_made


def _check_or_create_configured_agent_dirs(repo_root: Path, config: AgentConfig) -> bool:
    """Check configured managed surfaces and create legacy local dirs if needed."""
    console.print("\n[cyan]Checking for missing directories...[/cyan]")
    changes_made = False
    missions_dir = repo_root / ".kittify" / "missions" / "software-dev" / "command-templates"

    for agent_key in config.available:
        if agent_key in GLOBAL_COMMAND_AGENTS:
            global_dir = get_global_command_dir(agent_key)
            if global_dir.exists():
                console.print(
                    f"  [green]✓[/green] Global commands present for {agent_key} at {_display_path(global_dir)}"
                )
            else:
                console.print(
                    f"  [yellow]⚠[/yellow] Global commands missing for {agent_key} at {_display_path(global_dir)}"
                )
            continue

        agent_dir_info = KEY_TO_AGENT_DIR.get(agent_key)
        if not agent_dir_info:
            console.print(f"  [yellow]⚠[/yellow] Unknown agent: {agent_key}")
            continue

        agent_root, subdir = agent_dir_info
        agent_dir = repo_root / agent_root / subdir
        if agent_dir.exists():
            continue

        try:
            agent_dir.mkdir(parents=True, exist_ok=True)
            if missions_dir.exists():
                for template_file in missions_dir.glob("*.md"):
                    dest_file = agent_dir / f"spec-kitty.{template_file.name}"
                    shutil.copy2(template_file, dest_file)

            console.print(f"  [green]✓[/green] Created {agent_root}/{subdir}/")
            changes_made = True
        except OSError as exc:
            console.print(f"  [red]✗[/red] Failed to create {agent_root}/{subdir}/: {exc}")

    return changes_made


@app.command(name="list")
def list_agents():
    """List configured agents and their status."""
    try:
        repo_root = find_repo_root()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Load config
    config = _load_config_or_exit(repo_root)

    if not config.available:
        console.print("[yellow]No agents configured.[/yellow]")
        console.print("\nRun 'spec-kitty init' or use 'spec-kitty agent config add' to add agents.")
        return

    # Display configured agents
    console.print("[cyan]Configured agents:[/cyan]")
    for agent_key in config.available:
        _, location, exists = _agent_location(repo_root, agent_key)
        status = "✓" if exists else "⚠"
        console.print(f"  {status} {agent_key} ({location})")

    # Show auto-commit setting
    auto_commit_label = "[green]enabled[/green]" if config.auto_commit else "[yellow]disabled[/yellow]"
    console.print(f"\n[cyan]Auto-commit:[/cyan] {auto_commit_label}")
    if not config.auto_commit:
        console.print("[dim]  Agents will stage changes but not create commits unless explicitly instructed.[/dim]")
        console.print("[dim]  Override per-command with --auto-commit flag.[/dim]")

    # Show available but not configured
    all_agent_keys = VALID_AGENTS
    not_configured = all_agent_keys - set(config.available)

    if not_configured:
        console.print("\n[dim]Available but not configured:[/dim]")
        for agent_key in sorted(not_configured):
            console.print(f"  - {agent_key}")


@app.command(name="add")
def add_agents(
    agents: list[str] = typer.Argument(..., help="Agent keys to add (e.g., claude codex)"),
):
    """Add agents to the project.

    Creates agent directories and updates config.yaml.

    Example:
        spec-kitty agent config add claude codex
    """
    try:
        repo_root = find_repo_root()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Load current config
    config = _load_config_or_exit(repo_root)

    # Validate agent keys — command-layer agents come from AGENT_DIR_TO_KEY;
    # skill-only agents (codex, vibe) have their own installer path.
    invalid = [a for a in agents if a not in VALID_AGENTS]
    if invalid:
        console.print(f"[red]Error:[/red] Invalid agent keys: {', '.join(invalid)}")
        console.print(f"\nValid agents: {', '.join(sorted(VALID_AGENTS))}")
        raise typer.Exit(1)

    added = []
    already_configured = []
    errors = []

    for agent_key in agents:
        # Check if already configured
        if agent_key in config.available:
            already_configured.append(agent_key)
            continue

        if agent_key in SKILL_ONLY_AGENTS:
            ok, error = _register_skill_agent(repo_root, config, agent_key)
            if ok:
                added.append(agent_key)
            elif error:
                errors.append(error)
            continue

        if agent_key in GLOBAL_COMMAND_AGENTS:
            _register_global_command_agent(config, agent_key)
            added.append(agent_key)
            continue

        ok, error = _create_project_agent_dir(repo_root, config, agent_key)
        if ok:
            added.append(agent_key)
        elif error:
            errors.append(error)

    # Save updated config
    if added:
        save_agent_config(repo_root, config)
        console.print(f"\n[cyan]Updated config.yaml:[/cyan] added {', '.join(added)}")

    if already_configured:
        console.print(f"\n[dim]Already configured:[/dim] {', '.join(already_configured)}")

    if errors:
        console.print("\n[red]Errors:[/red]")
        for error in errors:
            console.print(f"  - {error}")
        raise typer.Exit(1)


@app.command(name="remove")
def remove_agents(
    agents: list[str] = typer.Argument(..., help="Agent keys to remove"),
    keep_config: bool = typer.Option(
        False,
        "--keep-config",
        help="Keep in config.yaml but delete directory",
    ),
):
    """Remove agents from the project.

    Deletes agent directories and updates config.yaml.

    Example:
        spec-kitty agent config remove codex gemini
    """
    try:
        repo_root = find_repo_root()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Load current config
    config = _load_config_or_exit(repo_root)

    # Validate agent keys — command-layer agents come from AGENT_DIR_TO_KEY;
    # skill-only agents (codex, vibe) have their own installer path.
    invalid = [a for a in agents if a not in VALID_AGENTS]
    if invalid:
        console.print(f"[red]Error:[/red] Invalid agent keys: {', '.join(invalid)}")
        console.print(f"\nValid agents: {', '.join(sorted(VALID_AGENTS))}")
        raise typer.Exit(1)

    removed = []
    removed_from_config = []
    errors = []

    for agent_key in agents:
        if agent_key in ("codex", "vibe"):
            from specify_cli.skills import command_installer
            try:
                report = command_installer.remove(repo_root, agent_key)
                removed.append(agent_key)
                console.print(f"[green]✓[/green] Removed skills for {agent_key} ({len(report.deleted)} files deleted)")
            except Exception as e:
                errors.append(f"Failed to remove skills for {agent_key}: {e}")
            # Update config (unless --keep-config)
            if not keep_config and agent_key in config.available:
                config.available.remove(agent_key)
                removed_from_config.append(agent_key)
            continue

        surface_removed, message = _remove_project_agent_surface(repo_root, agent_key)
        if surface_removed:
            removed.append(agent_key)
            console.print(f"[green]✓[/green] {message}")
        else:
            console.print(f"[dim]• {message}[/dim]")

        # Update config (unless --keep-config)
        if not keep_config and agent_key in config.available:
            config.available.remove(agent_key)
            removed_from_config.append(agent_key)

    # Save updated config
    if not keep_config and removed_from_config:
        save_agent_config(repo_root, config)
        console.print(f"\n[cyan]Updated config.yaml:[/cyan] removed {', '.join(removed_from_config)}")

    if errors:
        console.print("\n[yellow]Warnings:[/yellow]")
        for error in errors:
            console.print(f"  - {error}")


@app.command(name="status")
def agent_status():
    """Show which agents are configured vs present on filesystem.

    Identifies:
    - Configured and present (✓)
    - Configured but missing (⚠)
    - Not configured but present (orphaned) (✗)
    """
    try:
        repo_root = find_repo_root()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Load config
    config = _load_config_or_exit(repo_root)

    # Check filesystem for each agent
    table = Table(title="Agent Status")
    table.add_column("Agent Key", style="cyan")
    table.add_column("Directory", style="dim")
    table.add_column("Configured", justify="center")
    table.add_column("Exists", justify="center")
    table.add_column("Status")

    all_agent_keys = sorted(VALID_AGENTS)

    for agent_key in all_agent_keys:
        _, location, exists_bool = _agent_location(repo_root, agent_key)
        configured = "✓" if agent_key in config.available else "✗"
        exists = "✓" if exists_bool else "✗"

        if agent_key in config.available and exists_bool:
            status = "[green]OK[/green]"
        elif agent_key in config.available and not exists_bool:
            status = "[yellow]Missing[/yellow]"
        elif (
            agent_key not in config.available
            and (surface := _project_agent_surface(repo_root, agent_key)) is not None
            and surface[1].exists()
        ):
            status = "[red]Orphaned[/red]"
        else:
            status = "[dim]Not used[/dim]"

        table.add_row(agent_key, location, configured, exists, status)

    console.print(table)

    # Summary
    orphaned = [
        key
        for key in all_agent_keys
        if key not in config.available
        and (surface := _project_agent_surface(repo_root, key)) is not None
        and surface[1].exists()
    ]

    if orphaned:
        console.print(
            f"\n[yellow]⚠ {len(orphaned)} orphaned directories found[/yellow] "
            f"(present but not configured)"
        )
        console.print("Run 'spec-kitty agent config sync --remove-orphaned' to clean up")


@app.command(name="sync")
def sync_agents(
    create_missing: bool = typer.Option(
        False,
        "--create-missing",
        help="Create directories for configured agents that are missing",
    ),
    remove_orphaned: bool = typer.Option(
        True,
        "--remove-orphaned/--keep-orphaned",
        help="Remove directories for agents not in config",
    ),
):
    """Sync filesystem with config.yaml.

    By default, removes orphaned directories (present but not configured).
    Use --create-missing to also create directories for configured agents.
    """
    try:
        repo_root = find_repo_root()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Load config
    config = _load_config_or_exit(repo_root)

    changes_made = False

    # Remove orphaned directories
    if remove_orphaned:
        changes_made = _remove_orphaned_agent_dirs(repo_root, config) or changes_made

    # Create missing directories
    if create_missing:
        changes_made = _check_or_create_configured_agent_dirs(repo_root, config) or changes_made

    if not changes_made:
        console.print("[dim]No changes needed - filesystem matches config[/dim]")
    else:
        console.print("\n[green]✓ Sync complete[/green]")


@app.command(name="set")
def set_config(
    key: str = typer.Argument(..., help="Configuration key (e.g., auto_commit)"),
    value: str = typer.Argument(..., help="Configuration value (e.g., true, false)"),
):
    """Set a project-level agent configuration value.

    Currently supported keys:
        auto_commit  - Enable/disable automatic commits by agents (true/false)

    Examples:
        spec-kitty agent config set auto_commit false
        spec-kitty agent config set auto_commit true
    """
    try:
        repo_root = find_repo_root()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    config = _load_config_or_exit(repo_root)

    if key == "auto_commit":
        if value.lower() in ("true", "1", "yes", "on"):
            config.auto_commit = True
        elif value.lower() in ("false", "0", "no", "off"):
            config.auto_commit = False
        else:
            console.print(f"[red]Error:[/red] Invalid value for auto_commit: '{value}'. Use 'true' or 'false'.")
            raise typer.Exit(1)

        save_agent_config(repo_root, config)

        status_label = "[green]enabled[/green]" if config.auto_commit else "[yellow]disabled[/yellow]"
        console.print(f"[green]✓[/green] auto_commit set to {status_label}")
        if not config.auto_commit:
            console.print("[dim]Agents will stage changes but not create commits unless explicitly instructed.[/dim]")
            console.print("[dim]Per-command flags (--auto-commit/--no-auto-commit) override this setting.[/dim]")
    else:
        console.print(f"[red]Error:[/red] Unknown configuration key: '{key}'")
        console.print("\nSupported keys:")
        console.print("  auto_commit  - Enable/disable automatic commits by agents (true/false)")
        raise typer.Exit(1)


__all__ = ["app"]
