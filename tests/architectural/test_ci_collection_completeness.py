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
    ``main`` — on the GREEN PATH — evaluated with the real per-job selectors
    under the worst reachable filter state.

*Node*, not file. A file with one ``slow`` test and twenty ``fast`` ones
satisfies a file-level reading while the twenty never execute, and three of
#2957's four files are exactly that shape.

*Green path*, and the qualifier is load-bearing. The model has exactly one
deliberate fail-open term: ``needs.<job>.result == 'success'`` decides ``True``
(:data:`tests.architectural._gate_coverage._NEEDS_RESULT_RE_CONJUNCT`), because
reading it as unsatisfiable would declare every downstream job dead and make the
whole model useless. So a run in which an upstream job FAILS skips its dependents
and really does collect less than this gate assumes — correct GitHub behaviour,
and a different question from completeness. The practical consequence: an
uncollected count from this model is exact on a green run and a LOWER BOUND on a
red one.

THE MODEL IS BASELINE-FREE (deliberate, and checked below). Sanitation removes
the legacy orphan-file baseline and its update/check CLI rather than leaving a
mutable, unenforced second authority beside this oracle. This gate reads no
baseline, owns no allowlist, and has no regeneration path: the only way to make
it green is to make a job collect the test.

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
import re
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.architectural import _gate_coverage as gc

if TYPE_CHECKING:
    from collections.abc import Iterable

pytestmark = [pytest.mark.architectural, pytest.mark.fast]

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

# Non-vacuity floor for the monotonicity proof: the live workflows currently
# carry 70 filter-group atoms across 30 groups. A decomposition that stops
# finding them would make the proof silently empty, so it fails instead.
_MIN_GROUP_ATOMS = 55
# ``needs.<job>.outputs.<name>`` reference inside one condition atom. Only names
# that are declared dorny FILTER GROUPS bear on monotonicity; the same shape is
# also used for ordinary job outputs (``needs.lint.outputs.ruff_has_failures``),
# which the evaluator fails closed on and which no filter state can turn on.
_OUTPUT_REF_RE = re.compile(r"\.outputs\.([A-Za-z0-9_]+)")
# Rotations of the group ordering walked as subset chains (see the monotonicity
# test); each rotation covers every subset SIZE in a different membership order.
_MONOTONICITY_ROTATIONS = 4


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


_GATE_COVERAGE_MODULE = "_gate_coverage"

# Every ``_gate_coverage`` surface that reads or writes a frozen baseline. The
# point of trap 1 is that this module reaches NONE of them.
_BASELINE_SURFACES = frozenset(
    {
        "BASELINE_PATH",
        "baseline_diff",
        "check",
        "freeze_baselines",
        "load_baseline",
        "load_baseline_nodeids",
        "update_baseline",
        "write_baseline_nodeids",
    },
)

# Opening a baseline by literal path would reach it without naming a surface at
# all, so the checker also watches path CONSTRUCTION (call arguments and ``/``
# operands) for these names.
_BASELINE_FILENAMES: tuple[str, ...] = (
    "_gate_coverage_baseline.json",
    "_baselines.yaml",
)


def _dotted(node: ast.expr) -> str | None:
    """``a.b.c`` for a pure ``Name``/``Attribute`` chain, else ``None``."""
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return ".".join(reversed(parts))


def _names_the_module(dotted: str, aliases: frozenset[str]) -> bool:
    """Whether ``dotted`` denotes ``_gate_coverage`` — by alias or by full path."""
    return dotted in aliases or dotted.split(".")[-1] == _GATE_COVERAGE_MODULE


def _module_aliases(tree: ast.Module) -> frozenset[str]:
    """Every local name bound to ``_gate_coverage``, transitively.

    Covers the aliased from-import (``… import _gate_coverage as gc``), the
    aliased dotted import (``import pkg._gate_coverage as gate``) and plain
    re-bindings (``other = gc``), so renaming the import is not an escape.
    """
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            aliases.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == _GATE_COVERAGE_MODULE
            )
        elif isinstance(node, ast.Import):
            aliases.update(
                alias.asname
                for alias in node.names
                if alias.asname
                and alias.name.split(".")[-1] == _GATE_COVERAGE_MODULE
            )
    while True:
        grown = {
            target.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name)
            and node.value.id in aliases
            for target in node.targets
            if isinstance(target, ast.Name)
        } - aliases
        if not grown:
            break
        aliases |= grown
    return frozenset(aliases)


