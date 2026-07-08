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

from specify_cli.missions._read_path_resolver import (
    _canonicalize_primary_read_handle,
    candidate_feature_dir_for_mission,
    primary_feature_dir_for_mission,
)
import contextlib
import io
import importlib
import json
import sys
from pathlib import Path

import typer
from typing import Annotated

from specify_cli.core.context_validation import require_main_repo
from specify_cli.core.paths import get_main_repo_root, locate_project_root
from runtime.next._runtime_pkg_notice import maybe_emit_runtime_pkg_notice


_VALID_RESULTS = ("success", "failed", "blocked")


def decide_next(agent: str, mission_slug: str, result: str, repo_root):
    """Patchable lazy wrapper for the next mutation engine."""
    from runtime.next.decision import decide_next as _decide_next

    return _decide_next(agent, mission_slug, result, repo_root)


def _runtime_bridge_module():
    """Return the patched bridge when tests/consumers installed one."""
    return sys.modules.get("runtime.next.runtime_bridge") or importlib.import_module(
        "runtime.next.runtime_bridge"
    )


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

    # FR-006 caller contract: charter preflight runs BEFORE any state
    # mutation. On failure, print blocked_reason and exit 1 — the runtime
    # decision engine is never entered. Query mode (result is None) is
    # read-only and follows the dashboard's "log + warn + continue" path
    # so that operators can inspect mission state in repos whose charter
    # has not yet been synthesized (e.g., fresh clones, test envs).
    from pathlib import Path as _Path

    _run_charter_preflight_for_next(_Path(str(repo_root)), advancing=result is not None, json_output=json_output)

    from runtime.next.runtime_bridge import MissionNotFoundError as _MissionNotFoundError
    from specify_cli.missions._read_path_resolver import (
        StatusReadPathNotFound as _StatusReadPathNotFound,
    )

    try:
        mission_slug = _resolve_mission_slug(mission, repo_root)
    except _StatusReadPathNotFound as _exc:
        # FR-001 / C-IC02: preserve the typed read-path error (code + checked
        # paths + read-path remediation) instead of collapsing to MISSION_NOT_FOUND.
        _emit_read_path_error(_exc, json_output)
        raise typer.Exit(1) from _exc
    except _MissionNotFoundError as _exc:
        _emit_mission_not_found_error(_exc.handle, json_output)
        raise typer.Exit(1) from _exc
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
    # FR-004 (#2186): the lifecycle ``mission_id`` MUST be read from the PRIMARY
    # checkout. ``resolve_feature_dir_for_mission`` is topology-aware and selects
    # the STATUS-only ``-coord`` husk once one exists — which carries no meta.json
    # (a wrong-leg read raises or, with a stale husk meta, returns the wrong id).
    # Anchor identity on the topology-blind PRIMARY dir (handle folded first so a
    # bare mid8 / human slug resolves the durable ``<slug>-<mid8>`` home; an
    # ambiguous handle RAISES — no silent pick, C-003).
    try:
        feature_dir = primary_feature_dir_for_mission(
            repo_root_path,
            _canonicalize_primary_read_handle(repo_root_path, mission_slug),
        )
    except Exception:
        return

    try:
        identity = resolve_mission_identity(feature_dir)
    except (FileNotFoundError, ValueError, TypeError):
        return
    # #2278: the lifecycle pairing key is a ``mission_id`` field — it MUST be a
    # canonical ULID, never a slug (same fail-closed contract as #2138/FR-004).
    # A legacy mission without a minted ``mission_id`` skips the observability
    # pairing rather than persisting a slug into a ULID-typed field. The
    # ``started`` write fails closed identically, so the two stay symmetric.
    mission_id = identity.mission_id
    if mission_id is None:
        return

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
    # FR-004 (#2186): same PRIMARY anchoring as the completion pairing above — the
    # ``started`` lifecycle record's ``mission_id`` must come from the PRIMARY
    # meta.json, never the coord husk (which lacks it or carries a stale id).
    try:
        feature_dir = primary_feature_dir_for_mission(
            repo_root_path,
            _canonicalize_primary_read_handle(repo_root_path, mission_slug),
        )
    except Exception:
        return

    try:
        identity = resolve_mission_identity(feature_dir)
    except (FileNotFoundError, ValueError, TypeError):
        return
    # #2278: symmetric with the completion-pairing site above — the ``started``
    # record's ``mission_id`` field MUST be a canonical ULID, never a slug
    # (#2138/FR-004 fail-closed contract). Skip the observability record for a
    # legacy mission with no minted ``mission_id`` rather than persisting a slug.
    mission_id = identity.mission_id
    if mission_id is None:
        return

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


