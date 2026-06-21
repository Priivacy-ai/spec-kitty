"""Drift guards for the CI gate-coverage checker (Issue #2034 / #1933).

CI selects tests by ``(paths, -m marker_expr)`` per gate, sharded across jobs.
Tests carrying only authoring markers (``unit`` / ``contract``) or living in a
directory no gate touches are selected by **zero** gates — they never run in CI,
so a regression in them is invisible (a silent coverage hole, not a red).

The static model lives in :mod:`tests.architectural._gate_coverage`. These tests
are its guards:

* **Cheap structural guards** — assert the four suite-running workflows still
  parse into a well-formed gate model and that the *kinds* of selection the
  checker relies on (the core-misc shard matrix, the ``windows_ci`` /
  ``quarantine`` / ``timing`` / ``slow`` selectors) are still present. If CI is
  restructured so the checker can no longer see a selection, these fail loudly
  rather than letting the orphan analysis silently go stale.

* **The orphan ratchet** — recollects the whole suite and fails on any **new**
  ungated file beyond the frozen ``_gate_coverage_baseline.json`` worklist. The
  existing ~9.8k-test backlog is recorded, not fixed here (that re-tiering is the
  maintainer's migration, against this guardrail); only *new* leaks go red.
  Duplicate selections are **reported, not enforced** — fast↔integration overlap
  is intentional.

The ratchet recollects the suite in a subprocess (~90s). It is marked
``architectural`` so it runs in the dedicated shard, not the fast developer loop.
"""

from __future__ import annotations

import json
import subprocess
import warnings
from pathlib import Path

import pytest

from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]


# Selection structures the orphan analysis depends on. If a workflow refactor
# removes one of these, the checker's model is stale and must be updated — these
# names are matched against the parsed gates so the failure is explicit.
_REQUIRED_CORE_MISC_SHARDS: frozenset[str] = frozenset(
    {
        "architectural",
        "integration",
        "specify-cli-heavy",
        "specify-cli-rest",
        "auth-audit-git",
        "misc",
    }
)
# A representative single-token marker selector that must remain modellable.
_REQUIRED_MARKER_TOKENS: tuple[str, ...] = ("windows_ci", "quarantine", "timing", "slow")
# Floor on parsed gate count — a parser regression that silently drops gates
# (under-counting selection) would otherwise inflate the orphan set unnoticed.
_MIN_EXPECTED_GATES = 40


@pytest.fixture(scope="module")
def gates() -> list[gc.Gate]:
    return gc.load_gates()


@pytest.fixture(scope="module")
def coverage_report() -> gc.CoverageReport:
    """Collect the whole suite once and analyze it (shared across ratchet tests)."""
    return gc.analyze(gc.load_gates(), gc.collect_universe())


# ---------------------------------------------------------------------------
# Cheap structural guards (no collection)
# ---------------------------------------------------------------------------


def test_all_suite_workflows_parse_into_gates(gates: list[gc.Gate]) -> None:
    """Every suite-running workflow parses into a non-trivial, well-formed model."""
    assert len(gates) >= _MIN_EXPECTED_GATES, (
        f"Only {len(gates)} gates parsed (expected >= {_MIN_EXPECTED_GATES}). A "
        "parser regression or a workflow restructure is hiding pytest invocations "
        "from the checker — the orphan analysis would silently under-count."
    )
    seen_workflows = {g.workflow for g in gates}
    assert seen_workflows == set(gc.WORKFLOW_FILES), (
        "Gates were parsed from "
        f"{sorted(seen_workflows)} but expected all of {list(gc.WORKFLOW_FILES)}. "
        "A workflow that runs pytest stopped contributing gates."
    )
    for gate in gates:
        assert gate.paths or gate.marker_expr, (
            f"Gate {gate.label()} has neither paths nor a marker expression — it "
            "selects nothing, which means the parser mis-read its invocation."
        )


def test_marker_expressions_compile(gates: list[gc.Gate]) -> None:
    """Every parsed ``-m`` expression must compile with pytest's evaluator.

    A garbled expression would make :class:`CompiledGate` raise at analysis time;
    catching it here keeps the failure on the model, not on the ratchet run.
    """
    for gate in gates:
        if gate.marker_expr:
            gc.CompiledGate(gate)  # compiles the expression in __init__


def test_required_selection_structures_present(gates: list[gc.Gate]) -> None:
    """The core-misc shard matrix and the key marker selectors stay modellable."""
    shards = {g.shard for g in gates if g.shard}
    missing_shards = _REQUIRED_CORE_MISC_SHARDS - shards
    assert not missing_shards, (
        f"integration-tests-core-misc shards not found in the parsed model: "
        f"{sorted(missing_shards)}. The matrix was restructured — update the "
        "checker so these paths are still evaluated for coverage."
    )
    all_exprs = " ".join(g.marker_expr or "" for g in gates)
    missing_tokens = [tok for tok in _REQUIRED_MARKER_TOKENS if tok not in all_exprs]
    assert not missing_tokens, (
        f"Marker selectors no longer present in any gate: {missing_tokens}. If a "
        "selector genuinely went away, update _REQUIRED_MARKER_TOKENS; otherwise a "
        "gate that used to cover those tests was dropped."
    )


# ---------------------------------------------------------------------------
# Selection-logic unit guards (no collection)
# ---------------------------------------------------------------------------


