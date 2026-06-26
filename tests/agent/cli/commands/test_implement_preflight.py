"""Tests for the charter preflight hook in ``spec-kitty implement`` (T024 / T026).

Verifies the FR-006 caller contract: the preflight gate runs **before**
any worktree allocation or ``.kittify/`` modification. On failure we
exit 1 and ``create_lane_workspace`` is never invoked.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from specify_cli.charter_preflight.result import CharterPreflightResult


pytestmark = pytest.mark.fast


def _pass_result() -> CharterPreflightResult:
    return CharterPreflightResult(
        passed=True,
        checks=[],
        auto_refresh_applied=False,
        auto_refresh_actions=[],
        blocked_reason=None,
    )


def _fail_result(reason: str = "synthesized DRG missing; run: spec-kitty charter synthesize") -> CharterPreflightResult:
    return CharterPreflightResult(
        passed=False,
        checks=[],
        auto_refresh_applied=False,
        auto_refresh_actions=[],
        blocked_reason=reason,
    )


def _call_implement_unwrapped(**kwargs):
    """Invoke ``implement`` bypassing ``@_json_safe_output`` and ``@require_main_repo``."""
    from specify_cli.cli.commands import implement as implement_mod

    fn = implement_mod.implement
    # Two decorators stacked → two ``__wrapped__`` hops.
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__  # type: ignore[attr-defined]
    return fn(**kwargs)


def test_implement_aborts_before_worktree_allocation_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Preflight failure exits 1 BEFORE ``create_lane_workspace`` is called."""
    from specify_cli.cli.commands import implement as implement_mod
    from specify_cli.charter_preflight import hook as hook_mod

    monkeypatch.setattr(hook_mod, "run_charter_preflight", lambda **_: _fail_result())
    monkeypatch.setattr(implement_mod, "find_repo_root", lambda: tmp_path)

    create_calls: list = []

    def _create(*args, **kwargs):  # pragma: no cover — assertion is on non-call
        create_calls.append((args, kwargs))
        raise AssertionError(
            "create_lane_workspace must not be invoked when preflight fails"
        )

    monkeypatch.setattr(implement_mod, "create_lane_workspace", _create)

    with pytest.raises(typer.Exit) as excinfo:
        _call_implement_unwrapped(
            wp_id="WP01",
            mission="042-test-feature",
            auto_commit=None,
            json_output=False,
            recover=False,
            base=None,
            acknowledge_not_bulk_edit=False,
            actor=None,
        )

    assert excinfo.value.exit_code == 1
    assert create_calls == []
    captured = capsys.readouterr()
    assert "synthesized DRG missing" in captured.err


def test_implement_proceeds_past_preflight_when_passed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On success the gate releases control to the downstream stages."""
    from specify_cli.cli.commands import implement as implement_mod
    from specify_cli.charter_preflight import hook as hook_mod

    monkeypatch.setattr(hook_mod, "run_charter_preflight", lambda **_: _pass_result())
    monkeypatch.setattr(implement_mod, "find_repo_root", lambda: tmp_path)

    sentinel = RuntimeError("reached detect_feature_context")

    def _detect(*_args, **_kwargs):
        raise sentinel

    # detect_feature_context is the very next call after preflight; reaching
    # it proves the gate let us through.
    monkeypatch.setattr(implement_mod, "detect_feature_context", _detect)

    with pytest.raises(RuntimeError) as excinfo:
        _call_implement_unwrapped(
            wp_id="WP01",
            mission="042-test-feature",
            auto_commit=None,
            json_output=False,
            recover=False,
            base=None,
            acknowledge_not_bulk_edit=False,
            actor=None,
        )

    assert excinfo.value is sentinel