def _attribute_reach(node: ast.Attribute, aliases: frozenset[str]) -> set[str]:
    """``gc.load_baseline`` / ``pkg._gate_coverage.load_baseline``."""
    if node.attr not in _BASELINE_SURFACES:
        return set()
    dotted = _dotted(node)
    if dotted is None:
        return set()
    prefix = dotted.rpartition(".")[0]
    return {f"attribute {dotted}"} if _names_the_module(prefix, aliases) else set()


def _import_reach(node: ast.ImportFrom) -> set[str]:
    """``from tests.architectural._gate_coverage import load_baseline``."""
    if (node.module or "").split(".")[-1] != _GATE_COVERAGE_MODULE:
        return set()
    return {
        f"import {alias.name}"
        for alias in node.names
        if alias.name in _BASELINE_SURFACES
    }


def _getattr_reach(node: ast.Call, aliases: frozenset[str]) -> set[str]:
    """``getattr(gc, "load_baseline")`` — the string-indirection escape.

    Only the ``getattr`` BUILTIN counts: the behavioural half of trap 1
    legitimately calls ``monkeypatch.setattr(gc, "load_baseline", …)`` to sabotage
    the reader, and sabotaging it is the opposite of reaching it.
    """
    getattr_arity = 2
    if not (isinstance(node.func, ast.Name) and node.func.id == "getattr"):
        return set()
    if len(node.args) < getattr_arity:
        return set()
    dotted = _dotted(node.args[0])
    name = node.args[1]
    if dotted is None or not _names_the_module(dotted, aliases):
        return set()
    if isinstance(name, ast.Constant) and name.value in _BASELINE_SURFACES:
        return {f"getattr {name.value}"}
    return set()


def _path_literal_reach(node: ast.AST) -> set[str]:
    """A baseline filename used to BUILD a path: a call argument or a ``/`` operand.

    Deliberately narrower than "any string containing the name": this module's
    prose NAMES the baseline it refuses to touch, and so does
    :data:`_BASELINE_FILENAMES` itself. Both are inert text; ``Path("…json")``
    and ``root / "…json"`` are not.
    """
    if isinstance(node, ast.Call):
        # Keyword arguments are call arguments too. Reading only ``node.args``
        # let ``open(file="…_baseline.json")`` escape BOTH halves of the proof:
        # the static reader missed it, and the behavioural half cannot see it
        # either because it never goes through the module whose attributes that
        # half sabotages. Review found this; it is the one escape that defeated
        # the backstop as well as the reader.
        operands: list[ast.expr] = [*node.args, *(kw.value for kw in node.keywords)]
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        operands = [node.left, node.right]
    else:
        return set()
    return {
        f"literal path {name}"
        for operand in operands
        for text in _string_parts(operand)
        for name in _BASELINE_FILENAMES
        if name in text
    }


def _string_parts(node: ast.expr) -> list[str]:
    """Static string content of *node*: a plain literal or an f-string's fixed parts.

    ``Path(f"{root}/_gate_coverage_baseline.json")`` is a ``JoinedStr``, not a
    ``Constant``, so reading only ``Constant`` let it slip past. The interpolated
    slots are unknowable statically; the literal segments around them are not,
    and the filename lives in one of those.
    """
    if isinstance(node, ast.Constant):
        return [node.value] if isinstance(node.value, str) else []
    if isinstance(node, ast.JoinedStr):
        return [
            part.value
            for part in node.values
            if isinstance(part, ast.Constant) and isinstance(part.value, str)
        ]
    return []