def test_selection_logic_matches_marker_and_path() -> None:
    """A unit test marked only ``unit`` in a misc-shard dir is an orphan; the same
    path marked ``git_repo`` is covered. This is the #2034 failure mode in miniature.
    """
    misc_shard = gc.Gate(
        workflow="ci-quality.yml",
        job="integration-tests-core-misc",
        shard="misc",
        paths=["tests/tasks"],
        marker_expr="not windows_ci and (git_repo or integration or architectural)",
    )
    compiled = gc.CompiledGate(misc_shard)
    rel = "tests/tasks/test_tasks_2x_unit.py"
    assert not compiled.selects(rel, f"{rel}::test_x", {"unit"})
    assert compiled.selects(rel, f"{rel}::test_y", {"git_repo"})
    # Outside the gate's paths → never selected, regardless of marker.
    assert not compiled.selects(
        "tests/other/test_z.py", "tests/other/test_z.py::t", {"git_repo"}
    )


def test_parser_ignores_non_command_pytest_tokens() -> None:
    """``pytest`` as an *argument* (pipx inject, git grep) is not a gate; a
    ``"$VAR" -m pytest ... -m windows_ci`` invocation is parsed correctly.
    """
    assert gc._parse_pytest_invocation("pipx inject spec-kitty-cli pytest pytest-cov") is None
    assert gc._parse_pytest_invocation('done < <(git grep -l "@pytest.mark.x" -- tests)') is None
    parsed = gc._parse_pytest_invocation(
        '"$VENV_PYTHON" -m pytest -m windows_ci --maxfail=1 -v "${WINDOWS_TESTS[@]}"'
    )
    assert parsed is not None
    _paths, _ignores, marker = parsed
    assert marker == "windows_ci"


def test_collect_universe_fails_loudly_on_collection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-zero collection exit must raise, even if a partial dump was written.

    Guards Issue #2034 review P2: a collection-time import/syntax error in a NEW
    test file drops that file from collection; trusting the partial dump would let
    the orphan ratchet pass against an incomplete suite. The healthy collect-only
    exit (items cleared by the plugin) is NO_TESTS_COLLECTED — anything else fails.
    """

    def fake_run(
        *_args: object, env: dict[str, str], **_kw: object
    ) -> subprocess.CompletedProcess[str]:
        # Simulate the plugin having already written a (partial) dump before the
        # collection error aborted the run with a failure exit code.
        Path(env["SK_GATE_DUMP"]).write_text(
            json.dumps([{"nodeid": "x", "relpath": "x", "markers": []}])
        )
        return subprocess.CompletedProcess(
            args=[],
            returncode=int(pytest.ExitCode.TESTS_FAILED),
            stdout="ERROR collecting tests/new/test_broken.py",
            stderr="ImportError",
        )

    # gc imports the same ``subprocess`` module object, so patching it here patches
    # the call inside collect_universe too.
    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="did not complete cleanly"):
        gc.collect_universe()


# ---------------------------------------------------------------------------
# Ratchet + report (one collection, shared via the module fixture)
# ---------------------------------------------------------------------------


def test_baseline_file_is_well_formed() -> None:
    baseline = gc.load_baseline()
    for key in ("orphan_files", "orphan_test_count", "total_tests"):
        assert key in baseline, f"_gate_coverage_baseline.json missing key {key!r}."
    assert isinstance(baseline["orphan_files"], list)
    assert baseline["orphan_files"] == sorted(baseline["orphan_files"]), (
        "orphan_files must stay sorted (regenerate via --update-baseline)."
    )


def test_no_new_orphan_surfaces(coverage_report: gc.CoverageReport) -> None:
    """Hard ratchet: no test FILE may newly fall into zero CI gates.

    The frozen backlog in ``_gate_coverage_baseline.json`` is allowed; a file not
    on that list with zero-gate tests is a *new* coverage leak and fails here.
    """
    baseline_files = set(gc.load_baseline().get("orphan_files", []))
    new_files = sorted(set(coverage_report.orphan_files) - baseline_files)
    assert not new_files, (
        f"{len(new_files)} test file(s) are selected by ZERO CI gates and are not "
        "in the recorded baseline — they will never run in CI:\n"
        + "\n".join(f"  {f}" for f in new_files)
        + "\n\nFix: give the test(s) a marker a gate selects (e.g. `fast`, "
        "`integration`, `git_repo`) and/or place them under a gated path. If the "
        "coverage gap is intentional and tracked, regenerate the baseline with "
        "`uv run python -m tests.architectural._gate_coverage --update-baseline`."
    )


def test_orphan_backlog_does_not_grow(coverage_report: gc.CoverageReport) -> None:
    """Shrinkage is good news (warn); growth in file count is caught above.

    Emits a nudge to lock in a smaller baseline when the backlog shrinks, mirroring
    the repo's ratchet-baseline shrinkage convention.
    """
    baseline = gc.load_baseline()
    recorded = set(baseline.get("orphan_files", []))
    current = set(coverage_report.orphan_files)
    cleared = sorted(recorded - current)
    if cleared:
        warnings.warn(
            f"Gate-coverage backlog shrank by {len(cleared)} file(s) "
            f"(now {len(current)} vs baseline {len(recorded)}). Lock it in: "
            "uv run python -m tests.architectural._gate_coverage --update-baseline",
            UserWarning,
            stacklevel=2,
        )


def test_duplicate_selection_is_reported(coverage_report: gc.CoverageReport) -> None:
    """Duplicates (>=2 gates) are REPORTED, never enforced — overlap is intentional.

    fast↔integration domain splits deliberately overlap; this surfaces the count
    for visibility without failing CI.
    """
    dupes = coverage_report.duplicate_nodeids
    if dupes:
        warnings.warn(
            f"{len(dupes)} test(s) are selected by >=2 CI gates (duplicate run). "
            "This is report-only; some fast↔integration overlap is intentional.",
            UserWarning,
            stacklevel=2,
        )
    assert isinstance(dupes, list)
