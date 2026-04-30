"""Shared CLI helpers for Spec Kitty commands."""

from __future__ import annotations

import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import click
import typer
from rich.align import Align
from rich.console import Console
from rich.text import Text
from typer.core import TyperGroup

from specify_cli.core.config import BANNER
from specify_cli.core.project_resolver import locate_project_root

console = Console()
TAGLINE = "Spec Kitty - Spec-Driven Development Toolkit (forked from GitHub Spec Kit)"

# ---------------------------------------------------------------------------
# Nag-suppression helper (T032)
# ---------------------------------------------------------------------------


def _should_suppress_nag(argv: list[str] | None = None) -> bool:
    """Return True when nag output should be suppressed for this invocation.

    Suppression conditions (any one is sufficient):
    - ``--no-nag`` in argv.
    - ``--json`` in argv.
    - ``--quiet`` in argv.
    - ``--help`` / ``-h`` in argv.
    - ``--version`` / ``-v`` in argv.
    - ``CI`` environment variable is truthy.
    - ``SPEC_KITTY_NO_NAG`` environment variable is truthy.
    - stdout is not a TTY.

    Note: This function intentionally re-evaluates the suppression criteria
    from raw argv/env rather than delegating entirely to Invocation.suppresses_nag()
    in order to catch ``--json`` and ``--quiet`` which are command-level flags
    that Invocation.suppresses_nag() does not check (belt-and-suspenders per T032).
    """
    if argv is None:
        argv = sys.argv[1:]

    suppress_flags = frozenset({"--no-nag", "--json", "--quiet", "--help", "-h", "--version", "-v"})
    if any(tok in suppress_flags for tok in argv):
        return True

    from specify_cli.compat.planner import is_ci_env  # noqa: PLC0415

    if is_ci_env():
        return True

    no_nag_val = os.environ.get("SPEC_KITTY_NO_NAG", "")
    if no_nag_val and no_nag_val.lower() not in ("0", "false", "no", "off"):
        return True

    try:
        if not sys.stdout.isatty():
            return True
    except Exception:  # noqa: BLE001 — isatty() can raise on exotic stream objects; treat as non-tty (safe to suppress)
        return True

    return False


