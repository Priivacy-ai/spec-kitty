"""Regression pins for the runtime emitter flush target (ADR (c)).

ADR ``docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md``
Decision Outcome (c) adjudicated a latent correctness bug on the ``next``
bridge, executed by mission ``dead-port-disposition-01M1TZVN`` WP05:

* Under the strict retrospective gate (``timing=before_completion`` +
  ``failure_policy=block``) the engine emitter is replaced by a
  ``_BufferingRuntimeEmitter`` for EVERY advance, and the buffer used to be
  flushed into the plain no-op ``ctx.sync_emitter`` instead of
  ``ctx.emitter_for_engine`` -- the ``DecisionGitLog`` wrap the non-gated path
  uses. A strict-policy ``decision_required`` advance therefore never appended
  its ``DecisionInputRequested`` to ``decisions.events.jsonl``.
* The composition dispatch path passed the plain ``ctx.sync_emitter`` into
  ``advance_run_state_after_composition`` -- the same defect class, so
  decision events on that path never reached the git log regardless of policy.

Each fixture below uses a REAL ``DecisionGitLog`` (the durable decision sink)
as ``emitter_for_engine`` and a real ``NullEmitter`` as ``sync_emitter``, so the
assertion is on the file the operator actually reads back, not on a spy.

The refusal scenario (a terminal advance the gate rejects) must be GREEN
before and after the fix: rollback discards the buffer without a git write.
C-006: ``_BufferingRuntimeEmitter`` itself is untouched -- only its flush
TARGET changed at the call site.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from runtime.next import runtime_bridge as rb
from runtime.next import runtime_bridge_composition as _composition_seam
from runtime.next import runtime_bridge_cores as _cores
from runtime.next import runtime_bridge_retrospective as _retrospective_seam
from runtime.next._internal_runtime import MissionRunRef
from runtime.next._internal_runtime.events import DECISION_INPUT_REQUESTED, NullEmitter
from runtime.next._internal_runtime.schema import MissionRunSnapshot, NextDecision
from runtime.next.decision import Decision, DecisionKind
from spec_kitty_events.mission_next import (
    DecisionInputRequestedPayload,
    MissionRunCompletedPayload,
    RuntimeActorIdentity,
)
from specify_cli.events.decision_log import DecisionGitLog

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_SLUG = "042-mission"
_RUN_ID = "run-042"
_DECISION_ID = "audit:review"
_NOW = "2026-09-06T00:00:00+00:00"
_STRICT_POLICY = SimpleNamespace(enabled=True, timing="before_completion", failure_policy="block")


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _decision_log_path(repo_root: Path) -> Path:
    return repo_root / "kitty-specs" / _SLUG / "decisions.events.jsonl"


def _decision_log_rows(repo_root: Path) -> list[dict[str, Any]]:
    path = _decision_log_path(repo_root)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _actor() -> RuntimeActorIdentity:
    return RuntimeActorIdentity(actor_id="agent-x", actor_type="llm", provider=None, model=None, tool=None)


def _requested_payload() -> DecisionInputRequestedPayload:
    return DecisionInputRequestedPayload(
        run_id=_RUN_ID,
        decision_id=_DECISION_ID,
        step_id="review",
        question="Proceed?",
        options=("yes", "no"),
        input_key=None,
        actor=_actor(),
    )


def _completed_payload() -> MissionRunCompletedPayload:
    return MissionRunCompletedPayload(run_id=_RUN_ID, mission_type="software-dev", actor=_actor())


def _decision_required() -> NextDecision:
    return NextDecision(
        kind="decision_required",
        run_id=_RUN_ID,
        mission_key=_SLUG,
        decision_id=_DECISION_ID,
        step_id="review",
        question="Proceed?",
        options=["yes", "no"],
    )


def _make_ctx(tmp_path: Path, *, current_step_id: str) -> rb.DecideNextContext:
    """A ``DecideNextContext`` whose ``emitter_for_engine`` is a REAL
    ``DecisionGitLog`` wrapping the REAL ``NullEmitter`` that is also the
    context's ``sync_emitter`` -- exactly the shape ``_dn_bootstrap`` builds
    (``_wrap_with_decision_git_log(sync_emitter, ...)``)."""
    mission_dir = tmp_path / "kitty-specs" / _SLUG
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "meta.json").write_text(json.dumps({"mission_type": "software-dev"}), encoding="utf-8")
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    inner = NullEmitter()
    git_log = DecisionGitLog(
        repo_root=tmp_path,
        worktree_root=tmp_path,
        destination_ref=f"kitty/mission-{_SLUG}",
        mission_slug=_SLUG,
        inner=inner,
    )
    return rb.DecideNextContext(
        agent="agent-x",
        mission_slug=_SLUG,
        result="success",
        repo_root=tmp_path,
        feature_dir=mission_dir,
        now=_NOW,
        mission_type="software-dev",
        sync_emitter=inner,
        emitter_for_engine=git_log,
        origin={"mission_tier": "built-in", "mission_path": "software-dev"},
        progress=None,
        run_ref=MissionRunRef(run_id=_RUN_ID, run_dir=str(run_dir), mission_key=_SLUG),
        run_dir=run_dir,
        current_step_id=current_step_id,
    )


def _sentinel_decision(reason: str) -> Decision:
    return rb._materialize_decision(
        _cores.DecisionEnvelope(
            kind=DecisionKind.terminal,
            agent="agent-x",
            mission_slug=_SLUG,
            mission="software-dev",
            mission_state="done",
            timestamp=_NOW,
            reason=reason,
        )
    )


def _install_strict_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        _retrospective_seam,
        "_resolve_retrospective_policy_for_runtime",
        lambda repo_root: (_STRICT_POLICY, {}, None),
    )


# ---------------------------------------------------------------------------
# 1. Legacy ``runtime_next_step`` path: strict-gated decision_required advance
# ---------------------------------------------------------------------------


def test_strict_gated_decision_required_advance_reaches_decision_git_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR (c): under strict policy the engine writes only into the buffer; the
    flush after the (never-entered, non-terminal) gate is therefore the first
    and only ``DecisionGitLog`` write. It must land in ``decisions.events.jsonl``."""
    ctx = _make_ctx(tmp_path, current_step_id="review")
    _install_strict_policy(monkeypatch)

    def _engine(run_ref: Any, *, agent_id: str, result: str, emitter: Any) -> NextDecision:
        # The real engine's ``_emit_decision_required`` does exactly this
        # against whatever emitter the bridge handed it (the buffer here).
        emitter.emit_decision_input_requested(_requested_payload())
        return _decision_required()

    monkeypatch.setattr(rb, "runtime_next_step", _engine)
    sentinel = _sentinel_decision("decision-required-sentinel")
    monkeypatch.setattr(rb, "_map_runtime_decision", lambda *a: sentinel)

    assert _decision_log_rows(tmp_path) == []

    result = rb._dn_decision_materialize(ctx)

    assert result is sentinel
    rows = _decision_log_rows(tmp_path)
    assert [row["event_type"] for row in rows] == [DECISION_INPUT_REQUESTED], (
        "the buffered DecisionInputRequested was flushed into the plain no-op sync_emitter instead of the DecisionGitLog-wrapped emitter_for_engine"
    )
    assert rows[0]["payload"]["decision_id"] == _DECISION_ID
    assert rows[0]["payload"]["run_id"] == _RUN_ID


