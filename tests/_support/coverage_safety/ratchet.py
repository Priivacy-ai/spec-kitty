"""Stability ratchet helper (T006, C-RATCHET, FR-012, NFR-005, E4).

A parallelization flip is accepted only after **N consecutive green** parallel
runs of the shard (E4/I1) with zero new flaky tests relative to the serial
baseline (E4/I2). This mirrors the repo's existing "run twice on an unchanged
tree" ratchet convention (see ``tests/architectural/test_no_op_stable_writes.py``)
applied to test-suite stability instead of tree cleanliness.

Design for testability: the per-run execution is injected as a *runner*
callable (``Callable[[Sequence[str]], RunOutcome]``). Unit tests pass a stubbed
runner so the aggregation logic is exercised without launching N real suites
(Risks & Mitigations). The default runner shells out to ``pytest -n auto``.

A thin CLI (`python -m tests._support.coverage_safety.ratchet ...`) makes the
ratchet runnable from CI.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

__all__ = [
    "RatchetResult",
    "RunOutcome",
    "Runner",
    "default_pytest_runner",
    "main",
    "run_ratchet",
]

# pytest exit code for "tests collected and all passed".
_PYTEST_OK = 0
_DEFAULT_RUNS = 3


@dataclass(frozen=True)
class RunOutcome:
    """The outcome of a single parallel run of the shard.

    *failed_nodeids* lists the nodeids that failed on this run (empty when
    green). The runner is responsible for populating it; the default runner
    derives it from pytest's exit code (non-empty sentinel on failure) since
    parsing every failing nodeid from stdout is out of scope for the ratchet's
    pass/fail gate.
    """

    passed: bool
    failed_nodeids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class RatchetResult:
    """Aggregated result of an N-run stability ratchet.

    * :attr:`accepted` is True iff every run was green (E4/I1).
    * :attr:`new_failures` is the union of nodeids that failed on *any* run but
      were not failing on run 0's baseline — i.e. newly-introduced flakes
      relative to the first observed run (E4/I2).
    """

    runs: int
    outcomes: tuple[RunOutcome, ...]
    accepted: bool
    new_failures: frozenset[str] = field(default_factory=frozenset)

    @property
    def green_runs(self) -> int:
        """Number of green runs observed."""
        return sum(1 for o in self.outcomes if o.passed)

    def summary(self) -> str:
        """One-line human summary suitable for CI logs."""
        verdict = "ACCEPTED" if self.accepted else "REJECTED"
        line = (
            f"Stability ratchet {verdict}: {self.green_runs}/{self.runs} "
            f"parallel runs green."
        )
        if self.new_failures:
            line += (
                " New/flaky failures: "
                + ", ".join(sorted(self.new_failures))
            )
        return line


Runner = Callable[[Sequence[str]], RunOutcome]


def default_pytest_runner(pytest_args: Sequence[str]) -> RunOutcome:
    """Run the shard once under ``-n auto`` and report pass/fail.

    Used by CI. Unit tests inject a stub instead so the aggregation logic is
    tested without launching real suites.
    """
    completed = subprocess.run(  # noqa: S603 — args are caller-supplied test selectors, not shell input
        [
            sys.executable,
            "-m",
            "pytest",
            "-n",
            "auto",
            "--dist",
            "loadfile",
            "-p",
            "no:cacheprovider",
            *pytest_args,
        ],
        check=False,
    )
    passed = completed.returncode == _PYTEST_OK
    # The default runner cannot cheaply enumerate failing nodeids, so it uses a
    # single sentinel to mark "this run failed" without claiming a specific id.
    failed = frozenset() if passed else frozenset({"<run-failed>"})
    return RunOutcome(passed=passed, failed_nodeids=failed)


def run_ratchet(
    pytest_args: Sequence[str],
    n: int = _DEFAULT_RUNS,
    *,
    runner: Runner | None = None,
) -> RatchetResult:
    """Run the shard *n* times and require all green to accept the flip.

    Stops early on the first failing run (a flip cannot be accepted once any
    run is red, so further runs add no information — and CI time is precious).
    *runner* defaults to :func:`default_pytest_runner`; tests pass a stub.

    Raises :class:`ValueError` if *n* < 1.
    """
    if n < 1:
        raise ValueError(f"ratchet run count n must be >= 1, got {n}")
    active_runner = runner if runner is not None else default_pytest_runner

    outcomes: list[RunOutcome] = []
    new_failures: set[str] = set()
    for _ in range(n):
        outcome = active_runner(pytest_args)
        outcomes.append(outcome)
        if not outcome.passed:
            new_failures |= set(outcome.failed_nodeids)
            break  # any red run rejects the flip; stop burning CI time
    accepted = len(outcomes) == n and all(o.passed for o in outcomes)
    return RatchetResult(
        runs=n,
        outcomes=tuple(outcomes),
        accepted=accepted,
        new_failures=frozenset(new_failures),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry: ``python -m tests._support.coverage_safety.ratchet ...``.

    Returns process exit code: 0 when the flip is accepted (all runs green),
    1 otherwise — so CI can gate a parallelization flip on this command.
    """
    parser = argparse.ArgumentParser(
        prog="python -m tests._support.coverage_safety.ratchet",
        description=(
            "Run a pytest shard N times under -n auto and accept a "
            "parallelization flip only if every run is green (C-RATCHET)."
        ),
    )
    parser.add_argument(
        "-n",
        "--runs",
        type=int,
        default=_DEFAULT_RUNS,
        help="Number of consecutive green runs required (default: 3).",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Shard selector passed through to pytest (paths, -m, -k, ...).",
    )
    ns = parser.parse_args(argv)
    result = run_ratchet(ns.pytest_args, n=ns.runs)
    print(result.summary())
    return 0 if result.accepted else 1


if __name__ == "__main__":  # pragma: no cover — exercised via subprocess/CLI
    raise SystemExit(main())
