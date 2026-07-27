"""SC-013 / FR-013 / NFR-005: nothing is uncollectable on a push to ``main``.

Issue `#2957 <https://github.com/Priivacy-ai/spec-kitty/issues/2957>`_. Four
frozen-contract test files broke on ``main`` and ``main`` stayed quiet, because
the only jobs that collect them — ``fast-tests-cli`` / ``integration-tests-cli``
— are gated on ``needs.changes.outputs.cli == 'true'``, and the ``cli`` filter
covers only ``src/specify_cli/cli/**``, ``tests/cli/**`` and
``tests/specify_cli/cli/**``. A push whose diff misses those paths skips all
three ``cli``-gated jobs, so their reds are not merely unnoticed — they are
structurally uncollectable.

**This is WP01's defect one layer up.** A frozen-contract test that no
main-branch job collects is exactly as inert as a schema slot nothing produces.

WHAT THIS MODULE ASSERTS (the amended SC-013). Not "the union of job selections
equals the full collection" — that is only satisfiable by dismantling the dorny
topology, which roughly seventeen invariants across ``tests/architectural/``
pin. It asserts the property that actually matters:

    every collected test NODE is selected by >= 1 job that RUNS on a push to
    ``main``, evaluated with the real per-job selectors under the worst
    reachable filter state.

*Node*, not file. A file with one ``slow`` test and twenty ``fast`` ones
satisfies a file-level reading while the twenty never execute, and three of
#2957's four files are exactly that shape.

THE MODEL IS BASELINE-FREE (deliberate, and checked below). The sibling ratchet
``test_gate_coverage.py`` freezes today's orphan surface in
``_gate_coverage_baseline.json`` and its own failure message ends "regenerate
the baseline with ``--update-baseline``". Bolting gating-awareness onto that
ratchet would have produced a four-figure orphan list plus one documented
command that erases it. This gate therefore reads no baseline, owns no
allowlist, and has no regeneration path: the only way to make it green is to
make a job collect the test.

WHY THE WORST-CASE FILTER STATE, AND WHY ONE EVALUATION SUFFICES. See
:func:`tests.architectural._gate_coverage.main_push_active_jobs` — the
"no group matched" state is reachable (a push touching only an unclaimed
``tests/**`` directory), and a job ``if:`` is monotone in the active-group set,
so completeness there implies completeness everywhere richer.

COST. One whole-tree ``--collect-only`` (~50 s, module-scoped, the same pass
five sibling arch guards already take) and an in-process, sub-second gate
simulation over it. No subprocess per job.
"""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.architectural import _gate_coverage as gc

if TYPE_CHECKING:
    from collections.abc import Iterable

pytestmark = pytest.mark.architectural

_THIS_FILE = Path(__file__)

# The four files #2957 names: frozen contracts that broke on ``main`` while
# ``main`` reported nothing.
ISSUE_2957_FILES: tuple[str, ...] = (
    "tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py",
    "tests/specify_cli/cli/commands/test_completion_fast_path.py",
    "tests/specify_cli/cli/commands/test_mission_repair.py",
    "tests/cli/commands/test_merge_status_commit.py",
)

# The disjunct that keeps a filter-gated suite job alive on a push to ``main``
# while PRESERVING its ``needs.changes.outputs.<group>`` reference — deleting
# the reference instead would orphan the group and red
# ``test_src_filter_coverage.test_every_named_group_gates_a_test_running_job_live``.
# Precedented in this workflow by ``slow-tests`` and ``e2e-cross-cutting``.
PUSH_DISJUNCT = "github.event_name == 'push'"

# A path under no gate's positional roots and under no marker-selected sweep —
# the planted violation NFR-005 requires the gate to reject.
_PLANTED_RELPATH = "tests/_planted_uncollected_probe/test_planted.py"
_PLANTED_NODEID = f"{_PLANTED_RELPATH}::test_planted"

_MAX_REPORTED = 25


@pytest.fixture(scope="module")
def universe() -> list[gc.TestRecord]:
    """Every collected test with its marker set (one ``--collect-only`` pass)."""
    return gc.collect_universe()


@pytest.fixture(scope="module")
def models() -> dict[str, gc.WorkflowModel]:
    return gc.load_workflow_models()


@pytest.fixture(scope="module")
def gates() -> list[gc.Gate]:
    return gc.load_gates()


def _gate_coverage_attributes_used(module_path: Path) -> set[str]:
    """Every ``gc.<name>`` attribute this module reads, via its own AST.

    An AST read (not a substring scan) so the module's prose may NAME the
    baseline surfaces it refuses to touch — explaining the refusal is the point
    — while any real access still trips the check.
    """
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    return {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "gc"
    }