def _run_charter_preflight_for_next(repo_root, *, advancing: bool, json_output: bool) -> None:
    """Run charter preflight without letting advisory text contaminate JSON stdout."""
    if advancing:
        from specify_cli.charter_runtime.preflight.hook import run_preflight_or_abort

        if json_output:
            stderr_buffer = io.StringIO()
            error_payload: dict[str, str] | None = None
            with (
                contextlib.redirect_stdout(sys.stderr),
                contextlib.redirect_stderr(stderr_buffer),
            ):
                try:
                    run_preflight_or_abort(repo_root, consumer="next")
                    return
                except typer.Exit:
                    message = stderr_buffer.getvalue().strip() or "charter preflight failed"
                    blocked_reason = message.removeprefix("Error: ").strip()
                    error_payload = {
                        "error_code": "CHARTER_PREFLIGHT_FAILED",
                        "error": message,
                        "blocked_reason": blocked_reason,
                    }
            if error_payload is not None:
                print(json.dumps(error_payload))
                raise typer.Exit(1)
        run_preflight_or_abort(repo_root, consumer="next")
        return

    from specify_cli.charter_runtime.preflight.hook import run_preflight_for_dashboard

    # Query mode is read-only: warn-and-continue, like dashboard.
    stdout_redirect = contextlib.redirect_stdout(sys.stderr) if json_output else contextlib.nullcontext()
    with stdout_redirect:
        run_preflight_for_dashboard(repo_root)


def _resolve_mission_slug(mission: str | None, repo_root: Path) -> str:
    mission_norm = mission.strip() if isinstance(mission, str) else None
    if not mission_norm:
        raise typer.BadParameter("--mission <slug> is required")
    mission_slug = mission_norm

    raw_handle = mission_slug
    # F-001: ``--mission`` accepts handles (bare mid8, full ULID, numeric
    # prefix). Canonicalize at this boundary — the same pattern as the agent
    # ``_find_mission_slug`` helpers — so every downstream consumer
    # (``decide_next``, ``get_or_start_run`` keying ``.kittify/runtime/
    # feature-runs.json``, its persisted ``mission_slug``, and the run-scoped
    # event emitter) receives the canonical directory name. A raw mid8 here
    # creates a split-brain duplicate run vs the full-slug invocation.
    # Handles that resolve to no existing directory keep their raw form,
    # preserving the historical not-found behaviour downstream; an ambiguous
    # handle propagates MissionSelectorAmbiguous (C-CTX-4 — structured error,
    # never a silent fallback).
    from specify_cli.missions._read_path_resolver import StatusReadPathNotFound

    try:
        candidate = candidate_feature_dir_for_mission(
            get_main_repo_root(repo_root), raw_handle
        )
    except StatusReadPathNotFound:
        # FR-001 / C-IC02: the read resolver produced a precise typed error
        # (e.g. COORDINATION_BRANCH_DELETED / STATUS_READ_PATH_NOT_FOUND) with the
        # real read-path remediation. Do NOT collapse it into a generic
        # MISSION_NOT_FOUND ("run mission list") — that mis-routes the operator
        # (the mission is not missing; its read path is broken). Re-raise the
        # typed error so the command layer surfaces ``error_code`` + the checked
        # candidate paths verbatim.
        raise
    if candidate.exists():
        return candidate.name
    return raw_handle


def _print_error(message: str, json_output: bool) -> None:
    if json_output:
        print(json.dumps({"error": message}))
    else:
        print(message, file=sys.stderr)


