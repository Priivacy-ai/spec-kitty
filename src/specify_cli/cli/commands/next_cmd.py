"""CLI command for ``spec-kitty next``."""

from __future__ import annotations

import contextlib
import io
import json
import sys

import typer
from typing import Annotated

from specify_cli.core.context_validation import require_main_repo
from specify_cli.core.paths import locate_project_root, require_explicit_feature
from specify_cli.mission_v1.events import emit_event
from specify_cli.next.decision import DecisionKind, decide_next


_VALID_RESULTS = ("success", "failed", "blocked")


@require_main_repo
def next_step(
    agent: Annotated[str | None, typer.Option("--agent", help="Agent name (required for advancing mode)")] = None,
    result: Annotated[
        str | None,
        typer.Option(
            "--result",
            help=("Result of previous step: success|failed|blocked. If omitted, returns current state without advancing (query mode)."),
        ),
    ] = None,
    feature: Annotated[str | None, typer.Option("--mission", "--mission-run", "--feature", help="Mission slug")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON decision only")] = False,
    answer: Annotated[str | None, typer.Option("--answer", help="Answer to a pending decision")] = None,
    decision_id: Annotated[str | None, typer.Option("--decision-id", help="Decision ID (required if multiple pending)")] = None,
) -> None:
    """Decide and emit the next agent action for the current mission.

    Agents call this command repeatedly in a loop.  The system inspects the
    mission state machine, evaluates guards, and returns a deterministic
    decision with an action and prompt file.

    Examples:
        spec-kitty next --agent claude --json
        spec-kitty next --agent codex --mission-run 034-my-feature
        spec-kitty next --agent gemini --result failed --json
        spec-kitty next --agent claude --answer "yes" --json
        spec-kitty next --agent claude --answer "approve" --decision-id "input:review" --json
    """
    # Resolve repo root
    repo_root = locate_project_root()
    if repo_root is None:
        print("Error: Could not locate project root", file=sys.stderr)
        raise typer.Exit(1)

    # Resolve feature slug
    try:
        mission_slug = require_explicit_feature(feature, command_hint="--mission <slug>")
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(1) from exc

    if result is not None and result not in _VALID_RESULTS:
        print(f"Error: --result must be one of {_VALID_RESULTS}, got '{result}'", file=sys.stderr)
        raise typer.Exit(1)

    # Handle --answer flow before deciding whether the call is read-only or
    # advancing. Answering a pending decision is a mutation and still requires
    # agent identity, even when no --result is supplied.
    answered_id = None
    if answer is not None:
        if not agent:
            message = "Error: --agent is required when --answer is provided"
            if json_output:
                print(json.dumps({"error": message}))
            else:
                print(message, file=sys.stderr)
            raise typer.Exit(1)
        stderr_buffer = io.StringIO() if json_output else None
        redirect = contextlib.redirect_stderr(stderr_buffer) if stderr_buffer is not None else contextlib.nullcontext()
        try:
            with redirect:
                answered_id = _handle_answer(agent, mission_slug, answer, decision_id, repo_root)
        except typer.Exit as exc:
            if json_output:
                message = (stderr_buffer.getvalue().strip() if stderr_buffer is not None else "") or str(exc) or "Answer handling failed"
                print(json.dumps({"error": message}))
                raise typer.Exit(1)
            raise
        except Exception as exc:
            if json_output:
                print(json.dumps({"error": str(exc)}))
                raise typer.Exit(1) from exc
            raise

    # Query mode: bare call without --result remains read-only and does not
    # require agent identity.
    if result is None:
        from specify_cli.next.runtime_bridge import QueryModeValidationError, query_current_state

        try:
            decision = query_current_state(agent, mission_slug, repo_root)
        except QueryModeValidationError as exc:
            if json_output:
                print(json.dumps({"error": str(exc)}))
            else:
                print(f"Error: {exc}", file=sys.stderr)
            raise typer.Exit(1) from exc
        if json_output:
            d = decision.to_dict()
            if answered_id is not None:
                d["answered"] = answered_id
                d["answer"] = answer
            print(json.dumps(d, indent=2))
        else:
            _print_human(decision)
            if answered_id is not None:
                print(f"  Answered decision: {answered_id}")
        return  # No event emitted, no DAG advancement

    if not agent:
        print("Error: --agent is required when --result is provided", file=sys.stderr)
        raise typer.Exit(1)

    # Core decision
    decision = decide_next(agent, mission_slug, result, repo_root)

    # Emit MissionNextInvoked event
    feature_dir = repo_root / "kitty-specs" / mission_slug
    emit_event(
        "MissionNextInvoked",
        {
            "agent": agent,
            "result_input": result,
            "decision_kind": decision.kind,
            "action": decision.action,
            "wp_id": decision.wp_id,
            "mission_state": decision.mission_state,
        },
        mission_name=decision.mission,
        feature_dir=feature_dir if feature_dir.is_dir() else None,
    )

    # Output — always exactly one JSON document
    if json_output:
        d = decision.to_dict()
        if answered_id is not None:
            d["answered"] = answered_id
            d["answer"] = answer
        print(json.dumps(d, indent=2))
    else:
        if answered_id is not None:
            print(f"  Answered decision: {answered_id}")
        _print_human(decision)

    # Exit code
    if decision.kind == DecisionKind.blocked:
        raise typer.Exit(1)


def _handle_answer(
    agent: str,
    mission_slug: str,
    answer: str,
    decision_id: str | None,
    repo_root: object,
) -> str:
    """Handle the --answer flow for pending decisions.

    Returns the resolved decision_id.
    """
    from pathlib import Path

    repo_root_path = Path(str(repo_root)) if not isinstance(repo_root, Path) else repo_root

    try:
        from specify_cli.next.runtime_bridge import answer_decision_via_runtime, get_or_start_run
        from specify_cli.mission import get_mission_type

        feature_dir = repo_root_path / "kitty-specs" / mission_slug
        mission_type = get_mission_type(feature_dir)
        run_ref = get_or_start_run(mission_slug, repo_root_path, mission_type)

        # If no decision_id provided, try to auto-resolve
        if decision_id is None:
            from spec_kitty_runtime.engine import _read_snapshot

            snapshot = _read_snapshot(Path(run_ref.run_dir))
            pending = snapshot.pending_decisions

            if len(pending) == 0:
                print("Error: No pending decisions to answer", file=sys.stderr)
                raise typer.Exit(1)
            elif len(pending) == 1:
                decision_id = next(iter(pending.keys()))
            else:
                pending_ids = sorted(pending.keys())
                print(
                    f"Error: Multiple pending decisions ({', '.join(pending_ids)}). Use --decision-id to specify which one.",
                    file=sys.stderr,
                )
                raise typer.Exit(1)

        answer_decision_via_runtime(
            mission_slug,
            decision_id,
            answer,
            agent,
            repo_root_path,
        )

        return decision_id

    except typer.Exit:
        raise
    except Exception as exc:
        print(f"Error answering decision: {exc}", file=sys.stderr)
        raise typer.Exit(1) from exc


def _print_human(decision) -> None:
    """Print a human-readable summary."""

    # SC-003: query mode output must begin with the full verbatim label
    if getattr(decision, "is_query", False):
        print("[QUERY \u2014 no result provided, state not advanced]")
        print(f"  Mission: {decision.mission} @ {decision.mission_state}")
        if getattr(decision, "preview_step", None):
            print(f"  Next step: {decision.preview_step}")
        if getattr(decision, "question", None):
            print(f"  Question: {decision.question}")
            if getattr(decision, "options", None):
                print(f"  Options: {', '.join(decision.options)}")
            if getattr(decision, "decision_id", None):
                print(f"  Decision ID: {decision.decision_id}")
        elif getattr(decision, "reason", None):
            print(f"  Reason: {decision.reason}")
        if decision.progress:
            p = decision.progress
            total = p.get("total_wps", 0)
            done = p.get("done_wps", 0)
            if total > 0:
                pct = int(p.get("weighted_percentage", 0))
                print(f"  Progress: {pct}% ({done}/{total} done)")
        if decision.run_id:
            print(f"  Run ID: {decision.run_id}")
        return

    # --- Standard (non-query) output — unchanged below this line ---
    kind = decision.kind.upper()
    print(f"[{kind}] {decision.mission} @ {decision.mission_state}")

    if decision.action:
        if decision.wp_id:
            print(f"  Action: {decision.action} {decision.wp_id}")
        else:
            print(f"  Action: {decision.action}")

    if decision.workspace_path:
        print(f"  Workspace: {decision.workspace_path}")

    if decision.guard_failures:
        print(f"  Guards pending: {', '.join(decision.guard_failures)}")

    if decision.reason:
        print(f"  Reason: {decision.reason}")

    if getattr(decision, "question", None):
        print(f"  Question: {decision.question}")
    if getattr(decision, "options", None):
        for i, opt in enumerate(decision.options, 1):
            print(f"    {i}. {opt}")
    if decision.decision_id:
        print(f"  Decision ID: {decision.decision_id}")

    if decision.progress:
        p = decision.progress
        total = p.get("total_wps", 0)
        done = p.get("done_wps", 0)
        if total > 0:
            pct = int(p.get("weighted_percentage", 0))
            print(f"  Progress: {pct}% ({done}/{total} done)")

    if decision.run_id:
        print(f"  Run ID: {decision.run_id}")

    if decision.prompt_file:
        print()
        print("  Next step: read the prompt file:")
        print(f"    cat {decision.prompt_file}")
