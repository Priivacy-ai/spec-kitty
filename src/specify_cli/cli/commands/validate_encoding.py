"""Encoding validation command for Spec Kitty CLI."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from specify_cli.acceptance import AcceptanceError, detect_mission_slug
from specify_cli.cli.helpers import check_version_compatibility, console, get_project_root_or_exit
from specify_cli.core.project_resolver import resolve_worktree_aware_mission_dir
from specify_cli.tasks_support import TaskCliError, find_repo_root
from specify_cli.text_sanitization import detect_problematic_characters, sanitize_directory


def validate_encoding(
    mission: str | None = typer.Option(None, "--mission", help="Mission slug to validate (auto-detected when omitted)"),
    fix: bool = typer.Option(False, "--fix", help="Automatically fix encoding errors by sanitizing files"),
    check_all: bool = typer.Option(False, "--all", help="Check all missions, not just one"),
    backup: bool = typer.Option(True, "--backup/--no-backup", help="Create .bak files before fixing"),
) -> None:
    """Validate and optionally fix file encoding in mission artifacts.

    Scans markdown files for Windows-1252 smart quotes and other problematic
    characters that cause UTF-8 encoding errors. Can automatically fix issues
    by replacing problematic characters with safe alternatives.
    """
    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    project_root = get_project_root_or_exit(repo_root)
    check_version_compatibility(project_root, "validate-encoding")

    if check_all:
        # Validate all missions
        kitty_specs = repo_root / "kitty-specs"
        if not kitty_specs.exists():
            console.print("[yellow]No kitty-specs directory found.[/yellow]")
            raise typer.Exit(0)

        mission_dirs = [d for d in kitty_specs.iterdir() if d.is_dir()]
        if not mission_dirs:
            console.print("[yellow]No mission directories found.[/yellow]")
            raise typer.Exit(0)

        console.print(f"[cyan]Checking encoding for {len(mission_dirs)} missions...[/cyan]")
        console.print()

        total_issues = 0
        total_fixed = 0

        for mission_dir in sorted(mission_dirs):
            issues, fixed = _validate_mission_dir(mission_dir, fix=fix, backup=backup)
            total_issues += issues
            total_fixed += fixed

        console.print()
        console.print(
            Panel(
                f"[bold]Summary:[/bold]\n"
                f"Total files with issues: [yellow]{total_issues}[/yellow]\n"
                f"Total files fixed: [green]{total_fixed}[/green]",
                title="Encoding Validation Complete",
                border_style="cyan" if total_issues == 0 else "yellow",
            )
        )

        raise typer.Exit(0 if total_issues == 0 or fix else 1)

    # Validate single mission
    try:
        mission_slug = (mission or detect_mission_slug(repo_root, cwd=Path.cwd())).strip()
    except AcceptanceError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    mission_dir = resolve_worktree_aware_mission_dir(repo_root, mission_slug, Path.cwd(), console)

    if not mission_dir.exists():
        console.print(f"[red]Error:[/red] Mission directory not found: {mission_dir}")
        raise typer.Exit(1)

    console.print(f"[cyan]Validating encoding for mission:[/cyan] {mission_slug}")
    console.print()

    issues, fixed = _validate_mission_dir(mission_dir, fix=fix, backup=backup)

    if issues == 0:
        console.print("[green]✓ All files are properly UTF-8 encoded![/green]")
        raise typer.Exit(0)
    elif fix and fixed > 0:
        console.print()
        console.print(f"[green]✓ Fixed {fixed} file(s) with encoding issues.[/green]")
        if backup:
            console.print("[dim]Backup files (.bak) were created.[/dim]")
        raise typer.Exit(0)
    else:
        console.print()
        console.print(f"[yellow]Found {issues} file(s) with encoding issues.[/yellow]")
        console.print("[dim]Run with --fix to automatically repair these files.[/dim]")
        raise typer.Exit(1)


def _validate_mission_dir(mission_dir: Path, *, fix: bool, backup: bool) -> tuple[int, int]:  # noqa: C901
    """Validate encoding for a single mission directory.

    Returns:
        Tuple of (issues_found, files_fixed)
    """
    console.print(f"[cyan]Checking:[/cyan] {mission_dir.name}")

    # Scan all markdown files
    results = sanitize_directory(mission_dir, pattern="**/*.md", backup=backup, dry_run=not fix)

    files_with_issues = []
    files_fixed = []
    file_errors = []

    for file_path_str, (was_modified, error) in results.items():
        file_path = Path(file_path_str)
        relative_path = file_path.relative_to(mission_dir) if file_path.is_relative_to(mission_dir) else file_path

        if error:
            file_errors.append((relative_path, error))
        elif was_modified:
            files_with_issues.append(relative_path)
            if fix:
                files_fixed.append(relative_path)

    # Display results
    if files_with_issues:
        table = Table(title=f"Files with Encoding Issues: {mission_dir.name}", show_header=True)
        table.add_column("File", style="cyan")
        table.add_column("Status", style="yellow")

        for file_path in files_with_issues:
            status = "[green]Fixed[/green]" if fix else "[yellow]Needs Fix[/yellow]"
            table.add_row(str(file_path), status)

        console.print(table)

        # Show detailed character issues for first file
        if files_with_issues and not fix:
            first_file = mission_dir / files_with_issues[0]
            try:
                # Read with fallback encoding
                try:
                    content = first_file.read_text(encoding="utf-8-sig")
                except UnicodeDecodeError:
                    content_bytes = first_file.read_bytes()
                    for encoding in ("cp1252", "latin-1"):
                        try:
                            content = content_bytes.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        content = content_bytes.decode("utf-8", errors="replace")

                issues = detect_problematic_characters(content)
                if issues:
                    console.print()
                    console.print(f"[yellow]Example issues in {files_with_issues[0]}:[/yellow]")
                    for line_num, col, char, replacement in issues[:5]:  # Show first 5
                        console.print(f"  Line {line_num}, col {col}: '{char}' (U+{ord(char):04X}) → '{replacement}'")
                    if len(issues) > 5:
                        console.print(f"  ... and {len(issues) - 5} more")
            except Exception:  # noqa: S110
                pass

    if file_errors:
        console.print()
        console.print("[red]Errors encountered:[/red]")
        for file_path, error in file_errors:
            console.print(f"  [red]✗[/red] {file_path}: {error}")

    return len(files_with_issues), len(files_fixed)


__all__ = ["validate_encoding"]
