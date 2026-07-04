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
    },
)
# A representative single-token marker selector that must remain modellable.
_REQUIRED_MARKER_TOKENS: tuple[str, ...] = ("windows_ci", "quarantine", "timing", "slow")
# Floor on parsed gate count — a parser regression that silently drops gates
# (under-counting selection) would otherwise inflate the orphan set unnoticed.
_MIN_EXPECTED_GATES = 40


@pytest.fixture(scope="module")
def gates() -> list[gc.Gate]:
    """Parse the four suite-running workflows once per module."""
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


def test_windows_gate_models_windows_ci_marker(gates: list[gc.Gate]) -> None:
    """Every parsable ci-windows gate must narrow by ``-m windows_ci``.

    ci-windows.yml builds its test list dynamically (``git grep``), so its paths
    can't be parsed and the gate falls back to the whole tree (see
    ``CompiledGate.__init__``). That fallback is coverage-SAFE only because the
    gate narrows by ``-m windows_ci``: every parsable ci-windows gate must carry
    exactly that marker, or the whole-tree fallback would falsely mark
    windows-only tests as covered (Issue #2034 review, alphonso MED).
    """
    windows_gates = [
        g for g in gates if g.workflow == "ci-windows.yml" and g.marker_expr
    ]
    assert windows_gates, "no parsable pytest gate found in ci-windows.yml"
    for g in windows_gates:
        assert g.marker_expr == "windows_ci", (
            f"{g.label()} models marker {g.marker_expr!r}, expected 'windows_ci'. "
            "ci-windows paths are dynamic (git grep) so the gate falls back to the "
            "whole tree; without the windows_ci narrowing the fallback over-claims "
            "coverage."
        )


# ---------------------------------------------------------------------------
# Selection-logic unit guards (no collection)
# ---------------------------------------------------------------------------


