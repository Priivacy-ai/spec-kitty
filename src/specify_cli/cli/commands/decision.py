"""Decision Moment CLI subgroup — ``spec-kitty agent decision ...``

Exposes five subcommands that map directly to the decisions service and verifier:

    open      — open a new decision moment
    resolve   — resolve a decision with a final answer
    defer     — defer a decision for later resolution
    cancel    — cancel a decision (no longer relevant)
    verify    — cross-check deferred decisions against inline markers

All subcommands output JSON to stdout and exit 0 on success, 1 on structured error.
"""

from __future__ import annotations

import json
import re as _re
import sys
from pathlib import Path

import typer
import ulid as _ulid_mod

from specify_cli.decisions.models import (
    DecisionErrorCode,
    DecisionOpenResponse,
    DecisionTerminalResponse,
    OriginFlow,
)
from specify_cli.decisions.service import (
    DecisionError,
    cancel_decision,
    defer_decision,
    open_decision,
    resolve_decision,
)
from specify_cli.decisions.verify import verify as _verify_decisions

decision_app = typer.Typer(
    name="decision",
    help="Decision Moment ledger for interview questions.",
    no_args_is_help=True,
)

# Safe slug pattern: must start with an alphanumeric character and contain only
# alphanumeric characters, hyphens, and underscores.  This rejects path traversal
# payloads such as ``../../etc/passwd`` or ``../evil`` before they reach
# filesystem operations.
_SAFE_SLUG_RE = _re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _resolve_repo_root_and_slug(mission_handle: str) -> tuple[Path, str]:
    """Return ``(repo_root, mission_slug)`` for a mission handle.

    The mission handle is treated as a mission_slug directly.  repo_root is
    resolved by walking up from the current working directory looking for a
    ``kitty-specs/`` directory.  If none is found, the current working directory
    is returned as repo_root (allowing test fixtures to pass tmp_path directly
    via environment).

    This keeps the CLI decoupled from the heavier context resolver while still
    supporting the standard project layout used by spec-kitty.

    Security: the mission_handle is validated against ``_SAFE_SLUG_RE`` to
    prevent path-traversal attacks (RISK-1 from mission review 01KPWT8P).
    """
    # Reject path-traversal payloads early, before any filesystem access.
    if not _SAFE_SLUG_RE.match(mission_handle):
        raise typer.BadParameter(
            f"Invalid --mission value {mission_handle!r}: must match {_SAFE_SLUG_RE.pattern}",
            param_hint="'--mission'",
        )

    # Walk up looking for kitty-specs/ (project root marker)
    cwd = Path.cwd()
    candidate: Path | None = None
    current = cwd
    for _ in range(20):
        if (current / "kitty-specs").is_dir():
            candidate = current
            break
        parent = current.parent
        if parent == current:
            break
        current = parent

    repo_root = candidate if candidate is not None else cwd

    # Verify the resolved mission path stays within kitty-specs/ even after
    # Path normalization (defence-in-depth against any edge cases in slug parsing).
    resolved = (repo_root / "kitty-specs" / mission_handle).resolve()
    base = (repo_root / "kitty-specs").resolve()
    if not str(resolved).startswith(str(base) + "/") and resolved != base:
        raise typer.BadParameter(
            f"Mission path would escape kitty-specs/: {mission_handle!r}",
            param_hint="'--mission'",
        )

    return repo_root, mission_handle


def _open_response_to_dict(resp: DecisionOpenResponse) -> dict:  # type: ignore[type-arg]
    """Serialize DecisionOpenResponse to a plain dict."""
    return {
        "decision_id": resp.decision_id,
        "idempotent": resp.idempotent,
        "mission_id": resp.mission_id,
        "artifact_path": resp.artifact_path,
        "event_lamport": resp.event_lamport,
    }


