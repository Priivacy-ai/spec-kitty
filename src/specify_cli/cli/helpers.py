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


__all__ = ["BannerGroup", "callback", "console", "get_project_root_or_exit", "show_banner"]
