"""spec-kitty charter pack — charter pack management commands (FR-011)."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from charter.invocation_context import ProjectContext

__all__ = ["charter_pack_app"]

charter_pack_app = typer.Typer(
    name="pack",
    help="Charter pack management commands.",
    no_args_is_help=True,
)
console = Console()


@charter_pack_app.command("consistency-check")
def consistency_check_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    repo_root: Path = typer.Option(Path("."), hidden=True),
) -> None:
    """Run consistency check against activated doctrine artifacts (FR-011)."""
    from charter.consistency_check import run_consistency_check  # noqa: PLC0415

    ctx = ProjectContext.from_repo(repo_root)
    report = run_consistency_check(ctx)
    if json_output:
        typer.echo(report.to_json())
    else:
        if report.coherent:
            console.print("[green]Charter pack is coherent.[/green]")
        else:
            console.print("[red]Consistency issues found:[/red]")
            for ref in report.unknown_references:
                console.print(f"  [red]Unknown reference:[/red] {ref}")
            for ref in report.missing_from_doctrine:
                console.print(f"  [yellow]Missing from doctrine:[/yellow] {ref}")
            for v in report.kind_violations:
                console.print(f"  [red]Kind violation:[/red] {v}")
            for s in report.suggestions:
                console.print(f"  [dim]Suggestion:[/dim] {s}")
    raise typer.Exit(0 if report.coherent else 1)
