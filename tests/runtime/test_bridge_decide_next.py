"""Phase-split unit tests for ``decide_next_via_runtime`` (#2531 WP09, T033, FR-010).

``decide_next_via_runtime`` is rewritten as a linear four-phase early-return
chain over the frozen ``DecideNextContext`` dataclass: bootstrap ->
dependency-gate -> composition-dispatch -> decision-materialize. This module
exercises each phase function directly, against stubbed collaborators
(FR-006), plus a structural complexity guard proving the residual and every
phase helper stay <=15 (the WP09 headline: the module's last ``# noqa:
C901`` is gone).

End-to-end behavior (side-effect order/content across the 29 ``Decision``
sites) stays proven by the WP01 parity oracle (``test_bridge_parity.py``)
and the WP02 compat guard (``test_bridge_compat_surface.py``); this file is
the phase-local unit layer FR-006 asks for, mirroring the
``test_bridge_decision_builder.py`` / ``test_bridge_composition.py``
stub-based pattern from WP07/WP08.
"""

from __future__ import annotations

import tokenize
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import ast

import pytest

from runtime.next import runtime_bridge as rb
from runtime.next import runtime_bridge_cores as _cores
from runtime.next import runtime_bridge_engine as _engine_adapter
from runtime.next._internal_runtime import MissionRunRef
from runtime.next._internal_runtime.schema import NextDecision
from runtime.next.decision import Decision, DecisionKind
from charter.invocation_context import OperationalContext
from specify_cli.status import CanonicalStatusNotFoundError

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# 0. Shared fixtures / stubs
# ---------------------------------------------------------------------------

_RUNTIME_BRIDGE_PATH = Path(__file__).resolve().parents[2] / "src" / "runtime" / "next" / "runtime_bridge.py"

# The residual entry point plus every WP09 phase/sub-helper that composes it
# (FR-010) — the symbols the ceiling guard below must find and check.
_DN_SYMBOLS = (
    "decide_next_via_runtime",
    "_dn_bootstrap",
    "_dn_dependency_gate",
    "_dn_composition_blocked_decision",
    "_dn_composition_dispatch",
    "_dn_capture_pre_speculative_state",
    "_dn_rollback_buffered_run_state",
    "_dn_terminal_retrospective_gate",
    "_dn_decision_materialize",
)


def _make_run_ref(run_dir: Path) -> MissionRunRef:
    return MissionRunRef(run_id="run-042", run_dir=str(run_dir), mission_key="042-mission")


def _make_ctx(
    tmp_path: Path,
    *,
    result: str = "success",
    current_step_id: str | None = "implement",
    run_dir: Path | None = None,
) -> rb.DecideNextContext:
    """Build a ``DecideNextContext`` from cheap synthetic values for
    phase-local unit tests. ``sync_emitter``/``emitter_for_engine`` are
    opaque sentinels (``Any``) — the phases under test only forward them to
    stubbed collaborators, never call methods on them directly (except
    ``decision-materialize``'s own buffer-flush target, exercised with a
    real ``_BufferingRuntimeEmitter`` in its own tests below)."""
    feature_dir = tmp_path / "kitty-specs" / "042-mission"
    feature_dir.mkdir(parents=True, exist_ok=True)
    resolved_run_dir = run_dir if run_dir is not None else (tmp_path / "run")
    resolved_run_dir.mkdir(parents=True, exist_ok=True)
    return rb.DecideNextContext(
        agent="agent-x",
        mission_slug="042-mission",
        result=result,
        repo_root=tmp_path,
        feature_dir=feature_dir,
        now="2026-07-11T00:00:00+00:00",
        mission_type="software-dev",
        sync_emitter=cast(Any, object()),
        emitter_for_engine=cast(Any, object()),
        origin={"mission_tier": "built-in", "mission_path": "software-dev"},
        progress={"total_wps": 3},
        run_ref=_make_run_ref(resolved_run_dir),
        run_dir=resolved_run_dir,
        current_step_id=current_step_id,
    )


def _sentinel_decision(reason: str) -> Decision:
    """A realistic ``Decision`` test double built through the real WP07
    builder (not a bespoke fake shape)."""
    return rb._materialize_decision(
        _cores.DecisionEnvelope(
            kind=DecisionKind.terminal,
            agent="agent-x",
            mission_slug="042-mission",
            mission="software-dev",
            mission_state="done",
            timestamp="2026-07-11T00:00:00+00:00",
            reason=reason,
        )
    )