def baseline_reaches(source: str) -> set[str]:
    """Every way ``source`` could reach the orphan ratchet's baseline machinery.

    An AST read (not a substring scan) so a module's prose may NAME the surfaces
    it refuses to touch — explaining the refusal is the point — while four real
    access shapes still trip it: attribute access through any name bound to the
    module, ``from … import`` of a baseline symbol, ``getattr`` with a string
    constant, and path construction from a baseline filename.

    Residual, stated rather than papered over: a name assembled at runtime
    (``"load_" + "baseline"``), a filename bound to a variable before reaching
    ``Path``, ``importlib.import_module``, ``__import__``, ``sys.modules[…]``, a
    module returned from a function, and tuple-unpack or walrus alias binding
    (``a, b = gc, None``; ``(alias := gc)``) are outside this source checker.
    The load-bearing companion assertion is structural: the removed orphan
    baseline APIs and sidecar must not exist on the live model at all.
    """
    tree = ast.parse(source)
    aliases = _module_aliases(tree)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            found |= _attribute_reach(node, aliases)
        elif isinstance(node, ast.ImportFrom):
            found |= _import_reach(node)
        elif isinstance(node, ast.Call):
            found |= _getattr_reach(node, aliases) | _path_literal_reach(node)
        elif isinstance(node, ast.BinOp):
            found |= _path_literal_reach(node)
    return found


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


def test_oracle_has_independent_pr_route_and_operator_gate(
    universe: list[gc.TestRecord],
    gates: list[gc.Gate],
    models: dict[str, gc.WorkflowModel],
) -> None:
    """A selector regression cannot deselect both this oracle and its route proof.

    ``arch-adversarial`` is an in-repository operator gate through
    ``quality-gate``; it is not represented here as a GitHub branch-protection
    required context.  The module also carries ``fast`` so workflow changes run
    this proof independently in ``fast-tests-core-misc``.
    """
    nodeid = (
        "tests/architectural/test_ci_collection_completeness.py::"
        "test_every_test_node_is_collected_on_a_push_to_main"
    )
    record = next((item for item in universe if item["nodeid"] == nodeid), None)
    assert record is not None, f"retained oracle did not collect as {nodeid}"

    selecting = {
        gate.job
        for gate in gates
        if gc.CompiledGate(gate).selects(
            record["relpath"], record["nodeid"], set(record["markers"])
        )
    }
    assert "arch-adversarial" in selecting
    assert "fast-tests-core-misc" in selecting, (
        "the route proof lost its independent fast owner; an arch-selector "
        "regression could now deselect both the oracle and this proof"
    )

    ci = models["ci-quality.yml"]
    assert gc.gate_is_always_on_modulo_full_ci_block(
        ci.job_if["arch-adversarial"], require_always=True
    )
    assert ci.job_needs["arch-adversarial"] == ()
    assert "arch-adversarial" in ci.job_needs["quality-gate"]


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
) -> None:
    """Baseline-free by source and by successful live computation.

    A resurrected baseline/update surface would make a large finding one command
    away from vanishing. This module may name those forbidden shapes only in its
    static fault probes; the live oracle must compute without them.
    """
    forbidden = baseline_reaches(_THIS_FILE.read_text(encoding="utf-8"))
    assert not forbidden, (
        f"this gate reaches baseline machinery {sorted(forbidden)}; a "
        "baseline-backed completeness gate can be silenced by regenerating the "
        "baseline, which is the greenwashing path WP10 exists to avoid"
    )
    removed_surfaces = {
        "BASELINE_PATH",
        "_baseline_payload",
        "_print_check",
        "check",
        "load_baseline",
        "update_baseline",
    }
    resurrected = sorted(name for name in removed_surfaces if hasattr(gc, name))
    assert not resurrected, f"removed orphan-baseline API resurfaced: {resurrected}"
    assert not _THIS_FILE.with_name(_BASELINE_FILENAMES[0]).exists(), (
        "removed mutable orphan baseline sidecar resurfaced"
    )

    report = gc.main_push_uncollected(universe, gates, models)
    assert report.total == len(universe)


