"""``agent mission acceptance-verdict`` command (WP04 / T015).

write-side-seam-matrix-tracer-01KYP3MH, FR-001/FR-002/FR-012.

Records ONE acceptance-criterion verdict (a ``pass``/``fail``/``pending``
result plus its verification method/actor/evidence) into the mission's
``acceptance-matrix.json``, then commits it through the WP03 write seam
(:func:`specify_cli.acceptance.matrix.write_and_commit_acceptance_matrix`,
which composes :func:`~specify_cli.coordination.write_seam.write_artifact`).

This command *materializes and routes* — it never re-authors verdict
semantics. ``overall_verdict`` stays a computed
:pyattr:`~specify_cli.acceptance.matrix.AcceptanceMatrix.overall_verdict`
property (``acceptance/matrix.py``); this command only ever mutates one
``AcceptanceCriterion`` row inside ``matrix.criteria`` and never touches
``matrix.negative_invariants`` (so negative-invariant provenance, #2743's
integrity guard, is passed through untouched on every invocation).

Idempotence (FR-012): ``verified_at`` is bumped ONLY when the row's
observable state (result / verification method / actor / evidence) actually
changes. An identical re-invocation therefore serializes byte-identical JSON,
so the underlying commit resolves to ``"unchanged"`` (no duplicate commit) —
inherited straight from ``commit_for_mission``'s own idempotence contract, not
re-implemented here.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from specify_cli.acceptance.matrix import (
    CRITERION_VERDICTS,
    AcceptanceCriterion,
    read_acceptance_matrix,
    write_and_commit_acceptance_matrix,
)
from specify_cli.cli.console import console
from specify_cli.cli.selector_resolution import resolve_mission_handle
from specify_cli.task_utils import TaskCliError, find_repo_root

_PAYLOAD_KEY_SUCCESS = "success"
_PAYLOAD_KEY_ERROR = "error"
_RED_ERROR_PREFIX = "[red]Error:[/red] "


def _emit_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload))


def _emit_error(message: str, *, json_output: bool) -> None:
    if json_output:
        _emit_json({_PAYLOAD_KEY_SUCCESS: False, _PAYLOAD_KEY_ERROR: message})
    else:
        console.print(f"{_RED_ERROR_PREFIX}{message}")


def _matrix_read_dir(repo_root: Path, mission_slug: str) -> Path:
    """Resolve the matrix's current read/write surface via the ONE kind-aware seam.

    Mirrors ``acceptance/gates_core.py::_acceptance_matrix_read_dir`` — the
    same :func:`mission_runtime.placement_seam` authority, never a hand-derived
    ``kitty-specs/<slug>`` join.
    """
    from mission_runtime import MissionArtifactKind, placement_seam

    return placement_seam(repo_root, mission_slug).read_dir(
        MissionArtifactKind.ACCEPTANCE_MATRIX
    )


def _resolve_criterion_update(
    existing: AcceptanceCriterion,
    *,
    result: str,
    verification_method: str | None,
    actor: str | None,
    evidence: str | None,
) -> AcceptanceCriterion:
    """Compute the updated row, bumping ``verified_at`` only on a real change (FR-012).

    A candidate is built with every field the CLI can set applied, but
    ``verified_at`` held at the EXISTING value. If that candidate is
    dataclass-equal to ``existing``, nothing observable changed, so
    ``verified_at`` (and ``notes``, the change-log line) are left untouched —
    a re-invocation with identical inputs serializes byte-identical JSON,
    which is what makes the underlying commit resolve to ``"unchanged"``.
    """
    candidate = replace(
        existing,
        pass_fail=result,
        proof_type=verification_method if verification_method is not None else existing.proof_type,
        verified_by=actor if actor is not None else existing.verified_by,
        evidence=evidence if evidence is not None else existing.evidence,
    )
    if candidate == existing:
        return existing
    return replace(
        candidate,
        verified_at=datetime.now(UTC).isoformat(),
    )


def acceptance_verdict(
    mission: Annotated[str, typer.Option("--mission", help="Mission slug, mid8, or mission_id")],
    criterion: Annotated[str, typer.Option("--criterion", help="Acceptance criterion id (e.g. FR-001)")],
    result: Annotated[str, typer.Option("--result", help="pass | fail | pending")],
    verification_method: Annotated[
        str | None,
        typer.Option("--verification-method", help="How this was verified (updates proof_type)"),
    ] = None,
    actor: Annotated[str | None, typer.Option("--actor", help="Actor recording this verdict")] = None,
    evidence: Annotated[str | None, typer.Option("--evidence", help="Evidence reference (URL/path/etc.)")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON format")] = False,
) -> None:
    """Record one acceptance-criterion verdict, routed through the WP03 write seam."""
    if result not in CRITERION_VERDICTS:
        allowed = ", ".join(sorted(CRITERION_VERDICTS))
        _emit_error(f"--result must be one of {allowed}; got {result!r}", json_output=json_output)
        raise typer.Exit(2)

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        _emit_error(str(exc), json_output=json_output)
        raise typer.Exit(1) from None

    resolved = resolve_mission_handle(mission, repo_root, json_mode=json_output)
    mission_slug = resolved.mission_slug

    matrix_dir = _matrix_read_dir(repo_root, mission_slug)
    matrix = read_acceptance_matrix(matrix_dir)
    if matrix is None:
        _emit_error(
            f"No acceptance-matrix.json found for mission {mission_slug!r}. "
            "Run `spec-kitty agent mission finalize-tasks` to scaffold it first.",
            json_output=json_output,
        )
        raise typer.Exit(1)

    index_by_id = {c.criterion_id: idx for idx, c in enumerate(matrix.criteria)}
    if criterion not in index_by_id:
        available = ", ".join(sorted(index_by_id)) or "(none)"
        _emit_error(
            f"Unknown criterion {criterion!r} for mission {mission_slug!r}. "
            f"Available criteria: {available}",
            json_output=json_output,
        )
        raise typer.Exit(1)

    idx = index_by_id[criterion]
    updated = _resolve_criterion_update(
        matrix.criteria[idx],
        result=result,
        verification_method=verification_method,
        actor=actor,
        evidence=evidence,
    )
    matrix.criteria[idx] = updated

    write_result = write_and_commit_acceptance_matrix(
        repo_root,
        mission_slug,
        matrix_dir,
        matrix,
        entry_id=criterion,
        message=f"chore(acceptance): record {criterion}={result} for {mission_slug}",
    )

    if write_result.status == "refused":
        _emit_error(
            f"Could not route the acceptance-verdict write for {mission_slug!r}: "
            f"{write_result.diagnostic or 'unroutable target'}",
            json_output=json_output,
        )
        raise typer.Exit(1)
    if write_result.status == "error":
        _emit_error(
            f"Failed to commit acceptance verdict for {mission_slug!r}: "
            f"{write_result.diagnostic or 'unknown error'}",
            json_output=json_output,
        )
        raise typer.Exit(1)

    payload = {
        _PAYLOAD_KEY_SUCCESS: True,
        "mission": mission_slug,
        "criterion": criterion,
        "result": result,
        "overall_verdict": matrix.overall_verdict,
        "write_status": write_result.status,
        "destination_surface": write_result.destination_surface,
        "commit_hash": write_result.commit_hash,
    }
    if json_output:
        _emit_json(payload)
    else:
        console.print(
            f"[green]✓[/green] {criterion}={result} recorded for {mission_slug} "
            f"(overall_verdict={matrix.overall_verdict}, write={write_result.status})"
        )


__all__ = ["acceptance_verdict"]
