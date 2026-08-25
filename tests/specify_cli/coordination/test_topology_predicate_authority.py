"""Anti-divergence guard: ``_transaction_topology_available`` is the single topology authority.

#3460 / FR-004. This is an **enforcement-only** guard, not a behaviour change. The
post-plan squad (reviewer + debugger VERIFIED) censused every residual
``coordination_branch is (not) None`` site and found **zero surrogate GATEs to remove** —
the transactional routing gates in
``src/specify_cli/coordination/status_transition.py`` already consult the single
authority ``_transaction_topology_available`` on ``main``. So #3460 closes as
*"topology-availability is a single authority, pinned by an anti-divergence guard"*,
NOT *"removed surrogate gates"* (nothing is removed — that phrasing would dishonestly
credit M8 for main's existing state).

Because the invariant already holds, this guard is made **non-vacuous** the way WP3's
anti-bypass guard is: an AST checker is first asserted to FLAG a synthetic fixture that
gates on ``coordination_branch is None`` in a transactional-routing position, and only
THEN asserted clean against the live module. Deleting the checker or its exemption logic
turns the synthetic-fixture assertion red.

Census verdicts (re-confirmed at implement — all VALUE READS / SSOT-gated, not surrogate
gates; that is why WP1 changes no source):

======================================  =========================================================
Site                                    Verdict — why it is not a surrogate topology gate
======================================  =========================================================
status_transition.py:145                Inside ``_transaction_topology_available`` ITSELF — this is
(``is not None`` → return True)         the authority's own definition. EXEMPT (it is the SSOT).
status_transition.py:1481               Inside ``emit_inner_state_changed_transactional`` — the
(``is None`` → uncommitted emit)        deliberate off-axis #2939 exclusion. The shared authority's
                                        legacy-meta fallback arm (``transaction_meta_exists``) is
                                        trivially true for coord-less 083+ missions, so reusing it
                                        here regresses ``test_flat_topology_annotation_still_lands``.
                                        "Tried and reverted"; the bare check is the CORRECT narrower
                                        predicate for THIS path. EXEMPT (pinned by T002).
mission_runtime/resolution.py:1284      ``not routes_through_coordination(topology) or
                                        coordination_branch is None`` — gated on the stored-topology
                                        SSOT (``routes_through_coordination``); the ``is None`` arm is
                                        a value guard on the branch name, not a topology re-inference.
mission_runtime/resolution.py:1362      ``if coordination_branch is not None:`` derives a worktree
                                        path from the branch-name VALUE; not a topology gate.
mission_runtime/resolution.py:1460      ``... and coordination_branch is not None`` — gated on
                                        ``routes_through_coordination`` (comment: "single predicate,
                                        never re-derived per-ref"); value read.
mission_runtime/context.py:70           ``has_coord = coordination_branch is not None`` is INSIDE
                                        ``classify_topology`` — i.e. the classifier itself, the
                                        origin of topology facts, not a downstream surrogate.
======================================  =========================================================

The residual ``resolution.py`` / ``context.py`` sites live in a different module and are
out of the checker's scan scope (which is confined to the transactional routing paths of
``status_transition.py``); they are recorded here for the reviewer to verify against the
cited lines.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

import specify_cli.coordination.status_transition as _status_transition

pytestmark = pytest.mark.architectural

# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------

RULE = "surrogate-topology-gate"

#: The authoritative single-topology predicate every transactional routing gate
#: must consult instead of re-deriving topology from ``coordination_branch``.
_AUTHORITY = "_transaction_topology_available"

#: Transactional routing functions that MUST consult the authority (positive
#: structural assertion — these are the four gate sites on ``main``).
_GATE_FUNCTIONS = frozenset(
    {
        "read_current_wp_state_transactional",
        "_read_contract_from_transaction_target",
        "emit_status_transition_transactional",
        "emit_status_transition_batch_transactional",
    }
)

#: Functions allowed to test ``coordination_branch is (not) None`` directly:
#: the authority's own definition, and the deliberate #2939 off-axis exclusion.
_EXEMPT_FUNCTIONS = frozenset(
    {
        _AUTHORITY,
        "emit_inner_state_changed_transactional",
    }
)


@dataclass(frozen=True)
class Finding:
    """A surrogate topology gate detected in a transactional routing path."""

    file: str
    line: int
    rule: str
    function: str


def _is_transactional_scope(name: str) -> bool:
    """A function participates in the transactional routing surface."""
    return "transaction" in name.lower()


def _is_coordination_branch_ref(node: ast.expr) -> bool:
    """``x.coordination_branch`` (attribute) or a bare ``coordination_branch`` name."""
    if isinstance(node, ast.Attribute):
        return node.attr == "coordination_branch"
    if isinstance(node, ast.Name):
        return node.id == "coordination_branch"
    return False


def _is_none(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def _is_coord_none_identity_compare(node: ast.expr) -> bool:
    """``coordination_branch is None`` / ``is not None`` (either operand order)."""
    if not isinstance(node, ast.Compare):
        return False
    if len(node.ops) != 1 or len(node.comparators) != 1:
        return False
    if not isinstance(node.ops[0], (ast.Is, ast.IsNot)):
        return False
    left, right = node.left, node.comparators[0]
    return (_is_coordination_branch_ref(left) and _is_none(right)) or (
        _is_none(left) and _is_coordination_branch_ref(right)
    )


def _gate_compares_in_test(test: ast.expr) -> list[ast.Compare]:
    """Coord/None identity compares reachable from a control-flow *test* expression.

    Walking the ``test`` subtree of an ``if`` / ``while`` / ternary is what makes this
    a ROUTING-GATE detector (positive/structural) rather than a substring grep: a
    ``coordination_branch is None`` that is merely assigned to a variable elsewhere is
    NOT flagged unless that value is used as the control-flow test.
    """
    return [
        sub
        for sub in ast.walk(test)
        if isinstance(sub, ast.Compare) and _is_coord_none_identity_compare(sub)
    ]


def find_surrogate_gates(tree: ast.Module, filename: str) -> list[Finding]:
    """Flag ``coordination_branch is (not) None`` used as a routing gate.

    Scans top-level transactional functions (``"transaction" in name``), skipping the
    exempt authority + off-axis emit path, for a coord/None identity compare used as the
    test of an ``if`` / ``while`` / ternary. Iterating ``tree.body`` (not ``ast.walk``)
    attributes each control-flow node to its top-level enclosing function so the
    exemption applies by function identity.
    """
    findings: list[Finding] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if not _is_transactional_scope(node.name):
            continue
        if node.name in _EXEMPT_FUNCTIONS:
            continue
        for sub in ast.walk(node):
            if isinstance(sub, (ast.If, ast.While, ast.IfExp)):
                for cmp in _gate_compares_in_test(sub.test):
                    findings.append(
                        Finding(
                            file=filename,
                            line=cmp.lineno,
                            rule=RULE,
                            function=node.name,
                        )
                    )
    return findings


def _top_level_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name!r} not found in module")


def _calls_authority(func: ast.FunctionDef) -> bool:
    return any(
        isinstance(sub, ast.Call)
        and isinstance(sub.func, ast.Name)
        and sub.func.id == _AUTHORITY
        for sub in ast.walk(func)
    )


# ---------------------------------------------------------------------------
# Live-module fixtures
# ---------------------------------------------------------------------------

_MODULE_PATH = Path(_status_transition.__file__)
_MODULE_SOURCE = _MODULE_PATH.read_text(encoding="utf-8")
_MODULE_TREE = ast.parse(_MODULE_SOURCE)


# A routing function that (wrongly) re-derives topology from ``coordination_branch``
# instead of consulting the authority — the deliberately-red anchor proving the checker
# has teeth. ``"transaction"`` in the name puts it in scope; the ``if`` makes it a gate.
_SYNTHETIC_SURROGATE_SOURCE = '''
def emit_status_transition_synthetic_transactional(identity, mission_slug):
    """A hypothetical future routing gate that bypasses the authority."""
    if identity.coordination_branch is None:
        return _primary_write()
    return _coord_write()
'''


# ---------------------------------------------------------------------------
# T001 — single-authority anti-divergence guard
# ---------------------------------------------------------------------------


def test_topology_predicate_is_single_authority() -> None:
    """The transactional routing gates consult the authority, not a bare surrogate.

    Non-vacuity is proven first (the synthetic fixture MUST be flagged); the live module
    is then asserted clean. If the checker or its exemption logic is deleted, the
    synthetic assertion goes red.
    """
    # 1. Non-vacuity: the checker flags a synthetic surrogate gate, naming file:line+rule.
    synthetic_tree = ast.parse(_SYNTHETIC_SURROGATE_SOURCE)
    synthetic_findings = find_surrogate_gates(synthetic_tree, "synthetic_fixture.py")
    assert synthetic_findings, (
        "checker is vacuous — it failed to flag a synthetic coordination_branch-is-None "
        "routing gate in a transactional function"
    )
    flagged = synthetic_findings[0]
    assert flagged.rule == RULE
    assert flagged.file == "synthetic_fixture.py"
    assert flagged.function == "emit_status_transition_synthetic_transactional"
    # The gate is the ``if identity.coordination_branch is None:`` (4th line of the source).
    assert flagged.line == 4, f"unexpected flagged line: {flagged.line}"

    # 2. Live module transactional routing paths are clean (single authority holds).
    live_findings = find_surrogate_gates(_MODULE_TREE, str(_MODULE_PATH))
    assert live_findings == [], (
        "surrogate topology gate(s) re-introduced in status_transition.py transactional "
        f"routing paths: {live_findings}"
    )

    # 3. Positive assertion: each transactional routing gate DOES consult the authority.
    for name in _GATE_FUNCTIONS:
        func = _top_level_function(_MODULE_TREE, name)
        assert _calls_authority(func), (
            f"{name} no longer consults {_AUTHORITY}; a routing gate must go through the "
            "single topology authority"
        )


# ---------------------------------------------------------------------------
# T002 — exclusion pin (#2939 preservation)
# ---------------------------------------------------------------------------


def test_emit_annotation_keeps_narrow_predicate() -> None:
    """``emit_inner_state_changed_transactional`` keeps the bare ``coordination_branch is None``.

    Regression guard for #2939: the shared authority's legacy-meta fallback arm is
    trivially true for coord-less 083+ missions, so a future "single-authority cleanup"
    that routed this off-axis annotation path through ``_transaction_topology_available``
    would re-break ``test_flat_topology_annotation_still_lands``. See the function's own
    docstring (~status_transition.py:1428-1447): "tried and reverted".
    """
    emit = _top_level_function(_MODULE_TREE, "emit_inner_state_changed_transactional")

    # The bare coord/None check is present AND used as a routing gate (an ``if`` test).
    gate_present = any(
        isinstance(sub, ast.If) and _gate_compares_in_test(sub.test)
        for sub in ast.walk(emit)
    )
    assert gate_present, (
        "emit_inner_state_changed_transactional no longer routes on the bare "
        "'coordination_branch is None' check — this re-breaks #2939 "
        "(test_flat_topology_annotation_still_lands)"
    )

    # And it must NOT reach for the shared authority (that is the whole exclusion).
    assert not _calls_authority(emit), (
        "emit_inner_state_changed_transactional now consults "
        f"{_AUTHORITY}; the #2939 off-axis exclusion requires the narrower bare predicate"
    )
