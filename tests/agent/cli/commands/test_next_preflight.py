"""Tests for the charter preflight hook in ``spec-kitty next`` (T023 / T026).

Verifies the FR-006 caller contract:

* ``passed=True``  → ``next`` proceeds to mission decision logic.
* ``passed=False`` → ``next`` exits 1 with ``blocked_reason`` and emits
  no state mutation (the runtime decision engine is never invoked).

``run_charter_preflight`` is fully mocked so the tests stay framework-free
and don't spawn ``git status`` subprocesses.
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


def _fail_result(reason: str = "doctrine stale; run: spec-kitty charter sync") -> CharterPreflightResult:
    return CharterPreflightResult(
        passed=False,
        checks=[],
        auto_refresh_applied=False,
        auto_refresh_actions=[],
        blocked_reason=reason,
    )


def test_hook_returns_result_when_preflight_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shared helper returns the result on success without raising."""
    from specify_cli.charter_preflight import hook as hook_mod

    monkeypatch.setattr(hook_mod, "run_charter_preflight", lambda **_: _pass_result())

    result = hook_mod.run_preflight_or_abort(tmp_path, consumer="next")
    assert result.passed is True


def test_hook_disabled_by_project_config_does_not_load_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Project config disables the heavy runner without an env bypass."""
    from specify_cli.charter_preflight import hook as hook_mod

    config_path = tmp_path / ".kittify" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text("preflight:\n  enabled: false\n", encoding="utf-8")
    monkeypatch.setattr(
        hook_mod,
        "run_charter_preflight",
        lambda **_: pytest.fail("disabled preflight must not invoke runner"),
    )

    result = hook_mod.run_preflight_or_abort(tmp_path, consumer="next")

    assert result.passed is True


def test_null_project_config_enabled_still_runs_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Null enabled resets to the default; it must not silently skip the gate."""
    from specify_cli.charter_preflight import hook as hook_mod

    config_path = tmp_path / ".kittify" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text("preflight:\n  enabled: null\n", encoding="utf-8")
    runner_calls: list[dict] = []

    def _run_charter_preflight(**kwargs):
        runner_calls.append(kwargs)
        return _pass_result()

    monkeypatch.setattr(hook_mod, "run_charter_preflight", _run_charter_preflight)

    result = hook_mod.run_preflight_or_abort(tmp_path, consumer="next")

    assert result.passed is True
    assert runner_calls == [{"repo_root": tmp_path, "auto_refresh": False, "strict": False}]


def test_hook_aborts_with_exit_1_when_preflight_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Failure path exits 1 and surfaces the blocked_reason on stderr."""
    from specify_cli.charter_preflight import hook as hook_mod

    monkeypatch.setattr(hook_mod, "run_charter_preflight", lambda **_: _fail_result())

    with pytest.raises(typer.Exit) as excinfo:
        hook_mod.run_preflight_or_abort(tmp_path, consumer="next")

    assert excinfo.value.exit_code == 1
    captured = capsys.readouterr()
    assert "doctrine stale" in captured.err


def _call_next_step_unwrapped(**kwargs) -> None:
    """Invoke ``next_step`` bypassing the ``@require_main_repo`` decorator.

    The decorator inspects the test environment's git context; tests for
    the preflight gate are about the gate itself, so we unwrap.
    """
    from specify_cli.cli.commands import next_cmd

    underlying = next_cmd.next_step.__wrapped__  # type: ignore[attr-defined]
    return underlying(**kwargs)


def test_next_command_aborts_before_decide_next_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``next_step`` must not enter the runtime when preflight fails.

    We patch ``run_charter_preflight`` to fail and assert ``decide_next``
    is never called — proving "no state mutation" per the caller contract.
    """
    from specify_cli.cli.commands import next_cmd
    from specify_cli.charter_preflight import hook as hook_mod

    monkeypatch.setattr(
        hook_mod,
        "run_charter_preflight",
        lambda **_: _fail_result("stale; run: spec-kitty charter synthesize"),
    )
    monkeypatch.setattr(next_cmd, "locate_project_root", lambda: tmp_path)

    decide_calls: list = []

    def _decide(*args, **kwargs):  # pragma: no cover — assertion is on non-call
        decide_calls.append((args, kwargs))
        raise AssertionError("decide_next must not be invoked when preflight fails")

    monkeypatch.setattr(next_cmd, "decide_next", _decide)

    with pytest.raises(typer.Exit) as excinfo:
        _call_next_step_unwrapped(
            agent="claude",
            result="success",
            mission="042-test-feature",
            json_output=False,
            answer=None,
            decision_id=None,
        )

    assert excinfo.value.exit_code == 1
    assert decide_calls == []
    captured = capsys.readouterr()
    assert "stale" in captured.err


def test_next_command_continues_to_decide_when_preflight_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``next_step`` reaches ``decide_next`` only when preflight passes."""
    from specify_cli.cli.commands import next_cmd
    from specify_cli.charter_preflight import hook as hook_mod

    monkeypatch.setattr(hook_mod, "run_charter_preflight", lambda **_: _pass_result())
    monkeypatch.setattr(next_cmd, "locate_project_root", lambda: tmp_path)

    # Short-circuit downstream work with a sentinel exception so we can
    # confirm the hook lets execution continue past the gate without
    # building the full mission fixture.
    sentinel = RuntimeError("reached decide_next")

    def _decide(*_args, **_kwargs):
        raise sentinel

    monkeypatch.setattr(next_cmd, "decide_next", _decide)
    # Skip the previous-issuance lifecycle pairing helper; it depends on
    # mission metadata that the synthetic tmp_path repo does not have.
    monkeypatch.setattr(
        next_cmd,
        "_pair_previous_lifecycle_record",
        lambda *_a, **_k: None,
    )

    with pytest.raises(RuntimeError) as excinfo:
        _call_next_step_unwrapped(
            agent="claude",
            result="success",
            mission="042-test-feature",
            json_output=False,
            answer=None,
            decision_id=None,
        )

    assert excinfo.value is sentinel
