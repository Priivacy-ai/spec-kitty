"""Glossary management CLI commands.

Provides commands for listing glossary terms, viewing conflict history,
and resolving conflicts asynchronously.

Commands:
    glossary list       -- List all terms across scopes
    glossary conflicts  -- Display conflict history from event log
    glossary resolve    -- Resolve a conflict interactively
"""

import json as json_lib
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from specify_cli.glossary.events import (
    _local_append_event,
    build_clarification_resolved,
    get_event_log_path,
    read_events,
)
from specify_cli.glossary.models import (
    ConflictType,
    SenseRef,
    SemanticConflict,
    Severity,
    TermSurface,
)
from specify_cli.glossary.scope import GlossaryScope, load_seed_file
from specify_cli.glossary.store import GlossaryStore
from specify_cli.glossary.strictness import Strictness

logger = logging.getLogger(__name__)

app = typer.Typer(help="Glossary management commands")
console = Console(width=120)

# Valid scope values for validation
_VALID_SCOPES = {s.value for s in GlossaryScope}

# Valid strictness values for validation
_VALID_STRICTNESS = {s.value for s in Strictness}


def _load_store_from_seeds(repo_root: Path) -> GlossaryStore:
    """Load a GlossaryStore populated from seed files.

    Reads all scope seed files from .kittify/glossaries/ and populates
    an in-memory store.

    Args:
        repo_root: Repository root path

    Returns:
        Populated GlossaryStore
    """
    # Create a dummy event log path (store needs it but we read from seeds)
    event_log_path = repo_root / ".kittify" / "events" / "glossary" / "_cli.events.jsonl"
    store = GlossaryStore(event_log_path)

    for scope in GlossaryScope:
        senses = load_seed_file(scope, repo_root)
        for sense in senses:
            store.add_sense(sense)

    return store


def _get_all_terms_from_store(
    store: GlossaryStore,
    scope_filter: Optional[GlossaryScope] = None,
    status_filter: Optional[str] = None,
) -> list:
    """Retrieve all terms from a GlossaryStore.

    Args:
        store: Populated GlossaryStore
        scope_filter: Filter to specific scope (None = all scopes)
        status_filter: Filter by status (active/deprecated/draft)

    Returns:
        List of TermSense objects matching filters
    """
    terms = []

    # Determine scopes to query
    scopes = [scope_filter] if scope_filter else list(GlossaryScope)

    for scope in scopes:
        scope_value = scope.value
        if scope_value in store._cache:
            for _surface, senses in store._cache[scope_value].items():
                for sense in senses:
                    if status_filter and sense.status.value != status_filter:
                        continue
                    terms.append(sense)

    # Sort by scope precedence, then alphabetically by surface
    terms.sort(key=lambda t: (t.scope, t.surface.surface_text))
    return terms


def _extract_conflicts_from_events(
    events: list[dict],
    mission_filter: Optional[str] = None,
    unresolved_only: bool = False,
    strictness_filter: Optional[str] = None,
) -> list[dict]:
    """Extract conflict records from event log.

    Processes SemanticCheckEvaluated and GlossaryClarificationResolved events
    to build a conflict history with resolved/unresolved status.

    Args:
        events: List of parsed event dicts from JSONL
        mission_filter: Filter to specific mission ID
        unresolved_only: Show only unresolved conflicts
        strictness_filter: Filter by effective strictness level

    Returns:
        List of conflict dicts with status tracking
    """
    conflict_events: list[dict] = []
    resolved_conflict_ids: set[str] = set()

    for event in events:
        event_type = event.get("event_type", "")

        if event_type == "SemanticCheckEvaluated":
            if event.get("blocked"):
                step_id = event.get("step_id", "unknown")
                effective_strictness = event.get("effective_strictness", "unknown")
                for finding in event.get("findings", []):
                    term_data = finding.get("term", {})
                    # Handle both dict format and plain string
                    if isinstance(term_data, dict):
                        term_text = term_data.get("surface_text", "unknown")
                    else:
                        term_text = str(term_data)

                    conflict_id = f"{step_id}-{term_text}"
                    conflict_events.append({
                        "conflict_id": conflict_id,
                        "term": term_text,
                        "type": finding.get("conflict_type", "unknown"),
                        "severity": finding.get("severity", "unknown"),
                        "mission_id": event.get("mission_id", ""),
                        "timestamp": event.get("timestamp", ""),
                        "status": "unresolved",
                        "effective_strictness": effective_strictness,
                    })

        elif event_type == "GlossaryClarificationResolved":
            cid = event.get("conflict_id", "")
            if cid:
                resolved_conflict_ids.add(cid)

    # Mark resolved conflicts
    for conflict in conflict_events:
        if conflict["conflict_id"] in resolved_conflict_ids:
            conflict["status"] = "resolved"

    # Apply filters
    if mission_filter:
        conflict_events = [c for c in conflict_events if c["mission_id"] == mission_filter]

    if unresolved_only:
        conflict_events = [c for c in conflict_events if c["status"] == "unresolved"]

    if strictness_filter:
        conflict_events = [
            c for c in conflict_events
            if c["effective_strictness"] == strictness_filter
        ]

    return conflict_events


