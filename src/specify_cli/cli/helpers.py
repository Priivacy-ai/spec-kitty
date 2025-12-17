"""Shared CLI helpers for Spec Kitty commands."""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import typer
from rich.align import Align
from rich.console import Console
from rich.text import Text
from typer.core import TyperGroup

from specify_cli.core.config import BANNER
from specify_cli.core.project_resolver import locate_project_root

console = Console()
TAGLINE = "Spec Kitty - Spec-Driven Development Toolkit (forked from GitHub Spec Kit)"


class BannerGroup(TyperGroup):
    """Custom Typer group that renders the banner before help output."""

    def format_help(self, ctx, formatter):
        show_banner()
        super().format_help(ctx, formatter)


def show_banner() -> None:
    """Display the ASCII art banner with gradient styling."""
    banner_lines = BANNER.strip().split("\n")
    colors = ["bright_blue", "blue", "cyan", "bright_cyan", "white", "bright_white"]
    max_width = max((len(line) for line in banner_lines), default=0)

    styled_banner = Text()
    for index, line in enumerate(banner_lines):
        color = colors[index % len(colors)]
        padded_line = line.ljust(max_width)
        styled_banner.append(padded_line + "\n", style=color)

    try:
        pkg_version = version("spec-kitty-cli")
        version_text = f"v{pkg_version}"
    except PackageNotFoundError:
        version_text = "dev"

    console.print(Align.center(styled_banner))
    console.print(Align.center(Text(TAGLINE, style="italic bright_yellow")))
    console.print(Align.center(Text(version_text, style="dim cyan")))
    console.print()


def callback(ctx: typer.Context) -> None:
    """Display the banner when CLI is invoked without a subcommand."""
    if ctx.invoked_subcommand is None and "--help" not in sys.argv and "-h" not in sys.argv:
        show_banner()
        console.print(Align.center("[dim]Run 'spec-kitty --help' for usage information[/dim]"))
        console.print()


def get_project_root_or_exit(start: Path | None = None) -> Path:
    """Return the project root or exit when .kittify cannot be located."""
    project_root = locate_project_root(start)
    if project_root is None:
        console.print("[red]Error:[/red] Unable to locate the Spec Kitty project root (.kittify directory not found).")
        console.print("[dim]Run this command from the project root or from a feature worktree under .worktrees/<feature>/.[/dim]")
        console.print("[dim]Tip: Initialize a project with 'spec-kitty init <name>' if one does not exist.[/dim]")
        raise typer.Exit(1)
    return project_root


def check_version_compatibility(project_root: Path, command_name: str) -> None:
    """Check CLI/project version compatibility and exit if mismatch.

    Args:
        project_root: Path to project root (.kittify parent)
        command_name: Name of command being run (for should_check_version)

    Raises:
        typer.Exit(1) if version mismatch detected
    """
    from specify_cli.core.version_checker import (
        get_cli_version,
        get_project_version,
        compare_versions,
        format_version_error,
        should_check_version,
    )

    # Skip check for certain commands
    if not should_check_version(command_name):
        return

    cli_version = get_cli_version()
    project_version = get_project_version(project_root)

    # Handle missing metadata (legacy project)
    if project_version is None:
        console.print("[yellow]Warning:[/yellow] Project metadata not found (.kittify/metadata.yaml)")
        console.print("[yellow]Please run:[/yellow] spec-kitty upgrade")
        console.print()
        return  # Warn but don't block

    comparison, mismatch_type = compare_versions(cli_version, project_version)

    # Handle version mismatches
    if mismatch_type != "match":
        if mismatch_type == "unknown":
            console.print("[yellow]Warning:[/yellow] Unable to determine version compatibility")
            console.print(f"  CLI version: {cli_version}")
            console.print(f"  Project version: {project_version}")
            console.print()
            return  # Warn but don't block

        # Hard error for known version mismatches
        error_msg = format_version_error(cli_version, project_version, mismatch_type)
        console.print(error_msg)
        console.print()
        raise typer.Exit(1)


__all__ = ["BannerGroup", "callback", "check_version_compatibility", "console", "get_project_root_or_exit", "show_banner"]
