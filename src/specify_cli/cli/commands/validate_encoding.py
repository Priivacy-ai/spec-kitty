"""Encoding validation command for Spec Kitty CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.table import Table

from specify_cli.acceptance import AcceptanceError, detect_feature_slug
from specify_cli.cli.helpers import console, get_project_root_or_exit
from specify_cli.core.project_resolver import resolve_worktree_aware_feature_dir
from specify_cli.tasks_support import TaskCliError, find_repo_root
from specify_cli.text_sanitization import detect_problematic_characters, sanitize_directory, sanitize_file


def validate_encoding(
    feature: Optional[str] = typer.Option(None, "--feature", help="Feature slug to validate (auto-detected when omitted)"),
    fix: bool = typer.Option(False, "--fix", help="Automatically fix encoding errors by sanitizing files"),
    check_all: bool = typer.Option(False, "--all", help="Check all features, not just one"),
    backup: bool = typer.Option(True, "--backup/--no-backup", help="Create .bak files before fixing"),
) -> None:
    """Validate and optionally fix file encoding in feature artifacts.

    Scans markdown files for Windows-1252 smart quotes and other problematic
    characters that cause UTF-8 encoding errors. Can automatically fix issues
    by replacing problematic characters with safe alternatives.
    """
    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    project_root = get_project_root_or_exit(repo_root)

    if check_all:
        # Validate all features
        kitty_specs = repo_root / "kitty-specs"
        if not kitty_specs.exists():
            console.print("[yellow]No kitty-specs directory found.[/yellow]")
            raise typer.Exit(0)

        feature_dirs = [d for d in kitty_specs.iterdir() if d.is_dir()]
        if not feature_dirs:
            console.print("[yellow]No feature directories found.[/yellow]")
            raise typer.Exit(0)

        console.print(f"[cyan]Checking encoding for {len(feature_dirs)} features...[/cyan]")
        console.print()

        total_issues = 0
        total_fixed = 0

        for feature_dir in sorted(feature_dirs):
            issues, fixed = _validate_feature_dir(feature_dir, fix=fix, backup=backup)
            total_issues += issues
            total_fixed += fixed

        console.print()
        console.print(Panel(
            f"[bold]Summary:[/bold]\n"
            f"Total files with issues: [yellow]{total_issues}[/yellow]\n"
            f"Total files fixed: [green]{total_fixed}[/green]",
            title="Encoding Validation Complete",
            border_style="cyan" if total_issues == 0 else "yellow",
        ))

        raise typer.Exit(0 if total_issues == 0 or fix else 1)

    # Validate single feature
    try:
        feature_slug = (feature or detect_feature_slug(repo_root, cwd=Path.cwd())).strip()
    except AcceptanceError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    feature_dir = resolve_worktree_aware_feature_dir(repo_root, feature_slug, Path.cwd(), console)

    if not feature_dir.exists():
        console.print(f"[red]Error:[/red] Feature directory not found: {feature_dir}")
        raise typer.Exit(1)

    console.print(f"[cyan]Validating encoding for feature:[/cyan] {feature_slug}")
    console.print()

    issues, fixed = _validate_feature_dir(feature_dir, fix=fix, backup=backup)

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


def _validate_feature_dir(feature_dir: Path, *, fix: bool, backup: bool) -> tuple[int, int]:
    """Validate encoding for a single feature directory.

    Returns:
        Tuple of (issues_found, files_fixed)
    """
    console.print(f"[cyan]Checking:[/cyan] {feature_dir.name}")

    # Scan all markdown files
    results = sanitize_directory(feature_dir, pattern="**/*.md", backup=backup, dry_run=not fix)

    files_with_issues = []
    files_fixed = []
    file_errors = []

    for file_path_str, (was_modified, error) in results.items():
        file_path = Path(file_path_str)
        relative_path = file_path.relative_to(feature_dir) if file_path.is_relative_to(feature_dir) else file_path

        if error:
            file_errors.append((relative_path, error))
        elif was_modified:
            files_with_issues.append(relative_path)
            if fix:
                files_fixed.append(relative_path)

    # Display results
    if files_with_issues:
        table = Table(title=f"Files with Encoding Issues: {feature_dir.name}", show_header=True)
        table.add_column("File", style="cyan")
        table.add_column("Status", style="yellow")

        for file_path in files_with_issues:
            status = "[green]Fixed[/green]" if fix else "[yellow]Needs Fix[/yellow]"
            table.add_row(str(file_path), status)

        console.print(table)

        # Show detailed character issues for first file
        if files_with_issues and not fix:
            first_file = feature_dir / files_with_issues[0]
            try:
                # Read with fallback encoding
                try:
                    content = first_file.read_text(encoding="utf-8")
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
                        console.print(
                            f"  Line {line_num}, col {col}: '{char}' (U+{ord(char):04X}) → '{replacement}'"
                        )
                    if len(issues) > 5:
                        console.print(f"  ... and {len(issues) - 5} more")
            except Exception:
                pass

    if file_errors:
        console.print()
        console.print("[red]Errors encountered:[/red]")
        for file_path, error in file_errors:
            console.print(f"  [red]✗[/red] {file_path}: {error}")

    return len(files_with_issues), len(files_fixed)


__all__ = ["validate_encoding"]