def _raising(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("this collaborator must not be called on this branch")


# ---------------------------------------------------------------------------
# 1. Structural ceiling guard (FR-004/FR-010 headline)
# ---------------------------------------------------------------------------


def _cyclomatic_complexity(func: ast.AST) -> int:
    """A small, dependency-free McCabe-style cyclomatic complexity count.

    Neither ``radon`` nor ``mccabe`` is a runtime dependency of this project
    (ruff's C901 rule is a Rust-native reimplementation — see
    ``pyproject.toml``'s ``[tool.ruff.lint.mccabe]``), so this counts the
    same decision points ruff/radon count: if/elif/ternary, for/while,
    except handlers, boolean operators (and/or), and comprehension ifs. Not
    required to be bit-identical to ruff/radon (WP09's actual acceptance run
    used both) — only to catch a regression above the WP09 ceiling in CI
    without an extra dependency.
    """
    complexity = 1
    for node in ast.walk(func):
        if isinstance(node, (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            complexity += 1 + len(node.ifs)
    return complexity


def test_residual_and_every_phase_helper_stay_at_or_under_complexity_ceiling() -> None:
    """FR-004/FR-010 — ``decide_next_via_runtime``'s residual and all four
    phase helpers (plus their WP09-local sub-helpers) must stay <=15,
    matching the repo's ruff/Sonar C901 ceiling
    (``pyproject.toml [tool.ruff.lint.mccabe] max-complexity = 15``)."""
    tree = ast.parse(_RUNTIME_BRIDGE_PATH.read_text())
    functions_by_name = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

    for name in _DN_SYMBOLS:
        assert name in functions_by_name, f"expected WP09 phase-split symbol {name!r} not found"
        cc = _cyclomatic_complexity(functions_by_name[name])
        assert cc <= 15, f"{name} has complexity {cc}, exceeds the WP09 ceiling of 15"


def test_no_noqa_c901_comment_remains_in_runtime_bridge() -> None:
    """The WP09 headline: the last ``# noqa: C901`` in the module (which sat
    on ``decide_next_via_runtime``) is removed — zero suppressions is the
    mission's whole point. Uses ``tokenize`` (not a plain substring search)
    so a docstring that merely *mentions* the retired suppression (see
    ``_check_requirement_mapping_ready``'s docstring) cannot produce a false
    positive."""
    source = _RUNTIME_BRIDGE_PATH.read_text()
    comment_tokens = [tok.string for tok in tokenize.generate_tokens(StringIO(source).readline) if tok.type == tokenize.COMMENT]
    offending = [c for c in comment_tokens if "noqa: C901" in c]
    assert offending == [], f"unexpected '# noqa: C901' comment(s) remain: {offending}"


# ---------------------------------------------------------------------------
# 2. decide_next_via_runtime — the phase-chain wiring itself (T032)
# ---------------------------------------------------------------------------


def test_decide_next_via_runtime_returns_bootstrap_early_decision_without_running_other_phases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    early = _sentinel_decision("bootstrap-early")
    monkeypatch.setattr(rb, "_dn_bootstrap", lambda agent, slug, result, repo_root: (None, early))
    monkeypatch.setattr(rb, "_dn_dependency_gate", _raising)
    monkeypatch.setattr(rb, "_dn_composition_dispatch", _raising)
    monkeypatch.setattr(rb, "_dn_decision_materialize", _raising)

    result = rb.decide_next_via_runtime("agent-x", "042-mission", "success", tmp_path)

    assert result is early


def test_decide_next_via_runtime_short_circuits_at_first_non_none_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path)
    monkeypatch.setattr(rb, "_dn_bootstrap", lambda agent, slug, result, repo_root: (ctx, None))

    call_order: list[str] = []

    def _dep_gate(c: rb.DecideNextContext) -> Decision | None:
        call_order.append("dependency_gate")
        return None

    sentinel = _sentinel_decision("composition-sentinel")

    def _composition(c: rb.DecideNextContext) -> Decision | None:
        call_order.append("composition_dispatch")
        return sentinel

    monkeypatch.setattr(rb, "_dn_dependency_gate", _dep_gate)
    monkeypatch.setattr(rb, "_dn_composition_dispatch", _composition)
    monkeypatch.setattr(rb, "_dn_decision_materialize", _raising)

    result = rb.decide_next_via_runtime("agent-x", "042-mission", "success", tmp_path)

    assert result is sentinel
    assert call_order == ["dependency_gate", "composition_dispatch"]


def test_decide_next_via_runtime_runs_decision_materialize_when_earlier_phases_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path)
    monkeypatch.setattr(rb, "_dn_bootstrap", lambda agent, slug, result, repo_root: (ctx, None))
    monkeypatch.setattr(rb, "_dn_dependency_gate", lambda c: None)
    monkeypatch.setattr(rb, "_dn_composition_dispatch", lambda c: None)

    sentinel = _sentinel_decision("materialized")
    monkeypatch.setattr(rb, "_dn_decision_materialize", lambda c: sentinel)

    result = rb.decide_next_via_runtime("agent-x", "042-mission", "success", tmp_path)

    assert result is sentinel


# ---------------------------------------------------------------------------
# 3. _dn_bootstrap
# ---------------------------------------------------------------------------


def test_bootstrap_returns_blocked_decision_when_feature_dir_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing_dir = tmp_path / "nope"
    monkeypatch.setattr(rb, "_resolve_runtime_feature_dir", lambda repo_root, slug: missing_dir)

    ctx, decision = rb._dn_bootstrap("agent-x", "999-missing", "success", tmp_path)

    assert ctx is None
    assert decision is not None
    assert decision.kind == DecisionKind.blocked
    assert decision.mission_slug == "999-missing"
    assert decision.reason == f"Feature directory not found: {missing_dir}"


def test_bootstrap_returns_blocked_decision_when_run_start_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feature_dir = tmp_path / "kitty-specs" / "042-mission"
    feature_dir.mkdir(parents=True)
    monkeypatch.setattr(rb, "_resolve_runtime_feature_dir", lambda repo_root, slug: feature_dir)
    monkeypatch.setattr(rb, "get_mission_type", lambda fd: "software-dev")
    monkeypatch.setattr(rb, "_wrap_with_decision_git_log", lambda emitter, slug, repo_root: emitter)

    class _FakeSyncEmitter:
        @staticmethod
        def for_feature(**_kw: Any) -> _FakeSyncEmitter:
            return _FakeSyncEmitter()

    monkeypatch.setattr(rb, "SyncRuntimeEventEmitter", _FakeSyncEmitter)

    def _raise_start(*_a: Any, **_kw: Any) -> MissionRunRef:
        raise RuntimeError("cannot start run")

    monkeypatch.setattr(rb, "get_or_start_run", _raise_start)

    ctx, decision = rb._dn_bootstrap("agent-x", "042-mission", "success", tmp_path)

    assert ctx is None
    assert decision is not None
    assert decision.kind == DecisionKind.blocked
    assert decision.reason == "Failed to start/load runtime run: cannot start run"


def test_bootstrap_builds_full_context_on_happy_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feature_dir = tmp_path / "kitty-specs" / "042-mission"
    feature_dir.mkdir(parents=True)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_ref = _make_run_ref(run_dir)

    class _FakeSyncEmitter:
        def __init__(self) -> None:
            self.seeded: list[Any] = []

        def seed_from_snapshot(self, snapshot: Any) -> None:
            self.seeded.append(snapshot)

    fake_emitter = _FakeSyncEmitter()

    class _FakeSyncEmitterClass:
        @staticmethod
        def for_feature(**_kw: Any) -> _FakeSyncEmitter:
            return fake_emitter

    wrapped_sentinel = object()

    monkeypatch.setattr(rb, "_resolve_runtime_feature_dir", lambda repo_root, slug: feature_dir)
    monkeypatch.setattr(rb, "get_mission_type", lambda fd: "software-dev")
    monkeypatch.setattr(rb, "SyncRuntimeEventEmitter", _FakeSyncEmitterClass)
    monkeypatch.setattr(rb, "_wrap_with_decision_git_log", lambda emitter, slug, repo_root: wrapped_sentinel)
    monkeypatch.setattr(
        rb, "get_or_start_run", lambda slug, repo_root, mission_type, *, emitter: run_ref
    )
    monkeypatch.setattr(
        _engine_adapter, "_read_snapshot", lambda rd: SimpleNamespace(issued_step_id="implement")
    )
    monkeypatch.setattr(rb, "_build_operational_context_for_decision", lambda **_kw: OperationalContext())

    def _raise_not_found(mission_type: str, repo_root: Path) -> Any:
        raise FileNotFoundError(f"no mission template for {mission_type}")

    monkeypatch.setattr("specify_cli.runtime.resolver.resolve_mission", _raise_not_found)

    ctx, decision = rb._dn_bootstrap("agent-x", "042-mission", "success", tmp_path)

    assert decision is None
    assert ctx is not None
    assert ctx.agent == "agent-x"
    assert ctx.mission_slug == "042-mission"
    assert ctx.result == "success"
    assert ctx.repo_root == tmp_path
    assert ctx.feature_dir == feature_dir
    assert ctx.mission_type == "software-dev"
    assert ctx.sync_emitter is fake_emitter
    assert ctx.emitter_for_engine is wrapped_sentinel
    assert ctx.origin == {"mission_tier": "unknown", "mission_path": "unknown"}
    assert ctx.run_ref == run_ref
    assert ctx.run_dir == run_dir
    assert ctx.current_step_id == "implement"
    assert fake_emitter.seeded and fake_emitter.seeded[0].issued_step_id == "implement"


def test_bootstrap_defaults_current_step_id_to_none_when_snapshot_read_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feature_dir = tmp_path / "kitty-specs" / "042-mission"
    feature_dir.mkdir(parents=True)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_ref = _make_run_ref(run_dir)

    class _FakeSyncEmitter:
        def seed_from_snapshot(self, snapshot: Any) -> None:
            raise AssertionError("must not be reached when the snapshot read itself fails")

        @staticmethod
        def for_feature(**_kw: Any) -> _FakeSyncEmitter:
            return _FakeSyncEmitter()

    monkeypatch.setattr(rb, "_resolve_runtime_feature_dir", lambda repo_root, slug: feature_dir)
    monkeypatch.setattr(rb, "get_mission_type", lambda fd: "software-dev")
    monkeypatch.setattr(rb, "SyncRuntimeEventEmitter", _FakeSyncEmitter)
    monkeypatch.setattr(rb, "_wrap_with_decision_git_log", lambda emitter, slug, repo_root: emitter)
    monkeypatch.setattr(
        rb, "get_or_start_run", lambda slug, repo_root, mission_type, *, emitter: run_ref
    )

    def _raise_snapshot(*_a: Any, **_kw: Any) -> Any:
        raise RuntimeError("state.json unreadable")

    monkeypatch.setattr(_engine_adapter, "_read_snapshot", _raise_snapshot)
    monkeypatch.setattr(rb, "_build_operational_context_for_decision", lambda **_kw: OperationalContext())

    ctx, decision = rb._dn_bootstrap("agent-x", "042-mission", "success", tmp_path)

    assert decision is None
    assert ctx is not None
    assert ctx.current_step_id is None


# ---------------------------------------------------------------------------
# 4. _dn_dependency_gate
# ---------------------------------------------------------------------------


def test_dependency_gate_returns_none_when_result_not_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = _make_ctx(tmp_path, result="failed")
    monkeypatch.setattr(rb, "_is_wp_iteration_step", _raising)
    monkeypatch.setattr(rb, "_check_cli_guards", _raising)

    assert rb._dn_dependency_gate(ctx) is None


def test_dependency_gate_returns_none_without_current_step(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = _make_ctx(tmp_path, current_step_id=None)
    monkeypatch.setattr(rb, "_is_wp_iteration_step", _raising)

    assert rb._dn_dependency_gate(ctx) is None


def test_dependency_gate_returns_blocked_decision_on_status_lookup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path, current_step_id="implement")
    monkeypatch.setattr(rb, "_is_wp_iteration_step", lambda step: True)

    def _raise(*_a: Any, **_kw: Any) -> bool:
        raise CanonicalStatusNotFoundError("no status file")

    monkeypatch.setattr(rb, "_should_advance_wp_step", _raise)

    decision = rb._dn_dependency_gate(ctx)

    assert decision is not None
    assert decision.kind == DecisionKind.blocked
    assert decision.reason == "no status file"
    assert decision.guard_failures == ["no status file"]


def test_dependency_gate_stays_in_step_when_wps_remain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = _make_ctx(tmp_path, current_step_id="implement")
    monkeypatch.setattr(rb, "_is_wp_iteration_step", lambda step: True)
    monkeypatch.setattr(rb, "_should_advance_wp_step", lambda step, fd: False)
    monkeypatch.setattr(rb, "_check_cli_guards", _raising)

    sentinel = _sentinel_decision("stay-in-step")
    captured: dict[str, Any] = {}

    def _fake_wp_iteration(*args: Any, **kw: Any) -> Decision:
        captured["kw"] = kw
        return sentinel

    monkeypatch.setattr(rb, "_build_wp_iteration_decision", _fake_wp_iteration)

    decision = rb._dn_dependency_gate(ctx)

    assert decision is sentinel
    assert "guard_failures" not in captured["kw"]


def test_dependency_gate_stays_in_step_with_guard_failures_on_advance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path, current_step_id="implement")
    monkeypatch.setattr(rb, "_is_wp_iteration_step", lambda step: True)
    monkeypatch.setattr(rb, "_should_advance_wp_step", lambda step, fd: True)
    monkeypatch.setattr(rb, "_check_cli_guards", lambda step, fd: ["missing artifact"])

    sentinel = _sentinel_decision("guard-blocked")
    captured: dict[str, Any] = {}

    def _fake_wp_iteration(*args: Any, **kw: Any) -> Decision:
        captured["kw"] = kw
        return sentinel

    monkeypatch.setattr(rb, "_build_wp_iteration_decision", _fake_wp_iteration)

    decision = rb._dn_dependency_gate(ctx)

    assert decision is sentinel
    assert captured["kw"]["guard_failures"] == ["missing artifact"]