class BannerGroup(TyperGroup):
    """Custom Typer group that renders the banner before help output."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        if _should_use_simple_help():
            _format_simple_help(self, ctx, formatter)
            return
        show_banner()
        super().format_help(ctx, formatter)


def _should_use_simple_help() -> bool:
    """Choose a plain help renderer for narrow terminals or explicit opt-in."""
    raw = os.environ.get("SPEC_KITTY_SIMPLE_HELP", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return console.width < 100


def _format_simple_help(group: TyperGroup, ctx: click.Context, formatter: click.HelpFormatter) -> None:
    """Render machine-friendly help without Rich tables/banner noise."""
    formatter.write_usage(ctx.command_path, "[OPTIONS] COMMAND [ARGS]...")

    if group.help:
        formatter.write_paragraph()
        formatter.write_text(group.help)

    options = []
    for param in group.get_params(ctx):
        record = param.get_help_record(ctx)
        if record is not None:
            options.append(record)
    if options:
        with formatter.section("Options"):
            formatter.write_dl(options)

    commands = []
    for name in group.list_commands(ctx):
        cmd = group.get_command(ctx, name)
        if cmd is None or cmd.hidden:
            continue
        commands.append((name, cmd.get_short_help_str()))
    if commands:
        with formatter.section("Commands"):
            formatter.write_dl(commands)


def _should_render_banner_for_invocation(argv: list[str] | None = None) -> bool:
    """Return True only for invocations that should render ASCII art."""
    # Agent/tool contexts should never receive decorative banner output.
    # It pollutes deterministic parsing and wastes tokens.
    if os.environ.get("SPEC_KITTY_NO_BANNER", "").strip().lower() in {"1", "true", "yes", "on"}:
        return False

    agent_env_markers = (
        "CLAUDECODE",
        "CLAUDE_CODE",
        "CODEX",
        "OPENCODE",
        "CURSOR_TRACE_ID",
    )
    if any(key in os.environ for key in agent_env_markers):
        return False

    tokens = [token.strip().lower() for token in (argv if argv is not None else sys.argv[1:]) if token.strip()]
    if "--version" in tokens or "-v" in tokens:
        return True

    command = next((token for token in tokens if not token.startswith("-")), None)
    return command == "init"


def show_banner(force: bool = False) -> None:
    """Display the ASCII art banner with gradient styling."""
    if not force and not _should_render_banner_for_invocation():
        return

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


def _render_nag_if_needed(ctx: typer.Context) -> None:
    """Consult the compat planner and render a nag message when appropriate.

    This is the WP08 hook.  It is called once per CLI invocation from
    ``callback()`` (the single chokepoint) *before* the schema gate runs.

    Design choice (Option C from WP08 spec): we make a separate planner call
    here specifically for nag rendering.  The schema gate (migration/gate.py)
    makes its own planner call for block enforcement.  The cost of two planner
    calls per invocation is low; the gain is clean separation of concerns and
    no disruption to the gate's existing contract.

    Key invariants:
    - Only renders for ALLOW_WITH_NAG decisions.
    - Never updates last_shown_at when the nag is suppressed (preserves the
      user's throttle window across CI/non-interactive runs).
    - Uses stderr so stdout consumers (``--json``) see clean output.
    - Color disabled when stderr is not a TTY.
    """
    # Fast-path: suppress early to avoid the planner call cost.
    if _should_suppress_nag():
        return

    try:
        # Deferred imports to avoid circular imports at module load time.
        from datetime import UTC, datetime  # noqa: PLC0415

        from specify_cli.compat import Decision  # noqa: PLC0415
        from specify_cli.compat import Invocation  # noqa: PLC0415
        from specify_cli.compat import NagCache  # noqa: PLC0415
        from specify_cli.compat import NagCacheRecord  # noqa: PLC0415
        from specify_cli.compat import plan as compat_plan  # noqa: PLC0415

        # Build Invocation from argv (best-effort; never raises).
        inv = Invocation.from_argv()

        # If Invocation itself says suppress, honour it (belt-and-suspenders).
        if inv.suppresses_nag():
            return

        result = compat_plan(inv)

        # Stash on ctx.obj so subcommands can read it without re-planning.
        if ctx.obj is None:
            ctx.obj = {}
        if isinstance(ctx.obj, dict):
            ctx.obj["compat_plan_result"] = result

        if result.decision != Decision.ALLOW_WITH_NAG:
            # ALLOW → nothing to render.
            # BLOCK_* → handled by the schema gate (migration/gate.py).
            return

        # Render the nag to stderr.
        # Use Literal "auto" when stderr is a TTY, None (no color) otherwise.
        from typing import Literal  # noqa: PLC0415

        _color: Literal["auto"] | None = "auto" if sys.stderr.isatty() else None
        stderr_console = Console(stderr=True, color_system=_color)
        message = result.rendered_human.rstrip()
        if message:
            stderr_console.print(message)

        # Update last_shown_at in the nag cache so the throttle window starts.
        # This is intentionally NOT done when the nag is suppressed (CI / no-TTY).
        try:
            nag_cache = NagCache.default()
            existing = nag_cache.read()
            now = datetime.now(UTC)
            if existing is not None:
                updated_record = NagCacheRecord(
                    cli_version_key=existing.cli_version_key,
                    latest_version=existing.latest_version,
                    latest_source=existing.latest_source,
                    fetched_at=existing.fetched_at,
                    last_shown_at=now,
                )
            else:
                # No existing record — write a minimal one to record the show time.
                updated_record = NagCacheRecord(
                    cli_version_key=result.cli_status.installed_version,
                    latest_version=result.cli_status.latest_version,
                    latest_source=result.cli_status.latest_source,
                    fetched_at=now,
                    last_shown_at=now,
                )
            nag_cache.write(updated_record)
        except Exception:  # noqa: BLE001 — nag-cache write is best-effort; failure must not block the CLI
            pass  # Cache update failure is non-fatal.

    except Exception:  # noqa: BLE001 — nag rendering must never crash the CLI; planner errors are suppressed here
        # Fail open for nag rendering: if the planner errors, don't block the CLI.
        pass


def callback(ctx: typer.Context) -> None:
    """Display the banner when CLI is invoked without a subcommand."""
    if ctx.invoked_subcommand is None and "--help" not in sys.argv and "-h" not in sys.argv:
        show_banner()
        console.print(Align.center("[dim]Run 'spec-kitty --help' for usage information[/dim]"))
        console.print()

    # WP08: render upgrade nag through planner if needed.
    _render_nag_if_needed(ctx)


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


__all__ = [
    "BannerGroup",
    "callback",
    "console",
    "get_project_root_or_exit",
    "show_banner",
    "_render_nag_if_needed",
    "_should_suppress_nag",
]
