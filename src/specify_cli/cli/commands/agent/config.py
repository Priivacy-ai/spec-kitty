"""Agent configuration management commands."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import typer
from rich.console import Console
from rich.table import Table

from specify_cli.core.agent_config import (
    load_agent_config,
    save_agent_config,
    AgentConfig,
    AgentConfigError,
)
from specify_cli.core.config import AGENT_SKILL_CONFIG, SKILL_CLASS_SHARED
from specify_cli.runtime.agent_commands import (
    get_primary_project_command_root,
    install_project_commands_for_agent,
    supports_managed_commands,
)
from specify_cli.skills.installer import install_skills_for_agent
from specify_cli.skills.manifest import (
    ManagedSkillManifest,
    load_manifest,
    save_manifest,
)
from specify_cli.skills.paths import get_primary_project_skill_root
from specify_cli.skills.registry import SkillRegistry
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


def _load_config_or_exit(repo_root: Path) -> AgentConfig:
    try:
        return load_agent_config(repo_root)
    except AgentConfigError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


def _format_surface_label(agent_key: str) -> str:
    command_root = get_primary_project_command_root(agent_key)
    if command_root is not None:
        return f"{command_root.rstrip('/')}/"

    skill_root = get_primary_project_skill_root(agent_key)
    if skill_root is not None:
        return f"{skill_root.rstrip('/')}/ (skills only)"

    agent_dir_info = KEY_TO_AGENT_DIR.get(agent_key)
    if agent_dir_info is None:
        return agent_key
    agent_root, subdir = agent_dir_info
    return f"{agent_root}/{subdir}/"


def _primary_surface_path(repo_root: Path, agent_key: str) -> Path | None:
    command_root = get_primary_project_command_root(agent_key)
    if command_root is not None:
        return repo_root / command_root

    skill_root = get_primary_project_skill_root(agent_key)
    if skill_root is not None:
        return repo_root / skill_root

    agent_dir_info = KEY_TO_AGENT_DIR.get(agent_key)
    if agent_dir_info is None:
        return None
    agent_root, subdir = agent_dir_info
    return repo_root / agent_root / subdir


def _is_shared_skill_only_agent(agent_key: str) -> bool:
    config = AGENT_SKILL_CONFIG.get(agent_key)
    return (
        config is not None
        and config["class"] == SKILL_CLASS_SHARED
        and not supports_managed_commands(agent_key)
    )


def _surface_exists(repo_root: Path, agent_key: str, *, configured: bool) -> bool:
    """Return whether an agent's primary visible surface exists in this project."""
    surface_path = _primary_surface_path(repo_root, agent_key)
    if surface_path is None:
        return False

    if _is_shared_skill_only_agent(agent_key):
        if configured:
            return surface_path.exists()
        agent_dir_info = KEY_TO_AGENT_DIR.get(agent_key)
        if agent_dir_info is None:
            return False
        agent_root, _ = agent_dir_info
        return (repo_root / agent_root).exists()

    return surface_path.exists()


def _load_or_create_manifest(repo_root: Path) -> ManagedSkillManifest:
    manifest = load_manifest(repo_root)
    if manifest is not None:
        return manifest

    from specify_cli import __version__

    now = datetime.now(timezone.utc).isoformat()
    return ManagedSkillManifest(
        created_at=now,
        updated_at=now,
        spec_kitty_version=__version__,
    )


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
        surface_path = _primary_surface_path(repo_root, agent_key)
        if surface_path is not None:
            status = "✓" if _surface_exists(repo_root, agent_key, configured=True) else "⚠"
            console.print(f"  {status} {agent_key} ({_format_surface_label(agent_key)})")
        else:
            console.print(f"  ✗ {agent_key} (unknown agent)")

    # Show auto-commit setting
    auto_commit_label = "[green]enabled[/green]" if config.auto_commit else "[yellow]disabled[/yellow]"
    console.print(f"\n[cyan]Auto-commit:[/cyan] {auto_commit_label}")
    if not config.auto_commit:
        console.print("[dim]  Agents will stage changes but not create commits unless explicitly instructed.[/dim]")
        console.print("[dim]  Override per-command with --auto-commit flag.[/dim]")

    # Show available but not configured
    all_agent_keys = set(AGENT_DIR_TO_KEY.values())
    not_configured = all_agent_keys - set(config.available)

    if not_configured:
        console.print("\n[dim]Available but not configured:[/dim]")
        for agent_key in sorted(not_configured):
            console.print(f"  - {agent_key}")


