#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer",
#     "rich",
#     "platformdirs",
#     "readchar",
#     "httpx",
# ]
# ///
"""
Spec Kitty CLI - setup tooling for Spec Kitty projects.

Usage:
    spec-kitty init
    spec-kitty init <project-name>
    spec-kitty init .
    spec-kitty init --here
"""

import os
from pathlib import Path

import typer
from rich.console import Console

# Get version from package metadata
# Test mode: use environment override to ensure tests use source version
if os.environ.get("SPEC_KITTY_TEST_MODE") == "1":
    __version__ = os.environ.get("SPEC_KITTY_CLI_VERSION", "0.5.0-dev")
else:
    from specify_cli.version_utils import get_version

    __version__ = get_version()

from specify_cli.cli import StepTracker
from specify_cli.cli.helpers import (
    BannerGroup,
    callback as root_callback,
    console,
    show_banner,
)
from specify_cli.cli.commands import register_commands
from specify_cli.cli.commands.init import register_init_command
from specify_cli.core.project_resolver import locate_project_root


def activate_mission(project_path: Path, mission_type: str, mission_display: str, console: Console) -> str:
    """
    DEPRECATED: No-op function for backwards compatibility.

    As of v0.8.0, missions are selected per-feature during /spec-kitty.specify,
    not at the project level during init. This function is kept for backwards
    compatibility with existing init code but no longer sets an active mission.
    """
    # Just verify the mission directory exists
    kittify_root = project_path / ".kittify"
    missions_dir = kittify_root / "missions"
    mission_path = missions_dir / mission_type

    if mission_path.exists():
        return f"{mission_display} (per-feature selection)"
    else:
        console.print(
            f"[yellow]Note:[/yellow] Mission [cyan]{mission_display}[/cyan] templates will be "
            f"available when you run [cyan]/spec-kitty.specify[/cyan]."
        )
        return f"{mission_display} (templates pending)"


def version_callback(value: bool) -> None:
    """Display version and exit."""
    if value:
        show_banner(force=True)
        console.print(f"spec-kitty-cli version {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="spec-kitty",
    help="Setup tool for Spec Kitty spec-driven development projects",
    add_completion=False,
    invoke_without_command=True,
    cls=BannerGroup,
)


@app.callback()
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(  # noqa: ARG001
        None, "--version", "-v", callback=version_callback, is_eager=True, help="Show version and exit"
    ),
) -> None:
    """Main callback for root CLI setup."""
    root_callback(ctx)

    # FR-002: Ensure global runtime (~/.kittify/) is populated and current.
    # Must run BEFORE check_version_pin() so global assets are available.
    from specify_cli.runtime.agent_commands import ensure_global_agent_commands
    from specify_cli.runtime.agent_skills import ensure_global_agent_skills
    from specify_cli.runtime.bootstrap import check_version_pin, ensure_runtime

    ensure_runtime()
    ensure_global_agent_skills()
    ensure_global_agent_commands()

    # F-Pin-001 / 1A-16: Warn on runtime.pin_version for all project invocations.
    project_root = locate_project_root()
    if project_root is not None:
        check_version_pin(project_root)

    # FR-019 / FR-020: Schema version gate — refuse unmigrated or newer-than-CLI
    # projects before any command runs.  Exempt upgrade/init/--version/--help.
    if project_root is not None:
        from specify_cli.migration.gate import check_schema_version

        check_schema_version(project_root, invoked_subcommand=ctx.invoked_subcommand)


def _compute_execute_mode(mode: int) -> int:
    new_mode = mode
    if mode & 0o400:
        new_mode |= 0o100
    if mode & 0o040:
        new_mode |= 0o010
    if mode & 0o004:
        new_mode |= 0o001
    if not (new_mode & 0o100):
        new_mode |= 0o100
    return new_mode


def _try_chmod_script(script: Path, scripts_root: Path) -> tuple[bool, str | None]:
    try:
        if script.is_symlink() or not script.is_file():
            return False, None
        try:
            with script.open("rb") as f:
                if f.read(2) != b"#!":
                    return False, None
        except Exception:
            return False, None
        mode = script.stat().st_mode
        if mode & 0o111:
            return False, None
        os.chmod(script, _compute_execute_mode(mode))
        return True, None
    except Exception as e:
        return False, f"{script.relative_to(scripts_root)}: {e}"


def _report_chmod_results(tracker: StepTracker | None, updated: int, failures: list[str]) -> None:
    if tracker:
        detail = f"{updated} updated" + (f", {len(failures)} failed" if failures else "")
        tracker.add("chmod", "Set script permissions recursively")
        (tracker.error if failures else tracker.complete)("chmod", detail)
    else:
        if updated:
            console.print(f"[cyan]Updated execute permissions on {updated} script(s) recursively[/cyan]")
        if failures:
            console.print("[yellow]Some scripts could not be updated:[/yellow]")
            for f in failures:
                console.print(f"  - {f}")


def ensure_executable_scripts(project_path: Path, tracker: StepTracker | None = None) -> None:
    """Ensure POSIX .sh scripts under .kittify/scripts (recursively) have execute bits (no-op on Windows)."""
    if os.name == "nt":
        return  # Windows: skip silently
    scripts_root = project_path / ".kittify" / "scripts"
    if not scripts_root.is_dir():
        return
    failures: list[str] = []
    updated = 0
    for script in scripts_root.rglob("*.sh"):
        was_updated, error = _try_chmod_script(script, scripts_root)
        if was_updated:
            updated += 1
        if error:
            failures.append(error)
    _report_chmod_results(tracker, updated, failures)


# Register the init command with necessary dependencies
register_init_command(
    app,
    console=console,
    show_banner=show_banner,
    activate_mission=activate_mission,
    ensure_executable_scripts=ensure_executable_scripts,
)

register_commands(app)


def main() -> None:
    import sys

    # Ensure UTF-8 encoding on Windows to handle Unicode characters in git output
    # Fixes: https://github.com/Priivacy-ai/spec-kitty/issues/66
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            # Python < 3.7 or reconfigure not available
            pass

    # Check for spec-kitty-events library availability (required for 2.x branch)
    from specify_cli.events.adapter import EventAdapter

    if not EventAdapter.check_library_available():
        console.print(f"[red]{EventAdapter.get_missing_library_error()}[/red]")
        raise typer.Exit(1)

    app()


__all__ = ["main", "app", "__version__"]

if __name__ == "__main__":
    main()
