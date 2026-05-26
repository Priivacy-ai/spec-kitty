"""``spec-kitty charter context`` command (WP06 per-subcommand split)."""
from __future__ import annotations

import json

import typer

from specify_cli.task_utils import TaskCliError

from specify_cli.cli.commands.charter._app import charter_app, console

# Test-patch shim — see ``synthesize.py``.
import specify_cli.cli.commands.charter as _charter_pkg

__all__ = ["context"]


@charter_app.command()
def context(
    action: str = typer.Option(..., "--action", help="Workflow action (specify|plan|implement|review)"),
    mark_loaded: bool = typer.Option(True, "--mark-loaded/--no-mark-loaded", help="Persist first-load state"),
    json_output: bool = typer.Option(
        False,
        "--json",
        help=(
            "Output JSON. `directives` is action-scoped; `all_directives` and "
            "`project_charter` describe the project-local charter, while "
            "`org_charter` describes imported org packs."
        ),
    ),
) -> None:
    """Render charter context for a specific workflow action."""
    from charter.context import (
        BOOTSTRAP_ACTIONS,
        build_charter_context,
        build_charter_context_json,
    )

    from specify_cli.doctrine.config import resolve_org_roots
    from specify_cli.doctrine.org_charter_loader import load_org_charter_json_block

    try:
        repo_root = _charter_pkg.find_repo_root()
        # WP07 T034: resolve the configured org doctrine snapshot in the
        # specify_cli layer and pass it as data into the charter layer.
        # ``charter`` must not import ``specify_cli`` (ADR 2026-03-27-1).
        org_roots = [p for p in resolve_org_roots(repo_root) if p.exists()]
        org_root = org_roots[0] if org_roots else None
        result = build_charter_context(
            repo_root,
            action=action,
            mark_loaded=mark_loaded,
            org_root=org_root,
        )

        if json_output:
            # WP07 T033 + T046: structured JSON payload includes per-artifact
            # provenance and the additive ``org_charter`` block.  The block
            # is loaded in the specify_cli layer (where ``org_charter_loader``
            # may import the optional WP09 module) and passed as data into the
            # charter layer.
            org_charter_block = load_org_charter_json_block(org_roots)
            structured = build_charter_context_json(
                repo_root,
                action=action,
                depth=result.depth,
                org_root=org_root,
                org_charter_block=org_charter_block,
            )
            print(
                json.dumps(
                    {
                        "result": "success",
                        "success": True,
                        "action": result.action,
                        "mode": result.mode,
                        "first_load": result.first_load,
                        "references_count": result.references_count,
                        "context": result.text,
                        "text": result.text,
                        "directives": structured.get("directives", []),
                        "all_directives": structured.get("all_directives", []),
                        "tactics": structured.get("tactics", []),
                        "styleguides": structured.get("styleguides", []),
                        "toolguides": structured.get("toolguides", []),
                        "project_charter": structured.get(
                            "project_charter",
                            {
                                "present": False,
                                "path": ".kittify/charter/charter.md",
                            },
                        ),
                        "org_charter": structured.get(
                            "org_charter", {"present": False, "packs": []}
                        ),
                    },
                    indent=2,
                )
            )
            return

        if result.action in BOOTSTRAP_ACTIONS:
            console.print(f"Action: {result.action} ({result.mode})")
        console.print(result.text)

    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e
