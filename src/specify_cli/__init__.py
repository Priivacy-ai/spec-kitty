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
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any


import typer  # noqa: E402

if TYPE_CHECKING:
    from rich.console import Console
    from specify_cli.cli import StepTracker

# Get version from package metadata
# Test mode: use environment override to ensure tests use source version
if os.environ.get("SPEC_KITTY_TEST_MODE") == "1":
    __version__ = os.environ.get("SPEC_KITTY_CLI_VERSION", "0.5.0-dev")
else:
    from specify_cli.version_utils import get_version

    __version__ = get_version()

_APP: typer.Typer | None = None


def root_callback(*args: Any, **kwargs: Any) -> Any:
    from specify_cli.cli.helpers import callback as _root_callback

    return _root_callback(*args, **kwargs)


def locate_project_root() -> Path | None:
    from specify_cli.core.project_resolver import locate_project_root as _locate_project_root

    return _locate_project_root()


def activate_mission(project_path: Path, mission_type: str, mission_display: str, console: "Console") -> str:
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
        from specify_cli.cli.helpers import console, show_banner

        show_banner(force=True)
        console.print(f"spec-kitty-cli version {__version__}")
        raise typer.Exit()

def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(  # noqa: ARG001
        None, "--version", "-v", callback=version_callback, is_eager=True, help="Show version and exit"
    ),
) -> None:
    """Main callback for root CLI setup."""
    import sys

    if _is_doctor_restart_daemon_invocation(sys.argv):
        return

    next_fast_path = _is_next_invocation(sys.argv)
    if not next_fast_path:
        root_callback(ctx)

        # FR-002: Ensure global runtime (~/.kittify/) is populated and current.
        # Must run BEFORE check_version_pin() so global assets are available.
        from specify_cli.runtime.agent_commands import ensure_global_agent_commands
        from specify_cli.runtime.agent_skills import ensure_global_agent_skills
        from specify_cli.runtime.bootstrap import ensure_runtime

        ensure_runtime()
        ensure_global_agent_skills()
        if not _is_doctor_skills_invocation(sys.argv):
            ensure_global_agent_commands()

    _run_startup_project_gates(ctx)


def _run_startup_project_gates(ctx: typer.Context) -> None:
    """Run project-local safety gates shared by normal and startup-fast paths."""
    from specify_cli.runtime.bootstrap import check_version_pin

    # F-Pin-001 / 1A-16: Warn on runtime.pin_version for all project invocations.
    project_root = locate_project_root()
    if project_root is not None:
        check_version_pin(project_root)

    # FR-019 / FR-020: Schema version gate — refuse unmigrated or newer-than-CLI
    # projects before any command runs.  Exempt upgrade/init/--version/--help.
    if project_root is not None:
        from specify_cli.migration.gate import check_schema_version

        check_schema_version(project_root, invoked_subcommand=ctx.invoked_subcommand)


def _build_app() -> typer.Typer:
    from specify_cli.cli.commands import register_commands
    from specify_cli.cli.commands.init import register_init_command
    from specify_cli.cli.helpers import BannerGroup

    app = typer.Typer(
        name="spec-kitty",
        help=(
            "Setup tool for Spec Kitty spec-driven development projects.\n\n"
            "Set SPEC_KITTY_NO_UPGRADE_CHECK=1 to disable the upgrade-check notice."
        ),
        add_completion=False,
        invoke_without_command=True,
        cls=BannerGroup,
    )
    app.callback()(main_callback)
    register_init_command(
        app,
        console=_get_console(),
        show_banner=_get_show_banner(),
        activate_mission=activate_mission,
        ensure_executable_scripts=ensure_executable_scripts,
    )
    register_commands(app)
    return app


def _is_doctor_skills_invocation(argv: list[str]) -> bool:
    """Return True for ``spec-kitty doctor skills`` invocations.

    ``doctor skills`` audits and reports slash-command gaps itself. Running the
    startup slash-command repair first would hide those gaps from the doctor's
    machine-readable repair payload.
    """
    args = [arg for arg in argv[1:] if not arg.startswith("-")]
    return len(args) >= 2 and args[0] == "doctor" and args[1] == "skills"


