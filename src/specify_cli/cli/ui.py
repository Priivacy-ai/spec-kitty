"""Reusable UI helpers for Spec Kitty CLI interactions."""

from __future__ import annotations

from typing import Dict, List, Optional

import readchar
import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from .step_tracker import StepTracker


def get_key() -> str:
    """Get a single keypress in a cross-platform way using readchar."""
    key = readchar.readkey()

    if key == readchar.key.UP or key == readchar.key.CTRL_P:
        return "up"
    if key == readchar.key.DOWN or key == readchar.key.CTRL_N:
        return "down"

    if key == readchar.key.ENTER:
        return "enter"

    if key == readchar.key.ESC or key == "\x1b":
        return "escape"

    if key == readchar.key.CTRL_C:
        raise KeyboardInterrupt

    return key


def _resolve_console(console: Optional[Console]) -> Console:
    return console or Console()


def select_with_arrows(
    options: Dict,
    prompt_text: str = "Select an option",
    default_key: str | None = None,
    console: Console | None = None,
) -> str:
    """
    Interactive selection using arrow keys with Rich Live display.
    """
    console = _resolve_console(console)
    option_keys = list(options.keys())
    if default_key and default_key in option_keys:
        selected_index = option_keys.index(default_key)
    else:
        selected_index = 0

    selected_key = None

    def create_selection_panel():
        """Create the selection panel with current selection highlighted."""
        table = Table.grid(padding=(0, 2))
        table.add_column(style="cyan", justify="left", width=3)
        table.add_column(style="white", justify="left")

        for i, key in enumerate(option_keys):
            if i == selected_index:
                table.add_row("▶", f"[cyan]{key}[/cyan] [dim]({options[key]})[/dim]")
            else:
                table.add_row(" ", f"[cyan]{key}[/cyan] [dim]({options[key]})[/dim]")

        table.add_row("", "")
        table.add_row("", "[dim]Use ↑/↓ to navigate, Enter to select, Esc to cancel[/dim]")

        return Panel(
            table,
            title=f"[bold]{prompt_text}[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )

    console.print()

    def run_selection_loop():
        nonlocal selected_key, selected_index
        with Live(create_selection_panel(), console=console, transient=True, auto_refresh=False) as live:
            while True:
                try:
                    key = get_key()
                    if key == "up":
                        selected_index = (selected_index - 1) % len(option_keys)
                    elif key == "down":
                        selected_index = (selected_index + 1) % len(option_keys)
                    elif key == "enter":
                        selected_key = option_keys[selected_index]
                        break
                    elif key == "escape":
                        console.print("\n[yellow]Selection cancelled[/yellow]")
                        raise typer.Exit(1)

                    live.update(create_selection_panel(), refresh=True)

                except KeyboardInterrupt:
                    console.print("\n[yellow]Selection cancelled[/yellow]")
                    raise typer.Exit(1)

    run_selection_loop()

    if selected_key is None:
        console.print("\n[red]Selection failed.[/red]")
        raise typer.Exit(1)

    return selected_key


def multi_select_with_arrows(
    options: Dict[str, str],
    prompt_text: str = "Select options",
    default_keys: Optional[List[str]] = None,
    console: Console | None = None,
) -> List[str]:
    """Allow selecting one or more options using arrow keys + space to toggle."""

    console = _resolve_console(console)
    option_keys = list(options.keys())
    selected_indices: set[int] = set()
    if default_keys:
        for key in default_keys:
            if key in option_keys:
                selected_indices.add(option_keys.index(key))
    if not selected_indices and option_keys:
        selected_indices.add(0)

    cursor_index = next(iter(selected_indices)) if selected_indices else 0

    def build_panel():
        table = Table.grid(padding=(0, 2))
        table.add_column(style="cyan", justify="left", width=3)
        table.add_column(style="white", justify="left")

        for i, key in enumerate(option_keys):
            indicator = "[cyan]☑" if i in selected_indices else "[bright_black]☐"
            pointer = "▶" if i == cursor_index else " "
            table.add_row(pointer, f"{indicator} [cyan]{key}[/cyan] [dim]({options[key]})[/dim]")

        table.add_row("", "")
        table.add_row(
            "",
            "[dim]Use ↑/↓ to move, Space to toggle, Enter to confirm, Esc to cancel[/dim]",
        )

        return Panel(table, title=f"[bold]{prompt_text}[/bold]", border_style="cyan", padding=(1, 2))

    def normalize_selection() -> List[str]:
        return [option_keys[i] for i in range(len(option_keys)) if i in selected_indices]

    console.print()

    with Live(build_panel(), console=console, transient=True, auto_refresh=False) as live:
        while True:
            try:
                key = get_key()
                if key == "up":
                    cursor_index = (cursor_index - 1) % len(option_keys)
                elif key == "down":
                    cursor_index = (cursor_index + 1) % len(option_keys)
                elif key in (" ", readchar.key.SPACE):
                    if cursor_index in selected_indices:
                        selected_indices.remove(cursor_index)
                    else:
                        selected_indices.add(cursor_index)
                elif key == "enter":
                    current = normalize_selection()
                    if current:
                        return current
                elif key == "escape":
                    console.print("\n[yellow]Selection cancelled[/yellow]")
                    raise typer.Exit(1)

                live.update(build_panel(), refresh=True)

            except KeyboardInterrupt:
                console.print("\n[yellow]Selection cancelled[/yellow]")
                raise typer.Exit(1)


__all__ = [
    "StepTracker",
    "get_key",
    "select_with_arrows",
    "multi_select_with_arrows",
]