def test_selection_logic_matches_marker_and_path() -> None:
    """The #2034 failure mode in miniature: marker-only selection decides.

    A unit test marked only ``unit`` in a misc-shard dir is an orphan; the same
    path marked ``git_repo`` is covered.

    ``selects`` is a *pure, deterministic* function of its arguments — the marker
    expression compiles once and ``Expression.evaluate`` has no data-dependent
    branch that can flip for a fixed marker set. The diagnostic messages below
    therefore exist to make any *environmental* flake actionable: alphonso/debbie
    saw a transient ``False`` here on the architectural shard and traced the class
    to stale ``__pycache__`` / xdist worker contamination, not a logic fault. If
    this ever fails, investigate the runner — do NOT rerun-to-green (Issue #2034).
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
    assert not compiled.selects(rel, f"{rel}::test_x", {"unit"}), (
        f"unit-only test wrongly selected by gate expr {misc_shard.marker_expr!r}."
    )
    assert compiled.selects(rel, f"{rel}::test_y", {"git_repo"}), (
        f"git_repo test NOT selected by gate expr {misc_shard.marker_expr!r} for "
        f"path {rel!r}. selects() is pure given these inputs, so a transient "
        "failure here is an environment artifact (stale __pycache__ / xdist "
        "isolation), not a logic regression — investigate the runner, do not "
        "rerun-to-green (Issue #2034)."
    )
    # Outside the gate's paths → never selected, regardless of marker.
    assert not compiled.selects(
        "tests/other/test_z.py", "tests/other/test_z.py::t", {"git_repo"},
    ), "test outside the gate's paths was selected — the path filter is broken."


def test_parser_ignores_non_command_pytest_tokens() -> None:
    """``pytest`` as an *argument* (pipx inject, git grep) is not a gate.

    A ``"$VAR" -m pytest ... -m windows_ci`` invocation is parsed correctly.
    """
    assert gc.parse_pytest_invocation("pipx inject spec-kitty-cli pytest pytest-cov") is None
    assert gc.parse_pytest_invocation('done < <(git grep -l "@pytest.mark.x" -- tests)') is None
    parsed = gc.parse_pytest_invocation(
        '"$VENV_PYTHON" -m pytest -m windows_ci --maxfail=1 -v "${WINDOWS_TESTS[@]}"',
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
        *_args: object, env: dict[str, str], **_kw: object,
    ) -> subprocess.CompletedProcess[str]:
        # Simulate the plugin having already written a (partial) dump before the
        # collection error aborted the run with a failure exit code.
        Path(env["SK_GATE_DUMP"]).write_text(
            json.dumps([{"nodeid": "x", "relpath": "x", "markers": []}]),
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


def test_analyze_detects_orphan_and_covered_records() -> None:
    """``analyze`` must classify a zero-gate test as orphan, a gated one as covered.

    This is the direct guard on the analyzer core; the real-universe ratchet below only checks the *delta* against the baseline,
    so mutating ``analyze`` to never detect orphans leaves it (and the backlog
    test) green — the exact "untested-but-green" failure this PR exists to catch,
    reproduced in the checker's own guard (Issue #2034 review, renata HIGH). This
    synthetic universe pins the classification deterministically, no collection.
    """
    gate = gc.Gate(
        workflow="ci-quality.yml",
        job="integration-tests-core-misc",
        shard="misc",
        paths=["tests/tasks"],
        marker_expr="git_repo or integration",
    )
    universe: list[gc.TestRecord] = [
        # Orphan: in a gated path, but only an authoring marker no gate selects.
        {
            "nodeid": "tests/tasks/test_u.py::t",
            "relpath": "tests/tasks/test_u.py",
            "markers": ["unit"],
        },
        # Covered: same path, carries a marker the gate selects.
        {
            "nodeid": "tests/tasks/test_c.py::t",
            "relpath": "tests/tasks/test_c.py",
            "markers": ["git_repo"],
        },
    ]
    report = gc.analyze([gate], universe)
    assert report.orphan_files == ["tests/tasks/test_u.py"]
    assert report.orphan_nodeids == ["tests/tasks/test_u.py::t"]
    assert report.total == 2


def test_selection_respects_ignore() -> None:
    """A path under a gate's ``--ignore`` is NOT selected, even when path+marker match.

    Guards the exclusion branch in :meth:`CompiledGate.selects`: disabling it
    silently re-counts every ``--ignore``-d test as selected (the measured
    duplicate count jumps from 1443 to ~9294), inflating coverage. The 29 real
    ``--ignore`` args across the workflows make this branch load-bearing
    (Issue #2034 review, renata HIGH).
    """
    gate = gc.Gate(
        workflow="ci-quality.yml",
        job="fast-tests",
        shard=None,
        paths=["tests"],
        ignores=["tests/runtime"],
        marker_expr="fast",
    )
    compiled = gc.CompiledGate(gate)
    ignored = "tests/runtime/test_loop.py"
    assert not compiled.selects(ignored, f"{ignored}::t", {"fast"}), (
        "a test under --ignore=tests/runtime was selected — the ignore branch "
        "is not excluding."
    )
    kept = "tests/tasks/test_x.py"
    assert compiled.selects(kept, f"{kept}::t", {"fast"}), (
        "a fast test outside the ignore was wrongly excluded."
    )


def test_path_matches_nodeid_prefix_branch() -> None:
    """A ``::``-bearing entry matches by nodeid equality or prefix, not relpath."""
    nodeid = "tests/a/test_x.py::TestK::test_m"
    assert gc.path_matches("tests/a/test_x.py", nodeid, "tests/a/test_x.py::TestK")
    assert gc.path_matches("tests/a/test_x.py", nodeid, nodeid)
    assert not gc.path_matches(
        "tests/a/test_x.py", "tests/a/test_x.py::TestZ::t", "tests/a/test_x.py::TestK",
    )


def test_substitute_matrix_expands_and_blanks() -> None:
    """``${{ matrix.X }}`` expands to the variant value; other ``${{ ... }}`` blank."""
    out = gc.substitute_matrix(
        "pytest ${{ matrix.shard }} -m '${{ matrix.markers }}' ${{ github.sha }}",
        {"shard": "tests/misc", "markers": "fast"},
    )
    assert "tests/misc" in out
    assert "-m 'fast'" in out
    assert "${{" not in out  # non-matrix expressions are blanked, not left literal


def test_join_continuations_merges_backslash_lines() -> None:
    """Backslash-continued shell lines join into one logical line; others stand alone."""
    joined = gc.join_continuations(
        "pytest tests/a \\\n  -m fast \\\n  --maxfail=1\necho done",
    )
    assert any("pytest tests/a" in ln and "--maxfail=1" in ln for ln in joined)
    assert "echo done" in joined


def test_strip_to_command_strips_env_and_runner_prefixes() -> None:
    """Env-assignments and runner prefixes reduce down to the ``pytest`` token."""
    assert gc.strip_to_command(
        "FOO=1 BAR='x y' uv run pytest tests -m fast",
    ).startswith("pytest")
    assert gc.strip_to_command('"$VENV_PYTHON" -m pytest tests').startswith("pytest")
    # A command where ``pytest`` is only an argument is NOT reduced to a pytest head.
    assert not gc.strip_to_command("git grep -l pytest -- tests").startswith("pytest")


def test_pytest_marker_expression_import_contract() -> None:
    """The checker depends on pytest's private ``_pytest.mark.expression`` API.

    pytest is floored (``>=9.0.3``) not upper-pinned, so a future breaking bump
    could move or change this surface. Fail here with a clear pointer rather than
    deep inside a ratchet run (Issue #2034 review, alphonso MED).
    """
    from typing import Any, cast  # noqa: PLC0415  # intentional: exercises import surface

    from _pytest.mark.expression import Expression  # noqa: PLC0415  # intentional: exercises import surface

    expr = Expression.compile("a and not b")
    # pytest's matcher protocol is ``callable(name, /, **kw) -> bool``; a plain
    # membership test is structurally compatible (cast silences the Protocol),
    # mirroring ``CompiledGate.selects``.
    assert expr.evaluate(cast("Any", lambda name: name == "a")) is True
    assert expr.evaluate(cast("Any", lambda name: name in {"a", "b"})) is False


# ---------------------------------------------------------------------------
# Ratchet + report (one collection, shared via the module fixture)
# ---------------------------------------------------------------------------


def test_baseline_file_is_well_formed() -> None:
    """The ratchet baseline carries its required keys and stays sorted."""
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
    current = set(coverage_report.orphan_files)
    # Real-universe floor: while the frozen backlog is non-empty the analyzer
    # must still be DETECTING it — not silently returning an empty orphan set,
    # which would also make ``new_files`` empty and fake a pass (renata HIGH).
    # Since the #2296 drain (mission ci-suite-map-bind FR-006) the committed
    # baseline is EMPTY by design: zero live orphans at a zero-file baseline is
    # the invariant HOLDING, not the checker going blind. Checker-blindness
    # stays pinned deterministically by the synthetic
    # ``test_analyze_detects_orphan_and_covered_records`` (a known-orphan
    # record must be reported), which does not depend on live orphans existing.
    if baseline_files:
        assert current, (
            "analyze() reported ZERO orphan files against the real suite — the "
            "checker has STOPPED detecting coverage holes (expected a non-empty "
            f"subset of the {len(baseline_files)}-file baseline). This is the "
            "checker silently going blind, the one regression it must not allow."
        )
    new_files = sorted(current - baseline_files)
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