@app.command("list")
def list_terms(
    scope: Optional[str] = typer.Option(
        None,
        "--scope",
        help="Filter by scope (mission_local, team_domain, audience_domain, spec_kitty_core)",
    ),
    status: Optional[str] = typer.Option(
        None,
        "--status",
        help="Filter by status (active, deprecated, draft)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON (machine-parseable)",
    ),
) -> None:
    """List all terms in glossary."""
    repo_root = Path.cwd()

    # Validate scope
    scope_enum: Optional[GlossaryScope] = None
    if scope:
        if scope not in _VALID_SCOPES:
            console.print(
                f"[red]Error: Invalid scope '{scope}'. "
                f"Valid scopes: {', '.join(sorted(_VALID_SCOPES))}[/red]"
            )
            raise typer.Exit(1)
        scope_enum = GlossaryScope(scope)

    # Validate status
    valid_statuses = {"active", "deprecated", "draft"}
    if status and status not in valid_statuses:
        console.print(
            f"[red]Error: Invalid status '{status}'. "
            f"Valid statuses: {', '.join(sorted(valid_statuses))}[/red]"
        )
        raise typer.Exit(1)

    # Check glossary directory exists
    glossaries_dir = repo_root / ".kittify" / "glossaries"
    if not glossaries_dir.exists():
        console.print(
            "[red]Error: Glossary not initialized. "
            "Run 'spec-kitty init' with glossary enabled.[/red]"
        )
        raise typer.Exit(1)

    # Load store from seed files
    store = _load_store_from_seeds(repo_root)

    # Get all terms with filters
    all_terms = _get_all_terms_from_store(store, scope_enum, status)

    if not all_terms:
        if json_output:
            print("[]")
        else:
            console.print("[dim]No terms found[/dim]")
        return

    # JSON output for scripting (use print() to avoid Rich markup)
    if json_output:
        output = [
            {
                "surface": term.surface.surface_text,
                "scope": term.scope,
                "definition": term.definition,
                "status": term.status.value,
                "confidence": term.confidence,
            }
            for term in all_terms
        ]
        print(json_lib.dumps(output, indent=2))
        return

    # Rich table output
    table = Table(title="Glossary Terms")
    table.add_column("Scope", style="cyan")
    table.add_column("Term", style="bold")
    table.add_column("Definition")
    table.add_column("Status", style="yellow")
    table.add_column("Confidence", justify="right")

    for term in all_terms:
        status_style = {
            "active": "green",
            "deprecated": "red",
            "draft": "yellow",
        }.get(term.status.value, "white")

        definition = term.definition
        if len(definition) > 60:
            definition = definition[:60] + "..."

        table.add_row(
            term.scope,
            term.surface.surface_text,
            definition,
            f"[{status_style}]{term.status.value}[/{status_style}]",
            f"{term.confidence:.2f}",
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(all_terms)} term(s)[/dim]")


