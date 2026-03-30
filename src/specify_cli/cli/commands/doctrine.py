"""Doctrine management commands — thin CLI adapter over doctrine.curation.workflow."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from doctrine.artifact_kinds import ArtifactKind
from doctrine.curation.state import CurationSession, clear_session, load_session
from doctrine.curation.workflow import (
    CurationAborted,
    CurationIO,
    VerdictOrQuit,
    get_status_counts,
    load_or_create_session,
    promote_single,
    run_curate_session,
)
from doctrine.curation.engine import ProposedArtifact
from specify_cli.tasks_support import TaskCliError, find_repo_root

app = typer.Typer(
    name="doctrine",
    help="Doctrine artifact management — curation, status, promotion",
    no_args_is_help=True,
)

console = Console()


# ---------------------------------------------------------------------------
# Presentation helpers (CLI-layer only — no business logic)
# ---------------------------------------------------------------------------


def _present_artifact(
    art: ProposedArtifact, index: int, total: int, parent: ProposedArtifact | None = None
) -> None:
    header = f"[{index}/{total}] {art.artifact_type.upper()} — {art.title}"
    lines = [f"[dim]id:[/dim] {art.artifact_id}", f"[dim]file:[/dim] {art.filename}"]
    if parent:
        lines.append(
            f"[bold yellow]↳ referenced by {parent.artifact_type}:{parent.artifact_id}[/bold yellow]"
        )
    for key, val in art.summary_fields.items():
        display_val = val if len(val) < 200 else val[:197] + "..."
        lines.append(f"[dim]{key}:[/dim] {display_val}")
    console.print(Panel("\n".join(lines), title=header, border_style="cyan"))


def _prompt_verdict() -> VerdictOrQuit:
    choice = typer.prompt(
        "[a]ccept / [d]rop / [s]kip / [q]uit", default="s"
    ).strip().lower()
    if choice in ("a", "accept"):
        return "accepted"
    if choice in ("d", "drop"):
        return "dropped"
    if choice in ("q", "quit"):
        return "quit"
    return "skipped"


def _print_session_summary(session: CurationSession) -> None:
    accepted = len(session.accepted)
    dropped = len(session.dropped)
    skipped = len(session.skipped)
    pending = len(session.pending)
    total = len(session.decisions)

    bar_width = 30
    filled = int(bar_width * (total - pending) / total) if total else 0
    bar = "█" * filled + "░" * (bar_width - filled)

    console.print(
        f"  {bar} {session.progress_percent}%\n"
        f"  [green]{accepted} accepted[/green]  "
        f"[red]{dropped} dropped[/red]  "
        f"[yellow]{skipped} skipped[/yellow]  "
        f"[dim]{pending} pending[/dim]"
    )


def _repo_root() -> Path:
    try:
        return find_repo_root()
    except TaskCliError:
        return Path.cwd()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def curate(
    artifact_type: str | None = typer.Option(
        None, "--type", "-t",
        help=f"Filter by artifact type ({', '.join(k.plural for k in ArtifactKind if k != ArtifactKind.TEMPLATE)})",
    ),
    resume: bool = typer.Option(
        True, "--resume/--fresh",
        help="Resume existing session (default) or start fresh",
    ),
) -> None:
    """Interactive curation interview for _proposed/ artifacts.

    Presents each proposed artifact for review. You decide:
    accept (promote to shipped/), drop (delete), skip (defer), or quit.
    """
    repo_root = _repo_root()
    session, is_resumed = load_or_create_session(repo_root, resume)

    if is_resumed:
        console.print(
            f"[green]Resuming curation session[/green] — "
            f"{session.progress_percent}% complete"
        )
    else:
        console.print("[cyan]Starting new curation session[/cyan]")

    io = CurationIO(
        present=_present_artifact,
        prompt_verdict=_prompt_verdict,
        confirm_drop=lambda filename: typer.confirm(
            f"  Permanently delete {filename}?", default=False
        ),
        on_accepted=lambda _art, dest: console.print(
            f"  [green]✓ Promoted to {dest.relative_to(Path.cwd())}[/green]"
        ),
        on_dropped=lambda art: console.print(f"  [red]✗ Dropped {art.filename}[/red]"),
        on_skipped=lambda _art: console.print("  [dim]→ Skipped[/dim]"),
        on_verdict_downgraded=lambda _art: console.print("  [yellow]→ Skipped instead[/yellow]"),
    )

    try:
        session = run_curate_session(session, repo_root, artifact_type, io)
    except CurationAborted:
        console.print("\n[yellow]Session saved. Resume with:[/yellow] spec-kitty doctrine curate")
        raise typer.Exit(code=0) from None

    console.print()
    _print_session_summary(session)


@app.command()
def status() -> None:
    """Show curation status — what's proposed vs shipped."""
    counts = get_status_counts()

    table = Table(title="Doctrine Artifact Status")
    table.add_column("Type", style="cyan")
    table.add_column("Proposed", justify="right")
    table.add_column("Shipped", justify="right")

    total_proposed = total_shipped = 0
    for art_type in sorted(counts):
        c = counts[art_type]
        table.add_row(art_type, str(c["proposed"]), str(c["shipped"]))
        total_proposed += c["proposed"]
        total_shipped += c["shipped"]

    table.add_section()
    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{total_proposed}[/bold]",
        f"[bold]{total_shipped}[/bold]",
    )
    console.print(table)

    session = load_session(_repo_root())
    if session:
        console.print(f"\n[dim]Curation session: {session.progress_percent}% complete[/dim]")
        _print_session_summary(session)


@app.command()
def promote(
    artifact_id: str = typer.Argument(help="ID of the artifact to promote"),
    artifact_type: str = typer.Option(
        ..., "--type", "-t",
        help=f"Artifact type ({', '.join(k.plural for k in ArtifactKind if k != ArtifactKind.TEMPLATE)})",
    ),
) -> None:
    """Promote a single artifact from _proposed/ to shipped/."""
    try:
        art, dest = promote_single(artifact_id, artifact_type, _repo_root())
    except ValueError as exc:
        console.print(f"[red]Not found:[/red] {exc}")
        raise typer.Exit(code=1) from None
    console.print(f"[green]✓ Promoted {art.filename} → {dest}[/green]")


@app.command()
def reset() -> None:
    """Clear curation session state (does not move artifacts)."""
    repo_root = _repo_root()
    if load_session(repo_root) is None:
        console.print("[dim]No active curation session.[/dim]")
        return

    if typer.confirm("Clear curation session progress?", default=False):
        clear_session(repo_root)
        console.print("[green]Curation session cleared.[/green]")
