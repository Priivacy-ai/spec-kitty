"""``tracer-append`` command (FR-006 / contracts/commands.md).

A lane-origin-safe CLI wrapper over
:func:`specify_cli.retrospective.tracer_writer.append_tracer_finding`: appends
a dated, attributed finding to ``traces/<category>.md``, routed to the COORD
surface via the WP03 seam. Resolves ``repo_root`` to the MAIN repo root
(``get_main_repo_root``) exactly like ``record-analysis`` does, so invoking
this command from inside a lane worktree never touches the lane's own
``kitty-specs/`` checkout -- the write always targets the primary checkout,
which the seam then stages onto the coordination branch (#2980 / #2549).
"""

from __future__ import annotations

import json
from typing import Annotated

import typer

from specify_cli.cli.console import console
from specify_cli.core.paths import (
    get_feature_target_branch,
    get_main_repo_root,
    locate_project_root,
)
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.retrospective.tracer_writer import (
    TRACER_CATEGORIES,
    TracerAttributionError,
    TracerCategoryError,
    append_tracer_finding,
)

__all__ = ["tracer_append"]

_KIND_LABEL = "TRACER_FILE"
_DESTINATION_SURFACE = "coord"  # TRACER_FILE is unconditionally COORD-partition.
_REFUSAL_DEFERRED_TO = "#3033"
_PROJECT_ROOT_NOT_FOUND = "Could not locate project root"
_CATEGORY_HELP = "Tracer category: " + " | ".join(sorted(TRACER_CATEGORIES))


def _emit(payload: dict[str, object], *, json_output: bool, ok: bool) -> None:
    if json_output:
        print(json.dumps(payload))
        return
    if ok:
        console.print(f"[green]✓[/green] {payload.get('row_or_entry_ref', '')}")
    else:
        console.print(f"[red]Error:[/red] {payload.get('error', 'tracer-append failed')}")


def _error_payload(message: str) -> dict[str, object]:
    return {"ok": False, "kind": _KIND_LABEL, "error": message}


def tracer_append(
    mission: Annotated[str, typer.Option("--mission", help="Mission handle (e.g. 'my-mission-01ABCDEF')")],
    category: Annotated[str, typer.Option("--category", help=_CATEGORY_HELP)],
    entry: Annotated[str, typer.Option("--entry", help="Finding text")],
    actor: Annotated[str, typer.Option("--actor", help="Attribution (required, non-empty)")],
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Append a dated, attributed finding to the mission's tracer surface."""
    cwd_repo_root = locate_project_root()
    if cwd_repo_root is None:
        _emit(_error_payload(_PROJECT_ROOT_NOT_FOUND), json_output=json_output, ok=False)
        raise typer.Exit(1)
    repo_root = get_main_repo_root(cwd_repo_root)

    try:
        policy = ProtectionPolicy.resolve(repo_root)
        try:
            target_branch = get_feature_target_branch(repo_root, mission)
        except Exception:  # noqa: BLE001 - best-effort ff-advance target only
            target_branch = None

        result = append_tracer_finding(
            repo_root=repo_root,
            mission_slug=mission,
            category=category,
            entry=entry,
            actor=actor,
            policy=policy,
            target_branch=target_branch,
        )
    except (TracerAttributionError, TracerCategoryError) as exc:
        _emit(_error_payload(str(exc)), json_output=json_output, ok=False)
        raise typer.Exit(1) from None

    if result.status == "refused":
        payload = {
            "ok": False,
            "kind": _KIND_LABEL,
            "error": result.diagnostic or "tracer-append refused an unroutable write target",
            "refusal": {
                "reason": result.diagnostic,
                "deferred_to": _REFUSAL_DEFERRED_TO,
            },
        }
        _emit(payload, json_output=json_output, ok=False)
        raise typer.Exit(1)

    if result.status == "error":
        _emit(
            _error_payload(result.diagnostic or "tracer-append commit failed"),
            json_output=json_output,
            ok=False,
        )
        raise typer.Exit(1)

    payload = {
        "ok": True,
        "kind": _KIND_LABEL,
        "destination_surface": _DESTINATION_SURFACE,
        "row_or_entry_ref": result.entry_id,
        "status": result.status,
        "commit_ref": result.destination_surface,
        "commit_hash": result.commit_hash,
    }
    _emit(payload, json_output=json_output, ok=True)
