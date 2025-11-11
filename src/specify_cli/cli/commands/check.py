"""Check command implementation."""

from __future__ import annotations

import typer

from specify_cli.cli import StepTracker
from specify_cli.cli.helpers import console, show_banner
from specify_cli.core.tool_checker import check_tool_for_tracker

TOOL_LABELS = [
    ("git", "Git version control"),
    ("claude", "Claude Code CLI"),
    ("gemini", "Gemini CLI"),
    ("qwen", "Qwen Code CLI"),
    ("code", "Visual Studio Code"),
    ("code-insiders", "Visual Studio Code Insiders"),
    ("cursor-agent", "Cursor IDE agent"),
    ("windsurf", "Windsurf IDE"),
    ("kilocode", "Kilo Code IDE"),
    ("opencode", "opencode"),
    ("codex", "Codex CLI"),
    ("auggie", "Auggie CLI"),
    ("q", "Amazon Q Developer CLI"),
]


def check(json: bool = typer.Option(False, "--json", help="Output results as JSON")) -> None:
    """Check that required tooling is available."""
    import json as json_module

    if not json:
        show_banner()
        console.print("[bold]Checking for installed tools...[/bold]\n")

    tracker = StepTracker("Check Available Tools")
    for key, label in TOOL_LABELS:
        tracker.add(key, label)

    statuses = {key: check_tool_for_tracker(key, tracker) for key, _ in TOOL_LABELS}

    if json:
        output = {
            "status": "ok",
            "tools": {key: {"available": available} for key, available in statuses.items()}
        }
        console.print(json_module.dumps(output, indent=2))
    else:
        console.print(tracker.render())
        console.print("\n[bold green]Spec Kitty CLI is ready to use![bold green]")

        if not statuses.get("git", False):
            console.print("[dim]Tip: Install git for repository management[/dim]")
        if not any(statuses[key] for key in statuses if key != "git"):
            console.print("[dim]Tip: Install an AI assistant for the best experience[/dim]")


__all__ = ["check"]
