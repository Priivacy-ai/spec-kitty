"""Parity oracle capture script (WP08 / T037, NFR-001) -- run at base ONLY.

This script captures the golden parity tuples ``(outcome, scope, metadata,
block/exit, console)`` from the **incumbent** ``_mt_run_pre_review_gate`` path
**before** the WP09 hook inversion, so ``test_transition_gate_parity.py`` proves
behaviour *preservation* rather than snapshotting the refactored code (the
circular-oracle trap, squad finding R-F2).

**Anti-circular provenance (mandatory).** The oracle MUST be captured against
the base commit ``7081cf053`` (mission ``scopesource-gate-followup-01KY6S9P``
WP01 re-pin -- this lane's HEAD when it branched; ``src/specify_cli/review/``
and ``tests/review/`` are byte-identical to the mission's nominal base
``eb06ca176``, so this commit IS that incumbent for gate-behaviour purposes)
and NEVER regenerated from HEAD:

- The script ``assert``s ``git rev-parse HEAD == 7081cf053`` and **fails
  loudly** otherwise (see :func:`_require_base_commit`).
- It **machine-emits the actual SHA it ran against** into every fixture header
  (``base_commit`` read from the running worktree) -- a hand-typed SHA literal is
  rejected in review.

**How to (re)capture** -- via a detached ``git worktree`` at the base commit
(THE method, not a fallback)::

    git worktree add --detach /path/to/base-7081cf053 7081cf053
    cd /path/to/base-7081cf053
    PYTHONPATH=$(pwd)/src python \\
        <repo>/tests/review/fixtures/parity/_capture.py \\
        --out <repo>/tests/review/fixtures/parity

The two terminal outcomes are forced at base: the timeout path is driven by a
crafted ``TIMED_OUT`` head-run result (monkeypatching
``run_scoped_tests_at_head``), and ``CANCELLED`` reproduces the incumbent's
``KeyboardInterrupt`` branch verdict (``tasks_move_task.py`` :1241-1247).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: The ONE authorised base commit for the oracle. The capture refuses to run
#: anywhere else so the committed fixtures cannot silently drift onto HEAD.
#: Re-pinned by mission ``scopesource-gate-followup-01KY6S9P`` WP01: the
#: mission's nominal base is ``eb06ca176``, but this lane's actual HEAD is
#: this SHA (planning-only commits atop ``eb06ca176`` that touch only
#: ``kitty-specs/`` -- ``src/specify_cli/review/`` and ``tests/review/`` are
#: byte-identical, confirmed via ``git diff --stat eb06ca176 HEAD -- src/
#: tests/review/`` returning empty). Pinning to the literal ``eb06ca176``
#: would make ``_require_base_commit`` fail on every checkout of this lane.
BASE_COMMIT = "7081cf0537c6d2b7cddde3b1bd3c09be2dc61e41"
_BASE_SHORT = "7081cf053"


def _require_base_commit() -> str:
    """Return the running HEAD SHA, asserting it is the authorised base commit.

    Fails LOUDLY (``SystemExit``) on any other commit -- the fixtures must be
    captured from ``7081cf053`` against the incumbent function, never HEAD.
    """
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if head != BASE_COMMIT:
        raise SystemExit(
            "REFUSING to capture the parity oracle: this worktree is at "
            f"{head!r} but the oracle MUST be captured from the base commit "
            f"{BASE_COMMIT!r} ({_BASE_SHORT}) against the incumbent "
            "_mt_run_pre_review_gate. Check out a detached worktree at "
            f"{_BASE_SHORT} and re-run (see this module's docstring)."
        )
    return head


@dataclass(frozen=True)
class _Scenario:
    """One captured verdict shape plus the (block_enabled, force) matrix for it."""

    name: str
    build: Callable[[Any, Any], Any]  # (pre_review_gate, baseline_mod) -> GateVerdict
    matrix: tuple[tuple[bool, bool], ...]  # (block_enabled, force) combos


def _scope(prg: Any, targets: tuple[str, ...]) -> Any:
    return prg.ScopeResult.from_override(targets)


def _shard_scope(prg: Any) -> Any:
    """A census-derived scope carrying a NON-empty ``matched_shard_groups``.

    Every ``from_override`` scope above zeroes the shard/composite breakdown, so
    the incumbent metadata's ``matched_shard_groups`` / ``affected_shard_count``
    fields were NEVER exercised by the oracle — the exact coverage gap that let
    the WP09 ``ScopeSource`` reconstruction silently drop them. This is the SAME
    shape ``derive_test_scope`` emits for a ``status/emit.py``-type change
    (per-shard ``status`` group -> its own ``tests/status`` glob), constructed
    directly so the capture stays a pure metadata/console/decision snapshot.
    """
    return prg.ScopeResult(
        test_targets=("tests/status",),
        matched_shard_groups=("status",),
        matched_composite_dirs=(),
        empty_cone_composite_dirs=(),
        excluded_scope_files=(),
    )


def _run_result(
    prg: Any,
    *,
    ran: bool,
    state: Any,
    current_failures: tuple[Any, ...] = (),
    error: str | None = None,
) -> Any:
    return prg.HeadRunResult(
        ran=ran,
        current_failures=current_failures,
        state=state,
        error=error,
    )


def _drive_engine(prg: Any, scope: Any, run_result: Any, baseline: Any) -> Any:
    """Drive the incumbent ``evaluate_with_scope`` with a crafted head-run result.

    Monkeypatches the module-global ``run_scoped_tests_at_head`` so the genuine
    incumbent verdict-tail logic (not a fabricated verdict) produces the outcome.
    """
    original = prg.run_scoped_tests_at_head
    prg.run_scoped_tests_at_head = lambda *a, **k: run_result  # noqa: E731 (local shim)
    try:
        return prg.evaluate_with_scope(
            scope, repo_root=Path("."), baseline=baseline
        )
    finally:
        prg.run_scoped_tests_at_head = original


def _baseline_clean(baseline_mod: Any) -> Any:
    return baseline_mod.BaselineTestResult(
        wp_id="WP00",
        captured_at="2026-01-01T00:00:00+00:00",
        base_branch="main",
        base_commit="0" * 40,
        test_runner="pytest",
        total=1,
        passed=1,
        failed=0,
        skipped=0,
        failures=(),
    )


def _failure(baseline_mod: Any) -> Any:
    return baseline_mod.BaselineFailure(
        test="tests/review/test_x.py::test_regressed",
        error="AssertionError: boom",
        file="tests/review/test_x.py:12",
    )


def _build_no_coverage(prg: Any, _baseline_mod: Any) -> Any:
    # Empty scope -> incumbent short-circuits to NO_COVERAGE (no run).
    return prg.evaluate_with_scope(
        _scope(prg, ()), repo_root=Path("."), baseline=None
    )


def _build_no_new_failures(prg: Any, baseline_mod: Any) -> Any:
    run = _run_result(prg, ran=True, state=prg.HeadRunState.COMPLETED, current_failures=())
    return _drive_engine(prg, _scope(prg, ("tests/foo",)), run, _baseline_clean(baseline_mod))


def _build_shard_scope_no_new_failures(prg: Any, baseline_mod: Any) -> Any:
    # A clean run over a census-derived scope that carries matched_shard_groups —
    # exercises the metadata's affected_shard_count / matched_shard_groups fields.
    run = _run_result(prg, ran=True, state=prg.HeadRunState.COMPLETED, current_failures=())
    return _drive_engine(prg, _shard_scope(prg), run, _baseline_clean(baseline_mod))


def _build_new_failures(prg: Any, baseline_mod: Any) -> Any:
    run = _run_result(
        prg,
        ran=True,
        state=prg.HeadRunState.COMPLETED,
        current_failures=(_failure(baseline_mod),),
    )
    return _drive_engine(prg, _scope(prg, ("tests/foo",)), run, _baseline_clean(baseline_mod))


def _build_unverified_baseline(prg: Any, baseline_mod: Any) -> Any:
    run = _run_result(
        prg,
        ran=True,
        state=prg.HeadRunState.COMPLETED,
        current_failures=(_failure(baseline_mod),),
    )
    return _drive_engine(prg, _scope(prg, ("tests/foo",)), run, None)


def _build_timed_out(prg: Any, _baseline_mod: Any) -> Any:
    run = _run_result(
        prg,
        ran=False,
        state=prg.HeadRunState.TIMED_OUT,
        error="scoped test run exceeded the timeout",
    )
    return _drive_engine(prg, _scope(prg, ("tests/foo",)), run, _baseline_clean(_baseline_mod))


def _build_cancelled(prg: Any, _baseline_mod: Any) -> Any:
    # Reproduce the incumbent KeyboardInterrupt branch (tasks_move_task.py:1241).
    return prg.GateVerdict(
        outcome=prg.GateOutcome.CANCELLED,
        scope=prg.ScopeResult.from_override(()),
        reason="scoped test run cancelled",
        run_state=prg.HeadRunState.CANCELLED,
    )


def _patch_run_result(prg: Any, run_result: Any) -> Callable[[], None]:
    """Monkeypatch ``prg.run_scoped_tests_at_head`` to return ``run_result``.

    Returns a restore callback. Same patch point ``_drive_engine`` uses
    (module-global lookup, resolved at call time) so the override-tier
    builder below exercises the SAME real call site rather than a
    re-derived one.
    """
    original = prg.run_scoped_tests_at_head

    def _stub(*_args: Any, **_kwargs: Any) -> Any:
        return run_result

    prg.run_scoped_tests_at_head = _stub
    return lambda: setattr(prg, "run_scoped_tests_at_head", original)


def _build_override_nonempty(prg: Any, baseline_mod: Any) -> Any:
    """FR-004/NFR-006 override tier, driven with a NON-empty derived scope.

    Exercises ``_mt_pre_review_gate_with_override_scope`` ->
    ``evaluate_with_scope`` (``scope_source=None``) ->
    ``run_scoped_tests_at_head`` end to end, through the REAL
    ``tasks_move_task`` composition helper (not a hand-mirrored copy). An
    EMPTY override scope short-circuits *inside*
    ``_mt_pre_review_gate_with_override_scope`` before ``evaluate_with_scope``
    is even called (see that function's own early return) -- a golden built
    from an empty override list would never reach the run path this
    scenario exists to freeze (B-vacuous, post-plan squad finding). Using a
    non-empty ``("tests/foo",)`` target list is what makes this golden
    non-vacuous.
    """
    from specify_cli.cli.commands.agent import tasks_move_task as tmt

    run = _run_result(
        prg,
        ran=True,
        state=prg.HeadRunState.COMPLETED,
        current_failures=(_failure(baseline_mod),),
    )
    restore = _patch_run_result(prg, run)
    try:
        return tmt._mt_pre_review_gate_with_override_scope(
            ("tests/foo",),
            repo_root=Path("."),
            baseline=_baseline_clean(baseline_mod),
        )
    finally:
        restore()


_STD = ((False, False), (True, False))
_FULL_MATRIX = ((False, False), (False, True), (True, False), (True, True))
_SCENARIOS: tuple[_Scenario, ...] = (
    _Scenario("no_coverage", _build_no_coverage, _STD),
    _Scenario("no_new_failures", _build_no_new_failures, ((False, False),)),
    _Scenario("shard_scope_no_new_failures", _build_shard_scope_no_new_failures, ((False, False),)),
    _Scenario("new_failures", _build_new_failures, ((False, False), (True, False), (True, True))),
    _Scenario("unverified_baseline", _build_unverified_baseline, _STD),
    _Scenario("timed_out", _build_timed_out, _STD),
    _Scenario("cancelled", _build_cancelled, ((False, False),)),
    _Scenario("override_nonempty", _build_override_nonempty, _FULL_MATRIX),
)


def verdict_to_dict(verdict: Any) -> dict[str, Any]:
    """Serialise the constituent fields needed to rebuild the verdict at HEAD."""
    scope = verdict.scope
    return {
        "outcome": verdict.outcome.value,
        "reason": verdict.reason,
        "run_state": verdict.run_state.value,
        "scope": {
            "test_targets": list(scope.test_targets),
            "matched_shard_groups": list(scope.matched_shard_groups),
            "matched_composite_dirs": list(scope.matched_composite_dirs),
            "empty_cone_composite_dirs": list(scope.empty_cone_composite_dirs),
            "excluded_scope_files": list(scope.excluded_scope_files),
        },
        "new_failures": [
            {"test": f.test, "error": f.error, "file": f.file}
            for f in verdict.new_failures
        ],
        "pre_existing_failures": [
            {"test": f.test, "error": f.error, "file": f.file}
            for f in verdict.pre_existing_failures
        ],
    }


def _capture_case(
    tmt: Any, verdict: Any, *, block_enabled: bool, force: bool, base_sha: str
) -> dict[str, Any]:
    """Run the incumbent metadata/console/decision derivation for one matrix cell."""
    outcome = verdict.outcome
    would_block = block_enabled and outcome is tmt.pre_review_gate.GateOutcome.NEW_FAILURES
    force_bypassed = would_block and force
    blocked = would_block and not force_bypassed
    terminal = outcome in (
        tmt.pre_review_gate.GateOutcome.TIMED_OUT,
        tmt.pre_review_gate.GateOutcome.CANCELLED,
    )
    metadata = tmt._mt_pre_review_gate_metadata(
        verdict,
        block_enabled=block_enabled,
        blocked=blocked,
        force_bypassed=force_bypassed,
        new_checkout_paths=(),
    )
    if terminal:
        metadata["transition_applied"] = False
    console = tmt._mt_pre_review_gate_console_warning(verdict, block_enabled=block_enabled)
    exit_code = 1 if (terminal or blocked) else None
    return {
        "base_commit": base_sha,  # machine-emitted from the running worktree
        "oracle_provenance": (
            f"captured from base commit {base_sha} against the incumbent "
            "_mt_run_pre_review_gate (never regenerated from HEAD)"
        ),
        "block_enabled": block_enabled,
        "force": force,
        "verdict": verdict_to_dict(verdict),
        "expected": {
            "outcome": outcome.value,
            "metadata": metadata,
            "console": console,
            "blocked": blocked,
            "force_bypassed": force_bypassed,
            "terminal": terminal,
            "exit_code": exit_code,
            "transition_applied": not (terminal or blocked),
        },
    }


def capture(out_dir: Path) -> list[Path]:
    """Capture every scenario x matrix cell into JSON fixtures under ``out_dir``."""
    base_sha = _require_base_commit()
    from specify_cli.cli.commands.agent import tasks_move_task as tmt
    from specify_cli.review import baseline as baseline_mod
    from specify_cli.review import pre_review_gate as prg

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for scenario in _SCENARIOS:
        verdict = scenario.build(prg, baseline_mod)
        for block_enabled, force in scenario.matrix:
            case = _capture_case(
                tmt, verdict, block_enabled=block_enabled, force=force, base_sha=base_sha
            )
            name = f"{scenario.name}__block{int(block_enabled)}__force{int(force)}.json"
            path = out_dir / name
            path.write_text(json.dumps(case, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture the transition-gate parity oracle.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Output directory for the JSON fixtures.",
    )
    args = parser.parse_args(argv)
    written = capture(args.out)
    for path in written:
        print(f"wrote {path}")
    print(f"captured {len(written)} parity fixtures from base {BASE_COMMIT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
