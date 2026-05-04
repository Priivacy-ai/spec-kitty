"""Bridge wiring for the retrospective terminus gate.

Two scopes:

1. Unit tests for ``_BufferingRuntimeEmitter`` — record/flush/discard
   semantics. The buffer is the load-bearing mechanism that prevents the
   sync emitter from dispatching ``MissionRunCompleted`` on a speculative
   engine advance that the gate later refuses.

2. Real-bridge integration through ``decide_next_via_runtime`` — drives
   the full software-dev DAG to terminal with the retrospective lifecycle
   opted in via charter, monkeypatches ``SyncRuntimeEventEmitter`` to a
   recording wrapper, and asserts:
     * the final decision is ``blocked`` with the gate's reason,
     * ``run.events.jsonl`` does not contain ``MissionRunCompleted`` from
       the blocked attempt,
     * the recording sync emitter received zero
       ``emit_mission_run_completed`` calls,
     * ``state.json`` is rolled back (does not say all-completed).

This is the canonical regression for the post-merge P0: a naive
"call-engine-then-gate" design leaks both local terminal state and remote
sync events; the bridge MUST buffer + roll back atomically.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from specify_cli.next.decision import DecisionKind
from tests.lane_test_utils import write_single_lane_manifest

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Unit: _BufferingRuntimeEmitter
# ---------------------------------------------------------------------------


def test_buffering_emitter_records_calls_in_order() -> None:
    from specify_cli.next.runtime_bridge import _BufferingRuntimeEmitter

    buffer = _BufferingRuntimeEmitter()
    p1, p2, p3 = object(), object(), object()
    buffer.emit_mission_run_started(p1)
    buffer.emit_next_step_issued(p2)
    buffer.emit_mission_run_completed(p3)

    assert buffer.call_count() == 3
    assert buffer._calls == [
        ("emit_mission_run_started", p1),
        ("emit_next_step_issued", p2),
        ("emit_mission_run_completed", p3),
    ]


def test_buffering_emitter_flush_replays_in_order_then_clears() -> None:
    from specify_cli.next.runtime_bridge import _BufferingRuntimeEmitter

    buffer = _BufferingRuntimeEmitter()
    p_start, p_completed = object(), object()
    buffer.emit_mission_run_started(p_start)
    buffer.emit_mission_run_completed(p_completed)

    received: list[tuple[str, Any]] = []

    class _Recorder:
        def emit_mission_run_started(self, payload: Any) -> None:
            received.append(("emit_mission_run_started", payload))

        def emit_mission_run_completed(self, payload: Any) -> None:
            received.append(("emit_mission_run_completed", payload))

    target = _Recorder()
    buffer.flush(target)

    assert received == [
        ("emit_mission_run_started", p_start),
        ("emit_mission_run_completed", p_completed),
    ]
    # Re-flushing is a no-op (idempotent) and the buffer is cleared.
    received.clear()
    buffer.flush(target)
    assert received == []
    assert buffer.call_count() == 0


def test_buffering_emitter_flush_skips_missing_target_methods() -> None:
    from specify_cli.next.runtime_bridge import _BufferingRuntimeEmitter

    buffer = _BufferingRuntimeEmitter()
    p_start, p_completed = object(), object()
    buffer.emit_mission_run_started(p_start)
    buffer.emit_mission_run_completed(p_completed)

    received: list[tuple[str, Any]] = []

    class _PartialRecorder:
        def emit_mission_run_started(self, payload: Any) -> None:
            received.append(("emit_mission_run_started", payload))

    buffer.flush(_PartialRecorder())

    assert received == [("emit_mission_run_started", p_start)]
    assert buffer.call_count() == 0


def test_buffering_emitter_discard_drops_calls_without_replaying() -> None:
    from specify_cli.next.runtime_bridge import _BufferingRuntimeEmitter

    buffer = _BufferingRuntimeEmitter()
    buffer.emit_mission_run_completed(object())
    assert buffer.call_count() == 1

    received: list[Any] = []

    class _Recorder:
        def emit_mission_run_completed(self, payload: Any) -> None:
            received.append(payload)

    buffer.discard()
    buffer.flush(_Recorder())  # flushing after discard is a no-op
    assert received == []
    assert buffer.call_count() == 0


def test_buffering_emitter_implements_full_runtime_protocol() -> None:
    """All eight RuntimeEventEmitter methods accept a payload without raising."""
    from specify_cli.next.runtime_bridge import _BufferingRuntimeEmitter

    buffer = _BufferingRuntimeEmitter()
    p = object()
    buffer.emit_mission_run_started(p)
    buffer.emit_next_step_issued(p)
    buffer.emit_next_step_auto_completed(p)
    buffer.emit_decision_input_requested(p)
    buffer.emit_decision_input_answered(p)
    buffer.emit_mission_run_completed(p)
    buffer.emit_significance_evaluated(p)
    buffer.emit_decision_timeout_expired(p)
    buffer.seed_from_snapshot(p)  # pass-through, not buffered
    assert buffer.call_count() == 8


def test_rich_hic_prompt_returns_run_now(monkeypatch: pytest.MonkeyPatch) -> None:
    from rich.prompt import Confirm
    from specify_cli.next.runtime_bridge import _rich_hic_prompt

    monkeypatch.setattr(Confirm, "ask", lambda *args, **kwargs: True)

    assert _rich_hic_prompt() == (True, None)


def test_rich_hic_prompt_requires_non_empty_skip_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rich.prompt import Confirm, Prompt
    from specify_cli.next.runtime_bridge import _rich_hic_prompt

    answers = iter(["", "  needs operator review  "])
    monkeypatch.setattr(Confirm, "ask", lambda *args, **kwargs: False)
    monkeypatch.setattr(Prompt, "ask", lambda *args, **kwargs: next(answers))

    assert _rich_hic_prompt() == (False, "needs operator review")


def test_resolve_mission_id_for_terminus_falls_back_on_missing_or_bad_meta(
    tmp_path: Path,
) -> None:
    from specify_cli.next.runtime_bridge import _resolve_mission_id_for_terminus

    feature_dir = tmp_path / "mission-slug"
    feature_dir.mkdir()

    assert _resolve_mission_id_for_terminus(feature_dir) == "mission-slug"

    (feature_dir / "meta.json").write_text("{not-json", encoding="utf-8")
    assert _resolve_mission_id_for_terminus(feature_dir) == "mission-slug"

    (feature_dir / "meta.json").write_text(json.dumps({"mission_id": "  "}), encoding="utf-8")
    assert _resolve_mission_id_for_terminus(feature_dir) == "mission-slug"

    (feature_dir / "meta.json").write_text(json.dumps({"mission_id": "01KQMISSION"}), encoding="utf-8")
    assert _resolve_mission_id_for_terminus(feature_dir) == "01KQMISSION"


# ---------------------------------------------------------------------------
# Real-bridge integration: decide_next_via_runtime + opt-in + gate block
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True, check=True)
    (path / "README.md").write_text("# test", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)


def _seed_wp_lane(feature_dir: Path, wp_id: str, lane: str) -> None:
    from specify_cli.status.store import append_event
    from specify_cli.status.models import StatusEvent, Lane

    canonical = {"doing": "in_progress"}.get(lane, lane)
    event = StatusEvent(
        event_id=f"test-{wp_id}-{canonical}",
        mission_slug=feature_dir.name,
        wp_id=wp_id,
        from_lane=Lane.PLANNED,
        to_lane=Lane(canonical),
        at="2026-01-01T00:00:00+00:00",
        actor="test",
        force=True,
        execution_mode="worktree",
    )
    append_event(feature_dir, event)


def _scaffold_opt_in_project(tmp_path: Path) -> tuple[Path, Path]:
    """Build a fully scaffolded project with the retrospective gate opted in.

    Charter ``mode: autonomous`` activates the gate. The mission has WP01 in
    ``done`` so the DAG can drive to terminal without a real implement
    cycle. ``meta.json`` carries a ULID mission_id so the bridge resolves
    it correctly.
    """
    repo_root = tmp_path / "project"
    repo_root.mkdir()
    _init_git_repo(repo_root)

    # .kittify with charter that activates the gate
    kittify = repo_root / ".kittify"
    kittify.mkdir()
    charter_dir = kittify / "charter"
    charter_dir.mkdir()
    (charter_dir / "charter.md").write_text(
        "---\nmode: autonomous\n---\n# Charter\n",
        encoding="utf-8",
    )

    feature_slug = "test-mission-01KQ6YEG"
    feature_dir = repo_root / "kitty-specs" / feature_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": "01KQ6YEGT4YBZ3GZF7X680KQ3V",
                "mission_slug": feature_slug,
                "mission_type": "software-dev",
            }
        ),
        encoding="utf-8",
    )

    # CLI guard artifacts
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01.md").write_text(
        "---\nwork_package_id: WP01\nlane: done\ndependencies: []\ntitle: WP01\n---\n# WP01\n",
        encoding="utf-8",
    )
    _seed_wp_lane(feature_dir, "WP01", "done")
    write_single_lane_manifest(feature_dir, wp_ids=("WP01",))

    return repo_root, feature_dir


class _RecordingSyncEmitter:
    """Wraps the real SyncRuntimeEventEmitter to count emit_* calls.

    Used to assert that a gate-blocked terminal advance does NOT dispatch
    ``MissionRunCompleted`` to the sync layer (remote queues / SaaS).
    """

    def __init__(self, real_emitter: Any) -> None:
        self._real = real_emitter
        self.calls: list[tuple[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._real, name)
        if not callable(attr):
            return attr
        if not name.startswith("emit_"):
            return attr

        def _recorded(payload: Any, *args: Any, **kwargs: Any) -> Any:
            self.calls.append((name, payload))
            return attr(payload, *args, **kwargs)

        return _recorded


def test_legacy_path_blocks_and_rolls_back_on_terminal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Driving the real bridge to terminal with opt-in must:

    1. return ``Decision(blocked, reason="Retrospective gate refused...")``,
    2. NOT dispatch ``emit_mission_run_completed`` to the sync emitter,
    3. NOT leave a ``MissionRunCompleted`` line in run.events.jsonl,
    4. roll back state.json so it does not say all-completed.
    """
    from specify_cli.next import runtime_bridge as bridge
    from specify_cli.next._internal_runtime.events import NullEmitter

    repo_root, feature_dir = _scaffold_opt_in_project(tmp_path)

    class _LocalOnlyEmitter(NullEmitter):
        def seed_from_snapshot(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    # Patch the SyncRuntimeEventEmitter factory to a local recorder. The bridge
    # will use the wrapper everywhere; we'll inspect its call list at the end.
    recorders: list[_RecordingSyncEmitter] = []

    def _wrapped_for_feature(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        recorder = _RecordingSyncEmitter(_LocalOnlyEmitter())
        recorders.append(recorder)
        return recorder

    monkeypatch.setattr(bridge.SyncRuntimeEventEmitter, "for_feature", _wrapped_for_feature)

    decision = None
    for _ in range(40):
        decision = bridge.decide_next_via_runtime("test-agent", "test-mission-01KQ6YEG", "success", repo_root)
        if decision.kind == DecisionKind.blocked and "Retrospective gate" in (decision.reason or ""):
            break
        if decision.kind == DecisionKind.terminal:
            pytest.fail("Bridge reached terminal without the retrospective gate firing — the wire-in is not active or rollback failed.")

    assert decision is not None
    assert decision.kind == DecisionKind.blocked, f"Expected blocked decision after gate; got {decision.kind} ({decision.reason!r})"
    assert "Retrospective gate" in (decision.reason or ""), f"Expected retrospective-gate reason; got {decision.reason!r}"

    # Sync emitter MUST NOT have dispatched MissionRunCompleted.
    completed_dispatches = [(name, payload) for recorder in recorders for (name, payload) in recorder.calls if name == "emit_mission_run_completed"]
    assert completed_dispatches == [], f"MissionRunCompleted was dispatched to the sync emitter despite the gate blocking; calls observed: {completed_dispatches!r}"

    # run.events.jsonl must not carry MissionRunCompleted from the blocked attempt.
    feature_runs = repo_root / ".kittify" / "runtime" / "feature-runs.json"
    assert feature_runs.exists()
    runs_index = json.loads(feature_runs.read_text(encoding="utf-8"))
    run_dir = Path(runs_index["test-mission-01KQ6YEG"]["run_dir"])
    events_path = run_dir / "run.events.jsonl"
    assert events_path.exists()
    events_text = events_path.read_text(encoding="utf-8")
    assert "MissionRunCompleted" not in events_text, "run.events.jsonl carries MissionRunCompleted after gate block; rollback did not truncate properly"

    # state.json must not be in a fully-completed terminal shape.
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert state.get("issued_step_id") is not None, (
        "state.json shows issued_step_id=None (terminal-ish) after gate block; rollback did not restore the pre-call snapshot"
    )


def test_legacy_path_blocks_when_prestate_cannot_be_captured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.next import runtime_bridge as bridge

    repo_root, _feature_dir = _scaffold_opt_in_project(tmp_path)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "state.json").mkdir()

    monkeypatch.setattr(
        bridge.SyncRuntimeEventEmitter,
        "for_feature",
        lambda **kwargs: SimpleNamespace(seed_from_snapshot=lambda snapshot: None),
    )
    monkeypatch.setattr(
        bridge,
        "get_or_start_run",
        lambda *args, **kwargs: SimpleNamespace(run_dir=run_dir, run_id="run-1"),
    )

    decision = bridge.decide_next_via_runtime("test-agent", "test-mission-01KQ6YEG", "success", repo_root)

    assert decision.kind == DecisionKind.blocked
    assert "Cannot read run state.json" in (decision.reason or "")


def test_legacy_path_discards_buffer_when_runtime_engine_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.next import runtime_bridge as bridge

    repo_root, _feature_dir = _scaffold_opt_in_project(tmp_path)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "state.json").write_text("{}", encoding="utf-8")
    (run_dir / "run.events.jsonl").write_text("", encoding="utf-8")

    monkeypatch.setattr(
        bridge.SyncRuntimeEventEmitter,
        "for_feature",
        lambda **kwargs: SimpleNamespace(seed_from_snapshot=lambda snapshot: None),
    )
    monkeypatch.setattr(
        bridge,
        "get_or_start_run",
        lambda *args, **kwargs: SimpleNamespace(run_dir=run_dir, run_id="run-1"),
    )

    def _raise_runtime_error(*args: Any, **kwargs: Any) -> Any:
        emitter = kwargs["emitter"]
        emitter.emit_mission_run_completed(object())
        raise RuntimeError("engine failed")

    monkeypatch.setattr(bridge, "runtime_next_step", _raise_runtime_error)

    decision = bridge.decide_next_via_runtime("test-agent", "test-mission-01KQ6YEG", "success", repo_root)

    assert decision.kind == DecisionKind.blocked
    assert decision.reason == "Runtime engine error: engine failed"