def _emit_mission_not_found_error(
    handle: str, json_output: bool, next_step: str | None = None
) -> None:
    """Emit a structured MISSION_NOT_FOUND error in the appropriate format.

    Human mode writes to stderr; JSON mode writes a structured envelope to
    stdout.  Both paths exit non-zero (FR-004 / WP03).

    ``next_step`` carries the actionable operator remediation lifted from the
    raised :class:`MissionNotFoundError`; it is surfaced in both the JSON
    payload (alongside ``error_code``) and as a ``Next:`` line in human mode,
    restoring the affordance the superseded ``QueryModeValidationError`` gave
    (#1911). It also remains under the legacy ``remediation`` key for
    backward compatibility.
    """
    remediation = next_step or "Run 'spec-kitty mission list' to see available missions."
    if json_output:
        from specify_cli import __version__

        payload = {
            "result": "error",
            "error_code": "MISSION_NOT_FOUND",
            "handle": handle,
            "next_step": remediation,
            "remediation": remediation,
            "spec_kitty_version": __version__,
        }
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"Error: Mission not found: '{handle}'\n"
            f"No mission matching '{handle}' exists in this repository.",
            file=sys.stderr,
        )
        print(f"  Next: {remediation}", file=sys.stderr)


def _read_path_signal(exc: Exception) -> tuple[str, list[str], str | None]:
    """Extract ``(code, checked_paths, next_step)`` from a typed read-path error.

    FR-001 / C-IC02: both the ``StatusReadPathNotFound`` family (raised by the
    read resolver / ``_resolve_mission_slug``) and the ``ActionContextError``
    boundary type (raised by ``query_current_state`` /
    ``answer_decision_via_runtime``) carry the same underlying signal. The
    boundary ``ActionContextError`` flattens the candidate paths into its message,
    so its ``__cause__`` (the original ``StatusReadPathNotFound``) is the
    structured source of ``coord_candidate`` / ``primary_candidate`` /
    ``next_step``. This reads whichever shape is present without inventing a new
    error type (C-001).
    """
    # The structured carrier is either the exception itself (StatusReadPathNotFound
    # family) or its cause (the boundary ActionContextError wraps it).
    carrier = exc if hasattr(exc, "coord_candidate") else exc.__cause__
    code = getattr(exc, "code", None) or getattr(exc, "error_code", None) or "STATUS_READ_PATH_NOT_FOUND"
    checked: list[str] = []
    for attr in ("coord_candidate", "primary_candidate"):
        candidate = getattr(carrier, attr, None)
        if candidate is not None:
            checked.append(str(candidate))
    next_step = getattr(carrier, "next_step", None) or str(exc)
    return code, checked, next_step


