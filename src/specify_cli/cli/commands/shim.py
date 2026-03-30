"""``spec-kitty agent shim`` command group.

Each subcommand corresponds to one consumer-facing skill and accepts:
- ``--agent <name>``      Agent key (e.g. ``claude``).
- ``--raw-args <string>`` Raw argument string forwarded from the agent runtime.
- ``--context <token>``   Pre-resolved context token (optional).

The commands resolve context internally via
:func:`~specify_cli.shims.entrypoints.shim_dispatch` and print the
resolved context token so callers can chain commands.
"""

from __future__ import annotations

import json
import sys

import typer
from rich.console import Console
from typing import Annotated

from specify_cli.core.paths import locate_project_root
from specify_cli.shims.entrypoints import shim_dispatch

app = typer.Typer(
    name="shim",
    help="Thin shim entrypoints — resolve context and dispatch workflows",
    no_args_is_help=True,
)

console = Console()

# ---------------------------------------------------------------------------
# Shared option types
# ---------------------------------------------------------------------------

_AgentOpt = Annotated[
    str,
    typer.Option("--agent", help="Agent key (e.g. claude, codex, opencode)"),
]
_RawArgsOpt = Annotated[
    str,
    typer.Option("--raw-args", help="Raw argument string from the agent runtime"),
]
_ContextOpt = Annotated[
    str | None,
    typer.Option("--context", help="Pre-resolved context token (optional)"),
]
_JsonOpt = Annotated[
    bool,
    typer.Option("--json", help="Emit resolved context as JSON"),
]


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _run(
    command: str,
    agent: str,
    raw_args: str,
    context_token: str | None,
    json_output: bool,
) -> None:
    """Shared implementation for every shim subcommand."""
    try:
        repo_root = locate_project_root()
        if repo_root is None:
            console.print("[red]Error:[/red] Could not locate project root.")
            raise typer.Exit(1)

        ctx = shim_dispatch(
            command=command,
            agent=agent,
            raw_args=raw_args,
            context_token=context_token,
            repo_root=repo_root,
        )

        if ctx is None:
            # Prompt-driven command — no context to resolve.  The full
            # prompt template handles the workflow; nothing to dispatch.
            if json_output:
                print(json.dumps({"success": True, "context": None}, indent=2))
            else:
                console.print(
                    f"[green]✓[/green] {command} is prompt-driven — "
                    "no shim dispatch required."
                )
            return

        if json_output:
            print(json.dumps({"success": True, "context": ctx.to_dict()}, indent=2))
        else:
            console.print(f"[green]✓[/green] {command} context resolved: {ctx.token}")
            console.print(f"  Feature: {ctx.feature_slug}")
            console.print(f"  WP:      {ctx.wp_code}")
            console.print(f"  Agent:   {ctx.created_by}")

    except (ValueError, Exception) as exc:
        if json_output:
            print(json.dumps({"success": False, "error": str(exc)}, indent=2))
        else:
            console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Subcommands (one per consumer skill)
# ---------------------------------------------------------------------------

@app.command(name="specify")
def shim_specify(
    agent: _AgentOpt = "claude",
    raw_args: _RawArgsOpt = "",
    context: _ContextOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """Shim: spec-kitty specify."""
    _run("specify", agent, raw_args, context, json_output)


@app.command(name="plan")
def shim_plan(
    agent: _AgentOpt = "claude",
    raw_args: _RawArgsOpt = "",
    context: _ContextOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """Shim: spec-kitty plan."""
    _run("plan", agent, raw_args, context, json_output)


@app.command(name="tasks")
def shim_tasks(
    agent: _AgentOpt = "claude",
    raw_args: _RawArgsOpt = "",
    context: _ContextOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """Shim: spec-kitty tasks."""
    _run("tasks", agent, raw_args, context, json_output)


@app.command(name="implement")
def shim_implement(
    agent: _AgentOpt = "claude",
    raw_args: _RawArgsOpt = "",
    context: _ContextOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """Shim: spec-kitty implement."""
    _run("implement", agent, raw_args, context, json_output)


@app.command(name="review")
def shim_review(
    agent: _AgentOpt = "claude",
    raw_args: _RawArgsOpt = "",
    context: _ContextOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """Shim: spec-kitty review."""
    _run("review", agent, raw_args, context, json_output)


@app.command(name="accept")
def shim_accept(
    agent: _AgentOpt = "claude",
    raw_args: _RawArgsOpt = "",
    context: _ContextOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """Shim: spec-kitty accept."""
    _run("accept", agent, raw_args, context, json_output)


@app.command(name="merge")
def shim_merge(
    agent: _AgentOpt = "claude",
    raw_args: _RawArgsOpt = "",
    context: _ContextOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """Shim: spec-kitty merge."""
    _run("merge", agent, raw_args, context, json_output)


@app.command(name="status")
def shim_status(
    agent: _AgentOpt = "claude",
    raw_args: _RawArgsOpt = "",
    context: _ContextOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """Shim: spec-kitty status."""
    _run("status", agent, raw_args, context, json_output)


@app.command(name="constitution")
def shim_constitution(
    agent: _AgentOpt = "claude",
    raw_args: _RawArgsOpt = "",
    context: _ContextOpt = None,
    json_output: _JsonOpt = False,
) -> None:
    """Shim: spec-kitty constitution."""
    _run("constitution", agent, raw_args, context, json_output)


__all__ = ["app"]