def test_legacy_path_logs_rollback_failures_after_gate_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    from specify_cli.next import runtime_bridge as bridge
    from specify_cli.next._internal_runtime import retrospective_terminus
    from specify_cli.next._internal_runtime.schema import NextDecision

    repo_root, _feature_dir = _scaffold_opt_in_project(tmp_path)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    state_path = run_dir / "state.json"
    events_path = run_dir / "run.events.jsonl"
    state_path.write_text("pre-state", encoding="utf-8")
    events_path.write_text("pre-events", encoding="utf-8")

    monkeypatch.setattr(
        bridge.SyncRuntimeEventEmitter,
        "for_feature",
        lambda **kwargs: SimpleNamespace(seed_from_snapshot=lambda snapshot: None),
    )
    monkeypatch.setattr(
        bridge,
        "get_or_start_run",
        lambda *args, **kwargs: SimpleNamespace(run_dir=run_dir, run_id="run-1"),
    )
    monkeypatch.setattr(
        bridge,
        "runtime_next_step",
        lambda *args, **kwargs: NextDecision(kind="terminal", run_id="run-1", mission_key="software-dev"),
    )
    monkeypatch.setattr(
        retrospective_terminus,
        "run_terminus",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("gate blocked")),
    )

    original_write_bytes = Path.write_bytes
    original_open = open

    def _write_bytes(path: Path, data: bytes) -> int:
        if path == state_path:
            raise OSError("state restore failed")
        return original_write_bytes(path, data)

    def _open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if Path(file) == events_path and mode == "r+b":
            raise OSError("events truncate failed")
        return original_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "write_bytes", _write_bytes)
    monkeypatch.setattr("builtins.open", _open)

    decision = bridge.decide_next_via_runtime("test-agent", "test-mission-01KQ6YEG", "success", repo_root)

    assert decision.kind == DecisionKind.blocked
    assert decision.reason == "Retrospective gate refused completion: gate blocked"
    assert "rollback of state.json failed after gate block" in caplog.text
    assert "rollback of run.events.jsonl failed after gate block" in caplog.text