# ---------------------------------------------------------------------------
# 2. Composition dispatch path: same defect class
# ---------------------------------------------------------------------------


def test_composition_dispatch_decision_required_reaches_decision_git_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR (c), composition bypass: ``_dn_composition_dispatch`` must hand the
    ``DecisionGitLog``-wrapped emitter to ``advance_run_state_after_composition``
    so the engine's ``_emit_decision_required`` reaches the git log. The real
    adapter runs here (engine primitives stubbed at the source module, as in
    ``test_bridge_engine.py``); it also seeds the emitter first, so the wrapped
    emitter must satisfy the seam's full surface."""
    ctx = _make_ctx(tmp_path, current_step_id="tasks_outline")
    monkeypatch.setattr(_composition_seam, "_should_dispatch_via_composition", lambda *a, **kw: True)
    monkeypatch.setattr(_composition_seam, "_normalize_action_for_composition", lambda step: "tasks-outline")
    monkeypatch.setattr(_composition_seam, "_composition_dispatch_inputs", lambda **kw: (None, {"contract": True}))
    monkeypatch.setattr(_composition_seam, "_dispatch_via_composition", lambda **kw: [])

    snapshot = MissionRunSnapshot(run_id=_RUN_ID, mission_key=_SLUG, template_path="", template_hash="h")
    monkeypatch.setattr("runtime.next.runtime_bridge_engine._engine._read_snapshot", lambda run_dir: snapshot)
    monkeypatch.setattr("runtime.next.runtime_bridge_engine._engine._load_frozen_template", lambda run_dir: object())
    monkeypatch.setattr("runtime.next.runtime_bridge_engine._engine._write_snapshot", lambda run_dir, snap: None)
    monkeypatch.setattr("runtime.next.runtime_bridge_engine._engine._append_event", lambda *a: None)
    monkeypatch.setattr("runtime.next.runtime_bridge_engine._planner.plan_next", lambda *a, **k: _decision_required())
    sentinel = _sentinel_decision("composition-sentinel")
    monkeypatch.setattr(rb, "_map_runtime_decision", lambda *a: sentinel)

    result = rb._dn_composition_dispatch(ctx)

    assert result is sentinel, getattr(result, "reason", result)
    rows = _decision_log_rows(tmp_path)
    assert [row["event_type"] for row in rows] == [DECISION_INPUT_REQUESTED], (
        "the composition dispatch passed the plain no-op sync_emitter into the engine adapter; DecisionInputRequested never reached decisions.events.jsonl"
    )
    assert rows[0]["payload"]["decision_id"] == _DECISION_ID