def test_dependency_gate_falls_through_when_wp_step_advances_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path, current_step_id="implement")
    monkeypatch.setattr(rb, "_is_wp_iteration_step", lambda step: True)
    monkeypatch.setattr(rb, "_should_advance_wp_step", lambda step, fd: True)
    monkeypatch.setattr(rb, "_check_cli_guards", lambda step, fd: [])

    assert rb._dn_dependency_gate(ctx) is None


def test_dependency_gate_returns_step_decision_for_non_wp_guard_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path, current_step_id="specify")
    monkeypatch.setattr(rb, "_is_wp_iteration_step", lambda step: False)
    monkeypatch.setattr(rb, "_check_cli_guards", lambda step, fd: ["spec incomplete"])
    monkeypatch.setattr(rb, "_state_to_action", lambda step, slug, fd, root, mission: ("specify", None, None))
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("hello")
    monkeypatch.setattr(
        rb,
        "_build_prompt_or_error",
        lambda action, fd, slug, wp_id, agent, root, mission: (str(prompt_path), None),
    )

    decision = rb._dn_dependency_gate(ctx)

    assert decision is not None
    assert decision.kind == DecisionKind.step
    assert decision.guard_failures == ["spec incomplete"]
    assert decision.prompt_file == str(prompt_path)


