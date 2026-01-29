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

from specify_cli.mission import MissionNotFoundError
from specify_cli.cli import StepTracker
from specify_cli.cli.helpers import (
    BannerGroup,
    callback as root_callback,
    console,
    show_banner,
)
from specify_cli.cli.commands import register_commands
from specify_cli.cli.commands.init import register_init_command

def activate_mission(project_path: Path, mission_key: str, mission_display: str, console: Console) -> str:
    """
    DEPRECATED: No-op function for backwards compatibility.

    As of v0.8.0, missions are selected per-feature during /spec-kitty.specify,
    not at the project level during init. This function is kept for backwards
    compatibility with existing init code but no longer sets an active mission.
    """
    # Just verify the mission directory exists
    kittify_root = project_path / ".kittify"
    missions_dir = kittify_root / "missions"
    mission_path = missions_dir / mission_key

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
        console.print(f"spec-kitty-cli version {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="spec-kitty",
    help="Setup tool for Spec Kitty spec-driven development projects",
    add_completion=False,
    invoke_without_command=True,
    cls=BannerGroup,
)

app.callback()(root_callback)


@app.callback()
def main_callback(
    version: bool = typer.Option(None, "--version", "-v", callback=version_callback, is_eager=True, help="Show version and exit")
) -> None:
    """Main callback for version flag."""
    pass


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
        try:
            if script.is_symlink() or not script.is_file():
                continue
            try:
                with script.open("rb") as f:
                    if f.read(2) != b"#!":
                        continue
            except Exception:
                continue
            st = script.stat(); mode = st.st_mode
            if mode & 0o111:
                continue
            new_mode = mode
            if mode & 0o400: new_mode |= 0o100
            if mode & 0o040: new_mode |= 0o010
            if mode & 0o004: new_mode |= 0o001
            if not (new_mode & 0o100):
                new_mode |= 0o100
            os.chmod(script, new_mode)
            updated += 1
        except Exception as e:
            failures.append(f"{script.relative_to(scripts_root)}: {e}")
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


# Register the init command with necessary dependencies
register_init_command(
    app,
    console=console,
    show_banner=show_banner,
    activate_mission=activate_mission,
    ensure_executable_scripts=ensure_executable_scripts,
)

register_commands(app)

def main():
    import sys
    # Ensure UTF-8 encoding on Windows to handle Unicode characters in git output
    # Fixes: https://github.com/Priivacy-ai/spec-kitty/issues/66
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
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
