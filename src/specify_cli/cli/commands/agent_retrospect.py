"""Agent retrospect commands — synthesizer CLI surface (WP08 / FR-021).

Command surface: ``spec-kitty agent retrospect synthesize``

Default is dry-run.  Pass ``--apply`` to mutate project-local doctrine,
DRG, or glossary state.

Source-of-truth contract:
    kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/contracts/cli_surfaces.md
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from specify_cli.cli.selector_resolution import resolve_mission_handle
from specify_cli.core.paths import locate_project_root
from specify_cli.doctrine_synthesizer import (
    SynthesisResult,
    apply_proposals,
)
from specify_cli.retrospective.reader import SchemaError, YAMLParseError, read_record
from specify_cli.retrospective.schema import ActorRef

app = typer.Typer(
    name="retrospect",
    help="Retrospective synthesis commands for AI agents",
    no_args_is_help=True,
)

_console = Console()
_err_console = Console(stderr=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _retro_path(repo_root: Path, mission_id: str) -> Path:
    """Return the canonical retrospective.yaml path for a mission."""
    return repo_root / ".kittify" / "missions" / mission_id / "retrospective.yaml"


def _build_actor(actor_id: Optional[str]) -> ActorRef:
    """Build an :class:`ActorRef` from the supplied actor-id or environment."""
    resolved_id = actor_id or "agent"
    return ActorRef(kind="agent", id=resolved_id)


def _render_rich(result: SynthesisResult, *, dry_run: bool) -> None:
    """Render a :class:`SynthesisResult` as a Rich table to stdout.

    Informationally equivalent to the JSON ``result`` field (CHK034):
    - planned count + proposal_id + kind + diff_preview
    - applied count + proposal_id + target_urn + artifact_path
    - conflicts count + proposal_ids + reason
    - rejected count + proposal_id + reason + detail
    """
    mode_label = "[yellow]DRY-RUN[/yellow]" if dry_run else "[green]APPLY[/green]"
    _console.print(f"\n[bold]agent retrospect synthesize[/bold]  ({mode_label})\n")

    # Planned applications
    if result.planned:
        planned_table = Table(title="Planned Applications", show_header=True, header_style="bold cyan")
        planned_table.add_column("proposal_id", style="dim", no_wrap=True)
        planned_table.add_column("kind")
        planned_table.add_column("diff_preview")
        for p in result.planned:
            planned_table.add_row(p.proposal_id, p.kind, p.diff_preview)
        _console.print(planned_table)
    else:
        _console.print("[dim]No planned applications.[/dim]")

    # Applied changes (only populated when dry_run=False)
    if result.applied:
        applied_table = Table(title="Applied Changes", show_header=True, header_style="bold green")
        applied_table.add_column("proposal_id", style="dim", no_wrap=True)
        applied_table.add_column("target_urn")
        applied_table.add_column("artifact_path")
        applied_table.add_column("re_applied")
        for a in result.applied:
            applied_table.add_row(
                a.proposal_id,
                a.target_urn,
                a.artifact_path,
                str(a.re_applied),
            )
        _console.print(applied_table)

    # Conflicts
    if result.conflicts:
        conflict_table = Table(title="Conflicts", show_header=True, header_style="bold red")
        conflict_table.add_column("proposal_ids")
        conflict_table.add_column("reason")
        for cg in result.conflicts:
            conflict_table.add_row(", ".join(cg.proposal_ids), cg.reason)
        _console.print(conflict_table)

    # Rejections
    if result.rejected:
        rejected_table = Table(title="Rejections", show_header=True, header_style="bold magenta")
        rejected_table.add_column("proposal_id", style="dim", no_wrap=True)
        rejected_table.add_column("reason")
        rejected_table.add_column("detail")
        for r in result.rejected:
            rejected_table.add_row(r.proposal_id, r.reason, r.detail)
        _console.print(rejected_table)

    # Summary line
    _console.print(
        f"\n[bold]Summary:[/bold] "
        f"planned={len(result.planned)} "
        f"applied={len(result.applied)} "
        f"conflicts={len(result.conflicts)} "
        f"rejected={len(result.rejected)} "
        f"events_emitted={len(result.events_emitted)}"
    )


def _build_json_envelope(result: SynthesisResult, *, dry_run: bool) -> dict[str, object]:
    """Build the JSON output envelope per cli_surfaces.md / CHK034."""
    return {
        "schema_version": "1",
        "command": "agent.retrospect.synthesize",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "result": result.model_dump(),
    }


# ---------------------------------------------------------------------------
# synthesize subcommand
# ---------------------------------------------------------------------------


@app.command(
    "synthesize",
    help=(
        "Apply staged proposals from a mission's retrospective record.\n\n"
        "--dry-run is the default; pass --apply to mutate project state.\n"
        "flag_not_helpful is the only auto-applied kind (Q2-A).\n"
        "Conflict detection is fail-closed: any conflict blocks the whole batch."
    ),
)
def synthesize_cmd(
    mission: Annotated[str, typer.Option("--mission", help="Mission handle (mission_id / mid8 / mission_slug)")],
    apply: Annotated[bool, typer.Option("--apply", help="Execute application after checks pass (default is dry-run)")] = False,
    proposal_id: Annotated[Optional[list[str]], typer.Option("--proposal-id", help="Restrict batch to specific proposal ids (repeatable)")] = None,
    json_out: Annotated[Optional[Path], typer.Option("--json-out", help="Write JSON envelope to PATH in addition to other output")] = None,
    json_only: Annotated[bool, typer.Option("--json", help="Emit JSON to stdout (suppresses Rich rendering)")] = False,
    actor_id: Annotated[Optional[str], typer.Option("--actor-id", help="Override provenance actor id (default: inferred from environment)")] = None,
) -> None:
    """Apply staged proposals from a mission's retrospective record.

    --dry-run is the default; pass --apply to mutate project-local doctrine,
    DRG, or glossary state.  flag_not_helpful proposals are the only kind
    applied automatically.  Conflict detection is fail-closed.
    """
    # ------------------------------------------------------------------
    # Step 1: Locate project root
    # ------------------------------------------------------------------
    repo_root = locate_project_root()
    if repo_root is None:
        _err_console.print(
            "[red]Error:[/red] Could not locate project root. "
            "Ensure you are inside a spec-kitty project (has .kittify/ or kitty-specs/)."
        )
        raise typer.Exit(1)

    # ------------------------------------------------------------------
    # Step 2: Resolve mission handle → mission_id
    # Exit 1 on unresolvable / ambiguous handle (resolve_mission_handle
    # calls sys.exit(2) internally; we wrap it so our exit code matches
    # the contract's exit=1 for unresolvable).
    # ------------------------------------------------------------------
    try:
        resolved = resolve_mission_handle(mission, repo_root, json_mode=json_only)
    except SystemExit:
        # resolve_mission_handle already printed the error; exit 1 per contract
        raise typer.Exit(1)

    mission_id = resolved.mission_id

    # ------------------------------------------------------------------
    # Step 3: Load retrospective record
    # Exit 2 = I/O error, 3 = malformed/missing
    # ------------------------------------------------------------------
    retro_file = _retro_path(repo_root, mission_id)
    try:
        record = read_record(retro_file)
    except FileNotFoundError:
        msg = f"Retrospective record not found: {retro_file}"
        if json_only:
            _err_console.print_json(json.dumps({"error": "record_not_found", "path": str(retro_file)}))
        else:
            _err_console.print(f"[red]Error:[/red] {msg}")
        raise typer.Exit(3)
    except (YAMLParseError, SchemaError) as exc:
        msg = f"Retrospective record malformed: {exc}"
        if json_only:
            _err_console.print_json(json.dumps({"error": "record_malformed", "detail": str(exc)}))
        else:
            _err_console.print(f"[red]Error:[/red] {msg}")
        raise typer.Exit(3)
    except OSError as exc:
        msg = f"I/O error reading retrospective: {exc}"
        if json_only:
            _err_console.print_json(json.dumps({"error": "io_error", "detail": str(exc)}))
        else:
            _err_console.print(f"[red]Error:[/red] {msg}")
        raise typer.Exit(2)

    # ------------------------------------------------------------------
    # Step 4: Build the proposal batch
    # Default: all proposals with state.status == "accepted", plus all
    # flag_not_helpful proposals (apply_proposals handles the latter
    # automatically).
    # ------------------------------------------------------------------
    all_proposals = record.proposals

    if proposal_id:
        # --proposal-id filter: restrict approved_proposal_ids to those listed
        approved_ids: set[str] = set(proposal_id)
    else:
        # Default: all accepted proposals
        approved_ids = {
            p.id for p in all_proposals if p.state.status == "accepted"
        }

    actor = _build_actor(actor_id)
    dry_run = not apply

    # ------------------------------------------------------------------
    # Step 5: Call apply_proposals
    # ------------------------------------------------------------------
    result = apply_proposals(
        mission_id=mission_id,
        repo_root=repo_root,
        proposals=all_proposals,
        approved_proposal_ids=approved_ids,
        actor=actor,
        dry_run=dry_run,
    )

    # ------------------------------------------------------------------
    # Step 6: Render output (Rich + optional JSON)
    # ------------------------------------------------------------------
    envelope = _build_json_envelope(result, dry_run=dry_run)

    if json_only:
        _console.print_json(json.dumps(envelope))
    else:
        _render_rich(result, dry_run=dry_run)

    if json_out is not None:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
        if not json_only:
            _console.print(f"\n[dim]JSON written to {json_out}[/dim]")

    # ------------------------------------------------------------------
    # Step 7: Exit codes
    # Exit 0 = dry-run complete OR apply succeeded with no issues
    # Exit 4 = conflicts present (apply only)
    # Exit 5 = staleness/invalid-payload rejections (apply only)
    # ------------------------------------------------------------------
    if apply:
        if result.conflicts:
            raise typer.Exit(4)
        has_rejections = any(
            r.reason in ("stale_evidence", "invalid_payload")
            for r in result.rejected
        )
        if has_rejections:
            raise typer.Exit(5)

    raise typer.Exit(0)
