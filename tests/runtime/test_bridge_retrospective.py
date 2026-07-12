"""Retrospective-seam tests for ``runtime_bridge_retrospective`` (#2531 WP04, FR-006).

Three independent concerns:

1. **Architecture boundary** (``test_only_seam_imports_retrospective_package``)
   — asserts ``runtime_bridge.py`` no longer imports ``specify_cli.retrospective.*``
   directly; the seam module is the sole owner of that import surface (mirrors
   the WP03 engine-adapter's FR-013 boundary, scoped to this WP's cluster).
   A non-vacuousness check
   (``test_seam_defines_every_relocated_symbol``) guards against the "residual
   doesn't import it" assertion passing for the wrong reason (nobody needing
   the cluster at all).

2. **Focused unit tests (FR-006)** against the moved cluster in isolation —
   stubbing ``specify_cli.retrospective.*`` at its source (never the real
   generator/writer/lifecycle_events), mirroring the pattern
   ``tests/runtime/test_bridge_compat_surface.py``'s scenario builders already
   use. These pin the behavior-preserving move (C-001): identical branching,
   identical retrospective ``Confirm.ask`` gate semantics.

3. **Retrospective-pair live-lookup regression** (the WP04-specific risk
   flagged in ``research.md`` §Compat and ``contracts/compat-surface.md``):
   now that the whole cluster lives together in one seam module, an
   intra-cluster call between two compat-guarded symbols (e.g.
   ``_run_retrospective_learning_capture`` -> ``_build_retrospective_facilitator_callback``;
   the built facilitator -> ``_classify_and_emit_failure`` -> ``_classify_exc``/
   ``_remediation_hint``) MUST resolve via a live lookup back through
   ``runtime_bridge`` (never a bare intra-module call), or a
   ``monkeypatch.setattr(runtime_bridge, "<name>", …)`` becomes a no-op
   (false-green). ``test_*_uses_live_lookup_for_*`` pin this by patching the
   callee on ``runtime_bridge`` and asserting the (unpatched) caller in the
   seam still observes it.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

from runtime.next import runtime_bridge_retrospective as retro

# ---------------------------------------------------------------------------
# 1. Architecture boundary (non-vacuousness-checked)
# ---------------------------------------------------------------------------

_RUNTIME_BRIDGE_PATH = Path(__file__).resolve().parents[2] / "src" / "runtime" / "next" / "runtime_bridge.py"

# The 9 compat-guarded symbols (contracts/compat-surface.md) that MUST stay
# natively defined in runtime_bridge.py as thin delegates (never a plain
# re-export) -- see runtime_bridge_retrospective's module docstring for why.
_COMPAT_GUARDED_NAMES = frozenset(
    {
        "_BufferingRuntimeEmitter",
        "_rich_hic_prompt",
        "_resolve_mission_id_for_terminus",
        "_build_retrospective_facilitator_callback",
        "_resolve_retrospective_policy_for_runtime",
        "_run_retrospective_learning_capture",
        "_classify_exc",
        "_remediation_hint",
        "_classify_and_emit_failure",
    }
)

# The one symbol in the cluster that is NOT part of the WP02 compat guard's
# tracked inventory (nothing patches it) -- re-exported as a plain
# module-level import instead of a thin delegate. Kept out of the frozen
# guard's grep-derived inventory deliberately (see test_bridge_engine.py's
# analogous note on this exact symbol).
_PLAIN_REEXPORT_NAME = "_retrospective_blocks_completion"


@pytest.mark.architectural
def test_only_seam_imports_retrospective_package() -> None:
    """``runtime_bridge.py`` must not import ``specify_cli.retrospective.*``
    directly any more -- the retrospective seam is the sole owner of that
    surface now that the cluster moved (mirrors the WP03 FR-013 boundary
    pattern for the engine adapter)."""
    tree = ast.parse(_RUNTIME_BRIDGE_PATH.read_text(encoding="utf-8"), filename=str(_RUNTIME_BRIDGE_PATH))
    offenders = [
        f"line {node.lineno}: from {node.module} import ..."
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None and node.module.startswith("specify_cli.retrospective")
    ]
    assert not offenders, "runtime_bridge.py imports specify_cli.retrospective.* directly:\n" + "\n".join(offenders)


def test_seam_defines_every_relocated_symbol() -> None:
    """Non-vacuousness check: the seam must actually define all 10 relocated
    names, or the "residual doesn't import retrospective.*" assertion above
    would pass for the wrong reason (nobody needing the cluster at all)."""
    for name in sorted(_COMPAT_GUARDED_NAMES | {_PLAIN_REEXPORT_NAME}):
        assert hasattr(retro, name), f"seam is missing relocated symbol {name!r}"


def test_runtime_bridge_keeps_native_thin_delegates_for_compat_guarded_names() -> None:
    """Every compat-guarded symbol must stay a NATIVE ``def``/``class``
    statement in runtime_bridge.py (a thin delegate), never a plain
    ``import`` alias -- otherwise the WP02 compat guard's hardcoded
    identity/relocated-symbol baseline
    (``test_guard_b_identity_reexport_for_relocated_symbols``) trips."""
    from runtime.next import runtime_bridge as rb

    for name in sorted(_COMPAT_GUARDED_NAMES):
        obj = getattr(rb, name)
        assert obj.__module__ == rb.__name__, (
            f"{name!r} on runtime_bridge is NOT natively defined there "
            f"(__module__={obj.__module__!r}) -- it must be a native thin "
            "delegate, not a plain re-export, or guard B's hardcoded "
            "relocated-symbol baseline will fail."
        )


# ---------------------------------------------------------------------------
# 2a. _BufferingRuntimeEmitter
# ---------------------------------------------------------------------------


def test_buffering_runtime_emitter_records_and_flushes_in_order() -> None:
    buffer = retro._BufferingRuntimeEmitter()
    assert buffer.call_count() == 0

    p1, p2 = object(), object()
    buffer.emit_mission_run_started(p1)
    buffer.emit_next_step_issued(p2)
    buffer.seed_from_snapshot(object())  # pass-through, never buffered
    assert buffer.call_count() == 2

    class _Target:
        def __init__(self) -> None:
            self.seen: list[tuple[str, Any]] = []

        def emit_mission_run_started(self, payload: Any) -> None:
            self.seen.append(("emit_mission_run_started", payload))

        def emit_next_step_issued(self, payload: Any) -> None:
            self.seen.append(("emit_next_step_issued", payload))

    target = _Target()
    buffer.flush(target)
    assert target.seen == [("emit_mission_run_started", p1), ("emit_next_step_issued", p2)]
    assert buffer.call_count() == 0  # cleared after flush

    # Re-flush is a no-op (single one-shot replay).
    target2 = _Target()
    buffer.flush(target2)
    assert target2.seen == []


def test_buffering_runtime_emitter_discard_drops_without_replay() -> None:
    buffer = retro._BufferingRuntimeEmitter()
    buffer.emit_mission_run_completed(object())
    assert buffer.call_count() == 1
    buffer.discard()
    assert buffer.call_count() == 0

    class _Target:
        def __init__(self) -> None:
            self.called = False

        def emit_mission_run_completed(self, payload: Any) -> None:
            self.called = True

    target = _Target()
    buffer.flush(target)  # already flushed (discard sets the flag) -> no-op
    assert target.called is False


def test_buffering_runtime_emitter_flush_skips_unknown_target_methods() -> None:
    buffer = retro._BufferingRuntimeEmitter()
    buffer.emit_significance_evaluated(object())
    buffer.emit_decision_timeout_expired(object())

    class _BareTarget:
        pass

    # Target lacks both emit_* methods -- flush must not raise.
    buffer.flush(_BareTarget())
    assert buffer.call_count() == 0


# ---------------------------------------------------------------------------
# 2b. _rich_hic_prompt
# ---------------------------------------------------------------------------


def test_rich_hic_prompt_returns_run_now(monkeypatch: pytest.MonkeyPatch) -> None:
    from rich.prompt import Confirm

    monkeypatch.setattr(Confirm, "ask", lambda *args, **kwargs: True)
    assert retro._rich_hic_prompt() == (True, None)


def test_rich_hic_prompt_requires_non_empty_skip_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    from rich.prompt import Confirm, Prompt

    answers = iter(["", "  needs operator review  "])
    monkeypatch.setattr(Confirm, "ask", lambda *args, **kwargs: False)
    monkeypatch.setattr(Prompt, "ask", lambda *args, **kwargs: next(answers))
    assert retro._rich_hic_prompt() == (False, "needs operator review")


# ---------------------------------------------------------------------------
# 2c. _resolve_mission_id_for_terminus
# ---------------------------------------------------------------------------


def test_resolve_mission_id_for_terminus_falls_back_on_missing_or_bad_meta(tmp_path: Path) -> None:
    feature_dir = tmp_path / "mission-slug"
    feature_dir.mkdir()

    assert retro._resolve_mission_id_for_terminus(feature_dir) == "mission-slug"

    (feature_dir / "meta.json").write_text("{not-json", encoding="utf-8")
    assert retro._resolve_mission_id_for_terminus(feature_dir) == "mission-slug"

    (feature_dir / "meta.json").write_text(json.dumps({"mission_id": "  "}), encoding="utf-8")
    assert retro._resolve_mission_id_for_terminus(feature_dir) == "mission-slug"

    (feature_dir / "meta.json").write_text(json.dumps({"mission_id": "01KQMISSION"}), encoding="utf-8")
    assert retro._resolve_mission_id_for_terminus(feature_dir) == "01KQMISSION"


# ---------------------------------------------------------------------------
# 2d. _resolve_retrospective_policy_for_runtime / _retrospective_blocks_completion
# ---------------------------------------------------------------------------


def test_resolve_retrospective_policy_for_runtime_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sentinel_policy = object()
    monkeypatch.setattr(
        "specify_cli.retrospective.policy.resolve_policy",
        lambda repo_root: (sentinel_policy, {"enabled": "charter"}),
    )
    policy, source_map, error = retro._resolve_retrospective_policy_for_runtime(tmp_path)
    assert policy is sentinel_policy
    assert source_map == {"enabled": "charter"}
    assert error is None


def test_resolve_retrospective_policy_for_runtime_falls_back_to_default_on_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from specify_cli.retrospective.policy import default_policy

    boom = RuntimeError("malformed policy")

    def _raise(repo_root: Path) -> Any:
        raise boom

    monkeypatch.setattr("specify_cli.retrospective.policy.resolve_policy", _raise)
    policy, source_map, error = retro._resolve_retrospective_policy_for_runtime(tmp_path)
    assert policy == default_policy()
    assert source_map == {
        "enabled": "<resolution_error>",
        "timing": "<resolution_error>",
        "failure_policy": "<resolution_error>",
    }
    assert error is boom


@pytest.mark.parametrize(
    "enabled,timing,failure_policy,expected",
    [
        (True, "before_completion", "block", True),
        (True, "before_completion", "warn", False),
        (True, "post_completion", "block", False),
        (False, "before_completion", "block", False),
    ],
)
def test_retrospective_blocks_completion_matrix(
    enabled: bool, timing: str, failure_policy: str, expected: bool
) -> None:
    class _Policy:
        pass

    policy = _Policy()
    policy.enabled = enabled  # type: ignore[attr-defined]
    policy.timing = timing  # type: ignore[attr-defined]
    policy.failure_policy = failure_policy  # type: ignore[attr-defined]
    assert retro._retrospective_blocks_completion(policy) is expected


# ---------------------------------------------------------------------------
# 2e. _classify_exc / _remediation_hint
# ---------------------------------------------------------------------------


def test_classify_exc_branches() -> None:
    from specify_cli.retrospective.writer import RecordExistsError

    assert retro._classify_exc(RecordExistsError("already there")) == "other"
    assert retro._classify_exc(FileNotFoundError("missing")) == "missing_artifacts"
    assert retro._classify_exc(IsADirectoryError("is a dir")) == "missing_artifacts"
    assert retro._classify_exc(RuntimeError("boom")) == "generator_exception"


def test_remediation_hint_branches() -> None:
    from specify_cli.retrospective.writer import RecordExistsError

    assert retro._remediation_hint(RecordExistsError("x"), {}) == "Re-run with --overwrite to replace the existing record."
    assert "normalize-lifecycle" in (retro._remediation_hint(FileNotFoundError("missing"), {}) or "")
    hint = retro._remediation_hint(RuntimeError("oops"), {"enabled": "charter.yaml", "timing": "config.yaml"})
    assert hint == "Check policy configuration at: charter.yaml, config.yaml"
    assert retro._remediation_hint(RuntimeError("oops"), {}) == "Check policy configuration at: unknown"


# ---------------------------------------------------------------------------
# 2f/3. _classify_and_emit_failure -- behavior + retrospective-pair live lookup
# ---------------------------------------------------------------------------


def test_classify_and_emit_failure_calls_emit_capture_failed_with_classified_fields(tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def _fake_emit_capture_failed(**kwargs: Any) -> None:
        captured.update(kwargs)

    retro._classify_and_emit_failure(
        mission_id="mission-1",
        mission_slug="slug-1",
        repo_root=tmp_path,
        exc=FileNotFoundError("boom"),
        source_map={"enabled": "charter.yaml"},
        provenance_kind="runtime_post_completion",
        emit_capture_failed=_fake_emit_capture_failed,
    )

    assert captured["mission_id"] == "mission-1"
    assert captured["failure_category"] == "missing_artifacts"
    assert captured["remediation_hint"] == "Run `spec-kitty migrate normalize-lifecycle` to repair missing artifacts."
    assert captured["policy_source"] == {"enabled": "charter.yaml"}


def test_classify_and_emit_failure_swallows_emit_failure(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    def _raising_emit(**_kwargs: Any) -> None:
        raise RuntimeError("emit backend down")

    # Must not raise -- the original exception (classified) already won; a
    # secondary emit failure is logged, never propagated.
    retro._classify_and_emit_failure(
        mission_id="mission-1",
        mission_slug="slug-1",
        repo_root=tmp_path,
        exc=RuntimeError("original"),
        source_map={},
        provenance_kind="runtime_post_completion",
        emit_capture_failed=_raising_emit,
    )


def test_classify_and_emit_failure_uses_live_lookup_for_classify_and_hint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Retrospective-pair risk regression: ``_classify_and_emit_failure`` must
    resolve ``_classify_exc``/``_remediation_hint`` via a live lookup through
    ``runtime_bridge`` -- a bare intra-module call to this module's own
    functions would silently bypass a patch applied to
    ``runtime_bridge.<name>`` (the exact false-green mechanism
    contracts/compat-surface.md warns about)."""
    from runtime.next import runtime_bridge as rb

    calls: list[str] = []

    def _spy_classify(exc: Exception) -> str:
        calls.append("classify")
        return "generator_exception"

    def _spy_hint(exc: Exception, source_map: dict[str, str]) -> str:
        calls.append("hint")
        return "patched-hint"

    monkeypatch.setattr(rb, "_classify_exc", _spy_classify)
    monkeypatch.setattr(rb, "_remediation_hint", _spy_hint)

    captured: dict[str, Any] = {}
    retro._classify_and_emit_failure(
        mission_id="mission-1",
        mission_slug="slug-1",
        repo_root=tmp_path,
        exc=RuntimeError("boom"),
        source_map={},
        provenance_kind="runtime_post_completion",
        emit_capture_failed=lambda **kwargs: captured.update(kwargs),
    )

    assert calls == ["classify", "hint"]
    assert captured["failure_category"] == "generator_exception"
    assert captured["remediation_hint"] == "patched-hint"


