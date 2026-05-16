"""``spec-kitty doctrine`` command group.

Surface area:

* ``spec-kitty doctrine fetch [--pack <name>] [--dry-run]`` — fetch one or
  all configured org doctrine packs into their local snapshot directories.
* ``spec-kitty doctrine pack validate <pack-path> [--json]`` — validate a
  doctrine pack against the artifact / DRG / org-charter contracts.
* ``spec-kitty doctrine pack assemble <out> <inputs...> [--force]
  [--conflicts-out FILE] [--json]`` — assemble multiple input packs into a
  single distributable output pack.

Both ``pack validate`` and ``pack assemble`` are implemented by WP06; their
heavy lifting lives in :mod:`specify_cli.doctrine.pack_validator` and
:mod:`specify_cli.doctrine.pack_assembler` so this module only handles
argument parsing and exit-code mapping.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

__all__ = ["app"]

app = typer.Typer(
    name="doctrine",
    help="Manage org-layer doctrine packs (fetch, validate, assemble).",
    no_args_is_help=True,
)

pack_app = typer.Typer(
    name="pack",
    help="Validate or assemble doctrine packs.",
    no_args_is_help=True,
)
app.add_typer(pack_app, name="pack")

console = Console()


# ----------------------------------------------------------------------
# fetch
# ----------------------------------------------------------------------
@app.command(name="fetch")
def fetch(
    pack_name: str | None = typer.Option(
        None,
        "--pack",
        help="Fetch only the named pack (default: fetch all configured packs).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be fetched without contacting any remote.",
    ),
) -> None:
    """Fetch org doctrine pack(s) from their configured remote sources."""
    from specify_cli.core.paths import locate_project_root
    from specify_cli.doctrine.config import load_pack_registry
    from specify_cli.doctrine.snapshot import fetch_pack

    repo_root = locate_project_root()
    if repo_root is None:
        console.print(
            "[red]Could not locate spec-kitty project root.[/red] "
            "Run from inside a project containing .kittify/."
        )
        raise typer.Exit(1)

    registry = load_pack_registry(repo_root)
    if not registry.packs:
        console.print("[red]No org doctrine packs configured.[/red]")
        console.print(
            "Add a [bold]doctrine.org.packs[/bold] block to "
            ".kittify/config.yaml. See the contract at "
            "kitty-specs/layered-doctrine-org-layer-*/contracts/config-schema.yaml."
        )
        raise typer.Exit(1)

    target_packs = list(registry.packs)
    if pack_name is not None:
        target_packs = [p for p in registry.packs if p.name == pack_name]
        if not target_packs:
            names = ", ".join(registry.names()) or "(none)"
            console.print(
                f"[red]Pack '{pack_name}' not found.[/red] "
                f"Configured packs: {names}"
            )
            raise typer.Exit(1)

    if dry_run:
        for pack in target_packs:
            origin = pack.url or str(pack.local_path)
            console.print(
                f"Would fetch pack '[bold]{pack.name}[/bold]' from {origin} "
                f"into {pack.local_path}"
            )
        return

    any_failed = False
    for pack in target_packs:
        result = fetch_pack(pack)
        if result.ok:
            console.print(
                f"[green]Pack '{pack.name}': {result.artifacts_written} "
                "artifacts[/green]"
            )
            if result.pack_version:
                console.print(f"  Version: {result.pack_version}")
        else:
            console.print(f"[red]Pack '{pack.name}' failed:[/red]")
            for err in result.errors:
                console.print(f"  {err}")
            any_failed = True

    if any_failed:
        raise typer.Exit(1)


# ----------------------------------------------------------------------
# pack validate
# ----------------------------------------------------------------------
@pack_app.command(name="validate")
def pack_validate(
    pack_path: Path = typer.Argument(
        ...,
        help="Path to the doctrine pack directory to validate.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON instead of rich text.",
    ),
) -> None:
    """Validate a doctrine pack against schema and DRG constraints.

    Exits 0 when the pack passes validation (advisories do not affect the
    exit code) and 1 when at least one error is reported.
    """
    from specify_cli.doctrine.pack_validator import (
        render_validation_result,
        validate_pack,
    )

    result = validate_pack(pack_path)
    render_validation_result(result, json_output=json_output)
    raise typer.Exit(0 if result.ok else 1)


# ----------------------------------------------------------------------
# pack assemble
# ----------------------------------------------------------------------
@pack_app.command(name="assemble")
def pack_assemble(
    output_path: Path = typer.Argument(
        ...,
        help="Output directory for the assembled distributable pack.",
    ),
    input_packs: list[Path] = typer.Argument(
        ...,
        help="One or more input pack directories to assemble.",
    ),
    conflicts_out: Path | None = typer.Option(
        None,
        "--conflicts-out",
        help="Write the conflict report to this path (JSON).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help=(
            "Resolve artifact-id conflicts by last-pack-wins and drop "
            "duplicate DRG edges silently."
        ),
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON instead of rich text.",
    ),
) -> None:
    """Assemble multiple doctrine packs into a single distributable.

    Exits 0 on success and 1 when conflicts block the merge or when the
    assembled output fails validation.
    """
    from specify_cli.doctrine.pack_assembler import (
        assemble_pack,
        render_assembly_result,
    )

    result = assemble_pack(
        input_packs=list(input_packs),
        output_dir=output_path,
        force=force,
        conflicts_out=conflicts_out,
    )
    render_assembly_result(
        result,
        output_dir=output_path,
        input_packs=list(input_packs),
        json_output=json_output,
    )
    raise typer.Exit(0 if result.ok else 1)
