"""CLI command for ``spec-kitty next``.

FR-008 / T031 note: The `next` command dispatches mission-step actions via
``decide_next()``. In the 3.2.x baseline, mission-step invocations (specify,
plan, tasks, implement, review, merge, accept) are opened OUT-OF-PROCESS by
the agent that reads the decision — not by this command directly.

Therefore, this command does NOT open InvocationRecord objects itself.

When a future integration has `next` open an InvocationRecord directly (e.g.
for agent-mode automation), it should use:
    derive_mode(f"next.{action}")  -> ModeOfWork.MISSION_STEP
for any of: next.specify, next.plan, next.tasks, next.implement,
            next.review, next.merge, next.accept

The mapping is registered in _ENTRY_COMMAND_MODE (modes.py).
TODO(future): wire derive_mode(f"next.{action}") when InvocationRecord is
opened directly from the next command.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys

import typer
from typing import Annotated

from specify_cli.core.context_validation import require_main_repo
from specify_cli.core.paths import locate_project_root
from specify_cli.cli.selector_resolution import resolve_selector
from specify_cli.next._runtime_pkg_notice import maybe_emit_runtime_pkg_notice


_VALID_RESULTS = ("success", "failed", "blocked")


def decide_next(agent: str, mission_slug: str, result: str, repo_root):
    """Patchable lazy wrapper for the next mutation engine."""
    from specify_cli.next.decision import decide_next as _decide_next

    return _decide_next(agent, mission_slug, result, repo_root)


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
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug")] = None,
    feature: Annotated[
        str | None,
        typer.Option("--feature", hidden=True, help="(deprecated) Use --mission"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON decision only")] = False,
    answer: Annotated[str | None, typer.Option("--answer", help="Answer to a pending decision")] = None,
    decision_id: Annotated[str | None, typer.Option("--decision-id", help="Decision ID (required if multiple pending)")] = None,
) -> None:
    """Decide and emit the next agent action for the current mission.

    Agents call this command repeatedly in a loop.  The system inspects the
    mission state machine, evaluates guards, and returns a deterministic
    decision with an action and prompt file.

    Examples:
        spec-kitty next --mission 034-my-feature --json                            # query mode
        spec-kitty next --agent claude --mission 034-my-feature --result success --json
        spec-kitty next --agent codex --mission 034-my-feature
        spec-kitty next --agent gemini --mission 034-my-feature --result failed --json
        spec-kitty next --agent claude --mission 034-my-feature --answer "yes" --result success --json
        spec-kitty next --agent claude --mission 034-my-feature --answer "approve" --decision-id "input:review" --result success --json
    """
    _maybe_emit_runtime_notice(json_output)

    repo_root = locate_project_root()
    if repo_root is None:
        print("Error: Could not locate project root", file=sys.stderr)
        raise typer.Exit(1)

    mission_slug = _resolve_mission_slug(mission, feature)
    _validate_result_and_answer(result, answer, json_output)
    answered_id = _maybe_handle_answer(agent, mission_slug, answer, decision_id, repo_root, json_output)

    # Query mode: bare call without --result remains read-only and does not
    # require agent identity.
    if result is None:
        _run_query_mode(agent, mission_slug, repo_root, json_output, answered_id, answer)
        return  # No event emitted, no DAG advancement

    if not agent:
        print("Error: --agent is required when --result is provided", file=sys.stderr)
        raise typer.Exit(1)

    # WP05 (#843): pair the previous issuance's `started` lifecycle record
    # BEFORE we advance the runtime. This must run before decide_next so the
    # pair is observable even if decide_next raises.
    _pair_previous_lifecycle_record(agent, mission_slug, result, repo_root)

    decision = decide_next(agent, mission_slug, result, repo_root)
    _emit_mission_next_invoked(agent, result, mission_slug, repo_root, decision)

    # WP05 (#843): write the `started` lifecycle record AFTER the decision is
    # finalised but BEFORE returning to the agent, so the record exists iff
    # the agent actually saw the issued action.
    _write_issuance_lifecycle_record(agent, mission_slug, repo_root, decision)

    _print_decision(decision, json_output, answered_id, answer)

    if not json_output:
        _print_stalled_wp_interventions(mission_slug, repo_root)

    if decision.kind == "blocked":
        raise typer.Exit(1)


def _pair_previous_lifecycle_record(
    agent: str,
    mission_slug: str,
    result: str,
    repo_root: object,
) -> None:
    """Write the paired ``completed`` / ``failed`` record for the prior issuance.

    Matches the most recent unpaired ``started`` for ``(agent, mission_id)``
    in the local lifecycle store and appends a partner record carrying the
    SAME ``canonical_action_id``. The id is propagated, never re-computed
    (FR-011 / contract: "no rewriting at completion time").

    Best-effort: a missing meta.json or empty store is silently a no-op so
    new missions / first issuance behave naturally.
    """
    from pathlib import Path

    from specify_cli.invocation.lifecycle import (
        find_latest_unpaired_started,
        read_lifecycle_records,
        write_paired_completion,
    )
    from specify_cli.mission_metadata import resolve_mission_identity

    repo_root_path = Path(str(repo_root)) if not isinstance(repo_root, Path) else repo_root
    feature_dir = repo_root_path / "kitty-specs" / mission_slug

    try:
        identity = resolve_mission_identity(feature_dir)
    except (FileNotFoundError, ValueError, TypeError):
        return
    mission_id = identity.mission_id or identity.mission_slug

    records = read_lifecycle_records(repo_root_path)
    started = find_latest_unpaired_started(
        records,
        agent=agent,
        mission_id=mission_id,
    )
    if started is None:
        return

    if result == "success":
        phase: str = "completed"
        reason: str | None = None
    else:
        phase = "failed"
        reason = result  # "failed" or "blocked" — preserves caller intent

    write_paired_completion(
        repo_root_path,
        started=started,
        phase=phase,  # type: ignore[arg-type]
        reason=reason,
    )


def _write_issuance_lifecycle_record(
    agent: str,
    mission_slug: str,
    repo_root: object,
    decision: object,
) -> None:
    """Write a ``started`` lifecycle record for the action just issued.

    The canonical action id is ``f"{decision.mission_state}::{decision.action}"``
    — the mission step + action that the runtime actually issued. This
    value is read once here and never re-derived at completion time.

    No-op when the decision did not issue a public action (e.g. terminal,
    blocked, decision_required). Failures to write are swallowed: the
    lifecycle log is observability, not a hard runtime dependency.
    """
    from pathlib import Path

    from specify_cli.invocation.lifecycle import (
        make_canonical_action_id,
        write_started,
    )
    from specify_cli.mission_metadata import resolve_mission_identity

    action = getattr(decision, "action", None)
    mission_state = getattr(decision, "mission_state", None)
    kind = getattr(decision, "kind", None)
    if not action or not mission_state or kind != "step":
        return

    repo_root_path = Path(str(repo_root)) if not isinstance(repo_root, Path) else repo_root
    feature_dir = repo_root_path / "kitty-specs" / mission_slug

    try:
        identity = resolve_mission_identity(feature_dir)
    except (FileNotFoundError, ValueError, TypeError):
        return
    mission_id = identity.mission_id or identity.mission_slug

    try:
        canonical_id = make_canonical_action_id(mission_state, action)
    except ValueError:
        return

    try:
        write_started(
            repo_root_path,
            canonical_action_id=canonical_id,
            agent=agent,
            mission_id=mission_id,
            wp_id=getattr(decision, "wp_id", None),
        )
    except OSError:
        # Lifecycle log is observability; failures must not break `next`.
        return


def _maybe_emit_runtime_notice(json_output: bool) -> None:
    """Emit the stale-runtime notice only for human-readable output."""
    # FR-020 of mission shared-package-boundary-cutover-01KQ22DS: emit a
    # one-time deprecation notice if the retired spec-kitty-runtime package
    # is still installed in the operator's environment. The check uses
    # importlib.metadata, which does NOT import spec_kitty_runtime, so it
    # does not violate FR-002 / C-001. JSON mode is a machine contract:
    # stdout must be exactly one JSON document, and Typer's CliRunner may
    # combine stderr into result.output.
    if not json_output:
        maybe_emit_runtime_pkg_notice()


def _resolve_mission_slug(mission: str | None, feature: str | None) -> str:
    try:
        resolved = resolve_selector(
            canonical_value=mission,
            canonical_flag="--mission",
            alias_value=feature,
            alias_flag="--feature",
            suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
            command_hint="--mission <slug>",
        )
    except typer.BadParameter as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(1) from exc
    return resolved.canonical_value


def _print_error(message: str, json_output: bool) -> None:
    if json_output:
        print(json.dumps({"error": message}))
    else:
        print(message, file=sys.stderr)


def _validate_result_and_answer(result: str | None, answer: str | None, json_output: bool) -> None:
    if result is not None and result not in _VALID_RESULTS:
        print(f"Error: --result must be one of {_VALID_RESULTS}, got '{result}'", file=sys.stderr)
        raise typer.Exit(1)

    if answer is not None and result is None:
        _print_error("Error: --answer requires --result because query mode is read-only", json_output)
        raise typer.Exit(1)


def _maybe_handle_answer(
    agent: str | None,
    mission_slug: str,
    answer: str | None,
    decision_id: str | None,
    repo_root: object,
    json_output: bool,
) -> str | None:
    if answer is None:
        return None
    if not agent:
        _print_error("Error: --agent is required when --answer is provided", json_output)
        raise typer.Exit(1)

    stderr_buffer = io.StringIO() if json_output else None
    redirect = contextlib.redirect_stderr(stderr_buffer) if stderr_buffer is not None else contextlib.nullcontext()
    try:
        with redirect:
            return _handle_answer(agent, mission_slug, answer, decision_id, repo_root)
    except typer.Exit as exc:
        if json_output:
            message = (stderr_buffer.getvalue().strip() if stderr_buffer is not None else "") or str(exc) or "Answer handling failed"
            print(json.dumps({"error": message}))
            raise typer.Exit(1) from exc
        raise
    except Exception as exc:
        if json_output:
            print(json.dumps({"error": str(exc)}))
            raise typer.Exit(1) from exc
        raise


def _run_query_mode(
    agent: str | None,
    mission_slug: str,
    repo_root: object,
    json_output: bool,
    answered_id: str | None,
    answer: str | None,
) -> None:
    from specify_cli.next.runtime_bridge import QueryModeValidationError, query_current_state

    try:
        decision = query_current_state(agent, mission_slug, repo_root)
    except QueryModeValidationError as exc:
        _print_error(f"Error: {exc}" if not json_output else str(exc), json_output)
        raise typer.Exit(1) from exc
    _print_decision(decision, json_output, answered_id, answer)


def _emit_mission_next_invoked(agent: str, result: str, mission_slug: str, repo_root: object, decision) -> None:
    from specify_cli.mission_v1.events import emit_event

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


def _print_decision(decision, json_output: bool, answered_id: str | None, answer: str | None) -> None:
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
            from specify_cli.next._internal_runtime.engine import _read_snapshot

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
    if getattr(decision, "is_query", False):
        _print_query_human(decision)
        return
    _print_standard_human(decision)


def _print_query_human(decision) -> None:
    # SC-003: query mode output must begin with the full verbatim label.
    print("[QUERY \u2014 no result provided, state not advanced]")
    print(f"  Mission: {decision.mission_slug} @ {decision.mission_state}")
    if getattr(decision, "mission", None):
        print(f"  Mission Type: {decision.mission}")
    if getattr(decision, "preview_step", None):
        print(f"  Next step: {decision.preview_step}")
    _print_query_details(decision)
    _print_progress(decision)
    if decision.run_id:
        print(f"  Run ID: {decision.run_id}")


def _print_query_details(decision) -> None:
    if getattr(decision, "question", None):
        print(f"  Question: {decision.question}")
        if getattr(decision, "options", None):
            print(f"  Options: {', '.join(decision.options)}")
        if getattr(decision, "decision_id", None):
            print(f"  Decision ID: {decision.decision_id}")
    elif getattr(decision, "reason", None):
        print(f"  Reason: {decision.reason}")


def _print_standard_human(decision) -> None:
    kind = decision.kind.upper()
    print(f"[{kind}] {decision.mission_slug} @ {decision.mission_state}")
    if getattr(decision, "mission", None):
        print(f"  Mission Type: {decision.mission}")

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

    _print_progress(decision)

    if decision.run_id:
        print(f"  Run ID: {decision.run_id}")

    if decision.prompt_file:
        print()
        print("  Next step: read the prompt file:")
        print(f"    cat {decision.prompt_file}")


def _print_progress(decision) -> None:
    if decision.progress:
        p = decision.progress
        total = p.get("total_wps", 0)
        done = p.get("done_wps", 0)
        if total > 0:
            pct = int(p.get("weighted_percentage", 0))
            print(f"  Progress: {pct}% ({done}/{total} done)")


def _print_stalled_wp_interventions(mission_slug: str, repo_root: object) -> None:
    """Print intervention commands for any stalled in_review WPs.

    Calls show_kanban_status() in silent mode and surfaces stalled WPs found
    in the return dict.  Failures are swallowed — this is observability only.
    """
    try:
        import io
        import contextlib
        from specify_cli.agent_utils.status import show_kanban_status

        # Suppress board output — we only want the stalled_wps data
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            status_result = show_kanban_status(mission_slug)

        stalled = status_result.get("stalled_wps", [])
        for stall in stalled:
            wp_id = stall["wp_id"]
            age_m = stall["age_minutes"]
            slug = stall.get("mission_slug", mission_slug)
            print(
                f"\n⚠  {wp_id} has been in_review for {age_m}m — reviewer may be stalled.\n"
                f"   Intervention options:\n"
                f"     spec-kitty agent tasks move-task {wp_id} --to approved --force "
                f"--note 'Approved after {age_m}m stall' --mission {slug}\n"
                f"     spec-kitty agent tasks move-task {wp_id} --to planned "
                f"--review-feedback-file <path> --mission {slug}"
            )
    except Exception:  # noqa: BLE001 — stall check is observability only
        pass