def test_dependency_gate_falls_back_to_blocked_when_no_action_mapped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path, current_step_id="mystery_step")
    monkeypatch.setattr(rb, "_is_wp_iteration_step", lambda step: False)
    monkeypatch.setattr(rb, "_check_cli_guards", lambda step, fd: ["blocked"])
    monkeypatch.setattr(rb, "_state_to_action", lambda *a: (None, None, None))
    monkeypatch.setattr(rb, "_build_prompt_or_error", _raising)

    decision = rb._dn_dependency_gate(ctx)

    assert decision is not None
    # step_or_blocked (WP07) demotes an unresolvable prompt_file to kind=blocked.
    assert decision.kind == DecisionKind.blocked
    assert decision.reason == "no action mapped for step 'mystery_step'; cannot resolve prompt"


# ---------------------------------------------------------------------------
# 5. _dn_composition_blocked_decision / _dn_composition_dispatch
# ---------------------------------------------------------------------------


def test_composition_blocked_decision_builds_reason_and_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path, current_step_id="tasks_outline")
    monkeypatch.setattr(rb, "_state_to_action", lambda step, slug, fd, root, mission: ("tasks_outline", "WP01", "/work/x"))
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("hello")
    monkeypatch.setattr(
        rb, "_build_prompt_safe", lambda action, fd, slug, wp_id, agent, root, mission: str(prompt_path)
    )

    decision = rb._dn_composition_blocked_decision(ctx, "tasks_outline", ["guard failed"])

    assert decision.kind == DecisionKind.blocked
    assert decision.reason == "guard failed"
    assert decision.guard_failures == ["guard failed"]
    assert decision.action == "tasks_outline"
    assert decision.wp_id == "WP01"
    assert decision.workspace_path == "/work/x"
    assert decision.prompt_file == str(prompt_path)


