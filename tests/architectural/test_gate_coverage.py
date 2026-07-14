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
from pathlib import Path
from collections.abc import Callable

import pytest

from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

# Type of the built-in ``record_property`` fixture: records a (name, value)
# pair into the JUnit/report output. Used to route report-only diagnostics
# off the ``warnings`` channel (NFR-006) while preserving the signal.
RecordPropertyFn = Callable[[str, object], None]


# Selection structures the orphan analysis depends on. If a workflow refactor
# removes one of these, the checker's model is stale and must be updated — these
# names are matched against the parsed gates so the failure is explicit.
#
# The single "architectural" shard was retired by mission
# ci-health-charter-path-and-arch-shard-01KWRTB2 (#2397): arch-adversarial is
# now a 3-shard matrix (arch_shard_1/2/3), so the canary requires all three
# shard names to stay modellable instead of the one retired name.
_REQUIRED_CORE_MISC_SHARDS: frozenset[str] = frozenset(
    {
        "arch_shard_1",
        "arch_shard_2",
        "arch_shard_3",
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

# Mission ci-test-topology-performance-01KXBJRT WP02 (T007, GC-1/GC-2 linkage):
# `next_shard_1/2/3` become required matrix legs once WP06 (T014) converts
# `integration-tests-next` into a 3-leg matrix — mirrors
# `_REQUIRED_CORE_MISC_SHARDS`'s "a shard with no leg fails" contract for the
# `next` group WP01 registered into the shared shard-group registry.
_REQUIRED_NEXT_SHARDS: frozenset[str] = frozenset(
    {"next_shard_1", "next_shard_2", "next_shard_3"},
)


@pytest.fixture(scope="module")
def gates() -> list[gc.Gate]:
    """Parse the four suite-running workflows once per module."""
    return gc.load_gates()


@pytest.fixture(scope="module")
def universe() -> list[gc.TestRecord]:
    """Collect the whole suite once, shared by every fixture/test that needs it."""
    return gc.collect_universe()


@pytest.fixture(scope="module")
def coverage_report(universe: list[gc.TestRecord]) -> gc.CoverageReport:
    """Analyze the shared universe (no second collection pass)."""
    return gc.analyze(gc.load_gates(), universe)


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
    _assert_next_shards_complete_if_present(shards)


def _assert_next_shards_complete_if_present(shards: set[str]) -> None:
    """Conditional-on-presence completeness check for the `next_shard_*` legs.

    Mission ci-test-topology-performance-01KXBJRT WP02 (T007). A no-op TODAY:
    WP06 (T014) has not yet converted `integration-tests-next` into a 3-leg
    matrix, so no `next_shard_*` name is a parsed `Gate.shard` value and
    ``present`` below is empty — asserting the legs unconditionally would
    bare-RED this WP's own PR (freeze-before-change: WP02 must land BEFORE
    WP06 touches the workflow). The moment ANY `next_shard_N` leg appears in
    the live parsed model (WP06 lands), this auto-activates and requires ALL
    three, with no code change needed here. Extracted as its own function so
    ``test_next_shard_completeness_logic_is_wired`` below can prove the logic
    itself detects a missing leg using SYNTHETIC shard sets, independent of
    whether WP06 has landed on this branch yet (an anti-vacuous canary that
    never reds due to WP06's landing status, unlike a canary pinned to
    "legs are absent").
    """
    present = shards & _REQUIRED_NEXT_SHARDS
    if not present:
        return
    missing = _REQUIRED_NEXT_SHARDS - shards
    assert not missing, (
        f"next_shard leg(s) missing from the parsed gate model: {sorted(missing)}. "
        "WP06's integration-tests-next matrix must define all three next_shard_N "
        "legs once any one of them exists (GC-1's linkage requirement into the "
        "GC-2 model)."
    )


def test_next_shard_completeness_logic_is_wired() -> None:
    """Anti-vacuous canary (synthetic, no real gates): the conditional logic bites.

    Proves :func:`_assert_next_shards_complete_if_present` genuinely detects a
    missing leg once ANY next_shard appears — using constructed shard-name
    sets, not the live parsed model. Stays green regardless of whether WP06
    has shipped the real matrix on this branch: it is testing the FUNCTION,
    not today's CI topology, so it cannot silently rot into a no-op forever.
    """
    # No next_shard present yet -> no-op (today's real state).
    _assert_next_shards_complete_if_present({"arch_shard_1", "misc"})
    # All three present -> passes (WP06's shipped end-state).
    _assert_next_shards_complete_if_present(
        {"next_shard_1", "next_shard_2", "next_shard_3", "misc"},
    )
    # Partial (2 of 3) -> must red, naming the missing leg.
    with pytest.raises(AssertionError, match="next_shard_3"):
        _assert_next_shards_complete_if_present({"next_shard_1", "next_shard_2"})


def test_integration_tests_next_is_tier_classified_integration() -> None:
    """T006: confirm `integration-tests-next` is ALREADY tier `"integration"`.

    `_gate_tier` matches by job-name PREFIX (`_INTEGRATION_TIER_PREFIX =
    "integration-tests"`), so `integration-tests-next` — and each of its
    future `next_shard_N` matrix legs, which share the same job name — is
    already classified without any new hardcoded branch. Documented here per
    the WP02 prompt's instruction to verify rather than add a redundant
    branch (D-044/C-003): a same-tier-uniqueness regression on the `next`
    group would be caught by :func:`gc.same_tier_shard_counts` once WP06 ships
    the matrix, with zero code change required in this module for T006's tier
    registration.
    """
    gate = gc.Gate(
        workflow="ci-quality.yml",
        job="integration-tests-next",
        shard="next_shard_1",
        paths=["tests/next/"],
        marker_expr="not windows_ci and (git_repo or integration)",
    )
    assert gc._gate_tier(gate) == "integration", (
        "integration-tests-next stopped being tier-classified 'integration' — "
        "same_tier_shard_counts would silently stop covering its next_shard_N "
        "legs once WP06 ships the matrix."
    )


def test_cross_job_disjoint_selection_is_pure_and_detects_overlap() -> None:
    """T006 unit guard (synthetic, no collection): the disjointness primitive.

    ``cross_job_disjoint_selection`` must return the EMPTY set for two
    non-overlapping gate groups and the actual overlapping node-ids
    otherwise — this is the fault-injectable core of GC-2's cross-job
    disjointness clause, pinned deterministically before trusting it against
    the real orphan-sweep-vs-sync-pool case below.
    """
    universe: list[gc.TestRecord] = [
        {"nodeid": "tests/sync/test_a.py::t", "relpath": "tests/sync/test_a.py", "markers": ["fast"]},
        {
            "nodeid": "tests/sync/test_orphan_sweep.py::t",
            "relpath": "tests/sync/test_orphan_sweep.py",
            "markers": ["fast"],
        },
    ]
    orphan_gate = gc.Gate(
        workflow="ci-quality.yml", job="fast-tests-sync", shard=None,
        paths=["tests/sync/test_orphan_sweep.py"], marker_expr="not windows_ci",
    )
    pool_gate = gc.Gate(
        workflow="ci-quality.yml", job="fast-tests-sync", shard=None,
        paths=["tests/sync/"], ignores=["tests/sync/test_orphan_sweep.py"],
        marker_expr="fast and not windows_ci",
    )
    disjoint = gc.cross_job_disjoint_selection([orphan_gate], [pool_gate], universe)
    assert disjoint == frozenset(), (
        f"expected disjoint selections (ignore excludes the overlap), got {disjoint}"
    )
    # Fault-injection: drop the `--ignore` and the same two gates now overlap
    # on the orphan-sweep test — the primitive must detect it.
    pool_gate_no_ignore = gc.Gate(
        workflow="ci-quality.yml", job="fast-tests-sync", shard=None,
        paths=["tests/sync/"], marker_expr="fast and not windows_ci",
    )
    overlap = gc.cross_job_disjoint_selection([orphan_gate], [pool_gate_no_ignore], universe)
    assert overlap == frozenset({"tests/sync/test_orphan_sweep.py::t"}), (
        f"disjointness primitive failed to detect a real overlap: {overlap}"
    )


def test_orphan_sweep_and_sync_pool_are_disjoint_today(
    gates: list[gc.Gate], universe: list[gc.TestRecord],
) -> None:
    """GC-2 cross-job disjointness, evaluated against the REAL current topology.

    ``fast-tests-sync``'s parallel pool step and the orphan-sweep serial pass
    must select disjoint node-ids. Mission ci-test-topology-performance-01KXBJRT
    WP06 (T016) extracted the orphan-sweep step out of ``fast-tests-sync``
    into its own concurrent job (``fast-tests-sync-orphan-sweep``) so it stops
    sitting on ``fast-tests-sync``'s critical path — the invariant now holds
    ACROSS those two jobs instead of within one (the pool's ``--ignore``
    still excludes exactly the orphan-sweep file).
    """
    # `fast-tests-sync` / `fast-tests-sync-orphan-sweep` are parallelization-only
    # for this mission (not a GC-2b baseline target — see the scope note above
    # `gc.BASELINE_TARGETS`), so the two legs are located directly by their
    # distinguishing `(job, marker_expr)` rather than through the
    # BaselineTarget registry.
    sync_gates = [
        g
        for g in gates
        if g.workflow == "ci-quality.yml"
        and g.job in {"fast-tests-sync", "fast-tests-sync-orphan-sweep"}
    ]
    orphan_gate = next(
        g
        for g in sync_gates
        if g.job == "fast-tests-sync-orphan-sweep" and g.marker_expr == "not windows_ci"
    )
    pool_gate = next(
        g
        for g in sync_gates
        if g.job == "fast-tests-sync" and g.marker_expr == "fast and not windows_ci"
    )
    overlap = gc.cross_job_disjoint_selection([orphan_gate], [pool_gate], universe)
    assert not overlap, (
        f"{len(overlap)} test(s) double-run between the orphan-sweep step and "
        f"the parallel sync pool: {sorted(overlap)[:20]}"
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


def test_orphan_backlog_does_not_grow(
    coverage_report: gc.CoverageReport, record_property: RecordPropertyFn
) -> None:
    """Shrinkage is good news (report); growth in file count is caught above.

    Records a nudge to lock in a smaller baseline when the backlog shrinks,
    mirroring the repo's ratchet-baseline shrinkage convention. Report-only —
    routed via ``record_property`` (not ``warnings.warn``) so the diagnostic
    surfaces in the JUnit/report output without polluting the warnings channel
    NFR-006 requires to stay first-party-clean.
    """
    baseline = gc.load_baseline()
    recorded = set(baseline.get("orphan_files", []))
    current = set(coverage_report.orphan_files)
    cleared = sorted(recorded - current)
    if cleared:
        record_property(
            "gate_coverage_backlog_shrank",
            f"Gate-coverage backlog shrank by {len(cleared)} file(s) "
            f"(now {len(current)} vs baseline {len(recorded)}). Lock it in: "
            "uv run python -m tests.architectural._gate_coverage --update-baseline",
        )


def test_duplicate_selection_is_reported(
    coverage_report: gc.CoverageReport, record_property: RecordPropertyFn
) -> None:
    """Duplicates (>=2 gates) are REPORTED, never enforced — overlap is intentional.

    fast↔integration domain splits deliberately overlap; this surfaces the count
    for visibility without failing CI. Report-only — routed via
    ``record_property`` (not ``warnings.warn``) so the diagnostic surfaces in
    the JUnit/report output without polluting the warnings channel NFR-006
    requires to stay first-party-clean.
    """
    dupes = coverage_report.duplicate_nodeids
    if dupes:
        record_property(
            "gate_coverage_duplicate_selection",
            f"{len(dupes)} test(s) are selected by >=2 CI gates (duplicate run). "
            "This is report-only; some fast↔integration overlap is intentional.",
        )
    assert isinstance(dupes, list)


# ---------------------------------------------------------------------------
# GC-2b — E3 baseline node-id diff guard + its two fault seams (mission
# ci-test-topology-performance-01KXBJRT WP02, T008; FR-007/NFR-005 — this
# mission's load-bearing invariant). Every job WP06 re-topologizes must still
# execute the exact same set of tests it did before, enforced against a
# committed pre-change baseline (data-model E3), not just an internal
# partition-consistency claim (GC-1).
#
# Kept in THIS already-arch-sharded, WP02-owned module (rather than a new
# sibling file) so it inherits the arch shard-marker assignment without a
# cross-lane edit to WP01's tests/_arch_shard_map.py — the alternative the T008
# guidance names first ("a new test in test_gate_coverage.py ... or a sibling
# module").
#
# SCOPE + DESIGN: WP06 CHANGES the selected test set for the THREE jobs in
# ``gc.BASELINE_TARGETS`` (see the scope note above it) — integration-tests-next
# (T014 shard matrix), slow-tests (T015 path-narrow), and fast-tests-core-misc
# (T017 shard rebalance, a two-leg job); everything else WP06 touches is
# parallelization-only (adds ``-n auto``, same test set) and is coverage-safe by
# construction. The committed baseline for each target is a REAL native
# ``pytest --collect-only -q`` UNION across its legs
# (:func:`gc.collect_real_union_for_target` / :func:`gc.collect_job_nodeids`,
# which parse pytest's own ``-m``-honouring output — NOT the marker-dump plugin,
# which clears items before ``-m`` deselection and would freeze the UNFILTERED
# set). GC-2b then compares the modeled-current selection
# (:func:`gc._selected_nodeids` = :class:`gc.CompiledGate` over ONE shared
# :func:`gc.collect_universe`) against that REAL baseline: one collection reused
# across all parametrized cases, so this stays fast (a CI-speed mission must not
# add ~10min of per-job ``--collect-only`` fan-out to its own arch shard).
# Because the BASELINE is real and model-independent, GC-2b is itself a fidelity
# check (a mis-parsed ``-m``/path in ``selects()`` would diverge from the real
# baseline and RED); the ``next``-tier spot-check keeps that model==real proof
# LIVE at one subprocess. A comparison that only fault-injects the baseline side
# is a FAKEABLE seam for the producer side (reviewer-renata, MEDIUM); the two
# fault-injection tests below close both halves (baseline-file side AND
# producer/real-selection side).
#
# RE-SCOPE (mission test-suite-friction-remediation-01KXDKBX WP15, #2616):
# exact ``dropped``/``added`` equality over-fires on ROUTINE test-file
# add/remove — this mission alone does that 4-5x via new guard/regression
# files, forcing a ``--freeze-baselines`` refreeze every time nothing actually
# regressed. ``test_gc2b_current_selection_matches_baseline`` below now
# enforces only the LOAD-BEARING orphan-detection signal (a ``dropped``
# node-id that is a genuine orphan — still exists, selected by ZERO gates —
# via :func:`gc.gc2b_orphaned_drift`), and reports raw drift ADVISORY-only via
# ``record_property`` so a refreeze is a nudge, not a red. The two
# fault-injection tests and the ``next``-tier fidelity spot-check are
# untouched — they exercise :func:`gc.baseline_diff` / real collection
# directly and still prove true-positives.
# ---------------------------------------------------------------------------

_DIFF_PREVIEW = 20
# The sharded-tier job the scoped model-fidelity spot-check anchors on: the
# mission's `next` star — small and marker-selected, so one real collection
# proves selects()==real cheaply for the tier most at risk of a mis-model.
_FIDELITY_SPOTCHECK_SLUG = "integration-tests-next"


def _most_represented_file(nodeids: frozenset[str]) -> str:
    """The test file contributing the most node-ids in ``nodeids`` (deterministic).

    Used by the producer-side fault injection to pick an ``--ignore=`` target
    that is provably IN a job's real committed baseline — derived from the
    baseline itself rather than hard-coded, so file churn under the ``next``
    roots cannot silently make the injection a no-op (the failure mode that
    slipped the first cut: a hard-coded ``fast``-only file that the integration
    marker never selected, so ignoring it dropped nothing).
    """
    counts: dict[str, int] = {}
    for nodeid in nodeids:
        relpath = nodeid.split("::", 1)[0]
        counts[relpath] = counts.get(relpath, 0) + 1
    # Sort by (-count, name) for a stable, highest-impact pick.
    return min(counts, key=lambda relpath: (-counts[relpath], relpath))


def test_baseline_files_exist_for_all_targets() -> None:
    """Every registered :data:`gc.BASELINE_TARGETS` slug has a committed,
    NON-EMPTY baseline.

    The non-empty floor closes a vacuous-pass class: a future WP that narrows a
    selection-changing job to zero tests AND re-freezes would write an empty
    baseline that then compares equal to an empty modeled selection (green),
    silently accepting a total coverage drop. An E3 job that legitimately
    selects zero tests is itself the bug this guard should red on.
    """
    missing = [
        target.slug
        for target in gc.BASELINE_TARGETS
        if not (gc.BASELINES_DIR / f"{target.slug}-nodeids.txt").is_file()
    ]
    assert not missing, (
        f"no committed E3 baseline file for target(s): {missing}. Freeze with: "
        "uv run python -m tests.architectural._gate_coverage --freeze-baselines"
    )
    empty = [target.slug for target in gc.BASELINE_TARGETS if not gc.load_baseline_nodeids(target)]
    assert not empty, (
        f"E3 baseline is empty for target(s): {empty}. A zero-test selection is a "
        "coverage drop, not a valid baseline — investigate before re-freezing."
    )


@pytest.mark.parametrize("target", gc.BASELINE_TARGETS, ids=lambda t: t.slug)
def test_gc2b_current_selection_matches_baseline(
    target: gc.BaselineTarget,
    gates: list[gc.Gate],
    universe: list[gc.TestRecord],
    coverage_report: gc.CoverageReport,
    record_property: RecordPropertyFn,
) -> None:
    """GC-2b: the modeled-current selection has no GENUINE orphan vs. baseline.

    The committed baseline is a REAL native ``pytest --collect-only -q`` union
    across the job's legs (:func:`gc.collect_real_union_for_target`, frozen once
    by ``--freeze-baselines``). The ``current`` side is the model
    (:class:`gc.CompiledGate` via :func:`gc._selected_nodeids`) evaluated over
    ONE shared :func:`gc.collect_universe` — so all 22 parametrized cases reuse
    a single collection instead of spawning 22 real ``--collect-only``
    subprocesses per run (a CI-speed mission must not add ~10min to its own
    arch shard).

    Mission test-suite-friction-remediation-01KXDKBX WP15 (#2616) re-scopes
    this from exact symmetric-difference (which over-fires on routine
    test-file add/remove) to the LOAD-BEARING signal alone: a ``dropped``
    node-id (in the frozen baseline, not in ``current``) that is a GENUINE
    orphan today — it still exists in the collected universe AND is selected
    by ZERO of the ~40 CI gates (:func:`gc.gc2b_orphaned_drift`, reusing the
    same whole-suite orphan set :func:`gc.analyze` computes). A ``dropped``
    node-id whose file was deleted, or whose coverage moved to a DIFFERENT
    gate, is routine churn — not asserted, only reported ADVISORY-only via
    ``record_property`` (NFR-006) so a refreeze stays a nudge rather than a
    red. ``added`` (new node-ids not yet in the frozen baseline) is pure
    membership growth and never a fidelity problem — advisory-only for the
    same reason. Real fidelity is proven by the two fault-injection tests
    below (:func:`gc.baseline_diff` / real collection, direct) and the
    ``next``-tier spot-check.
    """
    current = gc._selected_nodeids(gc.gates_for_target(gates, target), universe)
    baseline = gc.load_baseline_nodeids(target)
    dropped, added = gc.baseline_diff(current, baseline)
    if dropped or added:
        record_property(
            "gc2b_baseline_drift",
            f"{target.slug}: {len(dropped)} dropped, {len(added)} added vs. the "
            "frozen E3 baseline. Advisory-only (routine test-file churn is "
            "expected); refreeze to clear: uv run python -m "
            "tests.architectural._gate_coverage --freeze-baselines",
        )
    orphaned = gc.gc2b_orphaned_drift(dropped, coverage_report.orphan_nodeids)
    assert not orphaned, (
        f"GC-2b GENUINE orphan drift for {target.slug!r}: {len(orphaned)} "
        "node-id(s) this target's baseline selected are now selected by ZERO "
        "CI gates — a real coverage-hole regression, not routine test-file "
        f"churn (first {_DIFF_PREVIEW}): {sorted(orphaned)[:_DIFF_PREVIEW]}\n"
        "Fix: restore coverage (give the test a marker/path a gate selects) "
        "or, if this drop is intentional, refreeze: uv run python -m "
        "tests.architectural._gate_coverage --freeze-baselines"
    )


def test_gc2b_orphan_drift_ignores_routine_test_file_churn() -> None:
    """T071(a): routine test-file add/remove must NOT trip the re-scoped ratchet.

    Mission test-suite-friction-remediation-01KXDKBX WP15 (#2616): this mission
    alone adds/removes guard/regression files 4-5x, and each one used to force
    a ``--freeze-baselines`` refreeze even though nothing regressed. Exercises
    :func:`gc.gc2b_orphaned_drift` directly (pure, no subprocess/fixtures —
    mirrors the fault-injection tests below) against the two shapes of
    routine churn a ``dropped`` node-id can take:

    1. the file was DELETED — it no longer exists anywhere in today's
       collected universe, so it cannot appear in ``orphan_nodeids`` (which
       :func:`gc.analyze` only ever populates from tests it actually
       collected);
    2. the file's coverage MOVED to a different gate — it still exists and is
       still selected by >=1 gate, so it is also absent from
       ``orphan_nodeids``.

    Neither shape is a genuine coverage-hole regression, so neither may
    surface from :func:`gc.gc2b_orphaned_drift`.
    """
    baseline = {
        "tests/architectural/test_deleted_guard.py::test_x",
        "tests/architectural/test_moved_guard.py::test_y",
    }
    current: frozenset[str] = frozenset()  # this target no longer selects either
    dropped, _added = gc.baseline_diff(current, baseline)
    assert dropped == baseline, "sanity: both node-ids must show up as 'dropped'"
    # Neither node-id is selected-by-zero-gates today: test_deleted_guard.py no
    # longer exists (not in the universe `analyze()` walks), test_moved_guard.py
    # is still selected by whichever gate its coverage moved to.
    orphan_nodeids: list[str] = []
    orphaned = gc.gc2b_orphaned_drift(dropped, orphan_nodeids)
    assert not orphaned, (
        f"routine test-file add/remove must not trip the re-scoped ratchet, "
        f"got {orphaned}"
    )


def test_gc2b_orphan_drift_bites_on_genuine_orphan() -> None:
    """T071(b): a genuine orphan (selected by ZERO gates) must still FAIL.

    Preserves the load-bearing GC-2b signal the re-scope (#2616) must not
    weaken: if a node-id this target's baseline selected is now selected by
    NOTHING — not the file being deleted, not coverage moving elsewhere, a
    real coverage-hole regression — :func:`gc.gc2b_orphaned_drift` must still
    surface it.
    """
    baseline = {"tests/architectural/test_regressed_guard.py::test_z"}
    current: frozenset[str] = frozenset()
    dropped, _added = gc.baseline_diff(current, baseline)
    orphan_nodeids = ["tests/architectural/test_regressed_guard.py::test_z"]
    orphaned = gc.gc2b_orphaned_drift(dropped, orphan_nodeids)
    assert orphaned == {"tests/architectural/test_regressed_guard.py::test_z"}, (
        f"a genuine orphan must still trip the re-scoped ratchet, got {orphaned}"
    )


def test_gc2b_bites_on_baseline_file_side_injection() -> None:
    """Fault-injection (baseline-file side): a tampered/stale baseline is caught.

    Simulates an out-of-band hand-edit of a committed baseline file (a node-id
    silently dropped from it while the real/current selection is unchanged) —
    ``baseline_diff`` is pure over plain iterables precisely so this needs no
    disk I/O or subprocess. This is the ORIGINAL fault-injection case, distinct
    from the producer-side case below (which reviewer-renata found missing).
    """
    current = {
        "tests/next/test_a.py::test_1",
        "tests/next/test_a.py::test_2",
        "tests/next/test_b.py::test_3",
    }
    tampered_baseline = current - {"tests/next/test_b.py::test_3"}
    dropped, added = gc.baseline_diff(current, tampered_baseline)
    assert not dropped, "nothing should be 'dropped' when only the baseline shrank"
    assert added == {"tests/next/test_b.py::test_3"}, (
        f"expected the baseline-side injection to surface as 'added', got {added}"
    )


def test_gc2b_bites_on_producer_side_selection_shrink(
    gates: list[gc.Gate], tmp_path: Path,
) -> None:
    """Fault-injection (producer side, reviewer-renata MEDIUM): a job's REAL
    selection shrinking (not the baseline file) must also red the guard.

    Closes the seam a baseline-file-only injection leaves open: a job's real
    YAML selection could shrink (e.g. a stray ``--ignore=`` on its pytest
    command) while a baseline-file-only check never notices, because it never
    re-derives the job's OWN selection from a (possibly edited) workflow.

    Builds a SYNTHETIC copy of one guarded job (``integration-tests-next``) —
    NOT the real ``ci-quality.yml``, which this WP does not own — with a
    spurious ``--ignore=`` injected, re-parses it through the REAL
    ``parse_workflow`` (no hand-rolled substitute, D-044/C-003), REAL-collects
    it via the SAME :func:`gc.collect_job_nodeids` GC-2b itself uses (not a
    modeled selection), and asserts the result is a strict subset of the
    committed baseline — proving the GC-2b comparator would RED on this
    producer-side shrink.

    Generalized over however many legs :func:`gc.gates_for_target` returns
    (mission ci-test-topology-performance-01KXBJRT WP06 T014 converted
    ``integration-tests-next`` from a single-leg job to a 3-leg
    ``next_shard_N`` matrix — each real leg only selects its OWN shard, so a
    fixture built from a single hardcoded leg would compare a partial
    selection against the FULL union baseline and false-red on every OTHER
    leg's node-ids, not just the injected file's). One synthetic job per real
    leg, each carrying that leg's own ``marker_expr`` plus the injected
    ``--ignore=``, unioned the same way :func:`gc.collect_real_union_for_target`
    unions real legs — this keeps the fixture correct whether the target is a
    single-leg job or an N-leg matrix, with no re-hardcoded leg count.
    """
    target = gc.target_by_slug("integration-tests-next")
    real_gates = gc.gates_for_target(gates, target)
    baseline = gc.load_baseline_nodeids(target)
    injected_file = _most_represented_file(baseline)
    job_blocks = "\n".join(
        f"""\
  integration-tests-next-leg-{index}:
    runs-on: ubuntu-latest
    steps:
      - run: |
          uv run python -m pytest {" ".join(real_gate.paths)} \\
            --ignore={injected_file} \\
            -m '{real_gate.marker_expr}' -q --tb=short
"""
        for index, real_gate in enumerate(real_gates)
    )
    fixture = f"name: fixture\non: push\njobs:\n{job_blocks}"
    fixture_path = tmp_path / "_producer_side_fault_injection_wf.yml"
    fixture_path.write_text(fixture, encoding="utf-8")
    shrunk_gates = gc.parse_workflow(fixture_path)
    assert len(shrunk_gates) == len(real_gates), (
        f"fixture workflow parsed into {len(shrunk_gates)} gates, expected "
        f"{len(real_gates)} (one per real leg)"
    )
    shrunk_current: frozenset[str] = frozenset().union(
        *(gc.collect_job_nodeids(gate) for gate in shrunk_gates),
    )
    assert shrunk_current < baseline, (
        "producer-side fault injection did not shrink the REAL selection: a "
        f"spurious --ignore={injected_file} on integration-tests-next's real "
        "command(s) should strictly narrow its real collection relative to the "
        "committed baseline — the GC-2b guard's producer-side seam is not closed."
    )
    dropped, _added = gc.baseline_diff(shrunk_current, baseline)
    assert all(injected_file in nodeid for nodeid in dropped), (
        f"expected every dropped node-id to come from the ignored file "
        f"{injected_file!r}, got (first {_DIFF_PREVIEW}): "
        f"{sorted(dropped)[:_DIFF_PREVIEW]}"
    )


def test_model_fidelity_spotcheck_sharded_next_tier(
    gates: list[gc.Gate], universe: list[gc.TestRecord],
) -> None:
    """Scoped model-fidelity anchor: modeled ``selects()`` == a FRESH real collect.

    GC-2b's ``current`` side is the model over a shared universe (for speed);
    this keeps a LIVE, independent proof that the model is faithful — that
    ``CompiledGate.selects()`` is not silently mis-modelling a job's ``-m``
    expr or a positional/ignore path while the modeled and real-baseline sides
    happen to agree (reviewer-renata, MEDIUM). It re-derives ONE job's
    selection through a completely independent path at runtime — a real, scoped
    ``pytest --collect-only`` subprocess (:func:`gc.collect_job_nodeids`, which
    parses pytest's own ``-m``-honouring output) — and asserts it equals the
    model over the universe.

    Scoped to the sharded ``next`` tier (not fanned out over all 22 targets):
    the mission's headline re-topologization, and a marker-selected,
    multi-positional command — exactly the shape most at risk of a mis-model —
    so the live proof costs one small collection, not twenty-two (a per-job
    real subprocess for every target would add ~10min to the arch shard, which
    a CI-speed mission must not do).
    """
    target = gc.target_by_slug(_FIDELITY_SPOTCHECK_SLUG)
    job_gates = gc.gates_for_target(gates, target)
    modeled = gc._selected_nodeids(job_gates, universe)
    fresh_real = gc.collect_real_union_for_target(target, gates)
    only_modeled = sorted(modeled - fresh_real)[:_DIFF_PREVIEW]
    only_real = sorted(fresh_real - modeled)[:_DIFF_PREVIEW]
    assert modeled == fresh_real, (
        f"model-fidelity mismatch for {target.slug!r}: CompiledGate.selects() "
        "diverges from a fresh real `pytest --collect-only` of this job's actual "
        f"command.\nonly in modeled (first {_DIFF_PREVIEW}): {only_modeled}\n"
        f"only in fresh real collection (first {_DIFF_PREVIEW}): {only_real}"
    )
