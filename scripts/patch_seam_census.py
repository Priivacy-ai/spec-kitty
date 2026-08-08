#!/usr/bin/env python3
"""AST census of ``patch()`` seams and the assertions that read them.

Mission ``sync-sleep-count-3136-01KZ9B5A``, WP03. This is the instrument behind
SC-001, SC-002 and SC-013 — and, because a census that simply *printed* the
expected table would satisfy all three, it is pinned by a committed control
fixture and a self-mutation arm in
``tests/architectural/test_patch_seam_census_control.py`` (SC-015).

**This is a reporter, not a gate.** It exits 0 on any successful analysis
regardless of what it finds. The mechanism-keyed gate is a separate deliverable.

Why the mechanism and not the string
------------------------------------
Keying on the literal ``time.sleep`` would refuse exactly one spelling. This
census keys on what ``unittest.mock._get_target`` actually does: it splits the
target on the **last** dot and imports the left half, so ``patch("a.b.c.attr")``
mutates whatever ``a.b.c`` resolves to. When that resolves to a ``ModuleType``
whose ``__name__`` **differs** from the dotted path, the patch is reaching
*through* one module to mutate a shared object owned by another — the defect
class, whatever it is spelled.

Why not the literal FR-005 predicate
------------------------------------
FR-005 as worded refuses any target whose penultimate segment resolves to a
``ModuleType``. Measured over ``tests/sync/``, that flags **649 of 664 sites
(97.7%)** — because that is simply how ``_get_target`` works, including for the
357 *correct* own-module patches. Built to the letter the gate is unshippable,
and the natural reaction is a hardcoded exclusion list, which is precisely the
vacuity the instrument exists to prevent. Every report therefore prints the
literal-predicate figure beside the narrowed buckets so the over-breadth stays
visible rather than being quietly dropped.

The narrowed discriminator is: resolved module ``__name__`` **≠** the dotted
module path (reach-through), **or** the resolved module is not first-party
(direct foreign).

The first-party boundary is a **definitional choice**, not a fact. It is derived
from ``src/``, overridable with ``--first-party-roots``, and echoed into every
``--json`` payload under ``first_party_roots`` so no report hides the definition
that produced its buckets.

Import identity
---------------
``scripts/`` has no ``__init__.py``, so it is an implicit namespace package, and
``pytest.ini`` deliberately keeps ``.`` off ``pythonpath`` to prevent one source
file being loaded under two module names. This script therefore inserts the
repository root and imports its sibling under its canonical ``scripts.`` name,
so the resolver — and its verdict enum — has exactly one module identity
regardless of entry point. There is **one** resolver, and it lives in
``check_patch_targets.py``; this file must never grow its own import walk.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.check_patch_targets import (  # noqa: E402
    PatchTargetOutcome,
    extract_targets,
    resolve_patch_target,
)

# Installed distributions and test-tree roots that are first-party but are not
# directories under src/. Declared, not inferred, so the boundary is auditable.
_DECLARED_EXTRA_ROOTS = frozenset({"tests", "spec_kitty_events", "spec_kitty_tracker"})

# Attribute names that constitute a "sleep seam". `_sleep` is the module-local
# alias form; `sleep` covers the reach-through `time.sleep` shape.
_SLEEP_ATTRS = frozenset({"sleep", "_sleep"})

# The module whose sleep seam the SC-002 contract lines are about. Declared and
# overridable (--seam-module) and echoed into --json, for the same reason the
# first-party root set is: it is a scope decision, and a scope decision that
# only exists inside the code is unauditable. `tests/sync/` also contains a
# `specify_cli.sync.batch` sleep seam, which is a genuine corruptible assertion
# but is out-of-class for this mission's contract.
_DEFAULT_SEAM_MODULE = "specify_cli.tracker.saas_client"

# The verdicts that make a read of a patched seam *corruptible*: the patch
# mutates an object the naming module does not own, so an unrelated caller
# touching the same shared object changes this test's verdict. `own_module` is
# deliberately absent — see `_disposition`, which has always called it
# `correct-by-alias`. Keeping the two in one constant is what stops the report
# and the disposition vocabulary drifting apart again.
_CORRUPTIBLE_VERDICTS = frozenset(
    {PatchTargetOutcome.REACH_THROUGH.value, PatchTargetOutcome.FOREIGN.value}
)

PATCH_FORMS = ("decorator", "context_manager", "call")

# Cardinality contributed by each assert_* mock method. The value is what the
# method actually constrains about the number of calls — `assert_called_with`
# constrains the *last* call, not how many, so it contributes 0.
_ASSERT_METHOD_CARDINALITY = {
    "assert_called_once": 1,
    "assert_called_once_with": 1,
    "assert_not_called": 0,
    "assert_called": 0,
    "assert_called_with": 0,
    "assert_any_call": 0,
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PatchSite:
    """One ``patch("<literal>")`` call found by the AST walker."""

    file: str
    line: int
    node_id: str
    patch_form: str
    target: str
    module: str
    attr: str
    verdict: str
    resolved_module: str | None
    binds: str | None = None


@dataclass(frozen=True, slots=True)
class Assertion:
    """One assertion that reads a patched mock (or its ``side_effect`` sink)."""

    file: str
    line: int
    node_id: str
    mock_name: str
    assertion_form: str
    n: int
    reads_sleep_seam: bool
    delays: list[float] | None = None


@dataclass
class CensusResult:
    """The single in-memory analysis every renderer consumes."""

    first_party_roots: frozenset[str]
    seam_module: str = _DEFAULT_SEAM_MODULE
    files_scanned: dict[str, int] = field(default_factory=dict)
    sites: list[PatchSite] = field(default_factory=list)
    assertions: list[Assertion] = field(default_factory=list)
    drives: list[Assertion] = field(default_factory=list)

    @property
    def buckets(self) -> dict[str, int]:
        counts = {outcome.value: 0 for outcome in PatchTargetOutcome}
        for site in self.sites:
            counts[site.verdict] += 1
        return counts

    @property
    def literal_predicate_flagged(self) -> int:
        """Sites the *literal* FR-005 predicate would flag (penultimate = module)."""
        module_verdicts = {
            PatchTargetOutcome.OWN_MODULE.value,
            PatchTargetOutcome.REACH_THROUGH.value,
            PatchTargetOutcome.FOREIGN.value,
        }
        return sum(1 for s in self.sites if s.verdict in module_verdicts)

    @property
    def sleep_seam_sites(self) -> list[PatchSite]:
        return [s for s in self.sites if s.attr in _SLEEP_ATTRS]

    @property
    def seam_sleep_sites_by_bind(self) -> dict[tuple[str, str, str], PatchSite]:
        """Declared-seam sleep sites, keyed by the mock name each one binds.

        Keyed on ``(file, node_id, binds)`` and never on ``(file, binds)``:
        ``mock_sleep`` recurs across ~30 functions in a single 1400-line test
        module, so a file-wide key silently collapses distinct sites onto one
        another and attributes one site's verdict to another site's assertions.
        """
        return {
            (s.file, s.node_id, s.binds): s for s in self.seam_sleep_sites if s.binds
        }

    @property
    def sleep_assertions(self) -> list[Assertion]:
        """Assertions that **read** a sleep seam on the declared seam module.

        **Verdict-agnostic by construction.** This is SC-001's second
        denominator, and `spec.md:551-555` requires it to hold at ``5`` while
        ``corruptible_assertions`` falls to ``0`` — "these three denominators
        must not move; only ``corruptible_assertions`` may". A report that
        renders both from one list can never satisfy that pair, and no
        measurement over the *pre-fix* tree can notice, because pre-fix every
        seam site happens to be ``reach_through``.

        SC-001's denominators are explicitly the ``saas_client`` slice
        (`spec.md:556-557`), so the scoping to ``seam_sleep_sites`` is what makes
        them comparable to the criterion. The wider set — which includes the
        ``specify_cli.sync.batch`` and ``specify_cli.sync.client`` seams — stays
        available as ``all_sleep_attr_assertions``.
        """
        nodes = {(s.file, s.node_id) for s in self.seam_sleep_sites}
        return [a for a in self.assertions if a.reads_sleep_seam and (a.file, a.node_id) in nodes]

    @property
    def corruptible(self) -> list[Assertion]:
        """The verdict-filtered subset of :attr:`sleep_assertions`.

        An assertion is corruptible when **the site it actually reads** patches
        a seam the naming module does not own. Deciding this from the node's
        sleep-seam membership alone contradicts this module's own
        ``_disposition``, which classifies ``own_module`` as
        ``correct-by-alias``: after FR-012's retargets every ``saas_client``
        sleep patch is an own-module alias patch, so a node-only predicate
        reports the whole class still open on the very tree that closed it.
        """
        sites = self.seam_sleep_sites_by_bind
        out: list[Assertion] = []
        for assertion in self.sleep_assertions:
            site = sites.get((assertion.file, assertion.node_id, assertion.mock_name))
            if site is not None and site.verdict in _CORRUPTIBLE_VERDICTS:
                out.append(assertion)
        return out

    @property
    def all_sleep_attr_assertions(self) -> list[Assertion]:
        return [a for a in self.assertions if a.reads_sleep_seam]

    @property
    def seam_sleep_sites(self) -> list[PatchSite]:
        """Sleep-seam sites on the declared seam module (SC-002 / T020 scope)."""
        return [
            s for s in self.sleep_seam_sites if s.target.startswith(f"{self.seam_module}.")
        ]

    @property
    def sleep_nodes(self) -> list[dict[str, str]]:
        """Nodes that **carry** a sleep assertion — SC-001's denominator.

        Deliberately derived from the assertions, not from the patch sites: a
        node can patch the sleep seam and assert nothing about it (14 nodes on
        the pre-fix ``tests/sync/`` patch the seam; only 4 read it). The
        patch-site view is ``seam_patch_nodes``.

        Derived from :attr:`sleep_assertions` and **not** from
        :attr:`corruptible`: SC-001 pins this denominator at ``4`` in both tree
        states while ``corruptible_assertions`` falls to ``0``, so a
        corruptible-derived version would collapse to ``0`` exactly when the fix
        lands.
        """
        seen: dict[tuple[str, str], None] = {}
        for a in self.sleep_assertions:
            seen.setdefault((a.file, a.node_id), None)
        return [{"file": f, "node_id": n} for f, n in seen]

    @property
    def seam_patch_nodes(self) -> list[dict[str, str]]:
        """Nodes that patch the declared sleep seam, whether or not they read it."""
        seen: dict[tuple[str, str], None] = {}
        for site in self.seam_sleep_sites:
            seen.setdefault((site.file, site.node_id), None)
        return [{"file": f, "node_id": n} for f, n in seen]

    @property
    def all_sleep_attr_nodes(self) -> list[dict[str, str]]:
        seen: dict[tuple[str, str], None] = {}
        for site in self.sleep_seam_sites:
            seen.setdefault((site.file, site.node_id), None)
        return [{"file": f, "node_id": n} for f, n in seen]


# ---------------------------------------------------------------------------
# First-party boundary
# ---------------------------------------------------------------------------


def default_first_party_roots(repo_root: Path) -> frozenset[str]:
    """Derive the first-party root set from ``src/`` plus declared extras."""
    src = repo_root / "src"
    derived = {
        entry.name
        for entry in src.iterdir()
        if entry.is_dir() and not entry.name.startswith((".", "_"))
    }
    return frozenset(derived | _DECLARED_EXTRA_ROOTS)


# ---------------------------------------------------------------------------
# Patch-site extraction (AST only — NFR-007)
# ---------------------------------------------------------------------------


def _is_patch_call(node: ast.AST) -> bool:
    """True for ``patch(...)`` and the ``mock.patch(...)`` attribute form."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "patch"
    if isinstance(func, ast.Attribute):
        return func.attr == "patch"
    return False


