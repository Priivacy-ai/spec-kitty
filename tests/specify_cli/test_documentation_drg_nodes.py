"""DRG node and resolve_context regression tests for documentation mission (#502).

These tests assert four facts on the *real* shipped DRG and the documentation
action bundles produced by WP03:

1. Each of the 6 documentation action nodes exists in the validated graph and
   ``resolve_context()`` returns a non-empty ``artifact_urns`` set (FR-004,
   FR-005).
2. Each documentation action's bundle ``index.yaml`` (slug-form
   directives/tactics) maps 1-to-1 to the URN-form ``relation: scope`` edges
   in ``src/doctrine/graph.yaml`` (FR-006).
3. ``resolve_context`` median latency for documentation actions is at most
   2x the median latency for research actions (NFR-007).

The mission spec forbids mocking ``charter._drg_helpers.load_validated_graph``
or ``doctrine.drg.query.resolve_context`` (C-007); these tests read the real
on-disk graph and call the production resolver directly.
"""

from __future__ import annotations

import statistics
import time
from pathlib import Path

import pytest
import yaml

from charter._drg_helpers import load_validated_graph
from doctrine.drg.query import resolve_context

# The 6 advancing documentation actions covered by the mission-runtime sidecar.
_DOC_ACTIONS: tuple[str, ...] = (
    "discover",
    "audit",
    "design",
    "generate",
    "validate",
    "publish",
)

# The 5 advancing research actions (used as the latency baseline in NFR-007).
_RESEARCH_ACTIONS: tuple[str, ...] = (
    "scoping",
    "methodology",
    "gathering",
    "synthesis",
    "output",
)

# Mirror the literal default of StepContractExecutionContext.resolution_depth
# (src/specify_cli/mission_step_contracts/executor.py); composition calls
# `resolve_context(graph, action_urn, depth=context.resolution_depth)`.
_COMPOSITION_RESOLUTION_DEPTH: int = 2

# Slug-form (action bundle index.yaml) -> URN-form (graph.yaml edge target).
# Per contracts/drg-shape.md "Contract: action bundle <-> DRG consistency".
_SLUG_TO_URN: dict[str, str] = {
    "001-architectural-integrity-standard": "directive:DIRECTIVE_001",
    "003-decision-documentation-requirement": "directive:DIRECTIVE_003",
    "010-specification-fidelity-requirement": "directive:DIRECTIVE_010",
    "037-living-documentation-sync": "directive:DIRECTIVE_037",
    "requirements-validation-workflow": "tactic:requirements-validation-workflow",
    "premortem-risk-identification": "tactic:premortem-risk-identification",
    "adr-drafting-workflow": "tactic:adr-drafting-workflow",
}


def _repo_root() -> Path:
    """Locate the repository root that holds ``src/doctrine/graph.yaml``."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / "src" / "doctrine" / "graph.yaml").is_file():
            return parent
    raise RuntimeError("Could not locate repo root containing src/doctrine/graph.yaml")


@pytest.mark.parametrize("action", _DOC_ACTIONS)
def test_each_documentation_action_has_drg_node_and_context(action: str) -> None:
    """FR-004 + FR-005: DRG node exists and resolve_context returns artifact_urns."""
    repo_root = _repo_root()
    graph = load_validated_graph(repo_root)
    urn = f"action:documentation/{action}"
    node = graph.get_node(urn)
    assert node is not None, f"missing DRG node: {urn}"

    ctx = resolve_context(graph, urn, depth=_COMPOSITION_RESOLUTION_DEPTH)
    assert ctx.artifact_urns, f"empty artifact_urns for {urn}; verify graph.yaml edges from this action node to directives/tactics."


@pytest.mark.parametrize("action", _DOC_ACTIONS)
def test_action_bundle_matches_drg_edges(action: str) -> None:
    """FR-006: action-bundle index.yaml directives/tactics match graph.yaml URN edges."""
    repo_root = _repo_root()
    bundle_path = repo_root / "src" / "doctrine" / "missions" / "documentation" / "actions" / action / "index.yaml"
    bundle = yaml.safe_load(bundle_path.read_text(encoding="utf-8"))
    slugs: list[str] = list(bundle.get("directives", []) or []) + list(bundle.get("tactics", []) or [])
    expected_urns = {_SLUG_TO_URN[slug] for slug in slugs}

    graph_yaml = yaml.safe_load((repo_root / "src" / "doctrine" / "graph.yaml").read_text(encoding="utf-8"))
    actual_urns = {
        edge["target"] for edge in graph_yaml.get("edges", []) if edge.get("source") == f"action:documentation/{action}" and edge.get("relation") == "scope"
    }

    assert expected_urns == actual_urns, f"bundle <-> DRG mismatch for {action}: bundle has {expected_urns}, graph has {actual_urns}"


def test_resolve_context_within_research_2x() -> None:
    """NFR-007: documentation resolve_context median <= 2x research median."""
    graph = load_validated_graph(_repo_root())

    def median_runs(actions: tuple[str, ...], mission: str) -> float:
        durations: list[float] = []
        for _ in range(5):
            for action in actions:
                t0 = time.perf_counter()
                resolve_context(
                    graph,
                    f"action:{mission}/{action}",
                    depth=_COMPOSITION_RESOLUTION_DEPTH,
                )
                durations.append(time.perf_counter() - t0)
        return statistics.median(durations)

    doc_med = median_runs(_DOC_ACTIONS, "documentation")
    research_med = median_runs(_RESEARCH_ACTIONS, "research")
    assert doc_med <= 2 * research_med, f"documentation median {doc_med:.6f}s exceeds 2x research median {research_med:.6f}s"