def _is_next_invocation(argv: list[str]) -> bool:
    """Return True for direct ``spec-kitty next`` invocations.

    ``next`` is the startup-sensitive mission loop command. It performs its
    own project-root resolution, charter preflight, and command validation, so
    the root callback must not run global asset repair on this path.
    """
    for arg in argv[1:]:
        if arg in {"--help", "-h"}:
            return False
        if arg == "next":
            return True
        if not arg.startswith("-"):
            return False
    return False


def _get_app() -> typer.Typer:
    global _APP
    if _APP is None:
        _APP = _build_app()
    return _APP


def _get_console() -> Any:
    from specify_cli.cli.helpers import console

    return console


def _get_show_banner() -> Any:
    from specify_cli.cli.helpers import show_banner

    return show_banner


def __getattr__(name: str) -> Any:
    if name == "app":
        return _get_app()
    raise AttributeError(name)


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


def _report_chmod_results(tracker: "StepTracker | None", updated: int, failures: list[str]) -> None:
    if tracker:
        detail = f"{updated} updated" + (f", {len(failures)} failed" if failures else "")
        tracker.add("chmod", "Set script permissions recursively")
        (tracker.error if failures else tracker.complete)("chmod", detail)
    else:
        console = _get_console()
        if updated:
            console.print(f"[cyan]Updated execute permissions on {updated} script(s) recursively[/cyan]")
        if failures:
            console.print("[yellow]Some scripts could not be updated:[/yellow]")
            for f in failures:
                console.print(f"  - {f}")


def ensure_executable_scripts(project_path: Path, tracker: "StepTracker | None" = None) -> None:
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


def _is_doctor_restart_daemon_invocation(argv: list[str]) -> bool:
    if any(arg in {"--help", "-h"} for arg in argv[1:]):
        return False
    command_parts: list[str] = []
    for arg in argv[1:]:
        if arg.startswith("-"):
            continue
        command_parts.append(arg)
        if len(command_parts) == 2:
            return command_parts == ["doctor", "restart-daemon"]
    return False


def _is_doctor_restart_daemon_process_fast_path(argv: list[str]) -> bool:
    if any(arg in {"--help", "-h"} for arg in argv[1:]):
        return False
    command_parts: list[str] = []
    for arg in argv[1:]:
        if arg.startswith("-"):
            if arg != "--json":
                return False
            continue
        command_parts.append(arg)
    return command_parts == ["doctor", "restart-daemon"]


def _run_doctor_restart_daemon_process_fast_path(argv: list[str]) -> None:
    os.environ["SPEC_KITTY_SYNC_MINIMAL_IMPORT"] = "1"
    from specify_cli.sync.restart import render_restart_result, restart_daemon

    result = restart_daemon(Path.cwd())
    sys.stdout.write(render_restart_result(result, json_output="--json" in argv) + "\n")
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(result.exit_code)


def main() -> None:
    # FR-130 / FR-131: Install the CLI logging bootstrap early — before the
    # Typer app runs — so that warnings.warn(...) calls (including
    # CharterCatalogMissWarning from charter._catalog_miss) are routed through
    # the logging subsystem and appear in the operator's terminal.
    # This is additive-only: if a handler is already attached, no second
    # handler is installed (no double-printing).
    from specify_cli.cli.logging_bootstrap import install_cli_logging_bootstrap

    install_cli_logging_bootstrap()

    # Ensure UTF-8 encoding on Windows to handle Unicode characters in git output
    # Fixes: https://github.com/Priivacy-ai/spec-kitty/issues/66
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            # Python < 3.7 or reconfigure not available
            pass

    if _is_doctor_restart_daemon_process_fast_path(sys.argv):
        _run_doctor_restart_daemon_process_fast_path(sys.argv)

    # Check for spec-kitty-events library availability (required for 2.x branch)
    from specify_cli.events.adapter import EventAdapter

    if not EventAdapter.check_library_available():
        _get_console().print(f"[red]{EventAdapter.get_missing_library_error()}[/red]")
        raise typer.Exit(1)

    _get_app()()


__all__ = ["main", "app", "__version__"]

if __name__ == "__main__":
    main()