# ---------------------------------------------------------------------------
# 2g/3. _run_retrospective_learning_capture -- behavior + live lookup
# ---------------------------------------------------------------------------


def test_run_retrospective_learning_capture_uses_live_lookup_for_facilitator_builder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Retrospective-pair risk regression: the (unpatched, real)
    ``_run_retrospective_learning_capture`` must invoke
    ``_build_retrospective_facilitator_callback`` via a live lookup through
    ``runtime_bridge`` -- see module docstring."""
    from runtime.next import runtime_bridge as rb

    build_calls: list[dict[str, Any]] = []
    facilitator_calls: list[dict[str, Any]] = []

    def _fake_builder(mission_slug: str, repo_root: Path, provenance_kind: str = "runtime_post_completion") -> Any:
        build_calls.append({"mission_slug": mission_slug, "provenance_kind": provenance_kind})

        def _facilitator(*, mission_id: str, feature_dir: Path, repo_root: Path, **_kw: Any) -> None:
            facilitator_calls.append({"mission_id": mission_id})

        return _facilitator

    monkeypatch.setattr(rb, "_build_retrospective_facilitator_callback", _fake_builder)

    retro._run_retrospective_learning_capture(
        mission_id="mission-9",
        mission_slug="slug-9",
        feature_dir=tmp_path,
        repo_root=tmp_path,
        block_on_failure=False,
    )

    assert build_calls == [{"mission_slug": "slug-9", "provenance_kind": "runtime_post_completion"}]
    assert facilitator_calls == [{"mission_id": "mission-9"}]


def test_run_retrospective_learning_capture_swallows_failure_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from runtime.next import runtime_bridge as rb

    def _raising_callback(*, mission_id: str, feature_dir: Path, repo_root: Path, **_kw: Any) -> None:
        raise RuntimeError("generator exploded")

    monkeypatch.setattr(rb, "_build_retrospective_facilitator_callback", lambda **_kw: _raising_callback)

    # Must not raise -- best-effort default (block_on_failure=False).
    retro._run_retrospective_learning_capture(
        mission_id="m",
        mission_slug="s",
        feature_dir=tmp_path,
        repo_root=tmp_path,
        block_on_failure=False,
    )


def test_run_retrospective_learning_capture_reraises_when_blocking(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from runtime.next import runtime_bridge as rb

    def _raising_callback(*, mission_id: str, feature_dir: Path, repo_root: Path, **_kw: Any) -> None:
        raise RuntimeError("strict gate failure")

    monkeypatch.setattr(rb, "_build_retrospective_facilitator_callback", lambda **_kw: _raising_callback)

    with pytest.raises(RuntimeError, match="strict gate failure"):
        retro._run_retrospective_learning_capture(
            mission_id="m",
            mission_slug="s",
            feature_dir=tmp_path,
            repo_root=tmp_path,
            block_on_failure=True,
        )


# ---------------------------------------------------------------------------
# 2h/3. _build_retrospective_facilitator_callback / _facilitator -- behavior +
# live lookup to _classify_and_emit_failure
# ---------------------------------------------------------------------------


def test_facilitator_short_circuits_when_policy_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class _DisabledPolicy:
        enabled = False

    monkeypatch.setattr(
        "specify_cli.retrospective.policy.resolve_policy",
        lambda repo_root: (_DisabledPolicy(), {}),
    )
    callback = retro._build_retrospective_facilitator_callback("slug-1", tmp_path)
    result = callback(mission_id="mission-1", feature_dir=tmp_path, repo_root=tmp_path)
    assert result is None


def test_facilitator_happy_path_writes_and_emits(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class _EnabledPolicy:
        enabled = True

    sentinel_record = object()
    write_calls: list[Any] = []
    emit_calls: list[Any] = []

    monkeypatch.setattr(
        "specify_cli.retrospective.policy.resolve_policy",
        lambda repo_root: (_EnabledPolicy(), {}),
    )
    monkeypatch.setattr(
        "specify_cli.retrospective.generator.generate_retrospective",
        lambda *a, **k: sentinel_record,
    )
    monkeypatch.setattr(
        "specify_cli.retrospective.writer.write_gen_record",
        lambda record, **k: write_calls.append(record),
    )
    monkeypatch.setattr(
        "specify_cli.retrospective.lifecycle_events.emit_captured",
        lambda record, repo_root, **k: emit_calls.append(record),
    )

    callback = retro._build_retrospective_facilitator_callback("slug-1", tmp_path)
    result = callback(mission_id="mission-1", feature_dir=tmp_path, repo_root=tmp_path)

    assert result is sentinel_record
    assert write_calls == [sentinel_record]
    assert emit_calls == [sentinel_record]


def test_facilitator_uses_live_lookup_for_classify_and_emit_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Retrospective-pair risk regression: the ``_facilitator`` closure built
    by (unpatched, real) ``_build_retrospective_facilitator_callback`` must
    invoke ``_classify_and_emit_failure`` via a live lookup through
    ``runtime_bridge`` when the generator raises -- see module docstring."""
    from runtime.next import runtime_bridge as rb

    class _EnabledPolicy:
        enabled = True

    classify_calls: list[dict[str, Any]] = []

    monkeypatch.setattr(
        "specify_cli.retrospective.policy.resolve_policy",
        lambda repo_root: (_EnabledPolicy(), {}),
    )

    def _raise_missing(*a: Any, **k: Any) -> Any:
        raise FileNotFoundError("forced for seam test")

    monkeypatch.setattr("specify_cli.retrospective.generator.generate_retrospective", _raise_missing)
    monkeypatch.setattr(
        rb,
        "_classify_and_emit_failure",
        lambda **kwargs: classify_calls.append(kwargs),
    )

    callback = retro._build_retrospective_facilitator_callback("slug-1", tmp_path)
    with pytest.raises(FileNotFoundError):
        callback(mission_id="mission-1", feature_dir=tmp_path, repo_root=tmp_path)

    assert len(classify_calls) == 1
    assert classify_calls[0]["mission_id"] == "mission-1"
    assert isinstance(classify_calls[0]["exc"], FileNotFoundError)


def test_facilitator_record_exists_is_non_fatal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from specify_cli.retrospective.writer import RecordExistsError

    class _EnabledPolicy:
        enabled = True

    sentinel_record = object()
    emit_calls: list[Any] = []

    monkeypatch.setattr(
        "specify_cli.retrospective.policy.resolve_policy",
        lambda repo_root: (_EnabledPolicy(), {}),
    )
    monkeypatch.setattr(
        "specify_cli.retrospective.generator.generate_retrospective",
        lambda *a, **k: sentinel_record,
    )

    def _raise_exists(record: Any, **k: Any) -> None:
        raise RecordExistsError("already written")

    monkeypatch.setattr("specify_cli.retrospective.writer.write_gen_record", _raise_exists)
    monkeypatch.setattr(
        "specify_cli.retrospective.lifecycle_events.emit_captured",
        lambda record, repo_root, **k: emit_calls.append(record),
    )

    callback = retro._build_retrospective_facilitator_callback("slug-1", tmp_path)
    result = callback(mission_id="mission-1", feature_dir=tmp_path, repo_root=tmp_path)

    # Non-fatal: RecordExistsError on write is swallowed and Captured is
    # still emitted with the existing record.
    assert result is sentinel_record
    assert emit_calls == [sentinel_record]
