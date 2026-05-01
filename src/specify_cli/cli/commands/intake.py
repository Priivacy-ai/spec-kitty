"""``spec-kitty intake`` command — ingest a plan document as a mission brief."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console

from specify_cli.intake.errors import (
    IntakeFileMissingError,
    IntakeFileUnreadableError,
    IntakeTooLargeError,
)
from specify_cli.intake.scanner import (
    load_max_brief_bytes,
    read_brief,
    read_stdin_capped,
)
from specify_cli.intake_sources import scan_for_plans
from specify_cli.mission_brief import (
    BRIEF_SOURCE_FILENAME,
    MISSION_BRIEF_FILENAME,
    read_brief_source,
    read_mission_brief,
    write_mission_brief,
)
from specify_cli.task_utils import TaskCliError, find_repo_root

console = Console()
err_console = Console(stderr=True)

# Maximum size for a mission brief file. Resolved from `.kittify/config.yaml`
# (`intake.max_brief_bytes`) at request time via `load_max_brief_bytes()`. The
# constant below is the documented hard fallback used when no config file is
# present; it must match `intake.scanner.DEFAULT_MAX_BRIEF_BYTES`.
MAX_BRIEF_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB


def _format_too_large_message(exc: IntakeTooLargeError) -> str:
    """Render an `IntakeTooLargeError` into a user-friendly stderr line."""
    size = exc.detail.get("size")
    cap = exc.detail.get("cap", 0)
    if isinstance(size, int):
        size_str = f"{size / 1024 / 1024:.1f} MB"
    else:
        size_str = "size unknown"
    cap_mb = max(cap // 1024 // 1024, 1)
    return (
        f"[red]File is too large to ingest ({size_str}). "
        f"Maximum allowed size is {cap_mb} MB.[/red]"
    )


def _resolve_repo_root() -> Path:
    """Resolve the project root for brief artifacts, falling back to CWD."""
    try:
        return find_repo_root(Path.cwd())
    except TaskCliError:
        return Path.cwd().resolve()


def _write_brief_from_candidate(
    repo_root: Path,
    found_path: Path,
    harness_key: str,
    source_agent_value: str | None,
    *,
    force: bool,
) -> None:
    """Write the brief from a resolved candidate file; exits 1 on conflict or error."""
    console.print(f"BRIEF DETECTED: {found_path} (source: {harness_key})")
    brief_path = repo_root / ".kittify" / MISSION_BRIEF_FILENAME
    source_path = repo_root / ".kittify" / BRIEF_SOURCE_FILENAME
    # Only block on an existing brief if BOTH files are present (complete state).
    # If only one file exists, that is partial state from a prior interrupted write;
    # write_mission_brief() will clean it up before re-writing.
    if brief_path.exists() and source_path.exists() and not force:
        err_console.print(
            "Brief already exists at .kittify/mission-brief.md. Use --force to overwrite."
        )
        raise typer.Exit(1)
    cap = load_max_brief_bytes(repo_root)
    try:
        content = read_brief(found_path, cap=cap)
    except IntakeTooLargeError as exc:
        err_console.print(_format_too_large_message(exc))
        raise typer.Exit(1) from None
    except IntakeFileMissingError:
        err_console.print(f"[red]File not found: {found_path}[/red]")
        raise typer.Exit(1) from None
    except IntakeFileUnreadableError as exc:
        err_console.print(f"[red]Could not read file: {exc.__cause__}[/red]")
        raise typer.Exit(1) from None
    write_mission_brief(repo_root, content, str(found_path), source_agent=source_agent_value)
    console.print("[green]\u2713[/green] Brief written to .kittify/mission-brief.md")
    console.print("[green]\u2713[/green] Provenance written to .kittify/brief-source.yaml")


def _prompt_candidate_selection(
    candidates: list[tuple[Path, str, str | None]],
) -> tuple[Path, str, str | None]:
    """Interactively prompt the user to pick one candidate; exits 1 on bad input."""
    err_console.print("Found multiple plan documents. Which should I use?")
    for idx, (found_path, harness_key, _) in enumerate(candidates, start=1):
        err_console.print(f"  {idx}. {found_path}  ({harness_key})")

    if not sys.stdin.isatty():
        err_console.print(
            "\nNon-interactive stdin — pass a path explicitly: spec-kitty intake <path>"
        )
        raise typer.Exit(1)

    selection_str = typer.prompt("Enter number")
    try:
        selection = int(selection_str)
        if not 1 <= selection <= len(candidates):
            raise ValueError  # noqa: TRY301
    except ValueError:
        err_console.print(
            f"[red]Invalid selection. Enter a number between 1 and {len(candidates)}.[/red]"
        )
        raise typer.Exit(1) from None

    return candidates[selection - 1]


def _auto_branch(repo_root: Path, *, force: bool) -> None:
    """Implement the --auto scan-and-ingest logic."""
    candidates = scan_for_plans(repo_root)

    if not candidates:
        err_console.print(
            "No plan document detected in known harness locations.\n"
            "Pass a path explicitly: spec-kitty intake <path>"
        )
        raise typer.Exit(1)

    if len(candidates) == 1:
        found_path, harness_key, source_agent_value = candidates[0]
    else:
        found_path, harness_key, source_agent_value = _prompt_candidate_selection(candidates)

    _write_brief_from_candidate(
        repo_root,
        found_path,
        harness_key,
        source_agent_value,
        force=force,
    )


def intake(
    path: str | None = typer.Argument(
        None,
        help="Path to plan document, or '-' to read from stdin. Omit when using --show or --auto.",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing brief."),
    show: bool = typer.Option(False, "--show", help="Print current brief and provenance; no writes."),
    auto: bool = typer.Option(False, "--auto", help="Scan known harness plan locations and ingest automatically."),
) -> None:
    """Ingest a plan document as a mission brief for /spec-kitty.specify."""
    repo_root = _resolve_repo_root()

    # --show branch: print and exit, no writes
    if show:
        try:
            brief = read_mission_brief(repo_root)
        except IntakeFileUnreadableError as exc:
            err_console.print(
                f"[red]Brief file at .kittify/mission-brief.md exists but is "
                f"unreadable: {exc.__cause__}[/red]"
            )
            raise typer.Exit(2) from None
        try:
            source = read_brief_source(repo_root)
        except IntakeFileUnreadableError as exc:
            err_console.print(
                f"[red]Brief provenance at .kittify/brief-source.yaml exists "
                f"but is unreadable: {exc.__cause__}[/red]"
            )
            raise typer.Exit(2) from None
        if brief is None and source is None:
            err_console.print("[red]No brief found at .kittify/mission-brief.md[/red]")
            raise typer.Exit(1)
        if source is not None:
            console.print(
                f"[bold]Source:[/bold] {source.get('source_file', '')} "
                f"  [bold]Ingested:[/bold] {source.get('ingested_at', '')} "
                f"  [bold]Hash:[/bold] {source.get('brief_hash', '')[:16]}..."
            )
        if brief is not None:
            console.print(brief)
        return

    # --auto + path mutual exclusion
    if path is not None and auto:
        err_console.print("[red]--auto cannot be combined with a positional path argument.[/red]")
        raise typer.Exit(1)

    # --auto branch
    if auto:
        _auto_branch(repo_root, force=force)
        return

    # No path, no --show, no --auto: print usage hint and exit 1
    if path is None:
        err_console.print("[red]Provide a file path, '-' for stdin, --show, or --auto[/red]")
        raise typer.Exit(1)

    # Normal write branch
    brief_path = repo_root / ".kittify" / MISSION_BRIEF_FILENAME
    _source_path = repo_root / ".kittify" / BRIEF_SOURCE_FILENAME
    # Gate only on complete state (both files present). Partial state is recovered by
    # write_mission_brief() and should not block re-ingest.
    if brief_path.exists() and _source_path.exists() and not force:
        err_console.print(
            "Brief already exists at .kittify/mission-brief.md. Use --force to overwrite."
        )
        raise typer.Exit(1)

    # Read content from file or stdin via the bounded intake helpers so
    # the documented size cap (FR-009 / NFR-003) is enforced before the
    # entire payload is buffered into memory.
    cap = load_max_brief_bytes(repo_root)
    if path == "-":
        try:
            content = read_stdin_capped(sys.stdin, cap=cap)
        except IntakeTooLargeError as exc:
            err_console.print(_format_too_large_message(exc))
            raise typer.Exit(1) from None
        except IntakeFileUnreadableError as exc:
            err_console.print(f"[red]Could not read stdin: {exc.__cause__}[/red]")
            raise typer.Exit(1) from None
        source_file = "stdin"
    else:
        explicit_path = Path(path)
        try:
            content = read_brief(explicit_path, cap=cap)
        except IntakeTooLargeError as exc:
            err_console.print(_format_too_large_message(exc))
            raise typer.Exit(1) from None
        except IntakeFileMissingError:
            err_console.print(f"[red]File not found: {path}[/red]")
            raise typer.Exit(1) from None
        except IntakeFileUnreadableError as exc:
            err_console.print(f"[red]Could not read file: {exc.__cause__}[/red]")
            raise typer.Exit(1) from None
        source_file = path

    write_mission_brief(repo_root, content, source_file)
    console.print("[green]\u2713[/green] Brief written to .kittify/mission-brief.md")
    console.print("[green]\u2713[/green] Provenance written to .kittify/brief-source.yaml")
