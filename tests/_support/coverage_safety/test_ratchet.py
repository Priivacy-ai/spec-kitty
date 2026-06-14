"""Unit tests for the stability ratchet aggregation (T006).

The per-run execution is injected as a *stubbed* runner so we test the
aggregation logic WITHOUT launching N real suites (Risks & Mitigations).
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence

import pytest

from tests._support.coverage_safety.ratchet import (
    RatchetResult,
    RunOutcome,
    main,
    run_ratchet,
)

pytestmark = [pytest.mark.fast]


def _scripted_runner(outcomes: Sequence[RunOutcome]) -> object:
    """A runner that replays *outcomes* in order, one per call."""
    it: Iterator[RunOutcome] = iter(outcomes)

    def runner(_args: Sequence[str]) -> RunOutcome:
        return next(it)

    return runner


def test_all_green_runs_accept_the_flip() -> None:
    runner = _scripted_runner([RunOutcome(passed=True)] * 3)
    result = run_ratchet(["tests/agent"], n=3, runner=runner)  # type: ignore[arg-type]
    assert isinstance(result, RatchetResult)
    assert result.accepted is True
    assert result.green_runs == 3
    assert result.runs == 3
    assert result.new_failures == frozenset()
    assert "ACCEPTED" in result.summary()


def test_a_single_red_run_rejects_and_stops_early() -> None:
    # Second run fails; the ratchet must reject and NOT call the runner a third
    # time (early stop conserves CI time).
    calls = {"n": 0}

    def runner(_args: Sequence[str]) -> RunOutcome:
        calls["n"] += 1
        if calls["n"] == 2:
            return RunOutcome(passed=False, failed_nodeids=frozenset({"t::a"}))
        return RunOutcome(passed=True)

    result = run_ratchet(["tests/agent"], n=3, runner=runner)
    assert result.accepted is False
    assert calls["n"] == 2  # stopped early — third run never executed
    assert result.green_runs == 1
    assert "t::a" in result.new_failures
    assert "REJECTED" in result.summary()
    assert "t::a" in result.summary()


def test_first_run_red_rejects_immediately() -> None:
    runner = _scripted_runner(
        [RunOutcome(passed=False, failed_nodeids=frozenset({"t::x"}))]
    )
    result = run_ratchet(["tests/agent"], n=3, runner=runner)  # type: ignore[arg-type]
    assert result.accepted is False
    assert result.green_runs == 0
    assert result.new_failures == frozenset({"t::x"})


def test_single_run_ratchet_accepts_on_green() -> None:
    runner = _scripted_runner([RunOutcome(passed=True)])
    result = run_ratchet(["tests/agent"], n=1, runner=runner)  # type: ignore[arg-type]
    assert result.accepted is True
    assert result.runs == 1


def test_invalid_run_count_raises() -> None:
    with pytest.raises(ValueError, match="n must be >= 1"):
        run_ratchet(["tests/agent"], n=0)


def test_default_run_count_is_three() -> None:
    runner = _scripted_runner([RunOutcome(passed=True)] * 3)
    result = run_ratchet(["tests/agent"], runner=runner)  # type: ignore[arg-type]
    assert result.runs == 3


def test_main_returns_zero_when_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    # Patch the runner the CLI uses so main() does not launch real suites.
    import tests._support.coverage_safety.ratchet as ratchet_mod

    monkeypatch.setattr(
        ratchet_mod,
        "default_pytest_runner",
        lambda _args: RunOutcome(passed=True),
    )
    assert main(["-n", "2", "--", "tests/agent"]) == 0


def test_main_returns_one_when_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    import tests._support.coverage_safety.ratchet as ratchet_mod

    monkeypatch.setattr(
        ratchet_mod,
        "default_pytest_runner",
        lambda _args: RunOutcome(passed=False, failed_nodeids=frozenset({"t::z"})),
    )
    assert main(["-n", "2", "--", "tests/agent"]) == 1
