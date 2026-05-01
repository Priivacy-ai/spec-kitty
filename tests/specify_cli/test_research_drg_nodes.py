"""DRG proofs for `action:research/*` nodes (mission research-composition-v2 WP03).

These tests assert two facts on the *real* shipped DRG:

1. Each of the 5 research action nodes exists in the validated graph.
2. ``resolve_context()`` returns a non-empty ``artifact_urns`` set for each
   action when called with the same composition depth that
   ``StepContractExecutionContext.resolution_depth`` defaults to.

The mission spec (C-007) explicitly forbids mocking
``charter._drg_helpers.load_validated_graph`` or
``doctrine.drg.query.resolve_context`` in real-runtime tests. These tests
read the on-disk graph and call the production resolver directly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from charter._drg_helpers import load_validated_graph
from doctrine.drg.query import resolve_context

# The 5 advancing research actions covered by the mission-runtime sidecar.
RESEARCH_ACTIONS: tuple[str, ...] = (
    "scoping",
    "methodology",
    "gathering",
    "synthesis",
    "output",
)

# Mirror the literal default of StepContractExecutionContext.resolution_depth
# (src/specify_cli/mission_step_contracts/executor.py:63). Composition calls
# `resolve_context(graph, action_urn, depth=context.resolution_depth)` at
# executor.py:153, so this is the depth that has to produce non-empty
# artifact_urns for the runtime to behave correctly.
COMPOSITION_RESOLUTION_DEPTH: int = 2


def _repo_root() -> Path:
    """Locate the repository root that holds ``src/doctrine/graph.yaml``."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / "src" / "doctrine" / "graph.yaml").is_file():
            return parent
    raise RuntimeError("Could not locate repo root containing src/doctrine/graph.yaml")


@pytest.mark.parametrize("action", RESEARCH_ACTIONS)
def test_research_action_nodes_exist(action: str) -> None:
    """Each `action:research/<action>` node is present in the validated DRG."""
    graph = load_validated_graph(_repo_root())
    urn = f"action:research/{action}"
    node = graph.get_node(urn)
    assert node is not None, f"Missing DRG node: {urn}"


@pytest.mark.parametrize("action", RESEARCH_ACTIONS)
def test_research_action_resolve_context_non_empty(action: str) -> None:
    """`resolve_context()` returns non-empty artifact_urns for each action.

    Uses the *real* composition resolver (`doctrine.drg.query.resolve_context`)
    and the *real* `load_validated_graph` — no mocks, per spec C-007.
    """
    graph = load_validated_graph(_repo_root())
    urn = f"action:research/{action}"
    ctx = resolve_context(graph, urn, depth=COMPOSITION_RESOLUTION_DEPTH)
    assert ctx.artifact_urns, (
        f"resolve_context returned empty artifact_urns for {urn}; "
        f"composition would receive nothing for this research action."
    )


def test_drg_assert_valid_passes() -> None:
    """`load_validated_graph()` succeeds (assert_valid is invoked internally)."""
    graph = load_validated_graph(_repo_root())
    # Sanity: non-trivial graph; the load-and-validate did not raise.
    assert len(graph.nodes) > 0
