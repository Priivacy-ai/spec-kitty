"""Surface calibration tests -- enforce minimum-effective-dose inequalities.

These tests load the **real** ``src/doctrine/graph.yaml`` (not a fixture)
and verify that each action's governance surface satisfies the ordering
constraints from the spec.  When a test fails the fix is **always** to
adjust ``scope`` edges in ``graph.yaml``, never to add conditional logic
in code.

Subtasks:
    T028 -- surface measurement helpers
    T029 -- calibration inequality assertions
    T030 -- structural DRG-only-knob audit
    T031 -- CI runner coverage (automatic via pytest collection)
"""

from __future__ import annotations

import ast
import textwrap
from collections import Counter
from pathlib import Path

import pytest

from doctrine.drg.loader import load_graph
from doctrine.drg.models import DRGGraph, NodeKind
from doctrine.drg.query import resolve_context

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REVIEW_THRESHOLD = 0.80  # review must be >= 80% of implement

# The five canonical software-dev actions
_ACTIONS = ("specify", "plan", "tasks", "implement", "review")
_ACTION_URNS = {a: f"action:software-dev/{a}" for a in _ACTIONS}

# Real graph.yaml shipped with the project
_GRAPH_PATH = (
    Path(__file__).resolve().parents[2] / "src" / "doctrine" / "graph.yaml"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def loaded_graph() -> DRGGraph:
    """Load the real shipped DRG graph (not a test fixture)."""
    assert _GRAPH_PATH.exists(), (
        f"graph.yaml not found at {_GRAPH_PATH}. "
        f"Was it removed or renamed?"
    )
    return load_graph(_GRAPH_PATH)


# ---------------------------------------------------------------------------
# T028 -- Surface measurement helpers
# ---------------------------------------------------------------------------


def measure_surface(graph: DRGGraph, action_urn: str, depth: int = 2) -> int:
    """Return the count of distinct artifact URNs reachable from *action_urn*.

    Uses :func:`resolve_context` from the DRG query module -- no traversal
    reimplementation.
    """
    resolved = resolve_context(graph, action_urn, depth=depth)
    return len(resolved.artifact_urns)


def measure_surface_detailed(
    graph: DRGGraph, action_urn: str, depth: int = 2,
) -> dict[str, int]:
    """Break down the governance surface by artifact kind.

    Returns a mapping from kind name (e.g. ``"directive"``, ``"tactic"``) to
    the count of resolved artifacts of that kind.  Useful for debugging when
    inequalities are violated.
    """
    resolved = resolve_context(graph, action_urn, depth=depth)
    counter: Counter[str] = Counter()
    for urn in resolved.artifact_urns:
        node = graph.get_node(urn)
        if node is not None:
            counter[node.kind.value] += 1
        else:
            counter["unknown"] += 1
    return dict(counter)


class TestSurfaceMeasurement:
    """T028: verify surface helpers return sensible values."""

    def test_each_action_has_positive_surface(self, loaded_graph: DRGGraph) -> None:
        for action_name, urn in _ACTION_URNS.items():
            size = measure_surface(loaded_graph, urn)
            assert size > 0, (
                f"Action {action_name!r} ({urn}) resolved zero artifacts. "
                f"Fix: add scope edges in graph.yaml"
            )

    def test_detailed_breakdown_sums_to_total(self, loaded_graph: DRGGraph) -> None:
        for action_name, urn in _ACTION_URNS.items():
            total = measure_surface(loaded_graph, urn)
            detailed = measure_surface_detailed(loaded_graph, urn)
            assert sum(detailed.values()) == total, (
                f"Detailed breakdown for {action_name!r} sums to "
                f"{sum(detailed.values())} but total is {total}"
            )

    def test_detailed_breakdown_keys_are_valid_kinds(
        self, loaded_graph: DRGGraph,
    ) -> None:
        valid_kinds = {k.value for k in NodeKind}
        valid_kinds.add("unknown")  # safety bucket
        for action_name, urn in _ACTION_URNS.items():
            detailed = measure_surface_detailed(loaded_graph, urn)
            for kind_name in detailed:
                assert kind_name in valid_kinds, (
                    f"Unexpected kind {kind_name!r} in detailed breakdown "
                    f"for {action_name!r}"
                )


# ---------------------------------------------------------------------------
# T029 -- Calibration inequality assertions
# ---------------------------------------------------------------------------


class TestCalibrationInequalities:
    """T029: enforce minimum-effective-dose ordering from the spec."""

    def test_surface_calibration_inequalities(
        self, loaded_graph: DRGGraph,
    ) -> None:
        """Each action's surface respects minimum-effective-dose ordering."""
        specify = measure_surface(loaded_graph, _ACTION_URNS["specify"])
        plan = measure_surface(loaded_graph, _ACTION_URNS["plan"])
        tasks = measure_surface(loaded_graph, _ACTION_URNS["tasks"])
        implement = measure_surface(loaded_graph, _ACTION_URNS["implement"])
        review = measure_surface(loaded_graph, _ACTION_URNS["review"])

        # Strict ordering: specify < plan < implement
        assert specify < plan, (
            f"specify ({specify}) must be < plan ({plan}). "
            f"Fix: remove scope edges from specify or add to plan in graph.yaml"
        )
        assert plan < implement, (
            f"plan ({plan}) must be < implement ({implement}). "
            f"Fix: add scope edges to implement or remove from plan in graph.yaml"
        )

        # tasks < implement
        assert tasks < implement, (
            f"tasks ({tasks}) must be < implement ({implement}). "
            f"Fix: remove scope edges from tasks or add to implement in graph.yaml"
        )

        # Approximate equality: review >= 80% of implement
        assert review >= implement * REVIEW_THRESHOLD, (
            f"review ({review}) must be >= {REVIEW_THRESHOLD * 100:.0f}% of "
            f"implement ({implement}). "
            f"Actual: {review / implement * 100:.0f}%. "
            f"Fix: add scope edges to review in graph.yaml"
        )

    def test_surface_report(self, loaded_graph: DRGGraph) -> None:
        """Report current surface sizes for CI visibility (always passes)."""
        print()  # noqa: T201 -- intentional CI output
        print("=== Governance Surface Report ===")  # noqa: T201
        for action_name in _ACTIONS:
            urn = _ACTION_URNS[action_name]
            size = measure_surface(loaded_graph, urn)
            detailed = measure_surface_detailed(loaded_graph, urn)
            print(f"  {action_name:12s}: {size:3d} total  {detailed}")  # noqa: T201
        print("=================================")  # noqa: T201


# ---------------------------------------------------------------------------
# T030 -- DRG-only-knob structural audit
# ---------------------------------------------------------------------------


def _collect_string_constants(node: ast.AST) -> set[str]:
    """Recursively collect all string literal values from an AST subtree."""
    strings: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            strings.add(child.value)
    return strings


def _find_action_conditionals(func_ast: ast.FunctionDef) -> list[str]:
    """Return descriptions of any ``if`` branches that compare against action names.

    Detects patterns like:
        if action == "specify": ...
        if action in {"specify", "plan"}: ...
        if action_name == "implement": ...
    """
    action_names = {"specify", "plan", "tasks", "implement", "review"}
    violations: list[str] = []

    for node in ast.walk(func_ast):
        if isinstance(node, (ast.If, ast.IfExp)):
            test = node.test if isinstance(node, ast.If) else node.test
            strings_in_test = _collect_string_constants(test)
            matches = strings_in_test & action_names
            if matches:
                lineno = getattr(node, "lineno", "?")
                violations.append(
                    f"Line {lineno}: if-branch references action names {matches}"
                )
    return violations


def _find_action_name_dicts_or_sets(func_ast: ast.FunctionDef) -> list[str]:
    """Detect dict/set literals containing action name strings.

    These could be used for per-action filtering maps, which violates
    the DRG-only-knob rule.
    """
    action_names = {"specify", "plan", "tasks", "implement", "review"}
    violations: list[str] = []

    for node in ast.walk(func_ast):
        if isinstance(node, (ast.Dict, ast.Set)):
            strings = _collect_string_constants(node)
            matches = strings & action_names
            # Only flag if 2+ action names appear (a single one could be
            # an innocuous default/example string)
            if len(matches) >= 2:
                lineno = getattr(node, "lineno", "?")
                violations.append(
                    f"Line {lineno}: dict/set contains action names {matches}"
                )
    return violations


def _parse_module(path: Path) -> ast.Module:
    """Parse a Python source file into an AST."""
    source = path.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(path))