def _literal_target(call: ast.Call) -> str | None:
    """The first positional argument, if it is a string constant."""
    if not call.args:
        return None
    first = call.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def _iter_functions(tree: ast.AST) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            yield node


def _decorator_patch_calls(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
) -> list[ast.Call]:
    return [d for d in node.decorator_list if _is_patch_call(d) and isinstance(d, ast.Call)]


@dataclass(frozen=True, slots=True)
class _RawCall:
    """A located ``patch()`` call before its target is resolved."""

    call: ast.Call
    form: str
    func: ast.FunctionDef | ast.AsyncFunctionDef | None
    binds: str | None
    qualname: str


def _walk_patch_calls(
    node: ast.AST,
    func: ast.FunctionDef | ast.AsyncFunctionDef | None,
    out: list[_RawCall],
    prefix: str = "",
) -> None:
    """Locate every ``patch()`` call and label it with its syntactic form.

    A plain recursive descent rather than ``ast.walk`` because the form and the
    enclosing function both depend on *where* the call sits, which a flat walk
    discards. Three forms are distinguished:

    * ``decorator`` — in a function's ``decorator_list``.
    * ``context_manager`` — a ``with`` item's context expression.
    * ``call`` — anything else, **including calls inside a function body** such
      as ``return patch("...")`` in a fixture helper. Restricting this form to
      module level silently under-counts; on this tree it lost exactly one site
      (``tests/sync/test_sync_action_gate.py:184``) and moved three reported
      figures.
    """
    if isinstance(node, ast.ClassDef):
        # Class-level @patch decorators apply to every test method in the
        # class. They are real patch sites and must be counted; omitting them
        # silently lost 5 sites on this tree (TestSyncFeatureDossier).
        for call in _decorator_patch_calls(node):
            out.append(_RawCall(call, "decorator", func, None, f"{prefix}{node.name}"))
        for child in node.body:
            _walk_patch_calls(child, func, out, f"{prefix}{node.name}::")
        return

    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        decorators = _decorator_patch_calls(node)
        bindings = _decorator_bindings(node, decorators)
        qualname = f"{prefix}{node.name}"
        for call in decorators:
            out.append(_RawCall(call, "decorator", node, bindings.get(id(call)), qualname))
        for child in node.body:
            _walk_patch_calls(child, node, out, prefix)
        return

    if isinstance(node, ast.With | ast.AsyncWith):
        for item in node.items:
            expr = item.context_expr
            if _is_patch_call(expr) and isinstance(expr, ast.Call):
                var = item.optional_vars
                bound = var.id if isinstance(var, ast.Name) else _sink_bindings(expr)
                out.append(
                    _RawCall(expr, "context_manager", func, bound, _qual(func, prefix))
                )
            else:
                _walk_patch_calls(expr, func, out, prefix)
        for child in node.body:
            _walk_patch_calls(child, func, out, prefix)
        return

    if isinstance(node, ast.Call) and _is_patch_call(node):
        out.append(_RawCall(node, "call", func, _sink_bindings(node), _qual(func, prefix)))
        return

    for descendant in ast.iter_child_nodes(node):
        _walk_patch_calls(descendant, func, out, prefix)