def _emit_read_path_error(exc: Exception, json_output: bool) -> None:
    """Surface a typed read-path error verbatim (FR-001 / FR-002 / C-IC02).

    Mirrors the ``QueryModeValidationError`` branch (a typed ``error_code`` +
    actionable ``next_step`` reach the JSON envelope) instead of collapsing the
    error into ``MISSION_NOT_FOUND`` / "run mission list". The remediation is the
    real read-path repair the resolver produced, never a mission-list hint.
    """
    code, checked_paths, next_step = _read_path_signal(exc)
    remediation = next_step or str(exc)
    if json_output:
        from specify_cli import __version__

        payload: dict[str, object] = {
            "result": "error",
            "error_code": code,
            "error": str(exc),
            "checked_paths": checked_paths,
            "next_step": remediation,
            "remediation": remediation,
            "spec_kitty_version": __version__,
        }
        print(json.dumps(payload, indent=2))
    else:
        print(f"Error: {exc}", file=sys.stderr)
        if checked_paths:
            print(f"  Checked: {', '.join(checked_paths)}", file=sys.stderr)
        if remediation:
            print(f"  Next: {remediation}", file=sys.stderr)


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

    from mission_runtime import ActionContextError

    stderr_buffer = io.StringIO() if json_output else None
    redirect = contextlib.redirect_stderr(stderr_buffer) if stderr_buffer is not None else contextlib.nullcontext()
    try:
        with redirect:
            return _handle_answer(agent, mission_slug, answer, decision_id, repo_root)
    except ActionContextError as exc:
        # FR-001 / C-IC02: the decision-answer path must preserve the typed
        # read-path code IDENTICALLY to the query path — not flatten it into a
        # generic ``error`` string. Surface code + checked paths + remediation.
        _emit_read_path_error(exc, json_output)
        raise typer.Exit(1) from exc
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
    runtime_bridge = _runtime_bridge_module()
    QueryModeValidationError = runtime_bridge.QueryModeValidationError
    # Import MissionNotFoundError from the canonical module so tests that
    # install a fake ``runtime.next.runtime_bridge`` shim still work.
    from mission_runtime import ActionContextError
    from runtime.next.runtime_bridge import MissionNotFoundError

    try:
        decision = runtime_bridge.query_current_state(agent, mission_slug, repo_root)
    except ActionContextError as exc:
        # FR-001 / C-IC02: the resolver produced a precise typed read-path error
        # (e.g. COORDINATION_BRANCH_DELETED). Surface its code + checked paths +
        # read-path remediation verbatim — never collapse to MISSION_NOT_FOUND.
        _emit_read_path_error(exc, json_output)
        raise typer.Exit(1) from exc
    except MissionNotFoundError as exc:
        _emit_mission_not_found_error(
            exc.handle, json_output, next_step=getattr(exc, "next_step", None)
        )
        raise typer.Exit(1) from exc
    except QueryModeValidationError as exc:
        # C-ERR-1 / FR-003: emit a structured payload (error_code + next_step)
        # rather than a silent unknown stub when a handle is unresolvable.
        if json_output:
            payload = {
                "error": str(exc),
                "error_code": getattr(exc, "error_code", "QUERY_MODE_VALIDATION_FAILED"),
            }
            next_step = getattr(exc, "next_step", None)
            if next_step is not None:
                payload["next_step"] = next_step
            print(json.dumps(payload, indent=2))
        else:
            print(f"Error: {exc}", file=sys.stderr)
            next_step = getattr(exc, "next_step", None)
            if next_step:
                print(f"  Next: {next_step}", file=sys.stderr)
        raise typer.Exit(1) from exc
    _print_decision(decision, json_output, answered_id, answer)


def _emit_mission_next_invoked(agent: str, result: str, mission_slug: str, repo_root: object, decision) -> None:
    from specify_cli.mission_v1.events import emit_event

    # WP09/FR-001 (kind-correct): ``mission-events.jsonl`` is a legacy
    # append-only per-mission event log, the same coord-aware STATUS-namespace
    # shape as ``status.events.jsonl`` — route it through the seam on
    # ``STATUS_STATE`` rather than the kind-blind resolver (NFR-001).
    from mission_runtime import MissionArtifactKind, placement_seam

    try:
        feature_dir = placement_seam(repo_root, mission_slug).read_dir(
            MissionArtifactKind.STATUS_STATE
        )
    except Exception:
        feature_dir = None
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
        feature_dir=feature_dir if feature_dir is not None and feature_dir.is_dir() else None,
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
        runtime_bridge = _runtime_bridge_module()
        from specify_cli.mission import get_mission_type

        # FR-004 (#2186): the mission TYPE drives ``get_or_start_run``. Reading it
        # off the topology-aware resolver lands on the STATUS-only coord husk (no
        # meta.json) → ``get_mission_type`` returns the default ``software-dev``,
        # starting the run with the WRONG type for a non-default mission. Anchor on
        # the PRIMARY dir so the type is read from the real meta.json.
        feature_dir = primary_feature_dir_for_mission(
            repo_root_path,
            _canonicalize_primary_read_handle(repo_root_path, mission_slug),
        )
        mission_type = get_mission_type(feature_dir)
        run_ref = runtime_bridge.get_or_start_run(mission_slug, repo_root_path, mission_type)

        # If no decision_id provided, try to auto-resolve
        if decision_id is None:
            from runtime.next._internal_runtime.engine import _read_snapshot

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

        runtime_bridge.answer_decision_via_runtime(
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