def _summarize(relpaths: Iterable[str]) -> str:
    ordered = sorted(set(relpaths))
    shown = "\n".join(f"    {path}" for path in ordered[:_MAX_REPORTED])
    if len(ordered) > _MAX_REPORTED:
        shown += f"\n    ... and {len(ordered) - _MAX_REPORTED} more file(s)"
    return shown


# ---------------------------------------------------------------------------
# SC-013 — the invariant.
# ---------------------------------------------------------------------------


def test_every_test_node_is_collected_on_a_push_to_main(
    universe: list[gc.TestRecord],
    gates: list[gc.Gate],
    models: dict[str, gc.WorkflowModel],
) -> None:
    """SC-013: no collected node is skipped by every job a push to ``main`` starts."""
    report = gc.main_push_uncollected(universe, gates, models)
    active = sorted(gc.main_push_active_jobs(models))
    assert report.orphan_count == 0, (
        f"{report.orphan_count} of {report.total} collected test NODES "
        f"({len(report.orphan_files)} files) run in NO job on a push to "
        f"{gc.PRIMARY_BRANCH!r} — a regression in them cannot turn the branch "
        "red (issue #2957).\n"
        f"Jobs that do run in this state ({len(active)}): "
        f"{[f'{workflow}::{job}' for workflow, job in active]}\n"
        "Files with at least one such node:\n"
        f"{_summarize(report.orphan_files)}\n\n"
        "FIX THE TOPOLOGY, NOT THIS TEST. A filter-gated suite job earns its "
        f"place on a push by adding `|| {PUSH_DISJUNCT}` to its group "
        "disjunction — keeping the `needs.changes.outputs.<group>` reference "
        "intact, as `slow-tests` and `e2e-cross-cutting` already do. There is "
        "no baseline and no allowlist to add the file to."
    )


def test_issue_2957_named_files_are_collected_on_a_push_to_main(
    universe: list[gc.TestRecord],
    gates: list[gc.Gate],
    models: dict[str, gc.WorkflowModel],
) -> None:
    """The four originally-reported frozen contracts, named so a revert is legible."""
    present = {record["relpath"] for record in universe}
    missing_from_tree = [path for path in ISSUE_2957_FILES if path not in present]
    assert not missing_from_tree, (
        "#2957's files are no longer in the tree; re-point ISSUE_2957_FILES at "
        f"their current homes rather than deleting the check: {missing_from_tree}"
    )
    uncollected = set(gc.main_push_uncollected(universe, gates, models).orphan_files)
    still_dark = sorted(set(ISSUE_2957_FILES) & uncollected)
    assert not still_dark, (
        "the exact files #2957 reported are STILL collected by no job on a push "
        f"to {gc.PRIMARY_BRANCH!r}: {still_dark}"
    )


def test_worst_case_filter_state_is_reachable(
    universe: list[gc.TestRecord],
    models: dict[str, gc.WorkflowModel],
) -> None:
    """The "no group matched" state this gate evaluates is real, not hypothetical.

    Two parsed facts make it reachable: ``on.push.paths`` admits a push that
    touches only ``tests/**``, and at least one collected test lives under a
    ``tests/`` directory that no dorny filter group globs. Such a push starts
    ``ci-quality`` with every named group false — and the fail-open catch-all
    stays silent because it fires only on an unclaimed ``src/**`` change.
    """
    model = models["ci-quality.yml"]
    assert "tests/**" in model.push_paths
    test_globs = {
        glob
        for globs in model.filter_groups.values()
        for glob in globs
        if glob.startswith("tests/")
    }
    claimed_roots = {glob.split("*", 1)[0].rstrip("/") for glob in test_globs}
    unclaimed = sorted(
        {
            record["relpath"]
            for record in universe
            if not any(record["relpath"].startswith(f"{root}/") for root in claimed_roots)
        },
    )
    assert unclaimed, (
        "every collected test now lives under a dorny-globbed tests/ root; the "
        "zero-group push state may no longer be reachable and this gate's "
        "worst-case choice needs re-deriving before it is weakened"
    )


# ---------------------------------------------------------------------------
# NFR-005 — the gate rejects planted violations (and only violations).
# ---------------------------------------------------------------------------