@app.command()
def conflicts(
    mission: Optional[str] = typer.Option(
        None,
        "--mission",
        help="Filter conflicts by mission ID",
    ),
    unresolved_only: bool = typer.Option(
        False,
        "--unresolved",
        help="Show only unresolved conflicts",
    ),
    strictness: Optional[str] = typer.Option(
        None,
        "--strictness",
        help="Filter by effective strictness level (off, medium, max)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON (machine-parseable)",
    ),
) -> None:
    """Display conflict history from event log."""
    repo_root = Path.cwd()

    # Validate strictness filter
    if strictness and strictness not in _VALID_STRICTNESS:
        console.print(
            f"[red]Error: Invalid strictness '{strictness}'. "
            f"Valid values: {', '.join(sorted(_VALID_STRICTNESS))}[/red]"
        )
        raise typer.Exit(1)

    # Collect events from all mission event logs
    events_dir = repo_root / ".kittify" / "events" / "glossary"
    all_events: list[dict] = []

    if events_dir.exists():
        for event_file in sorted(events_dir.glob("*.events.jsonl")):
            for event in read_events(event_file):
                all_events.append(event)

    if not all_events:
        if json_output:
            print("[]")
        else:
            console.print("[dim]No events found in glossary event log[/dim]")
        return

    # Extract conflicts from events
    conflict_events = _extract_conflicts_from_events(
        all_events,
        mission_filter=mission,
        unresolved_only=unresolved_only,
        strictness_filter=strictness,
    )

    if not conflict_events:
        if json_output:
            print("[]")
        else:
            console.print("[dim]No conflicts found[/dim]")
            console.print(f"\n[dim]Total: 0 conflict(s)[/dim]")
        return

    # JSON output (use print() to avoid Rich markup)
    if json_output:
        print(json_lib.dumps(conflict_events, indent=2, default=str))
        return

    # Rich table output
    table = Table(title="Conflict History")
    table.add_column("Conflict ID", style="dim")
    table.add_column("Term", style="bold")
    table.add_column("Type")
    table.add_column("Severity")
    table.add_column("Status")
    table.add_column("Strictness", style="magenta")
    table.add_column("Mission", style="cyan")
    table.add_column("Timestamp")

    for conflict in conflict_events:
        severity_style = {
            "high": "red",
            "medium": "yellow",
            "low": "green",
        }.get(conflict["severity"], "white")

        status_style = {
            "resolved": "green",
            "unresolved": "red",
        }.get(conflict["status"], "white")

        cid = conflict["conflict_id"]
        if len(cid) > 20:
            cid = cid[:20] + "..."

        timestamp = conflict["timestamp"]
        if len(timestamp) > 19:
            timestamp = timestamp[:19]

        table.add_row(
            cid,
            conflict["term"],
            conflict["type"],
            f"[{severity_style}]{conflict['severity']}[/{severity_style}]",
            f"[{status_style}]{conflict['status']}[/{status_style}]",
            conflict.get("effective_strictness", ""),
            conflict.get("mission_id", ""),
            timestamp,
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(conflict_events)} conflict(s)[/dim]")

    # Summary statistics
    unresolved_count = len([c for c in conflict_events if c["status"] == "unresolved"])
    if unresolved_count > 0:
        console.print(f"[red]Unresolved: {unresolved_count}[/red]")