# Source shapes that all reach the same baseline reader. The first version of
# this guard caught only the first of them, which is the failure mode this
# mission exists to eliminate: a guard that LOOKS airtight and is not. Each
# entry is a self-mutation of the module under test, expressed as source.
_BASELINE_ESCAPES: dict[str, str] = {
    "aliased attribute": (
        "from tests.architectural import _gate_coverage as gc\n"
        "gc.load_baseline()\n"
    ),
    "getattr indirection": (
        "from tests.architectural import _gate_coverage as gc\n"
        "getattr(gc, 'load_baseline')()\n"
    ),
    "direct symbol import": (
        "from tests.architectural._gate_coverage import load_baseline\n"
        "load_baseline()\n"
    ),
    "renamed module import": (
        "import tests.architectural._gate_coverage as gate\n"
        "gate.load_baseline()\n"
    ),
    "fully dotted access": (
        "import tests.architectural._gate_coverage\n"
        "tests.architectural._gate_coverage.load_baseline()\n"
    ),
    "rebound alias": (
        "from tests.architectural import _gate_coverage as gc\n"
        "sneaky = gc\n"
        "sneaky.update_baseline()\n"
    ),
    "literal baseline path": (
        "from pathlib import Path\n"
        "Path('tests/architectural/_gate_coverage_baseline.json').read_text()\n"
    ),
    "literal path by joining": (
        "from pathlib import Path\n"
        "data = Path('tests/architectural') / '_gate_coverage_baseline.json'\n"
    ),
    # The two below defeated BOTH halves of trap 1 until review found them: the
    # static reader missed them, and the behavioural half never sees them because
    # they bypass the module whose attributes it sabotages.
    "literal path as a keyword argument": (
        "open(file='tests/architectural/_gate_coverage_baseline.json').read()\n"
    ),
    "literal path inside an f-string": (
        "from pathlib import Path\n"
        "root = 'tests/architectural'\n"
        "data = Path(f'{root}/_gate_coverage_baseline.json').read_text()\n"
    ),
}

# Prose may name every surface it refuses to touch — that is the whole point of
# reading the AST instead of grepping.
_BASELINE_PROSE_ONLY = (
    '"""Refuses to call load_baseline or read _gate_coverage_baseline.json."""\n'
    "from tests.architectural import _gate_coverage as gc\n"
    "gc.collect_universe()\n"
)


@pytest.mark.parametrize(
    ("shape", "source"),
    sorted(_BASELINE_ESCAPES.items()),
)
def test_the_baseline_reach_checker_catches_every_known_escape(
    shape: str, source: str,
) -> None:
    """NFR-005 applied to the checker itself: each escape must be reported."""
    assert baseline_reaches(source), (
        f"the baseline-reach checker misses the {shape!r} escape, so trap 1 "
        "could be walked around by rewriting one import line"
    )


def test_the_baseline_reach_checker_does_not_fire_on_prose() -> None:
    """Naming the forbidden surfaces in a docstring is not reaching them."""
    assert not baseline_reaches(_BASELINE_PROSE_ONLY)


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


def _all_filter_groups(models: dict[str, gc.WorkflowModel]) -> frozenset[str]:
    return frozenset(name for model in models.values() for name in model.filter_groups)


def _condition_atoms(expr: str) -> list[str]:
    """Decompose an ``if:`` into exactly the terms the evaluator decides.

    Mirrors :func:`gc.job_runs_under`'s own descent (``||`` then ``&&``,
    parentheses respected) using only its public helpers, so the two cannot
    disagree about what an atom is.
    """
    inner = gc.normalize_condition(expr)
    if not inner:
        return []
    for operator in ("||", "&&"):
        parts = gc.split_top_level(inner, operator)
        if len(parts) > 1:
            return [atom for part in parts for atom in _condition_atoms(part)]
    return [inner]