def _qual(func: ast.FunctionDef | ast.AsyncFunctionDef | None, prefix: str) -> str:
    return f"{prefix}{func.name}" if func is not None else "<module>"


def _decorator_bindings(
    func: ast.FunctionDef | ast.AsyncFunctionDef, calls: Sequence[ast.Call]
) -> dict[int, str]:
    """Map each decorator patch call to the parameter name it binds.

    Decorators apply bottom-up: the decorator **closest** to ``def`` supplies the
    first injected parameter. So source order is reversed before zipping against
    the positional parameters (``self``/``cls`` skipped).
    """
    params = [a.arg for a in func.args.args if a.arg not in {"self", "cls"}]
    bindings: dict[int, str] = {}
    for index, call in enumerate(reversed(calls)):
        if index < len(params):
            bindings[id(call)] = params[index]
    return bindings


# ---------------------------------------------------------------------------
# Read-side matcher — per-form recognisers dispatched from a table (T016)
# ---------------------------------------------------------------------------


def _attr_chain_root(node: ast.AST) -> str | None:
    """The root ``Name`` of an attribute chain like ``a.b.c``."""
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _int_constant(node: ast.AST) -> int | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    return None


def _referenced_names(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _build_alias_map(func: ast.AST, mocks: set[str]) -> dict[str, str]:
    """Resolve local aliases back to the mock they derive from.

    One level of this is load-bearing, and the canonical shape needs two::

        sleep_calls = mock_sleep.call_args_list      # alias -> mock
        assert len(sleep_calls) == 3
        delays = [c.args[0] for c in sleep_calls]    # alias -> alias -> mock
        assert delays == [0.9, 2.0, 4.4]

    Without alias resolution a probe misses **both** assertions entirely. This
    walks assignments in source order, so chained aliases resolve transitively.
    """
    aliases: dict[str, str] = {}
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        for name in _referenced_names(node.value):
            if name in mocks:
                aliases[target.id] = name
                break
            if name in aliases:
                aliases[target.id] = aliases[name]
                break
    return aliases


def _resolve_mock(name: str | None, mocks: set[str], aliases: dict[str, str]) -> str | None:
    if name is None:
        return None
    if name in mocks:
        return name
    return aliases.get(name)


def _literal_floats(nodes: Sequence[ast.expr]) -> list[float] | None:
    """The literal numeric values of a sequence, or None if any is symbolic.

    ``test_final_sync_diagnostics.py:309`` asserts against *named constants*
    rather than literals, so its delay sequence is deliberately not derivable —
    it stays a corruptible assertion in the JSON payload without inventing a
    literal for the SC-002 contract lines.
    """
    out: list[float] = []
    for node in nodes:
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            out.append(float(node.value))
        else:
            return None
    return out


def _recognise_assert_method(
    node: ast.AST, mocks: set[str], aliases: dict[str, str]
) -> tuple[str, str, int, list[float] | None] | None:
    """``mock.assert_called_once_with(...)`` and friends."""
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return None
    call = node.value
    if not isinstance(call.func, ast.Attribute):
        return None
    method = call.func.attr
    if not method.startswith("assert_"):
        return None
    owner = _resolve_mock(_attr_chain_root(call.func.value), mocks, aliases)
    if owner is None:
        return None
    if method == "assert_has_calls" and call.args:
        first = call.args[0]
        n = len(first.elts) if isinstance(first, ast.List) else 0
        return (method, owner, n, None)
    return (
        method,
        owner,
        _ASSERT_METHOD_CARDINALITY.get(method, 0),
        _literal_floats(call.args),
    )


def _recognise_call_count(
    test: ast.AST, mocks: set[str], aliases: dict[str, str]
) -> tuple[str, str, int, list[float] | None] | None:
    """``assert mock.call_count == N``."""
    if not isinstance(test, ast.Compare) or not isinstance(test.ops[0], ast.Eq):
        return None
    left = test.left
    if not isinstance(left, ast.Attribute) or left.attr != "call_count":
        return None
    owner = _resolve_mock(_attr_chain_root(left.value), mocks, aliases)
    n = _int_constant(test.comparators[0])
    if owner is None or n is None:
        return None
    return ("call_count", owner, n, None)


def _recognise_len_call_args(
    test: ast.AST, mocks: set[str], aliases: dict[str, str]
) -> tuple[str, str, int, list[float] | None] | None:
    """``assert len(mock.call_args_list) == N`` — alias permitted."""
    if not isinstance(test, ast.Compare) or not isinstance(test.ops[0], ast.Eq):
        return None
    left = test.left
    if not isinstance(left, ast.Call) or not isinstance(left.func, ast.Name):
        return None
    if left.func.id != "len" or not left.args:
        return None
    owner = _resolve_mock(_attr_chain_root(left.args[0]), mocks, aliases)
    n = _int_constant(test.comparators[0])
    if owner is None or n is None:
        return None
    return ("len_call_args_list", owner, n, None)


def _recognise_whole_list_equality(
    test: ast.AST, mocks: set[str], aliases: dict[str, str]
) -> tuple[str, str, int, list[float] | None] | None:
    """``assert delays == [...]`` — whole-list equality via an alias or sink."""
    if not isinstance(test, ast.Compare) or not isinstance(test.ops[0], ast.Eq):
        return None
    right = test.comparators[0]
    if not isinstance(right, ast.List):
        return None
    owner = _resolve_mock(_attr_chain_root(test.left), mocks, aliases)
    if owner is None:
        return None
    return ("whole_list_equality", owner, len(right.elts), _literal_floats(right.elts))


def _recognise_membership(
    test: ast.AST, mocks: set[str], aliases: dict[str, str]
) -> tuple[str, str, int, list[float] | None] | None:
    """``assert x in [c.args[0] for c in mock.call_args_list]`` — asserts NO count.

    Reporting ``n`` from the length of the printed delay list would say ``n=1``
    here — honest about what it printed, and wrong about what the assertion
    constrains. The ``in`` form must report ``n=0``.
    """
    if not isinstance(test, ast.Compare) or not isinstance(test.ops[0], ast.In):
        return None
    for name in _referenced_names(test):
        owner = _resolve_mock(name, mocks, aliases)
        if owner is not None:
            return ("membership", owner, 0, None)
    return None


def _recognise_call_args_read(
    test: ast.AST, mocks: set[str], aliases: dict[str, str]
) -> tuple[str, str, int, list[float] | None] | None:
    """Any remaining read of ``.call_args`` / ``.call_args_list``."""
    for node in ast.walk(test):
        if not isinstance(node, ast.Attribute) or node.attr not in {
            "call_args",
            "call_args_list",
        }:
            continue
        owner = _resolve_mock(_attr_chain_root(node.value), mocks, aliases)
        if owner is not None:
            return ("call_args_read", owner, 0, None)
    return None


# Ordered: the first recogniser that matches wins. Membership is tried before
# the generic call_args read so the `in` form keeps its n=0 label.
_ASSERT_RECOGNISERS = (
    _recognise_call_count,
    _recognise_len_call_args,
    _recognise_whole_list_equality,
    _recognise_membership,
    _recognise_call_args_read,
)


def _recognise_assert_stmt(
    node: ast.AST, mocks: set[str], aliases: dict[str, str]
) -> tuple[str, str, int, list[float] | None] | None:
    if not isinstance(node, ast.Assert):
        return None
    for recogniser in _ASSERT_RECOGNISERS:
        hit = recogniser(node.test, mocks, aliases)
        if hit is not None:
            return hit
    return None


# ---------------------------------------------------------------------------
# Per-file analysis
# ---------------------------------------------------------------------------


def _site_from_call(
    call: ast.Call,
    *,
    path: Path,
    node_id: str,
    form: str,
    roots: frozenset[str],
    binds: str | None,
) -> PatchSite | None:
    target = _literal_target(call)
    if target is None:
        return None
    verdict = resolve_patch_target(target, first_party_roots=roots)
    return PatchSite(
        file=str(path),
        line=call.lineno,
        node_id=node_id,
        patch_form=form,
        target=target,
        module=verdict.module_path,
        attr=verdict.attr,
        verdict=verdict.outcome.value,
        resolved_module=verdict.resolved_module_name,
        binds=binds,
    )


def _sink_bindings(call: ast.Call) -> str | None:
    """The sink list name for ``side_effect=<name>.append``."""
    for kw in call.keywords:
        if kw.arg != "side_effect":
            continue
        if isinstance(kw.value, ast.Attribute) and kw.value.attr == "append":
            return _attr_chain_root(kw.value.value)
    return None


def _collect_function_assertions(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    path: Path,
    qualname: str,
    sites: Sequence[PatchSite],
) -> tuple[list[Assertion], list[Assertion]]:
    sleep_mocks = {s.binds for s in sites if s.attr in _SLEEP_ATTRS and s.binds}
    all_mocks = {s.binds for s in sites if s.binds}
    mocks = {m for m in all_mocks if m}
    aliases = _build_alias_map(func, mocks)
    found: list[Assertion] = []
    drives: list[Assertion] = []
    for node in ast.walk(func):
        # Every recognised form (Assign / Expr / Assert) is a statement, and
        # narrowing here is what makes `node.lineno` well-typed below.
        if not isinstance(node, ast.stmt):
            continue
        driven = _recognise_side_effect_assignment(node, mocks, aliases)
        if driven is not None:
            drives.append(
                Assertion(
                    file=str(path),
                    line=node.lineno,
                    node_id=qualname,
                    mock_name=driven,
                    assertion_form="side_effect_assignment",
                    n=0,
                    reads_sleep_seam=driven in sleep_mocks,
                )
            )
        hit = _recognise_assert_method(node, mocks, aliases) or _recognise_assert_stmt(
            node, mocks, aliases
        )
        if hit is None:
            continue
        form, owner, n, delays = hit
        found.append(
            Assertion(
                file=str(path),
                line=node.lineno,
                node_id=qualname,
                mock_name=owner,
                assertion_form=form,
                n=n,
                reads_sleep_seam=owner in sleep_mocks,
                delays=delays,
            )
        )
    return found, drives


def _recognise_side_effect_assignment(
    node: ast.AST, mocks: set[str], aliases: dict[str, str]
) -> str | None:
    """``mock_monotonic.side_effect = [0.0, 301.0]`` — a driver, not an assertion.

    It asserts nothing, so it never enters ``corruptible_assertions``. But it
    makes the mock load-bearing for the test's outcome, so a sibling seam driven
    this way is *disposed*, not undisposed.
    """
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        return None
    target = node.targets[0]
    if not isinstance(target, ast.Attribute) or target.attr != "side_effect":
        return None
    return _resolve_mock(_attr_chain_root(target.value), mocks, aliases)


def analyse_file(
    path: Path, roots: frozenset[str], forms: frozenset[str]
) -> tuple[list[PatchSite], list[Assertion], list[Assertion]]:
    """Parse one file and return its patch sites and read-side assertions."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return [], [], []

    raw: list[_RawCall] = []
    _walk_patch_calls(tree, None, raw)

    sites: list[PatchSite] = []
    by_func: dict[int, tuple[ast.FunctionDef | ast.AsyncFunctionDef, str, list[PatchSite]]] = {}
    for entry in raw:
        if entry.form not in forms:
            continue
        site = _site_from_call(
            entry.call,
            path=path,
            node_id=entry.qualname,
            form=entry.form,
            roots=roots,
            binds=entry.binds,
        )
        if site is None:
            continue
        sites.append(site)
        if entry.func is not None:
            by_func.setdefault(id(entry.func), (entry.func, entry.qualname, []))[2].append(site)

    assertions: list[Assertion] = []
    drives: list[Assertion] = []
    for func, qualname, func_sites in by_func.values():
        found, driven = _collect_function_assertions(func, path, qualname, func_sites)
        assertions.extend(found)
        drives.extend(driven)
    return sites, assertions, drives


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------


def iter_python_files(paths: Iterable[Path]) -> list[Path]:
    """Expand paths into a sorted list of ``*.py`` files.

    Directories are walked recursively; explicit file arguments are taken as
    given, which is what lets the control test feed ``tmp_path`` fixtures
    straight to the CLI.
    """
    found: list[Path] = []
    for p in paths:
        if p.is_dir():
            found.extend(sorted(p.rglob("*.py")))
        elif p.suffix == ".py":
            found.append(p)
    return found


def run_census(
    paths: Sequence[Path],
    roots: frozenset[str],
    forms: frozenset[str],
    seam_module: str = _DEFAULT_SEAM_MODULE,
) -> CensusResult:
    """One analysis pass. Every renderer consumes this single result."""
    result = CensusResult(first_party_roots=roots, seam_module=seam_module)
    for scope in paths:
        files = iter_python_files([scope])
        result.files_scanned[str(scope)] = len(files)
        for path in files:
            sites, assertions, drives = analyse_file(path, roots, forms)
            result.sites.extend(sites)
            result.assertions.extend(assertions)
            result.drives.extend(drives)
    result.sites.sort(key=lambda s: (s.file, s.line))
    result.assertions.sort(key=lambda a: (a.file, a.line))
    result.drives.sort(key=lambda a: (a.file, a.line))
    return result


def cross_check(result: CensusResult, paths: Sequence[Path]) -> dict[str, list[dict[str, object]]]:
    """Compare the AST site set against ``check_patch_targets.py``'s regex set.

    The two extractors are known to disagree in both directions, and both
    disagreements are correct behaviour rather than defects:

    * **regex-only** hits are ``patch()`` targets quoted inside docstrings —
      which NFR-007 requires the AST to exclude.
    * **AST-only** hits are calls where a comment sits between ``patch(`` and
      the target string, so the regex's ``\\s*`` cannot bridge it.
    """
    ast_keys = {(s.file, s.line) for s in result.sites}
    regex_keys: set[tuple[str, int]] = set()
    for scope in paths:
        for path in iter_python_files([scope]):
            for _target, line in extract_targets(path):
                regex_keys.add((str(path), line))
    return {
        "regex_only": [
            {"file": _to_rel(f), "line": n} for f, n in sorted(regex_keys - ast_keys)
        ],
        "ast_only": [{"file": _to_rel(f), "line": n} for f, n in sorted(ast_keys - regex_keys)],
    }


def _to_rel(f: str) -> str:
    """Repo-relative path, so cross-check output is stable across checkouts."""
    try:
        return str(Path(f).resolve().relative_to(_REPO_ROOT))
    except ValueError:
        return f


# ---------------------------------------------------------------------------
# Renderers — dict-dispatched, one analysis pass behind all of them
# ---------------------------------------------------------------------------


def _rendered_sites(result: CensusResult, sites: Sequence[PatchSite]) -> list[dict[str, object]]:
    """Sites joined to the assertion forms that read them.

    FR-005 requires the gate to name what it scanned, not just count it, so each
    site carries the read-side forms observed against the mock it binds. A site
    with ``assertion_forms: []`` is patched but never read — visible rather than
    silently folded into a total.
    """
    reads: dict[tuple[str, str, str], list[str]] = {}
    for a in result.assertions + result.drives:
        reads.setdefault((a.file, a.node_id, a.mock_name), []).append(a.assertion_form)
    out: list[dict[str, object]] = []
    for site in sites:
        record = asdict(site)
        key = (site.file, site.node_id, site.binds or "")
        record["assertion_forms"] = sorted(set(reads.get(key, [])))
        out.append(record)
    return out


def render_json(result: CensusResult, extra: dict[str, object]) -> str:
    """The full machine-readable payload.

    Carries the definitional choices (``first_party_roots``, ``seam_module``)
    alongside the counts, and names every site rather than only counting them —
    FR-005 requires the gate to say what it scanned.

    ``sleep_assertions`` and ``corruptible_assertions`` are rendered from two
    **different** properties. They are SC-001's third and fourth figures and the
    criterion requires them to diverge post-fix; rendering both from one list
    makes the criterion unsatisfiable however the tree changes.
    """
    payload: dict[str, object] = {
        "first_party_roots": sorted(result.first_party_roots),
        "seam_module": result.seam_module,
        "files_scanned": result.files_scanned,
        "buckets": result.buckets,
        "literal_predicate_flagged": result.literal_predicate_flagged,
        "sites": _rendered_sites(result, result.sites),
        "sleep_seam_patch_sites": _rendered_sites(result, result.seam_sleep_sites),
        "all_sleep_attr_sites": _rendered_sites(result, result.sleep_seam_sites),
        "nodes_with_sleep_assertions": result.sleep_nodes,
        "sleep_assertions": [asdict(a) for a in result.sleep_assertions],
        "seam_patch_nodes": result.seam_patch_nodes,
        "all_sleep_attr_nodes": result.all_sleep_attr_nodes,
        "all_sleep_attr_assertions": [asdict(a) for a in result.all_sleep_attr_assertions],
        "corruptible_assertions": [asdict(a) for a in result.corruptible],
        "side_effect_drives": [asdict(a) for a in result.drives],
    }
    payload.update(extra)
    return json.dumps(payload, indent=2, sort_keys=False)


def render_contract(result: CensusResult, _extra: dict[str, object]) -> str:
    """The SC-002 delay contract, one line per test node, in file order.

    Node-keyed rather than assertion-keyed: a single node can carry several
    assertions about the same delay sequence (``test_exponential_backoff_intervals``
    carries two, at ``:784`` and ``:786``), and SC-002 pins the *contract*, not the
    assertion count. Every line is derived from live ``ast.Assert`` /
    assert-method-call nodes; docstrings, comments and bare literals contribute
    nothing (NFR-007).

    ``n`` comes from the node's own cardinality expression. The ``in`` form
    contributes ``n=0``, so a node asserting only membership cannot masquerade
    as one asserting a count.

    Sourced from ``sleep_assertions``, never from ``corruptible``: SC-002 pins
    the *delay contract*, which the retargets leave intact. Reading it off the
    verdict-filtered set would empty the contract lines precisely when the fix
    lands, i.e. would grade the tree's state rather than its correctness.
    """
    seam_nodes = {(s.file, s.node_id) for s in result.seam_sleep_sites}
    grouped: dict[tuple[str, str], list[Assertion]] = {}
    for a in result.sleep_assertions:
        key = (a.file, a.node_id)
        if key in seam_nodes:
            grouped.setdefault(key, []).append(a)

    lines = []
    # True file order: by path, then by the node's first assertion line — not
    # by node name, which would put :957 before :937.
    ordered = sorted(grouped.items(), key=lambda kv: (kv[0][0], min(a.line for a in kv[1])))
    for (file, node_id), items in ordered:
        n = max(a.n for a in items)
        delays = next((a.delays for a in items if a.delays is not None), None)
        rendered = "[" + ", ".join(_fmt(d) for d in delays) + "]" if delays else "[]"
        lines.append(f"{Path(file).name}::{node_id}  n={n}  delays={rendered}")
    return "\n".join(lines)


def _fmt(value: float) -> str:
    """Render a delay the way the source literal spells it (2.0 not 2)."""
    return str(int(value)) if value == int(value) and "." not in repr(value) else repr(value)


def _disposition(site: PatchSite, disposed: bool) -> str:
    """Derive a sibling seam's disposition from the resolver verdict.

    Derived, never printed from a literal — SC-013 sub-1 exists precisely to
    defeat a hardcoded disposition table here.

    * ``correct-by-alias`` — the target resolves ``own_module``: it patches a
      symbol where that symbol is defined, so nothing is reached through.
    * ``corruptible`` — a reach-through or foreign seam that the test actually
      reads or drives, so an unrelated caller mutating the same shared module
      object changes this test's verdict.
    * ``undisposed`` — patched, but neither read nor driven. Nothing decides
      what it is for.
    """
    if site.verdict == PatchTargetOutcome.OWN_MODULE.value:
        return "correct-by-alias"
    return "corruptible" if disposed else "undisposed"


def render_siblings(result: CensusResult, _extra: dict[str, object]) -> str:
    """Sibling seams inside seam-patching nodes, keyed on where they are read.

    A "sibling" is a non-sleep mock patched in a function that also patches the
    sleep seam — ``mock_randbelow`` and ``mock_monotonic`` alongside
    ``mock_sleep``. They matter because they share the sleep seam's fate: they
    are patched on the same shared module objects.

    Scoped to ``seam_patch_nodes`` (nodes that **patch** the seam) rather than
    ``sleep_nodes`` (nodes that **assert on** it). The narrower scope hides
    exactly the node this report exists to surface: a sibling in a
    patched-but-never-read node is what ``undisposed`` is a name for, and
    dropping it makes the vocabulary look non-vacuous only because the vacuous
    cases were filtered out first. Absent is worse than ``undisposed``.

    Reads and drives are reported at *their own* line, not the decorator's, so
    ``assert mock_randbelow.call_count == 3`` and
    ``mock_monotonic.side_effect = [0.0, 301.0]`` are each named where they
    actually appear. A sibling with no read and no drive is reported at its
    patch line as ``undisposed``.

    Keyed on ``(file, node_id, binds)``. ``(file, binds)`` collapses distinct
    sites: ``mock_monotonic`` and ``mock_cls`` recur across ~30 functions in a
    single 1400-line module, so the file-wide key both drops candidates and can
    print one function's ``target=``/``verdict=`` beside another's read.
    """
    scope_nodes = {(n["file"], n["node_id"]) for n in result.seam_patch_nodes}
    siblings: dict[tuple[str, str, str], PatchSite] = {
        (s.file, s.node_id, s.binds): s
        for s in result.sites
        if s.binds and s.attr not in _SLEEP_ATTRS and (s.file, s.node_id) in scope_nodes
    }

    lines: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for record in sorted(result.assertions + result.drives, key=lambda a: (a.file, a.line)):
        key = (record.file, record.node_id, record.mock_name)
        site = siblings.get(key)
        if site is None:
            continue
        seen.add(key)
        lines.append(
            f"{record.file}:{record.line}  {record.node_id}  "
            f"target={site.target}  verdict={site.verdict}  "
            f"read={record.assertion_form}  "
            f"disposition={_disposition(site, disposed=True)}"
        )

    for key, site in sorted(siblings.items()):
        if key in seen:
            continue
        lines.append(
            f"{site.file}:{site.line}  {site.node_id}  "
            f"target={site.target}  verdict={site.verdict}  "
            f"read=none  disposition={_disposition(site, disposed=False)}"
        )
    return "\n".join(lines)


_RENDERERS = {
    "json": render_json,
    "contract": render_contract,
    "siblings": render_siblings,
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", type=Path, help="files or directories to scan")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--json", action="store_true", help="full machine-readable payload")
    mode.add_argument("--contract", action="store_true", help="the SC-002 assertion lines")
    mode.add_argument("--siblings", action="store_true", help="sibling seams and dispositions")
    parser.add_argument(
        "--first-party-roots",
        type=str,
        default=None,
        help="comma-separated override for the first-party root set",
    )
    parser.add_argument(
        "--only-forms",
        type=str,
        default=None,
        help=(
            "comma-separated subset of "
            f"{','.join(PATCH_FORMS)} — narrows the analyzer. Used by the "
            "control test's self-mutation arm; never narrow this in normal use."
        ),
    )
    parser.add_argument(
        "--seam-module",
        type=str,
        default=_DEFAULT_SEAM_MODULE,
        help="dotted module whose sleep seam the contract lines are about",
    )
    parser.add_argument(
        "--cross-check",
        action="store_true",
        help="include the AST-vs-regex difference in both directions",
    )
    return parser


def _selected_mode(args: argparse.Namespace) -> str:
    for name in _RENDERERS:
        if getattr(args, name):
            return name
    raise AssertionError("argparse guarantees exactly one mode")


def main(argv: Sequence[str] | None = None) -> int:
    """Run one analysis pass and render it in the selected mode.

    Always returns 0 on a successful analysis, whatever the buckets contain:
    this is a reporter, and the gate that fails a build is a separate concern.
    """
    args = _build_parser().parse_args(argv)
    roots = (
        frozenset(r.strip() for r in args.first_party_roots.split(",") if r.strip())
        if args.first_party_roots
        else default_first_party_roots(_REPO_ROOT)
    )
    forms = (
        frozenset(f.strip() for f in args.only_forms.split(",") if f.strip())
        if args.only_forms
        else frozenset(PATCH_FORMS)
    )
    result = run_census(args.paths, roots, forms, args.seam_module)
    extra: dict[str, object] = {}
    if args.cross_check:
        extra["cross_check"] = cross_check(result, args.paths)
    print(_RENDERERS[_selected_mode(args)](result, extra))
    return 0


if __name__ == "__main__":
    sys.exit(main())