@app.command()
def resolve(
    conflict_id: str = typer.Argument(..., help="Conflict ID to resolve"),
    mission: Optional[str] = typer.Option(
        None,
        "--mission",
        help="Mission ID for event log (auto-detected if omitted)",
    ),
) -> None:
    """Resolve a conflict asynchronously."""
    repo_root = Path.cwd()

    # Collect events from all mission event logs
    events_dir = repo_root / ".kittify" / "events" / "glossary"
    all_events: list[dict] = []
    event_mission_map: dict[str, str] = {}  # conflict_id -> mission_id

    if events_dir.exists():
        for event_file in sorted(events_dir.glob("*.events.jsonl")):
            for event in read_events(event_file):
                all_events.append(event)

    # Find the conflict in events
    conflict_finding: Optional[dict] = None
    conflict_mission_id: Optional[str] = None

    for event in all_events:
        if event.get("event_type") == "SemanticCheckEvaluated" and event.get("blocked"):
            step_id = event.get("step_id", "unknown")
            for finding in event.get("findings", []):
                term_data = finding.get("term", {})
                if isinstance(term_data, dict):
                    term_text = term_data.get("surface_text", "unknown")
                else:
                    term_text = str(term_data)
                cid = f"{step_id}-{term_text}"
                if cid == conflict_id:
                    conflict_finding = finding
                    conflict_mission_id = event.get("mission_id", "unknown")
                    break
            if conflict_finding:
                break

    if not conflict_finding:
        console.print(f"[red]Error: Conflict '{conflict_id}' not found[/red]")
        raise typer.Exit(1)

    # Check if already resolved
    resolved = any(
        e.get("event_type") == "GlossaryClarificationResolved"
        and e.get("conflict_id") == conflict_id
        for e in all_events
    )

    if resolved:
        console.print(f"[yellow]Warning: Conflict '{conflict_id}' already resolved[/yellow]")
        if not typer.confirm("Resolve again?"):
            raise typer.Exit(0)

    # Display conflict details
    term_data = conflict_finding.get("term", {})
    if isinstance(term_data, dict):
        term_text = term_data.get("surface_text", "unknown")
    else:
        term_text = str(term_data)

    console.print(f"\n[bold]Conflict: {conflict_id}[/bold]")
    console.print(f"Term: [cyan]{term_text}[/cyan]")
    console.print(f"Type: {conflict_finding.get('conflict_type', 'unknown')}")
    console.print(f"Severity: {conflict_finding.get('severity', 'unknown')}")
    console.print(f"Context: {conflict_finding.get('context', 'N/A')}")

    # Show candidate senses
    candidates = conflict_finding.get("candidate_senses", [])
    if candidates:
        console.print("\n[bold]Candidate senses:[/bold]")
        for i, candidate in enumerate(candidates, 1):
            console.print(
                f"  {i}. [{candidate.get('scope', '?')}] "
                f"{candidate.get('definition', 'No definition')}"
            )
    console.print()

    # Prompt for resolution
    options_text = ""
    if candidates:
        options_text = f"Enter 1-{len(candidates)} to select a candidate, "
    options_text += "'C' for custom definition, 'D' to defer"
    console.print(f"[dim]{options_text}[/dim]")

    choice = typer.prompt("Resolution")

    effective_mission = mission or conflict_mission_id or "unknown"

    if choice.upper() == "D":
        console.print("[yellow]Conflict deferred (no resolution made)[/yellow]")
        raise typer.Exit(0)

    if choice.upper() == "C":
        custom_def = typer.prompt("Enter custom definition")
        selected_sense = {
            "surface": term_text,
            "scope": "team_domain",
            "definition": custom_def,
            "confidence": 1.0,
        }
    elif candidates and choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(candidates):
            selected_sense = candidates[idx]
        else:
            console.print(f"[red]Error: Invalid selection '{choice}'[/red]")
            raise typer.Exit(1)
    else:
        console.print(f"[red]Error: Invalid choice '{choice}'[/red]")
        raise typer.Exit(1)

    # Build and persist GlossaryClarificationResolved event
    event = build_clarification_resolved(
        conflict_id=conflict_id,
        term_surface=term_text,
        selected_sense=selected_sense,
        actor={
            "actor_id": "user:cli",
            "actor_type": "human",
            "display_name": "CLI User",
        },
        resolution_mode="async",
        provenance={
            "source": "cli_resolve",
            "timestamp": "",
            "actor_id": "user:cli",
        },
    )

    # Persist to event log
    event_log_path = get_event_log_path(repo_root, effective_mission)
    _local_append_event(event, event_log_path)

    console.print("[green]Conflict resolved successfully[/green]")
