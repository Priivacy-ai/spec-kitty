"""Standing architecture invariants for the ``runtime_bridge*`` seam family --
NFR-002 zero-C901 (via ruff's own offender count, not a text grep) and C-007
no-top-level-import-cycle + the WP10 Import-DAG rules. These are permanent
family guards, not mission-scoped."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_SRC_NEXT_DIR = Path(__file__).resolve().parents[2] / "src" / "runtime" / "next"


def _family_files() -> list[Path]:
    files = [_SRC_NEXT_DIR / "runtime_bridge.py"]
    files.extend(sorted(_SRC_NEXT_DIR.glob("runtime_bridge_*.py")))
    for f in files:
        assert f.is_file(), f"expected family member missing: {f}"
    return files


def test_zero_c901_offenders_across_the_runtime_bridge_family() -> None:
    """The mission-closing complexity assertion (NFR-002/SC-002): ruff's own
    C901 (mccabe complexity) offender count must be exactly zero across
    ``runtime_bridge.py`` and every ``runtime_bridge_*.py`` sibling -- no
    function is over the ceiling, so no ``# noqa: C901`` suppression is ever
    needed. A text grep for the literal marker is NOT used here deliberately:
    it would false-positive on the prose mention of the marker inside a
    docstring."""
    files = _family_files()
    proc = subprocess.run(
        ["uv", "run", "ruff", "check", "--select", "C901", "--output-format", "json", *[str(f) for f in files]],
        capture_output=True,
        text=True,
        check=False,
    )
    offenders = json.loads(proc.stdout) if proc.stdout.strip() else []
    assert offenders == [], (
        f"ruff --select C901 found {len(offenders)} offender(s) across the runtime_bridge "
        f"family (expected zero): {[o.get('filename') for o in offenders]}"
    )


def test_no_noqa_c901_suppressions_exist_in_the_family() -> None:
    """Companion assertion: no function anywhere in the family actually
    carries a real ``# noqa: C901`` suppression comment (as opposed to a
    docstring that merely mentions the marker as prose) -- verified via
    ``tokenize`` (comments only), not a raw text grep over the whole file."""
    import tokenize

    for path in _family_files():
        with tokenize.open(path) as fh:
            comment_lines = [tok.string for tok in tokenize.generate_tokens(fh.readline) if tok.type == tokenize.COMMENT]
        offenders = [c for c in comment_lines if "noqa: C901" in c or "noqa:C901" in c]
        assert not offenders, f"{path}: real '# noqa: C901' suppression comment(s) found: {offenders}"


_FAMILY_MODULE_NAMES = frozenset(
    {
        "runtime_bridge",
        "runtime_bridge_engine",
        "runtime_bridge_cores",
        "runtime_bridge_io",
        "runtime_bridge_composition",
        "runtime_bridge_retrospective",
        "runtime_bridge_identity",
        "decision",
    }
)


def _module_short_name(dotted: str | None) -> str | None:
    if dotted is None:
        return None
    tail = dotted.rsplit(".", 1)[-1]
    return tail if tail in _FAMILY_MODULE_NAMES else None


def _top_level_family_edges(path: Path, own_name: str) -> set[str]:
    """Return the set of family module names ``path`` imports at MODULE
    scope (top-level ``Import``/``ImportFrom`` only -- deferred/function-scope
    imports, the lazy-accessor mechanism this whole mission relies on, are
    deliberately excluded; they are what keeps the graph acyclic)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    edges: set[str] = set()
    for node in tree.body:  # module-level statements ONLY
        if isinstance(node, ast.ImportFrom):
            target = _module_short_name(node.module)
            if target is not None and target != own_name:
                edges.add(target)
            if node.module == "runtime.next":
                for alias in node.names:
                    if alias.name in _FAMILY_MODULE_NAMES and alias.name != own_name:
                        edges.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                target = _module_short_name(alias.name)
                if target is not None and target != own_name:
                    edges.add(target)
    return edges


def _build_family_graph() -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for name in _FAMILY_MODULE_NAMES:
        filename = "decision.py" if name == "decision" else f"{name}.py"
        path = _SRC_NEXT_DIR / filename
        assert path.is_file(), f"expected family member missing: {path}"
        graph[name] = _top_level_family_edges(path, name)
    return graph


def test_no_new_top_level_import_cycle_in_runtime_bridge_family() -> None:
    """C-007 whole-family closure: build the top-level import edges for every
    ``runtime_bridge*`` module plus ``decision.py`` and assert the graph is
    acyclic. The ``decision.py:428 -> runtime_bridge.decide_next_via_runtime``
    edge is a deferred (function-scope) import specifically so it never
    appears here -- see the dedicated assertion below."""
    graph = _build_family_graph()

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(graph, WHITE)
    cycle_path: list[str] = []

    def _visit(node: str, stack: list[str]) -> bool:
        color[node] = GRAY
        stack.append(node)
        for neighbor in graph.get(node, ()):
            if color[neighbor] == GRAY:
                cycle_path.extend([*stack, neighbor])
                return True
            if color[neighbor] == WHITE and _visit(neighbor, stack):
                return True
        stack.pop()
        color[node] = BLACK
        return False

    for start in graph:
        if color[start] == WHITE and _visit(start, []):
            raise AssertionError(
                f"top-level import cycle detected in runtime_bridge family: {' -> '.join(cycle_path)}"
            )


def test_decision_module_has_no_top_level_edge_back_into_runtime_bridge_family() -> None:
    """The named C-007 invariant: ``decision.py``'s orchestrator edge
    (``decide_next -> runtime_bridge.decide_next_via_runtime``) MUST stay a
    deferred/function-scope import, never a top-level one -- a top-level edge
    here would create exactly the cycle the whole extraction strategy is
    designed to avoid (``runtime_bridge`` already imports ``decision`` at its
    own top level)."""
    edges = _top_level_family_edges(_SRC_NEXT_DIR / "decision.py", "decision")
    assert edges == set(), (
        f"decision.py has a top-level import edge into the runtime_bridge family: {edges} "
        "-- this must stay a deferred (function-scope) import (C-007)."
    )


def test_identity_seam_not_imported_by_cores() -> None:
    """The WP10-specific Import DAG rule (research.md §Import DAG): ``cores``
    sits at the base of the DAG (stdlib/``Lane``/decision types only) and must
    never import ``identity``."""
    edges = _top_level_family_edges(_SRC_NEXT_DIR / "runtime_bridge_cores.py", "runtime_bridge_cores")
    assert "runtime_bridge_identity" not in edges, "runtime_bridge_cores.py must not import runtime_bridge_identity (DAG violation)"


def test_identity_seam_has_no_top_level_edge_into_runtime_bridge() -> None:
    """The identity seam's own deferred-import discipline: its
    ``from runtime.next import runtime_bridge as _rb`` lazy accessor must stay
    function-scoped (never top-level), or it would create the residual<->seam
    import cycle its own module docstring explains."""
    edges = _top_level_family_edges(_SRC_NEXT_DIR / "runtime_bridge_identity.py", "runtime_bridge_identity")
    assert "runtime_bridge" not in edges, "runtime_bridge_identity.py imports runtime_bridge at module scope (would be circular)"
