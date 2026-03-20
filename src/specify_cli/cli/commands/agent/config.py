"""Agent configuration management commands."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import typer
from rich.console import Console
from rich.table import Table

from specify_cli.core.agent_surface import get_agent_surface
from specify_cli.core.agent_config import (
    load_agent_config,
    save_agent_config,
    AgentConfig,
    AgentConfigError,
)
from specify_cli.skills.manifest import (
    ManagedFile,
    compute_file_hash,
    load_manifest,
    write_manifest,
)
from specify_cli.skills.roots import resolve_skill_roots
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


def _refresh_manifest_from_filesystem(
    repo_root: Path,
    config: AgentConfig,
    manifest,
) -> None:
    """Rebuild manifest state from the current config and filesystem."""
    managed_files: list[ManagedFile] = []
    installed_roots: list[str] = []

    expected_roots = resolve_skill_roots(config.available, mode=manifest.skills_mode)
    for root in expected_roots:
        root_path = repo_root / root
        if not root_path.exists():
            continue
        installed_roots.append(root)
        gitkeep = root_path / ".gitkeep"
        if gitkeep.exists():
            managed_files.append(
                ManagedFile(
                    path=str(Path(root) / ".gitkeep"),
                    sha256=compute_file_hash(gitkeep),
                    file_type="skill_root_marker",
                )
            )

    for agent_key in config.available:
        surface = get_agent_surface(agent_key)
        wrapper_dir = repo_root / surface.wrapper.dir
        if not wrapper_dir.exists():
            continue
        for wrapper_file in sorted(wrapper_dir.iterdir()):
            if wrapper_file.is_file() and wrapper_file.name.startswith("spec-kitty."):
                managed_files.append(
                    ManagedFile(
                        path=str(wrapper_file.relative_to(repo_root)),
                        sha256=compute_file_hash(wrapper_file),
                        file_type="wrapper",
                    )
                )

    manifest.selected_agents = list(config.available)
    manifest.installed_skill_roots = sorted(installed_roots)
    manifest.managed_files = managed_files
    manifest.updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_manifest(repo_root, manifest)


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
        agent_dir_info = KEY_TO_AGENT_DIR.get(agent_key)
        if agent_dir_info:
            agent_dir, subdir = agent_dir_info
            agent_path = repo_root / agent_dir / subdir
            status = "✓" if agent_path.exists() else "⚠"
            console.print(f"  {status} {agent_key} ({agent_dir}/{subdir}/)")
        else:
            console.print(f"  ✗ {agent_key} (unknown agent)")

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

        agent_root, subdir = agent_dir_info
        agent_dir = repo_root / agent_root / subdir

        # Create directory structure
        try:
            agent_dir.mkdir(parents=True, exist_ok=True)

            # Generate templates for this agent
            # Copy from mission templates
            missions_dir = repo_root / ".kittify" / "missions" / "software-dev" / "command-templates"

            if missions_dir.exists():
                for template_file in missions_dir.glob("*.md"):
                    dest_file = agent_dir / f"spec-kitty.{template_file.name}"
                    shutil.copy2(template_file, dest_file)

            added.append(agent_key)
            config.available.append(agent_key)
            console.print(f"[green]✓[/green] Added {agent_root}/{subdir}/")

        except OSError as e:
            errors.append(f"Failed to create {agent_root}/{subdir}/: {e}")

    # Save updated config
    if added:
        save_agent_config(repo_root, config)
        console.print(f"\n[cyan]Updated config.yaml:[/cyan] added {', '.join(added)}")
        manifest = load_manifest(repo_root)
        if manifest is not None:
            _refresh_manifest_from_filesystem(repo_root, config, manifest)

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
        manifest = load_manifest(repo_root)
        if manifest is not None:
            _refresh_manifest_from_filesystem(repo_root, config, manifest)

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
        agent_dir_info = KEY_TO_AGENT_DIR.get(agent_key)
        if not agent_dir_info:
            continue

        agent_root, subdir = agent_dir_info
        agent_path = repo_root / agent_root / subdir

        configured = "✓" if agent_key in config.available else "✗"
        exists = "✓" if agent_path.exists() else "✗"

        if agent_key in config.available and agent_path.exists():
            status = "[green]OK[/green]"
        elif agent_key in config.available and not agent_path.exists():
            status = "[yellow]Missing[/yellow]"
        elif agent_key not in config.available and agent_path.exists():
            status = "[red]Orphaned[/red]"
        else:
            status = "[dim]Not used[/dim]"

        table.add_row(agent_key, f"{agent_root}/{subdir}", configured, exists, status)

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
    Also manages skill root directories based on the skills manifest.
    """
    try:
        repo_root = find_repo_root()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Load config
    config = _load_config_or_exit(repo_root)

    # T028: Load manifest for skill root awareness
    manifest = load_manifest(repo_root)
    if manifest is None:
        console.print("[dim]No skills manifest found - skipping skill root sync[/dim]")

    changes_made = False
    expected_roots: list[str] = []

    # Remove orphaned directories
    if remove_orphaned:
        console.print("[cyan]Checking for orphaned directories...[/cyan]")
        all_agent_keys = set(AGENT_DIR_TO_KEY.values())
        orphaned = [
            key
            for key in all_agent_keys
            if key not in config.available and (repo_root / KEY_TO_AGENT_DIR[key][0]).exists()
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

    # T030: Orphaned skill root removal with shared root protection
    if remove_orphaned and manifest:
        console.print("\n[cyan]Checking for orphaned skill roots...[/cyan]")
        # Compute which roots are still needed by configured agents
        needed_roots = set(resolve_skill_roots(config.available, mode=manifest.skills_mode))
        # Check manifest for roots that were installed but are no longer needed
        for root in manifest.installed_skill_roots:
            if root not in needed_roots:
                root_path = repo_root / root
                if root_path.exists():
                    # Only remove managed content (gitkeep), not user files
                    gitkeep = root_path / ".gitkeep"
                    if gitkeep.exists():
                        gitkeep.unlink()
                    # Only rmdir if empty (don't delete user content)
                    try:
                        root_path.rmdir()
                        console.print(f"  [green]✓[/green] Removed orphaned skill root {root}")
                        changes_made = True
                    except OSError:
                        console.print(
                            f"  [yellow]⚠[/yellow] Skill root {root} has non-managed content, keeping"
                        )

    # Create missing directories
    if create_missing:
        console.print("\n[cyan]Checking for missing directories...[/cyan]")
        missions_dir = repo_root / ".kittify" / "missions" / "software-dev" / "command-templates"

        for agent_key in config.available:
            agent_dir_info = KEY_TO_AGENT_DIR.get(agent_key)
            if not agent_dir_info:
                console.print(f"  [yellow]⚠[/yellow] Unknown agent: {agent_key}")
                continue

            agent_root, subdir = agent_dir_info
            agent_dir = repo_root / agent_root / subdir

            if not agent_dir.exists():
                try:
                    agent_dir.mkdir(parents=True, exist_ok=True)

                    # Copy templates if available
                    if missions_dir.exists():
                        for template_file in missions_dir.glob("*.md"):
                            dest_file = agent_dir / f"spec-kitty.{template_file.name}"
                            shutil.copy2(template_file, dest_file)

                    console.print(f"  [green]✓[/green] Created {agent_root}/{subdir}/")
                    changes_made = True
                except OSError as e:
                    console.print(f"  [red]✗[/red] Failed to create {agent_root}/{subdir}/: {e}")

    # T029: Repair missing skill roots for configured agents
    if create_missing and manifest:
        console.print("\n[cyan]Checking for missing skill roots...[/cyan]")
        expected_roots = resolve_skill_roots(config.available, mode=manifest.skills_mode)
        for root in expected_roots:
            root_path = repo_root / root
            if not root_path.exists():
                root_path.mkdir(parents=True, exist_ok=True)
                (root_path / ".gitkeep").write_text("", encoding="utf-8")
                console.print(f"  [green]✓[/green] Recreated skill root {root}")
                changes_made = True

    # T031: Update manifest after sync changes
    if changes_made and manifest:
        _refresh_manifest_from_filesystem(repo_root, config, manifest)

    if not changes_made:
        console.print("[dim]No changes needed - filesystem matches config[/dim]")
    else:
        console.print("\n[green]✓ Sync complete[/green]")


__all__ = ["app"]