def test_composition_blocked_decision_skips_prompt_build_when_action_unmapped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path)
    monkeypatch.setattr(rb, "_state_to_action", lambda *a: (None, None, None))
    monkeypatch.setattr(rb, "_build_prompt_safe", _raising)

    decision = rb._dn_composition_blocked_decision(ctx, "implement", ["guard failed"])

    assert decision.prompt_file is None
    assert decision.action is None


def test_composition_dispatch_returns_none_when_not_applicable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path)
    monkeypatch.setattr(rb, "_should_dispatch_via_composition", lambda *a, **kw: False)
    monkeypatch.setattr(rb, "_dispatch_via_composition", _raising)

    assert rb._dn_composition_dispatch(ctx) is None


def test_composition_dispatch_skips_selection_seam_when_result_not_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path, result="failed")
    monkeypatch.setattr(rb, "_should_dispatch_via_composition", _raising)

    assert rb._dn_composition_dispatch(ctx) is None


def test_composition_dispatch_returns_none_when_no_current_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path, current_step_id=None)
    monkeypatch.setattr(rb, "_should_dispatch_via_composition", _raising)

    assert rb._dn_composition_dispatch(ctx) is None


def test_composition_dispatch_returns_blocked_decision_on_guard_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path, current_step_id="tasks_outline")
    monkeypatch.setattr(rb, "_should_dispatch_via_composition", lambda *a, **kw: True)
    monkeypatch.setattr(rb, "_normalize_action_for_composition", lambda step: "tasks-outline")
    monkeypatch.setattr(rb, "_composition_dispatch_inputs", lambda **kw: (None, {"contract": True}))
    monkeypatch.setattr(rb, "_dispatch_via_composition", lambda **kw: ["composition guard failed"])
    monkeypatch.setattr(rb, "_state_to_action", lambda *a: (None, None, None))
    monkeypatch.setattr(rb, "_advance_run_state_after_composition", _raising)

    decision = rb._dn_composition_dispatch(ctx)

    assert decision is not None
    assert decision.kind == DecisionKind.blocked
    assert decision.reason == "composition guard failed"
    assert decision.guard_failures == ["composition guard failed"]