def _terminal_response_to_dict(resp: DecisionTerminalResponse) -> dict:  # type: ignore[type-arg]
    """Serialize DecisionTerminalResponse to a plain dict."""
    return {
        "decision_id": resp.decision_id,
        "status": resp.status.value,
        "terminal_outcome": resp.terminal_outcome,
        "idempotent": resp.idempotent,
        "event_lamport": resp.event_lamport,
    }


def _handle_decision_error(exc: DecisionError) -> None:
    """Emit structured JSON error to stderr and raise Exit(1)."""
    payload = {
        "error": str(exc),
        "code": exc.code.value,
        "details": exc.details,
    }
    typer.echo(json.dumps(payload, sort_keys=True), err=True)
    raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Subcommand: open
# ---------------------------------------------------------------------------


@decision_app.command("open")
def cmd_open(  # noqa: PLR0913
    mission: str = typer.Option(..., "--mission", help="Mission handle (slug, mission_id, or mid8)"),
    flow: str = typer.Option(..., "--flow", help="Origin flow: charter | specify | plan"),
    input_key: str = typer.Option(..., "--input-key", help="The input key this decision governs"),
    question: str = typer.Option(..., "--question", help="Human-readable question text"),
    step_id: str | None = typer.Option(None, "--step-id", help="Interview step identifier"),
    slot_key: str | None = typer.Option(None, "--slot-key", help="Slot key (use when step_id unavailable)"),
    options: str | None = typer.Option(None, "--options", help="Candidate answers as a JSON array string"),
    actor: str = typer.Option("cli", "--actor", help="Identity of the opening actor"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without writing"),
    json_out: bool = typer.Option(True, "--json/--no-json", help="Output JSON (default true)"),  # noqa: ARG001
) -> None:
    """Open a new Decision Moment or return idempotently if one already exists."""
    # Validate flow
    try:
        origin_flow = OriginFlow(flow)
    except ValueError:
        valid = ", ".join(f.value for f in OriginFlow)
        err = DecisionError(
            code=DecisionErrorCode.MISSING_STEP_OR_SLOT,
            details={"flow": flow, "valid_values": valid},
            message=f"Invalid --flow value {flow!r}. Must be one of: {valid}",
        )
        _handle_decision_error(err)
        return  # unreachable — _handle_decision_error raises

    # Parse options JSON
    parsed_options: tuple[str, ...] = ()
    if options is not None:
        try:
            raw = json.loads(options)
        except json.JSONDecodeError as json_exc:
            err = DecisionError(
                code=DecisionErrorCode.MISSING_STEP_OR_SLOT,
                details={"options": options, "parse_error": str(json_exc)},
                message=f"--options must be a valid JSON array string, got: {options!r}",
            )
            _handle_decision_error(err)
            return
        if not isinstance(raw, list):
            err = DecisionError(
                code=DecisionErrorCode.MISSING_STEP_OR_SLOT,
                details={"options": options},
                message="--options must be a JSON array (list), got a non-list value",
            )
            _handle_decision_error(err)
            return
        parsed_options = tuple(str(item) for item in raw)

    repo_root, mission_slug = _resolve_repo_root_and_slug(mission)

    # FR-003: mint decision_id BEFORE any artifact write or event emission,
    # and emit it to stdout immediately so callers always receive the id even
    # if the process is killed mid-write.  dry_run uses "DRY_RUN" as the id
    # (matching the service-layer convention) so callers can detect the mode.
    minted_id = "DRY_RUN" if dry_run else str(_ulid_mod.ULID())
    typer.echo(json.dumps({"decision_id": minted_id, "phase": "minted"}, sort_keys=True))
    sys.stdout.flush()

    try:
        resp = open_decision(
            repo_root,
            mission_slug,
            origin_flow=origin_flow,
            input_key=input_key,
            question=question,
            options=parsed_options,
            step_id=step_id,
            slot_key=slot_key,
            actor=actor,
            dry_run=dry_run,
            decision_id=minted_id if not dry_run else None,
        )
    except DecisionError as exc:
        _handle_decision_error(exc)
        return

    typer.echo(json.dumps(_open_response_to_dict(resp), sort_keys=True))


# ---------------------------------------------------------------------------
# Subcommand: resolve
# ---------------------------------------------------------------------------


@decision_app.command("resolve")
def cmd_resolve(  # noqa: PLR0913
    decision_id: str = typer.Argument(..., help="ULID identifier of the decision to resolve"),
    mission: str = typer.Option(..., "--mission", help="Mission handle"),
    final_answer: str = typer.Option(..., "--final-answer", help="The chosen answer (non-empty)"),
    other_answer: bool = typer.Option(False, "--other-answer", help="True if answer is a write-in"),
    rationale: str | None = typer.Option(None, "--rationale", help="Explanation of the choice"),
    resolved_by: str | None = typer.Option(None, "--resolved-by", help="Identity of resolver"),
    actor: str = typer.Option("cli", "--actor", help="Identity of the acting agent"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without writing"),
    json_out: bool = typer.Option(True, "--json/--no-json", help="Output JSON (default true)"),  # noqa: ARG001
) -> None:
    """Resolve a decision with a concrete final answer."""
    repo_root, mission_slug = _resolve_repo_root_and_slug(mission)

    try:
        resp = resolve_decision(
            repo_root,
            mission_slug,
            decision_id,
            final_answer=final_answer,
            other_answer=other_answer,
            rationale=rationale,
            resolved_by=resolved_by,
            actor=actor,
            dry_run=dry_run,
        )
    except DecisionError as exc:
        _handle_decision_error(exc)
        return

    typer.echo(json.dumps(_terminal_response_to_dict(resp), sort_keys=True))


# ---------------------------------------------------------------------------
# Subcommand: defer
# ---------------------------------------------------------------------------


@decision_app.command("defer")
def cmd_defer(
    decision_id: str = typer.Argument(..., help="ULID identifier of the decision to defer"),
    mission: str = typer.Option(..., "--mission", help="Mission handle"),
    rationale: str = typer.Option(..., "--rationale", help="Explanation of why it's being deferred (required)"),
    resolved_by: str | None = typer.Option(None, "--resolved-by", help="Identity of deferring party"),
    actor: str = typer.Option("cli", "--actor", help="Identity of the acting agent"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without writing"),
    json_out: bool = typer.Option(True, "--json/--no-json", help="Output JSON (default true)"),  # noqa: ARG001
) -> None:
    """Defer a decision for later resolution."""
    if not rationale.strip():
        err = DecisionError(
            code=DecisionErrorCode.MISSING_STEP_OR_SLOT,
            details={"field": "rationale"},
            message="--rationale must be a non-empty string",
        )
        _handle_decision_error(err)
        return

    repo_root, mission_slug = _resolve_repo_root_and_slug(mission)

    try:
        resp = defer_decision(
            repo_root,
            mission_slug,
            decision_id,
            rationale=rationale,
            resolved_by=resolved_by,
            actor=actor,
            dry_run=dry_run,
        )
    except DecisionError as exc:
        _handle_decision_error(exc)
        return

    typer.echo(json.dumps(_terminal_response_to_dict(resp), sort_keys=True))


# ---------------------------------------------------------------------------
# Subcommand: cancel
# ---------------------------------------------------------------------------


@decision_app.command("cancel")
def cmd_cancel(
    decision_id: str = typer.Argument(..., help="ULID identifier of the decision to cancel"),
    mission: str = typer.Option(..., "--mission", help="Mission handle"),
    rationale: str = typer.Option(..., "--rationale", help="Explanation of why it's being canceled (required)"),
    resolved_by: str | None = typer.Option(None, "--resolved-by", help="Identity of canceling party"),
    actor: str = typer.Option("cli", "--actor", help="Identity of the acting agent"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without writing"),
    json_out: bool = typer.Option(True, "--json/--no-json", help="Output JSON (default true)"),  # noqa: ARG001
) -> None:
    """Cancel a decision (deemed no longer relevant)."""
    if not rationale.strip():
        err = DecisionError(
            code=DecisionErrorCode.MISSING_STEP_OR_SLOT,
            details={"field": "rationale"},
            message="--rationale must be a non-empty string",
        )
        _handle_decision_error(err)
        return

    repo_root, mission_slug = _resolve_repo_root_and_slug(mission)

    try:
        resp = cancel_decision(
            repo_root,
            mission_slug,
            decision_id,
            rationale=rationale,
            resolved_by=resolved_by,
            actor=actor,
            dry_run=dry_run,
        )
    except DecisionError as exc:
        _handle_decision_error(exc)
        return

    typer.echo(json.dumps(_terminal_response_to_dict(resp), sort_keys=True))


# ---------------------------------------------------------------------------
# Subcommand: verify
# ---------------------------------------------------------------------------


@decision_app.command("verify")
def cmd_verify(
    mission: str = typer.Option(..., "--mission", help="Mission handle"),
    fail_on_stale: bool = typer.Option(
        True,
        "--fail-on-stale/--no-fail-on-stale",
        help="Exit non-zero when findings are present (default true)",
    ),
    json_out: bool = typer.Option(True, "--json/--no-json", help="Output JSON (default true)"),  # noqa: ARG001
) -> None:
    """Cross-check deferred decisions against inline sentinel markers."""
    repo_root, mission_slug = _resolve_repo_root_and_slug(mission)
    mission_dir = repo_root / "kitty-specs" / mission_slug

    result = _verify_decisions(mission_dir, mission_slug)

    findings_list = [
        {
            "kind": f.kind,
            "decision_id_or_ref": f.decision_id_or_ref,
            "location": f.location,
            "detail": f.detail,
        }
        for f in result.findings
    ]

    payload = {
        "status": result.status,
        "deferred_count": result.deferred_count,
        "marker_count": result.marker_count,
        "findings": findings_list,
    }

    typer.echo(json.dumps(payload, sort_keys=True))

    if result.findings and fail_on_stale:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Subcommand: widen  (hidden — internal / automation use only)
# ---------------------------------------------------------------------------


@decision_app.command("widen", hidden=True)
def cmd_widen(
    decision_id: str = typer.Argument(..., help="ULID of the DecisionPoint to widen"),
    invited: str = typer.Option(..., "--invited", help="Comma-separated Teamspace user IDs to invite"),
    mission_slug: str | None = typer.Option(None, "--mission-slug", help="Mission slug"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would be called without calling it"),
) -> None:
    """[internal] Call the widen endpoint for a decision. Not for end users."""
    from specify_cli.saas_client import SaasClient, SaasClientError

    invited_raw = [n.strip() for n in invited.split(",") if n.strip()]
    if not invited_raw:
        typer.echo("Error: --invited must be a non-empty comma-separated list of user IDs", err=True)
        raise typer.Exit(1)
    try:
        invited_list = [int(value) for value in invited_raw]
    except ValueError:
        typer.echo("Error: --invited must contain Teamspace user IDs, not display names", err=True)
        raise typer.Exit(1) from None

    if dry_run:
        typer.echo(
            json.dumps(
                {
                    "dry_run": True,
                    "decision_id": decision_id,
                    "endpoint": f"POST /a/<team_slug>/collaboration/decision-points/{decision_id}/widen",
                    "invited": invited_list,
                    "mission_slug": mission_slug,
                    "payload": {"invited_user_ids": invited_list},
                },
                indent=2,
            )
        )
        raise typer.Exit(0)

    try:
        client = SaasClient.from_env()
        response = client.post_widen(decision_id=decision_id, invited=invited_list)
        typer.echo(
            json.dumps(
                {
                    "decision_id": response["decision_id"],
                    "invited_count": response["invited_count"],
                    "slack_thread_url": response["slack_thread_url"],
                    "success": True,
                    "widened_at": response["widened_at"],
                },
                indent=2,
            )
        )
    except SaasClientError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc


__all__ = ["decision_app"]
