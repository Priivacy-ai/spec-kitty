"""Lightweight in-repo fallback for ``spec_kitty_runtime``.

This shim provides the subset of runtime API used by ``specify_cli.next`` and
its tests when the external ``spec-kitty-runtime`` package is unavailable.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from ._state import (
    append_event,
    create_initial_state,
    read_state,
    read_template,
    resolve_template,
    write_state,
)
from .models import (
    DiscoveryContext,
    MissionPolicySnapshot,
    MissionRunRef,
    NextDecision,
    PendingDecision,
    RuntimeState,
)
from .schema import ActorIdentity, MissionRuntimeError


class NullEmitter:
    """No-op event emitter compatible with runtime API."""

    def emit(self, *_args: object, **_kwargs: object) -> None:
        return None



def start_mission_run(
    *,
    template_key: str,
    inputs: dict[str, object],
    policy_snapshot: MissionPolicySnapshot,
    context: DiscoveryContext,
    run_store: Path,
    emitter: NullEmitter,
) -> MissionRunRef:
    """Create a persisted mission run and return its reference."""
    del inputs, policy_snapshot, emitter

    template_path = resolve_template(template_key, context)
    template = read_template(template_path)

    run_id = f"run-{uuid4().hex[:12]}"
    run_dir = run_store / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    state = create_initial_state(run_id, template)
    write_state(run_dir, state)

    return MissionRunRef(
        run_id=run_id,
        run_dir=str(run_dir),
        mission_key=template.mission.key,
    )



def _issue_step(state: RuntimeState, run_dir: Path, index: int) -> NextDecision:
    if index < 0 or index >= len(state.steps):
        state.terminal = True
        write_state(run_dir, state)
        return NextDecision(
            kind="terminal",
            run_id=state.run_id,
            step_id=state.issued_step_id,
            reason="Mission complete",
        )

    step_raw = state.steps[index]
    step_id_obj = step_raw.get("id")
    if not isinstance(step_id_obj, str):
        raise MissionRuntimeError("Invalid runtime step definition: missing id")

    step_id = step_id_obj
    state.current_index = index
    state.issued_step_id = step_id

    # Reset pending decisions for newly issued step.
    state.pending_decisions = {}

    required_inputs = step_raw.get("requires_inputs")
    if isinstance(required_inputs, list):
        for input_key in required_inputs:
            if not isinstance(input_key, str):
                continue
            if input_key in state.answered_inputs:
                continue
            decision_id = f"input:{input_key}"
            state.pending_decisions[decision_id] = PendingDecision(
                input_key=input_key,
                question=f"Provide value for '{input_key}'",
                options=["yes", "no"],
                step_id=step_id,
            )

    write_state(run_dir, state)

    if state.pending_decisions:
        first_id = sorted(state.pending_decisions.keys())[0]
        pending = state.pending_decisions[first_id]
        return NextDecision(
            kind="decision_required",
            run_id=state.run_id,
            step_id=step_id,
            decision_id=first_id,
            input_key=pending.input_key,
            question=pending.question,
            options=list(pending.options),
            reason="Decision required",
        )

    return NextDecision(kind="step", run_id=state.run_id, step_id=step_id)



def next_step(
    run_ref: MissionRunRef,
    *,
    agent_id: str,
    result: str,
    emitter: NullEmitter,
) -> NextDecision:
    """Advance the runtime mission by one step."""
    del emitter

    run_dir = Path(run_ref.run_dir)
    state = read_state(run_dir)

    if state.terminal:
        return NextDecision(
            kind="terminal",
            run_id=state.run_id,
            step_id=state.issued_step_id,
            reason="Mission complete",
        )

    # First call: issue initial step.
    if state.issued_step_id is None:
        return _issue_step(state, run_dir, 0)

    if result != "success":
        append_event(
            run_dir,
            "NextStepAutoCompleted",
            {
                "agent_id": agent_id,
                "result": result,
                "step_id": state.issued_step_id,
                "run_id": state.run_id,
            },
        )
        return NextDecision(
            kind="blocked",
            run_id=state.run_id,
            step_id=state.issued_step_id,
            reason=f"Previous step reported {result}",
        )

    # Cannot advance until pending decisions for current step are answered.
    pending_for_current = [
        (decision_id, pending)
        for decision_id, pending in state.pending_decisions.items()
        if pending.step_id == state.issued_step_id
    ]
    if pending_for_current:
        decision_id, pending = sorted(pending_for_current, key=lambda item: item[0])[0]
        return NextDecision(
            kind="decision_required",
            run_id=state.run_id,
            step_id=state.issued_step_id,
            decision_id=decision_id,
            input_key=pending.input_key,
            question=pending.question,
            options=list(pending.options),
            reason="Decision required",
        )

    append_event(
        run_dir,
        "NextStepAutoCompleted",
        {
            "agent_id": agent_id,
            "result": result,
            "step_id": state.issued_step_id,
            "run_id": state.run_id,
        },
    )

    next_index = state.current_index + 1
    if next_index >= len(state.steps):
        state.terminal = True
        write_state(run_dir, state)
        return NextDecision(
            kind="terminal",
            run_id=state.run_id,
            step_id=state.issued_step_id,
            reason="Mission complete",
        )

    return _issue_step(state, run_dir, next_index)



def provide_decision_answer(
    run_ref: MissionRunRef,
    decision_id: str,
    answer: str,
    actor: ActorIdentity,
    *,
    emitter: NullEmitter,
) -> None:
    """Persist a decision answer for the active run."""
    del emitter

    run_dir = Path(run_ref.run_dir)
    state = read_state(run_dir)

    pending = state.pending_decisions.get(decision_id)
    if pending is None:
        raise MissionRuntimeError(f"Decision '{decision_id}' not found")

    state.answered_inputs[pending.input_key] = answer
    del state.pending_decisions[decision_id]
    write_state(run_dir, state)

    append_event(
        run_dir,
        "DecisionAnswered",
        {
            "decision_id": decision_id,
            "input_key": pending.input_key,
            "answer": answer,
            "actor_id": actor.actor_id,
            "actor_type": actor.actor_type,
            "run_id": state.run_id,
        },
    )


__all__ = [
    "ActorIdentity",
    "DiscoveryContext",
    "MissionPolicySnapshot",
    "MissionRunRef",
    "MissionRuntimeError",
    "NextDecision",
    "NullEmitter",
    "next_step",
    "provide_decision_answer",
    "start_mission_run",
]