def test_selfmutation_planted_uncollected_node_is_reported(
    universe: list[gc.TestRecord],
    gates: list[gc.Gate],
    models: dict[str, gc.WorkflowModel],
) -> None:
    """A marker-less test under an unrouted directory must surface as uncollected."""
    planted: gc.TestRecord = {
        "nodeid": _PLANTED_NODEID,
        "relpath": _PLANTED_RELPATH,
        "markers": [],
    }
    mutated = gc.main_push_uncollected([*universe, planted], gates, models)
    assert _PLANTED_NODEID in mutated.orphan_nodeids, (
        "the completeness gate did not notice a planted test that no job "
        "collects — it is vacuous and would pass over a real coverage hole"
    )


def test_selfmutation_removing_the_push_disjunct_is_reported(
    universe: list[gc.TestRecord],
    gates: list[gc.Gate],
    models: dict[str, gc.WorkflowModel],
) -> None:
    """Reverting the fix must red: strip the push disjuncts and the hole reopens.

    This is the discriminating half of NFR-005. The planted-node case proves the
    gate reacts to a missing test; this proves it reacts to the exact topology
    regression #2957 describes — a suite job that stops running on ``main``.
    """
    reverted = {
        name: _model_without_push_disjunct(model) for name, model in models.items()
    }
    report = gc.main_push_uncollected(universe, gates, reverted)
    assert report.orphan_count > 0, (
        "removing every `|| github.event_name == 'push'` disjunct left the "
        "collection complete — the gate is not actually measuring job "
        "activation and cannot detect the #2957 regression"
    )
    cli_files = sorted(
        path
        for path in report.orphan_files
        if path.startswith(("tests/cli/", "tests/specify_cli/cli/"))
    )
    assert cli_files, (
        "the `cli`-gated files #2957 names did not reappear as uncollected when "
        "the push disjuncts were removed; the mutation is not exercising the "
        "gating path it claims to"
    )


def _model_without_push_disjunct(model: gc.WorkflowModel) -> gc.WorkflowModel:
    """A copy of ``model`` whose job conditions lost their push allowance.

    Operates on the parsed ``if:`` scalars only — the workflow file on disk is
    never touched.
    """
    stripped: dict[str, str | bool | None] = {
        job: (
            _drop_push_disjunct(if_value)
            if isinstance(if_value, str) and PUSH_DISJUNCT in if_value
            else if_value
        )
        for job, if_value in model.job_if.items()
    }
    return replace(model, job_if=stripped)


def _drop_push_disjunct(expr: str) -> str:
    """Rewrite ``expr`` with every ``github.event_name == 'push'`` term falsified."""
    inner = gc.normalize_condition(expr)
    disjuncts = gc.split_top_level(inner, "||")
    if len(disjuncts) > 1:
        kept = [
            part for part in disjuncts if gc.normalize_condition(part) != PUSH_DISJUNCT
        ]
        if not kept:
            return "false"
        rebuilt = " || ".join(_drop_push_disjunct(part) for part in kept)
        # Always re-parenthesize: the rewritten disjunction may sit inside an
        # enclosing ``&&``, and a redundant pair of parens around a single
        # survivor is stripped again by ``normalize_condition``.
        return f"({rebuilt})"
    conjuncts = gc.split_top_level(inner, "&&")
    if len(conjuncts) > 1:
        return " && ".join(_drop_push_disjunct(part) for part in conjuncts)
    return "false" if inner == PUSH_DISJUNCT else inner


# ---------------------------------------------------------------------------
# Trap 1 — the gate must not be able to launder its findings into a baseline.
# ---------------------------------------------------------------------------