def test_composition_dispatch_advances_run_state_on_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path, current_step_id="tasks_outline")
    monkeypatch.setattr(rb, "_should_dispatch_via_composition", lambda *a, **kw: True)
    monkeypatch.setattr(rb, "_normalize_action_for_composition", lambda step: "tasks-outline")
    monkeypatch.setattr(rb, "_composition_dispatch_inputs", lambda **kw: (None, {"contract": True}))
    monkeypatch.setattr(rb, "_dispatch_via_composition", lambda **kw: [])

    sentinel = _sentinel_decision("advanced")
    captured_kwargs: dict[str, Any] = {}

    def _fake_advance(**kw: Any) -> Decision:
        captured_kwargs.update(kw)
        return sentinel

    monkeypatch.setattr(rb, "_advance_run_state_after_composition", _fake_advance)

    decision = rb._dn_composition_dispatch(ctx)

    assert decision is sentinel
    assert captured_kwargs["run_ref"] == ctx.run_ref
    assert captured_kwargs["sync_emitter"] is ctx.sync_emitter


def test_composition_dispatch_returns_blocked_decision_when_advance_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path, current_step_id="tasks_outline")
    monkeypatch.setattr(rb, "_should_dispatch_via_composition", lambda *a, **kw: True)
    monkeypatch.setattr(rb, "_normalize_action_for_composition", lambda step: "tasks-outline")
    monkeypatch.setattr(rb, "_composition_dispatch_inputs", lambda **kw: (None, {"contract": True}))
    monkeypatch.setattr(rb, "_dispatch_via_composition", lambda **kw: [])

    def _raise_advance(**_kw: Any) -> Decision:
        raise RuntimeError("advance boom")

    monkeypatch.setattr(rb, "_advance_run_state_after_composition", _raise_advance)

    decision = rb._dn_composition_dispatch(ctx)

    assert decision is not None
    assert decision.kind == DecisionKind.blocked
    assert "advance boom" in (decision.reason or "")
    assert "tasks-outline" in (decision.reason or "")