# ---------------------------------------------------------------------------
# 3. Rollback: a refused terminal gate discards the buffer -- no git write
# ---------------------------------------------------------------------------


def test_refused_terminal_gate_discards_buffer_without_a_decision_git_log_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """GREEN before and after the fix. The gate at the bridge runs BEFORE the
    flush and the buffer is one-shot: refusal drops every buffered call and
    rolls state.json / run.events.jsonl back. The engine never buffers a
    decision request on a terminal advance (the two kinds are exclusive
    branches); this fixture buffers one deliberately so the discard is
    observable through the git log, which ignores ``MissionRunCompleted``."""
    ctx = _make_ctx(tmp_path, current_step_id="review")
    state_path = ctx.run_dir / "state.json"
    events_path = ctx.run_dir / "run.events.jsonl"
    state_path.write_text('{"pre": true}', encoding="utf-8")
    events_path.write_text("event-1\n", encoding="utf-8")
    _install_strict_policy(monkeypatch)

    def _engine(run_ref: Any, *, agent_id: str, result: str, emitter: Any) -> NextDecision:
        emitter.emit_decision_input_requested(_requested_payload())
        emitter.emit_mission_run_completed(_completed_payload())
        state_path.write_text('{"post": true}', encoding="utf-8")
        events_path.write_text("event-1\nevent-2\n", encoding="utf-8")
        return NextDecision(kind="terminal", run_id=_RUN_ID, mission_key=_SLUG)

    monkeypatch.setattr(rb, "runtime_next_step", _engine)

    def _refuse(**_kw: Any) -> None:
        raise RuntimeError("gate refused")

    monkeypatch.setattr(_retrospective_seam, "_run_retrospective_learning_capture", _refuse)
    monkeypatch.setattr(_retrospective_seam, "_resolve_mission_id_for_terminus", lambda feature_dir: "mission-id")

    decision = rb._dn_decision_materialize(ctx)

    assert decision.kind == DecisionKind.blocked
    assert decision.reason == "Retrospective gate refused completion: gate refused"
    assert not _decision_log_path(tmp_path).exists(), "a refused gate must not write the decision git log"
    assert state_path.read_text(encoding="utf-8") == '{"pre": true}'
    assert events_path.read_bytes() == b"event-1\n"