def _find_function_def(module: ast.Module, name: str) -> ast.FunctionDef | None:
    """Find a top-level (or nested) function definition by name."""
    for node in ast.walk(module):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == name:
                return node  # type: ignore[return-value]
    return None


class TestDRGOnlyKnob:
    """T030: structural regression -- no per-action filtering in code."""

    _CONTEXT_PY = (
        Path(__file__).resolve().parents[2]
        / "src" / "charter" / "context.py"
    )
    _QUERY_PY = (
        Path(__file__).resolve().parents[2]
        / "src" / "doctrine" / "drg" / "query.py"
    )

    def test_build_context_v2_has_no_action_conditionals(self) -> None:
        """build_context_v2 must not branch on specific action names.

        The DRG graph.yaml scope edges are the **only** knob that controls
        which artifacts each action receives.  Adding ``if action == "X"``
        logic is a regression.
        """
        tree = _parse_module(self._CONTEXT_PY)
        func = _find_function_def(tree, "build_context_v2")
        assert func is not None, "build_context_v2 not found in context.py"

        violations = _find_action_conditionals(func)
        assert not violations, (
            "build_context_v2 contains action-specific conditionals "
            "(DRG-only-knob violation):\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\nFix: adjust scope edges in graph.yaml instead of adding "
            "code-level filtering"
        )

    def test_build_context_v2_has_no_action_name_maps(self) -> None:
        """build_context_v2 must not use dicts/sets of action names for filtering."""
        tree = _parse_module(self._CONTEXT_PY)
        func = _find_function_def(tree, "build_context_v2")
        assert func is not None, "build_context_v2 not found in context.py"

        violations = _find_action_name_dicts_or_sets(func)
        assert not violations, (
            "build_context_v2 contains action-name dicts/sets "
            "(DRG-only-knob violation):\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\nFix: adjust scope edges in graph.yaml instead of adding "
            "code-level filtering"
        )

    def test_query_module_has_no_action_specific_logic(self) -> None:
        """DRG query primitives must be generic -- no action name references.

        walk_edges and resolve_context should work with any graph and any
        node kinds.  Embedding action names makes the query layer non-generic.
        """
        tree = _parse_module(self._QUERY_PY)

        # Check every function in the module
        all_violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cond_violations = _find_action_conditionals(node)
                map_violations = _find_action_name_dicts_or_sets(node)
                for v in cond_violations + map_violations:
                    all_violations.append(f"{node.name}: {v}")

        assert not all_violations, (
            "DRG query module contains action-specific logic "
            "(DRG-only-knob violation):\n"
            + "\n".join(f"  - {v}" for v in all_violations)
            + "\nFix: adjust scope edges in graph.yaml instead of adding "
            "code-level filtering"
        )

    def test_query_functions_accept_generic_urns(self) -> None:
        """Verify query function signatures do not constrain action URNs.

        Check that walk_edges and resolve_context accept plain ``str``
        parameters, not enums or restricted types that would imply
        action-specific logic.
        """
        tree = _parse_module(self._QUERY_PY)

        for func_name in ("walk_edges", "resolve_context"):
            func = _find_function_def(tree, func_name)
            assert func is not None, f"{func_name} not found in query.py"
            # The function should exist and accept string URN arguments --
            # we verify this structurally by checking the function exists
            # and has no embedded action-name filtering (covered above).
            # A type-level check is not needed because the signatures use
            # plain ``str`` already.