def test_every_group_atom_is_a_positive_unnegated_test(
    models: dict[str, gc.WorkflowModel],
) -> None:
    """WHY one worst-case evaluation settles every filter state — structurally.

    Monotonicity of ``active_job_keys`` in ``active_groups`` is a property of the
    workflow's SHAPE, not of two sampled points. It holds because every atom that
    reads a filter group is a positive equality (``… == 'true'``), never a
    negation and never a ``!=``, and the only combinators above those atoms are
    ``&&`` / ``||`` — both monotone. This test asserts that shape directly, atom
    by atom, over every job condition in every modelled workflow.

    A ``needs.changes.outputs.<g> != 'true'`` term, or a ``!(… == 'true')``, would
    make a job DISAPPEAR as the filter state grows, and the worst-case-only
    evaluation would stop being sound. That is what this catches.
    """
    all_groups = _all_filter_groups(models)
    empty: frozenset[str] = frozenset()
    checked = 0
    for workflow, model in models.items():
        for job, if_value in model.job_if.items():
            if not isinstance(if_value, str):
                continue
            for atom in _condition_atoms(if_value):
                if not set(_OUTPUT_REF_RE.findall(atom)) & all_groups:
                    continue
                checked += 1
                where = f"{workflow}::{job}: {atom}"
                assert not atom.startswith("!"), (
                    f"a NEGATED filter-group atom ({where}) makes job activation "
                    "non-monotone in the group set, so evaluating only the "
                    "no-group-matched state no longer settles every filter state"
                )
                assert not gc.job_runs_under(
                    atom, event_name=gc.PUSH_EVENT, active_groups=empty,
                ), f"group atom is satisfied with NO group active ({where})"
                assert gc.job_runs_under(
                    atom, event_name=gc.PUSH_EVENT, active_groups=all_groups,
                ), (
                    f"group atom is NOT satisfied with every group active "
                    f"({where}); either it is not a positive group test or the "
                    "evaluator does not model it"
                )
    assert checked >= _MIN_GROUP_ATOMS, (
        f"only {checked} filter-group atoms were examined (floor "
        f"{_MIN_GROUP_ATOMS}); the decomposition stopped seeing the dorny "
        "topology, so this test proves nothing about monotonicity"
    )


def test_active_jobs_grow_monotonically_with_the_filter_state(
    models: dict[str, gc.WorkflowModel],
) -> None:
    """The structural property, exercised end-to-end over real subset chains.

    Not two points: for each of several rotations of the group ordering this
    walks the full chain ``∅ ⊂ {g1} ⊂ {g1,g2} ⊂ … ⊂ all`` and asserts the active
    set never shrinks, plus every singleton against the worst case. Every subset
    SIZE is therefore covered, and each rotation covers a different membership
    order. The reason it holds for the subsets NOT sampled is
    :func:`test_every_group_atom_is_a_positive_unnegated_test`.
    """
    worst = gc.main_push_active_jobs(models)
    ordered = sorted(_all_filter_groups(models))

    def active(groups: frozenset[str]) -> frozenset[gc.JobKey]:
        return gc.active_job_keys(
            models, event_name=gc.PUSH_EVENT, active_groups=groups,
        )

    assert worst == active(frozenset())
    for group in ordered:
        assert worst <= active(frozenset({group})), (
            f"activating the {group!r} filter group REMOVED a job from the "
            "active set; job activation is not monotone in the group state"
        )
    for rotation in range(_MONOTONICITY_ROTATIONS):
        offset = (rotation * len(ordered)) // _MONOTONICITY_ROTATIONS
        sequence = ordered[offset:] + ordered[:offset]
        previous = active(frozenset())
        for size in range(1, len(sequence) + 1):
            current = active(frozenset(sequence[:size]))
            assert previous <= current, (
                f"the active set shrank going from {size - 1} to {size} active "
                f"groups (rotation {rotation}); one worst-case evaluation no "
                "longer settles the whole filter-state family"
            )
            previous = current
    assert previous == active(frozenset(ordered))


def test_analyze_default_still_models_every_job(
    universe: list[gc.TestRecord],
    gates: list[gc.Gate],
) -> None:
    """The ``active_jobs=None`` default is unchanged for existing callers."""
    assert gc.analyze(gates, universe) == gc.analyze(gates, universe, None)