# ---------------------------------------------------------------------------
# 6. _dn_capture_pre_speculative_state / _dn_rollback_buffered_run_state
# ---------------------------------------------------------------------------


def test_capture_pre_speculative_state_reads_existing_files(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "state.json").write_bytes(b'{"a": 1}')
    (run_dir / "run.events.jsonl").write_bytes(b"event-1\nevent-2\n")

    captured = rb._dn_capture_pre_speculative_state(run_dir)

    assert captured == (b'{"a": 1}', len(b"event-1\nevent-2\n"))


def test_capture_pre_speculative_state_defaults_when_files_absent(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    captured = rb._dn_capture_pre_speculative_state(run_dir)

    assert captured == (None, 0)


def test_capture_pre_speculative_state_returns_none_on_os_error(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    # A directory in place of state.json makes .read_bytes() raise OSError.
    (run_dir / "state.json").mkdir()

    assert rb._dn_capture_pre_speculative_state(run_dir) is None


def test_rollback_buffered_run_state_restores_bytes_and_truncates_events(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "state.json").write_bytes(b'{"post": true}')
    (run_dir / "run.events.jsonl").write_bytes(b"event-1\nevent-2\n")

    rb._dn_rollback_buffered_run_state(run_dir, b'{"pre": true}', len(b"event-1\n"))

    assert (run_dir / "state.json").read_bytes() == b'{"pre": true}'
    assert (run_dir / "run.events.jsonl").read_bytes() == b"event-1\n"


def test_rollback_buffered_run_state_is_a_noop_when_nothing_was_captured(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    # No pre-existing files at all; both pre_* values are their "absent" sentinels.
    rb._dn_rollback_buffered_run_state(run_dir, None, None)

    assert not (run_dir / "state.json").exists()
    assert not (run_dir / "run.events.jsonl").exists()


# ---------------------------------------------------------------------------
# 7. _dn_decision_materialize (+ _dn_terminal_retrospective_gate)
# ---------------------------------------------------------------------------


def test_decision_materialize_returns_blocked_when_engine_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path)
    monkeypatch.setattr(rb, "_resolve_retrospective_policy_for_runtime", lambda repo_root: (None, {}, None))

    def _raise(*_a: Any, **_kw: Any) -> NextDecision:
        raise RuntimeError("engine boom")

    monkeypatch.setattr(rb, "runtime_next_step", _raise)

    decision = rb._dn_decision_materialize(ctx)

    assert decision.kind == DecisionKind.blocked
    assert decision.reason == "Runtime engine error: engine boom"


def test_decision_materialize_returns_blocked_when_pre_state_capture_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path)
    (ctx.run_dir / "state.json").mkdir()  # forces _dn_capture_pre_speculative_state -> None
    policy = SimpleNamespace(enabled=True, timing="before_completion", failure_policy="block")
    monkeypatch.setattr(rb, "_resolve_retrospective_policy_for_runtime", lambda repo_root: (policy, {}, None))
    monkeypatch.setattr(rb, "runtime_next_step", _raising)

    decision = rb._dn_decision_materialize(ctx)

    assert decision.kind == DecisionKind.blocked
    assert decision.reason is not None
    assert "Cannot read run state.json" in decision.reason


def test_decision_materialize_rolls_back_state_on_retrospective_gate_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path)
    state_path = ctx.run_dir / "state.json"
    events_path = ctx.run_dir / "run.events.jsonl"
    state_path.write_text('{"pre": true}')
    events_path.write_text("event-1\n")

    policy = SimpleNamespace(enabled=True, timing="before_completion", failure_policy="block")
    monkeypatch.setattr(rb, "_resolve_retrospective_policy_for_runtime", lambda repo_root: (policy, {}, None))

    def _fake_runtime_next_step(run_ref: Any, *, agent_id: str, result: str, emitter: Any) -> NextDecision:
        # Simulate the engine's speculative write before returning terminal —
        # this is exactly what the real engine would do to state.json /
        # run.events.jsonl during the advance the gate is about to refuse.
        state_path.write_text('{"post": true}')
        events_path.write_text("event-1\nevent-2\n")
        return NextDecision(kind="terminal", run_id="run-042", mission_key="042-mission")

    monkeypatch.setattr(rb, "runtime_next_step", _fake_runtime_next_step)

    def _raising_capture(**_kw: Any) -> None:
        raise RuntimeError("gate refused")

    monkeypatch.setattr(rb, "_run_retrospective_learning_capture", _raising_capture)
    monkeypatch.setattr(rb, "_resolve_mission_id_for_terminus", lambda feature_dir: "mission-id")

    decision = rb._dn_decision_materialize(ctx)

    assert decision.kind == DecisionKind.blocked
    assert decision.reason == "Retrospective gate refused completion: gate refused"
    assert state_path.read_text() == '{"pre": true}'
    assert events_path.read_bytes() == b"event-1\n"