def test_gate_reads_no_ratchet_baseline(
    universe: list[gc.TestRecord],
    gates: list[gc.Gate],
    models: dict[str, gc.WorkflowModel],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Baseline-free, proved twice: by source and by behaviour.

    ``test_gate_coverage.py``'s orphan ratchet ends its failure message with
    "regenerate the baseline with ``--update-baseline``". If this gate could
    reach that file, a four-figure finding would be one documented command away
    from vanishing. So: this module names no baseline surface, and the
    computation still completes with the baseline reader sabotaged.
    """
    touched = _gate_coverage_attributes_used(_THIS_FILE)
    forbidden = touched & {
        "BASELINE_PATH",
        "load_baseline",
        "update_baseline",
        "check",
        "freeze_baselines",
        "load_baseline_nodeids",
        "write_baseline_nodeids",
    }
    assert not forbidden, (
        f"this gate reaches baseline machinery {sorted(forbidden)}; a "
        "baseline-backed completeness gate can be silenced by regenerating the "
        "baseline, which is the greenwashing path WP10 exists to avoid"
    )

    def _refuse() -> dict[str, object]:
        message = "the completeness gate must not read the orphan ratchet baseline"
        raise AssertionError(message)

    monkeypatch.setattr(gc, "load_baseline", _refuse)
    monkeypatch.setattr(gc, "BASELINE_PATH", tmp_path / "absent.json")
    report = gc.main_push_uncollected(universe, gates, models)
    assert report.total == len(universe)


# ---------------------------------------------------------------------------
# The activation model itself (pure units — no collection, no subprocess).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        (None, True),
        (True, True),
        (False, False),
        ("always()", True),
        ("always() && needs.changes.outputs.cli == 'true'", False),
        ("always() && needs.changes.outputs.core_misc == 'true'", False),
        (
            "always() && (needs.changes.outputs.cli == 'true' "
            "|| github.event_name == 'push')",
            True,
        ),
        ("always() && github.event_name == 'push'", True),
        ("always() && github.event_name == 'pull_request'", False),
        ("always() && github.event_name != 'pull_request'", True),
        ("needs.fast-tests-cli.result == 'success'", True),
        ("needs.kernel-tests.result != 'failure'", True),
        (
            "${{ (always()) && "
            "!contains(github.event.pull_request.labels.*.name, 'pr:deferred') }}",
            True,
        ),
        ("some.unmodelled.expression == 'true'", False),
    ],
)
def test_job_runs_under_push_with_no_group_active(
    condition: str | bool | None,
    expected: bool,
) -> None:
    """The activation truth table, including the fail-closed unknown-term case."""
    assert (
        gc.job_runs_under(
            condition, event_name=gc.PUSH_EVENT, active_groups=frozenset(),
        )
        is expected
    )


def test_job_runs_under_honours_an_active_group() -> None:
    """A group-gated job runs once its group is active — the monotonicity premise."""
    condition = "always() && needs.changes.outputs.cli == 'true'"
    assert not gc.job_runs_under(
        condition, event_name=gc.PUSH_EVENT, active_groups=frozenset(),
    )
    assert gc.job_runs_under(
        condition, event_name=gc.PUSH_EVENT, active_groups=frozenset({"cli"}),
    )


def test_label_guard_blocks_only_pull_requests() -> None:
    """``!contains(labels...)`` is vacuously true when there is no pull request."""
    guard = "!contains(github.event.pull_request.labels.*.name, 'pr:skip-ci')"
    assert gc.job_runs_under(guard, event_name=gc.PUSH_EVENT, active_groups=frozenset())
    assert not gc.job_runs_under(
        guard, event_name=gc.PULL_REQUEST_EVENT, active_groups=frozenset(),
    )


@pytest.mark.parametrize(
    ("expr", "operator", "expected"),
    [
        ("a && b", "&&", ["a", "b"]),
        ("a && (b && c)", "&&", ["a", "(b && c)"]),
        ("a || b || c", "||", ["a", "b", "c"]),
        ("(a || b) && c", "||", ["(a || b) && c"]),
        ("", "&&", []),
    ],
)
def test_split_top_level_respects_parentheses(
    expr: str, operator: str, expected: list[str],
) -> None:
    assert gc.split_top_level(expr, operator) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("${{ always() }}", "always()"),
        ("((always()))", "always()"),
        ("always()\n  && github.event_name == 'push'", "always() && github.event_name == 'push'"),
        ("(a) && (b)", "(a) && (b)"),
    ],
)
def test_normalize_condition(raw: str, expected: str) -> None:
    assert gc.normalize_condition(raw) == expected


def test_release_workflow_does_not_run_on_a_push_to_main(
    models: dict[str, gc.WorkflowModel],
) -> None:
    """``release.yml`` is tag-triggered, so its jobs cannot cover a main push.

    Recorded as a live fact rather than an assumption: if release.yml ever gains
    a ``main`` push trigger, the completeness model must start counting it.
    """
    assert not gc.workflow_runs_on_push(models["release.yml"])
    assert gc.workflow_runs_on_push(models["ci-quality.yml"])


def test_active_jobs_grow_monotonically_with_the_filter_state(
    models: dict[str, gc.WorkflowModel],
) -> None:
    """The premise that one worst-case evaluation settles every filter state."""
    worst = gc.main_push_active_jobs(models)
    all_groups = frozenset(
        name for model in models.values() for name in model.filter_groups
    )
    richer = gc.active_job_keys(
        models, event_name=gc.PUSH_EVENT, active_groups=all_groups,
    )
    assert worst <= richer


def test_analyze_default_still_models_every_job(
    universe: list[gc.TestRecord],
    gates: list[gc.Gate],
) -> None:
    """The ``active_jobs=None`` default is unchanged for existing callers."""
    assert gc.analyze(gates, universe) == gc.analyze(gates, universe, None)
