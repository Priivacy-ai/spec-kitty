"""``spec-kitty team-projection publish`` (D1-T1, §3.5/§5).

The only CLI surface for the team/public projection package. No separate
``--public`` flag: the sole opt-in axis is the tracked
``public_projection.enabled`` key in ``.kittify/config.yaml`` (§6.8) — the
CLI has nothing extra to expose beyond ``publish`` itself.
"""

from __future__ import annotations

import json
from typing import Annotated

import typer

from specify_cli.cli.console import console
from specify_cli.core.paths import locate_project_root
from specify_cli.team_projection.provenance import DirtyTreeError
from specify_cli.team_projection.write import write_team_projection

app = typer.Typer(
    name="team-projection",
    help="Read-only team/public mission projections with exact-commit provenance.",
    no_args_is_help=True,
)

_EXIT_OK = 0
_EXIT_REFUSED = 1
_EXIT_ERROR = 2


@app.callback()
def _team_projection_callback() -> None:
    """Read-only team/public mission projections with exact-commit provenance.

    A no-op callback: its only purpose is to keep ``team-projection`` a real
    command GROUP (``spec-kitty team-projection publish``) rather than
    collapsing into the bare ``publish`` command — Typer's single-command
    auto-collapse would otherwise make ``spec-kitty team-projection`` itself
    run ``publish``, dropping the subcommand name the §3.5/§5 CLI surface
    requires.
    """


@app.command("publish")
def publish(
    json_output: Annotated[
        bool, typer.Option("--json", help="Emit the attestation manifest as JSON.")
    ] = False,
) -> None:
    """Build and write every team/public projection artifact for HEAD.

    Refuses (non-zero exit) on a dirty working tree — the manifest-mode
    guarantee is all-or-nothing (§3.4, §4 N10): zero files are written on
    refusal.
    """
    root = locate_project_root()
    if root is None:
        console.print("[red]Not in a spec-kitty project (no project root resolved).[/red]")
        raise typer.Exit(_EXIT_ERROR)

    try:
        manifest = write_team_projection(root)
    except DirtyTreeError as refused:
        console.print(f"[red]team-projection publish refused:[/red] {refused}")
        raise typer.Exit(_EXIT_REFUSED) from refused

    if json_output:
        console.print(json.dumps(manifest.model_dump(mode="json", by_alias=True), sort_keys=True))
        return

    present = sum(1 for entry in manifest.entries if entry.present)
    console.print(
        f"[green]Published[/green] {present} artifact(s) for commit "
        f"{manifest.provenance.commit_sha[:12]}."
    )
    for entry in manifest.entries:
        status = "wrote" if entry.present else "skipped (public opt-out)"
        label = entry.mission_slug or "(index)"
        console.print(f"  {entry.artifact:<24} {label:<30} {status}")


__all__ = ["app", "publish"]