@app.command(name="add")
def add_agents(
    agents: List[str] = typer.Argument(..., help="Agent keys to add (e.g., claude codex)"),
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

    # Validate agent keys
    invalid = [a for a in agents if a not in AGENT_DIR_TO_KEY.values()]
    if invalid:
        console.print(f"[red]Error:[/red] Invalid agent keys: {', '.join(invalid)}")
        console.print(f"\nValid agents: {', '.join(sorted(AGENT_DIR_TO_KEY.values()))}")
        raise typer.Exit(1)

    added = []
    already_configured = []
    errors = []
    skill_registry = SkillRegistry.from_package()
    skills = skill_registry.discover_skills()
    manifest = _load_or_create_manifest(repo_root)
    manifest_dirty = False
    shared_root_installed: set[str] = set()

    for agent_key in agents:
        # Check if already configured
        if agent_key in config.available:
            already_configured.append(agent_key)
            continue

        # Get directory for this agent
        agent_dir_info = KEY_TO_AGENT_DIR.get(agent_key)
        if not agent_dir_info:
            errors.append(f"Unknown agent: {agent_key}")
            continue

        try:
            install_project_commands_for_agent(repo_root, agent_key)
            entries = install_skills_for_agent(
                repo_root,
                agent_key,
                skills,
                shared_root_installed=shared_root_installed,
            )
            for entry in entries:
                manifest.add_entry(entry)
            if entries:
                manifest_dirty = True
            added.append(agent_key)
            config.available.append(agent_key)
            console.print(f"[green]✓[/green] Added {_format_surface_label(agent_key)}")

        except OSError as e:
            errors.append(f"Failed to provision {_format_surface_label(agent_key)}: {e}")
        except Exception as e:  # noqa: BLE001
            errors.append(f"Failed to provision {agent_key}: {e}")

    # Save updated config
    if added:
        save_agent_config(repo_root, config)
        console.print(f"\n[cyan]Updated config.yaml:[/cyan] added {', '.join(added)}")
    if manifest_dirty:
        save_manifest(manifest, repo_root)

    if already_configured:
        console.print(f"\n[dim]Already configured:[/dim] {', '.join(already_configured)}")

    if errors:
        console.print("\n[red]Errors:[/red]")
        for error in errors:
            console.print(f"  - {error}")
        raise typer.Exit(1)


@app.command(name="remove")
def remove_agents(
    agents: List[str] = typer.Argument(..., help="Agent keys to remove"),
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

    # Validate agent keys
    invalid = [a for a in agents if a not in AGENT_DIR_TO_KEY.values()]
    if invalid:
        console.print(f"[red]Error:[/red] Invalid agent keys: {', '.join(invalid)}")
        console.print(f"\nValid agents: {', '.join(sorted(AGENT_DIR_TO_KEY.values()))}")
        raise typer.Exit(1)

    removed = []
    errors = []

    for agent_key in agents:
        # Get directory for this agent
        agent_dir_info = KEY_TO_AGENT_DIR.get(agent_key)
        if not agent_dir_info:
            errors.append(f"Unknown agent: {agent_key}")
            continue

        agent_root, subdir = agent_dir_info

        # Delete directory
        agent_path = repo_root / agent_root
        if agent_path.exists():
            try:
                shutil.rmtree(agent_path)
                removed.append(agent_key)
                console.print(f"[green]✓[/green] Removed {agent_root}/")
            except OSError as e:
                errors.append(f"Failed to remove {agent_root}/: {e}")
        else:
            console.print(f"[dim]• {agent_root}/ already removed[/dim]")

        # Update config (unless --keep-config)
        if not keep_config and agent_key in config.available:
            config.available.remove(agent_key)

    # Save updated config
    if not keep_config and (removed or any(a in config.available for a in agents)):
        save_agent_config(repo_root, config)
        console.print(f"\n[cyan]Updated config.yaml:[/cyan] removed {', '.join(removed)}")

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

    all_agent_keys = sorted(AGENT_DIR_TO_KEY.values())

    for agent_key in all_agent_keys:
        surface_path = _primary_surface_path(repo_root, agent_key)
        if surface_path is None:
            continue

        path_exists = _surface_exists(repo_root, agent_key, configured=agent_key in config.available)
        configured = "✓" if agent_key in config.available else "✗"
        exists = "✓" if path_exists else "✗"

        if agent_key in config.available and path_exists:
            status = "[green]OK[/green]"
        elif agent_key in config.available and not path_exists:
            status = "[yellow]Missing[/yellow]"
        elif agent_key not in config.available and path_exists:
            status = "[red]Orphaned[/red]"
        else:
            status = "[dim]Not used[/dim]"

        table.add_row(agent_key, _format_surface_label(agent_key), configured, exists, status)

    console.print(table)

    # Summary
    orphaned = [
        key
        for key in all_agent_keys
        if key not in config.available and (repo_root / KEY_TO_AGENT_DIR[key][0]).exists()
    ]

    if orphaned:
        console.print(
            f"\n[yellow]⚠ {len(orphaned)} orphaned directories found[/yellow] "
            f"(present but not configured)"
        )
        console.print(f"Run 'spec-kitty agent config sync --remove-orphaned' to clean up")


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
        console.print("[cyan]Checking for orphaned directories...[/cyan]")
        all_agent_keys = set(AGENT_DIR_TO_KEY.values())
        orphaned = [
            key
            for key in all_agent_keys
            if key not in config.available
            and _surface_exists(repo_root, key, configured=False)
        ]

        for agent_key in orphaned:
            agent_root, _ = KEY_TO_AGENT_DIR[agent_key]
            agent_path = repo_root / agent_root

            try:
                shutil.rmtree(agent_path)
                console.print(f"  [green]✓[/green] Removed orphaned {agent_root}/")
                changes_made = True
            except OSError as e:
                console.print(f"  [red]✗[/red] Failed to remove {agent_root}/: {e}")

    # Create missing directories
    if create_missing:
        console.print("\n[cyan]Checking for missing directories...[/cyan]")
        skill_registry = SkillRegistry.from_package()
        skills = skill_registry.discover_skills()
        manifest = _load_or_create_manifest(repo_root)
        manifest_dirty = False
        shared_root_installed: set[str] = set()

        for agent_key in config.available:
            surface_path = _primary_surface_path(repo_root, agent_key)
            if surface_path is None:
                console.print(f"  [yellow]⚠[/yellow] Unknown agent: {agent_key}")
                continue

            if not _surface_exists(repo_root, agent_key, configured=True):
                try:
                    install_project_commands_for_agent(repo_root, agent_key)
                    entries = install_skills_for_agent(
                        repo_root,
                        agent_key,
                        skills,
                        shared_root_installed=shared_root_installed,
                    )
                    for entry in entries:
                        manifest.add_entry(entry)
                    if entries:
                        manifest_dirty = True
                    console.print(f"  [green]✓[/green] Created {_format_surface_label(agent_key)}")
                    changes_made = True
                except OSError as e:
                    console.print(f"  [red]✗[/red] Failed to create {_format_surface_label(agent_key)}: {e}")
                except Exception as e:  # noqa: BLE001
                    console.print(f"  [red]✗[/red] Failed to provision {agent_key}: {e}")

        if manifest_dirty:
            save_manifest(manifest, repo_root)

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
