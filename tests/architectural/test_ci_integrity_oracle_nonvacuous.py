"""CI-integrity oracle: non-vacuity + planted-orphan + the real #2967 fix (WP17).

FR-016 / SC-004 / #2967. This module is the SO#5 red-first anchor for the
collection-completeness / two-authority integrity oracle. It carries three
non-vacuity guards plus the concrete #2967 bug reproduction:

* **The real #2967 defect** — a *zero-producer / inert-slot bare name* (a gate
  that resolves to no real producer: no parsed positional paths AND no marker)
  currently falls back to the whole ``tests`` tree in
  :class:`tests.architectural._gate_coverage.CompiledGate` and silently claims
  coverage of *every* test. The anchor test below asserts such a gate covers
  NOTHING; it reds on base for exactly that defect (not "the oracle is absent").
* **Planted-orphan negative** — a src-backed routing group wired to no job reds
  the rebuilt oracle (it must not pass while a real orphan exists).
* **Non-vacuity floor (DIR-043)** — the oracle fails if it evaluates an empty
  set, so a rebuild that "passes" because it checked nothing is itself a defect.

The rebuilt oracle lives in the sibling helper ``_ci_integrity_oracle`` and is
**lazy-imported** inside each test body, so this file *collects* green on base
(before the helper exists) and the red is a failed behavioural assertion, never
a collection/import error.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.architectural import _gate_coverage as gc

if TYPE_CHECKING:
    from tests.architectural._gate_coverage import TestRecord

pytestmark = [pytest.mark.architectural, pytest.mark.fast]


def _one_test_universe() -> list[TestRecord]:
    """A minimal single-test universe (no marker) for coverage reasoning."""
    return [
        {
            "relpath": "tests/sample/test_sample.py",
            "nodeid": "tests/sample/test_sample.py::test_sample",
            "markers": [],
        },
    ]


# ---------------------------------------------------------------------------
# T088 anchor — the REAL #2967 zero-producer / inert-slot bare-name false-pass.
# ---------------------------------------------------------------------------


def test_zero_producer_bare_name_is_not_counted_as_covered() -> None:
    """#2967: an inert gate (no paths, no marker) must cover NOTHING.

    A gate that parses to no positional paths AND no marker expression is a
    *zero-producer / inert slot* — a bare name that resolves to no real
    producer. On base, ``CompiledGate`` falls back to the whole ``tests`` tree
    with no marker to narrow it, so it selects every test and the single test
    below is reported covered (``orphan_nodeids == []``). That is the #2967
    false-pass. The fixed model must treat the inert gate as covering nothing,
    leaving the test an orphan.
    """
    inert = gc.Gate(
        workflow="synthetic",
        job="inert-slot",
        shard=None,
        paths=[],
        marker_expr=None,
    )
    universe = _one_test_universe()

    report = gc.analyze([inert], universe)

    assert report.orphan_nodeids == ["tests/sample/test_sample.py::test_sample"], (
        "a zero-producer / inert-slot gate (no paths, no marker) must NOT count "
        "as covering any test — it resolves to no real producer (#2967). On base "
        "it falls back to whole-tree coverage and silently claims the test, which "
        "is the exact false-pass this guard reproduces."
    )


def test_marker_narrowed_whole_tree_fallback_still_covers_its_marked_tests() -> None:
    """The #2967 fix must stay NARROW: an empty-paths gate WITH a marker is safe.

    ``ci-windows`` builds its test list dynamically (``git grep``) so its gate
    parses to no positional paths, but it runs ``-m windows_ci`` — the marker
    narrows the whole-tree fallback to exactly the windows-only tests. That
    legitimate coverage must survive the fix; only the marker-LESS inert gate is
    demoted to covering nothing.
    """
    windows_gate = gc.Gate(
        workflow="ci-windows.yml",
        job="windows-critical",
        shard=None,
        paths=[],
        marker_expr="windows_ci",
    )
    universe: list[TestRecord] = [
        {
            "relpath": "tests/win/test_win.py",
            "nodeid": "tests/win/test_win.py::test_win",
            "markers": ["windows_ci"],
        },
        {
            "relpath": "tests/lin/test_lin.py",
            "nodeid": "tests/lin/test_lin.py::test_lin",
            "markers": ["fast"],
        },
    ]

    report = gc.analyze([windows_gate], universe)

    # The windows-marked test is covered; the unmarked one is the only orphan.
    assert report.orphan_nodeids == ["tests/lin/test_lin.py::test_lin"]


# ---------------------------------------------------------------------------
# T090 — non-vacuity floor (DIR-043): the oracle fails if it evaluates nothing.
# ---------------------------------------------------------------------------


def test_non_vacuity_floor_empty_router_raises() -> None:
    """A router with no src-backed routing group makes the oracle evaluate nothing.

    A vacuous oracle that "passes" because it checked an empty set is the exact
    defect FR-016 closes, so it must raise rather than return clean.
    """
    from scripts.ci.gate_selection import Router

    from tests.architectural import _ci_integrity_oracle as oracle

    empty = Router(
        filters={"any_src": ("src/**",)},  # only the fail-closed probe → 0 routing groups
        job_gates={"ruff": frozenset()},
    )

    with pytest.raises(oracle.OracleVacuousError):
        oracle.assert_no_zero_gated_group(empty)


# ---------------------------------------------------------------------------
# T089 — planted-orphan negative: a group wired to no job reds the oracle.
# ---------------------------------------------------------------------------


def test_planted_orphan_group_reds_the_oracle() -> None:
    """A src-backed group that gates NO job is a zero-gated orphan and must red.

    ``orphan`` carries a ``src/`` glob (so it is a routing group a src change can
    hit) but appears in no job ``if:``; a change confined to it routes to no
    test/arch job. The oracle — driven by the single ``select_gates`` authority —
    must detect the empty gate set and raise.
    """
    from scripts.ci.gate_selection import Router

    from tests.architectural import _ci_integrity_oracle as oracle

    router = Router(
        filters={
            "cli": ("src/specify_cli/cli/**",),
            "orphan": ("src/orphan/**",),
            "any_src": ("src/**",),
        },
        job_gates={
            "ruff": frozenset(),  # always-on, no group
            "architectural-heavy": frozenset({"cli"}),  # a real code shard
            "tests-cli": frozenset({"cli"}),
            # NOTHING gates `orphan` → planted orphan.
        },
    )

    with pytest.raises(oracle.ZeroGatedGroupError) as excinfo:
        oracle.assert_no_zero_gated_group(router)
    assert "orphan" in str(excinfo.value)


def test_planted_orphan_is_reported_by_the_map_builder() -> None:
    """The derived group→gate map exposes the orphan as an empty selection."""
    from scripts.ci.gate_selection import Router

    from tests.architectural import _ci_integrity_oracle as oracle

    router = Router(
        filters={
            "cli": ("src/specify_cli/cli/**",),
            "orphan": ("src/orphan/**",),
            "any_src": ("src/**",),
        },
        job_gates={
            "architectural-heavy": frozenset({"cli"}),
            "tests-cli": frozenset({"cli"}),
        },
    )

    assert oracle.zero_gated_groups(router) == frozenset({"orphan"})


# ---------------------------------------------------------------------------
# T089/T092 — the REAL on-disk router: positive wiring assertions (SC-004).
# ---------------------------------------------------------------------------


def test_real_router_has_no_zero_gated_group() -> None:
    """Every src-backed group on the real ci-router.yml selects >=1 code shard."""
    from scripts.ci.gate_selection import load_router

    from tests.architectural import _ci_integrity_oracle as oracle

    router = load_router()
    # Non-vacuous: there is a real set to evaluate.
    assert router.src_backed_groups
    oracle.assert_no_zero_gated_group(router)  # must not raise
    assert oracle.zero_gated_groups(router) == frozenset()


def test_enumerated_must_run_gates_are_all_wired() -> None:
    """SC-004: the enumerated must-run gates are wired in the reinstated topology.

    The always-on lint/regen/terminology/layer gates run unconditionally, and
    the heavy architectural battery is code-scoped over exactly the src-backed
    routing groups (contract router-two-authority §"Derived").
    """
    from scripts.ci.gate_selection import load_router

    from tests.architectural import _ci_integrity_oracle as oracle

    router = load_router()
    oracle.assert_must_run_gates_wired(router)  # must not raise
    # Content assertions (not a cardinality count).
    assert router.always_on_jobs >= oracle.MUST_RUN_ALWAYS_ON_GATES
    assert oracle.HEAVY_BATTERY_GATE in router.code_shard_jobs
    assert router.job_gates[oracle.HEAVY_BATTERY_GATE] == router.src_backed_groups


def test_unwired_must_run_gate_reds_the_oracle() -> None:
    """Dropping an enumerated must-run gate must red the wiring oracle."""
    from scripts.ci.gate_selection import Router

    from tests.architectural import _ci_integrity_oracle as oracle

    # A router missing `terminology` (an enumerated always-on must-run gate).
    router = Router(
        filters={"cli": ("src/specify_cli/cli/**",), "any_src": ("src/**",)},
        job_gates={
            "ruff": frozenset(),
            "import-linter": frozenset(),
            "regen-check": frozenset(),
            "layer-rules": frozenset(),
            "architectural-heavy": frozenset({"cli"}),
        },
    )

    with pytest.raises(oracle.MustRunGateUnwiredError):
        oracle.assert_must_run_gates_wired(router)


# ---------------------------------------------------------------------------
# T093 — runtime-vs-static boundary: the oracle proves WIRING only.
# ---------------------------------------------------------------------------


def test_oracle_proves_wiring_not_runtime() -> None:
    """The oracle proves static WIRING; runtime is each job's own result (SC-004).

    Evidenced structurally: the oracle consumes the single ``gate_selection``
    authority (no second parser — it never imports ``yaml`` or re-parses the
    workflow), runs no subprocess, and inspects no job result/conclusion. It can
    therefore never over-claim that a gate ran green — only that it is wired.
    """
    import inspect

    from tests.architectural import _ci_integrity_oracle as oracle

    src = inspect.getsource(oracle)
    # Single authority, no second parser (reviewer anti-#2476 check).
    assert "from scripts.ci.gate_selection import" in src
    assert "select_gates(" in src
    # Proves-wiring, not runtime: the oracle does not re-parse YAML, shell out,
    # or read a job's runtime outcome. Match the import/call machinery, not the
    # prose (the docstring legitimately explains *why* it imports no parser).
    assert "import yaml" not in src
    assert "safe_load(" not in src
    assert "import subprocess" not in src
    assert oracle.RUNTIME_EVIDENCE_BOUNDARY  # documented boundary constant