def test_decision_materialize_flushes_buffer_and_materializes_after_gate_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path)
    policy = SimpleNamespace(enabled=True, timing="before_completion", failure_policy="block")
    monkeypatch.setattr(rb, "_resolve_retrospective_policy_for_runtime", lambda repo_root: (policy, {}, None))

    runtime_decision = NextDecision(kind="terminal", run_id="run-042", mission_key="042-mission")
    monkeypatch.setattr(rb, "runtime_next_step", lambda run_ref, *, agent_id, result, emitter: runtime_decision)
    monkeypatch.setattr(rb, "_run_retrospective_learning_capture", lambda **kw: None)
    monkeypatch.setattr(rb, "_resolve_mission_id_for_terminus", lambda feature_dir: "mission-id")

    sentinel = _sentinel_decision("terminal-sentinel")
    calls: list[tuple[Any, ...]] = []

    def _fake_map(*args: Any) -> Decision:
        calls.append(args)
        return sentinel

    monkeypatch.setattr(rb, "_map_runtime_decision", _fake_map)

    result = rb._dn_decision_materialize(ctx)

    assert result is sentinel
    assert calls == [
        (
            runtime_decision,
            ctx.agent,
            ctx.mission_slug,
            ctx.mission_type,
            ctx.repo_root,
            ctx.feature_dir,
            ctx.now,
            ctx.progress,
            ctx.origin,
        )
    ]


def test_decision_materialize_fires_non_blocking_retrospective_after_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path)
    # enabled + NOT before_completion/block -> retrospective_enabled True,
    # block_on_retrospective False (real _retrospective_blocks_completion).
    policy = SimpleNamespace(enabled=True, timing="after_completion", failure_policy="best_effort")
    monkeypatch.setattr(rb, "_resolve_retrospective_policy_for_runtime", lambda repo_root: (policy, {}, None))

    runtime_decision = NextDecision(kind="terminal", run_id="run-042", mission_key="042-mission")
    monkeypatch.setattr(rb, "runtime_next_step", lambda run_ref, *, agent_id, result, emitter: runtime_decision)
    monkeypatch.setattr(rb, "_resolve_mission_id_for_terminus", lambda feature_dir: "mission-id")

    calls: list[dict[str, Any]] = []

    def _fake_capture(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(rb, "_run_retrospective_learning_capture", _fake_capture)

    sentinel = _sentinel_decision("fire-and-forget")
    monkeypatch.setattr(rb, "_map_runtime_decision", lambda *a: sentinel)

    result = rb._dn_decision_materialize(ctx)

    assert result is sentinel
    assert calls == [
        {
            "mission_id": "mission-id",
            "mission_slug": ctx.mission_slug,
            "feature_dir": ctx.feature_dir,
            "repo_root": ctx.repo_root,
            "block_on_failure": False,
        }
    ]


def test_decision_materialize_skips_retrospective_for_non_terminal_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(tmp_path)
    policy = SimpleNamespace(enabled=True, timing="after_completion", failure_policy="best_effort")
    monkeypatch.setattr(rb, "_resolve_retrospective_policy_for_runtime", lambda repo_root: (policy, {}, None))

    runtime_decision = NextDecision(kind="step", run_id="run-042", mission_key="042-mission", step_id="implement")
    monkeypatch.setattr(rb, "runtime_next_step", lambda run_ref, *, agent_id, result, emitter: runtime_decision)
    monkeypatch.setattr(rb, "_run_retrospective_learning_capture", _raising)
    monkeypatch.setattr(rb, "_resolve_mission_id_for_terminus", _raising)

    sentinel = _sentinel_decision("non-terminal")
    monkeypatch.setattr(rb, "_map_runtime_decision", lambda *a: sentinel)

    result = rb._dn_decision_materialize(ctx)

    assert result is sentinel
